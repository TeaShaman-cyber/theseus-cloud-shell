#!/usr/bin/env python3
"""Opt-in lifecycle for newly created, disposable foreground work."""
import argparse
import errno
import json
import os
from pathlib import Path
import re
import shutil
import signal
import socket
import stat
import subprocess
import sys
import tempfile
import time


def receipt(data, status, **extra):
    print(json.dumps({**data, "status": status, **extra}, sort_keys=True),
          file=sys.stderr, flush=True)


def same_directory(path, original):
    try:
        current = path.lstat()
    except OSError:
        return False
    return (stat.S_ISDIR(current.st_mode) and
            (current.st_dev, current.st_ino) == (original.st_dev, original.st_ino))


def retained_location(root, root_identity, original):
    # Inspect direct children of the owned root only; never follow a symlink
    # or guess where a command moved evidence outside the managed boundary.
    if not same_directory(root, root_identity):
        return None
    try:
        for candidate in root.iterdir():
            if same_directory(candidate, original):
                return str(candidate)
    except OSError:
        pass
    return None


def has_terminal():
    if any(os.isatty(fd) for fd in (0, 1, 2)):
        return True
    try:
        fd = os.open("/dev/tty", os.O_RDONLY | os.O_NOCTTY)
    except OSError as exc:
        if exc.errno in (errno.ENXIO, errno.ENODEV, errno.ENOENT):
            return False
        raise
    os.close(fd)
    return True


def update_relocated_manifest(path, root, root_identity, original, data):
    # Only update a verified direct child with no mounted descendants.
    if path is None:
        return False
    target = Path(path)
    if (target.parent != root or not same_directory(root, root_identity)
            or not same_directory(target, original) or has_mount(target)):
        return False
    fd = os.open(target, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    temporary = ".theseus-scratch.relocated.tmp"
    created = False
    try:
        st = os.fstat(fd)
        if (st.st_dev, st.st_ino) != (original.st_dev, original.st_ino):
            return False
        handle = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                         0o600, dir_fd=fd)
        created = True
        with os.fdopen(handle, "w") as out:
            json.dump({**data, "path": path, "original_path": data["path"]}, out, sort_keys=True)
            out.write("\n")
        os.replace(temporary, ".theseus-scratch.json", src_dir_fd=fd, dst_dir_fd=fd)
        created = False
        return True
    finally:
        if created:
            os.unlink(temporary, dir_fd=fd)
        os.close(fd)


def group_quiet(pid):
    try:
        os.killpg(pid, 0)
    except ProcessLookupError:
        return True
    except PermissionError:
        return False
    # Linux can retain orphaned zombie group members indefinitely. They
    # cannot access files; unreadable process state is not proof of quiescence.
    try:
        for proc in Path("/proc").iterdir():
            if not proc.name.isdecimal():
                continue
            try:
                fields = proc.joinpath("stat").read_text().rsplit(")", 1)[1].split()
            except FileNotFoundError:
                continue
            if int(fields[2]) == pid and fields[0] not in ("Z", "X"):
                return False
    except (OSError, ValueError, IndexError):
        return False
    return True


def has_mount(path):
    for line in Path("/proc/self/mountinfo").read_text().splitlines():
        mount = re.sub(r"\\([0-7]{3})", lambda m: chr(int(m[1], 8)), line.split()[4])
        if mount == str(path) or mount.startswith(str(path) + "/"):
            return True
    return False


# The child cannot execute the requested command before its parent commits the
# launch by writing one byte. EOF (including wrapper death) cancels the launch.
_GATED_EXEC = """
import os, signal, sys
fd = int(sys.argv[1])
try:
    allowed = os.read(fd, 1)
finally:
    os.close(fd)
if allowed != b'1':
    sys.exit(1)
for name in ('SIGPIPE', 'SIGXFZ', 'SIGXFSZ'):
    if hasattr(signal, name):
        signal.signal(getattr(signal, name), signal.SIG_DFL)
try:
    os.execvp(sys.argv[2], sys.argv[2:])
except OSError as exc:
    print('managed command exec failed: ' + type(exc).__name__, file=sys.stderr)
    sys.exit(1)
"""


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--owner", required=True)
    parser.add_argument("--source", required=True)
    parser.add_argument("--purpose", required=True)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command
    if command[:1] == ["--"]:
        command = command[1:]
    if not command or not re.fullmatch(r"[\w.-]+/[\w.-]+#[1-9][0-9]*", args.owner):
        parser.error("require owner/repo#issue and a foreground command")
    if not args.source.strip() or not args.purpose.strip():
        parser.error("source and purpose must be nonempty")
    try:
        terminal = has_terminal()
    except OSError:
        parser.error("cannot establish non-interactive execution")
    if terminal:
        parser.error("managed scratch requires non-interactive execution without a terminal")
    root = Path.home() / ".cache" / "theseus-managed-scratch"
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    info = root.lstat()
    if (root.resolve() != root or not stat.S_ISDIR(info.st_mode)
            or info.st_uid != os.getuid() or info.st_mode & 0o077):
        parser.error("scratch root must be a private, owned, non-symlink directory")
    path = Path(tempfile.mkdtemp(prefix="run-", dir=root))
    identity = path.lstat()
    data = {"path": str(path), "owner": args.owner, "source": args.source,
            "purpose": args.purpose, "host": socket.gethostname(), "runtime": sys.platform,
            "class": "PENDING_CLEANUP",
            "evidence": {"device": identity.st_dev, "inode": identity.st_ino,
                         "root_device": info.st_dev, "root_inode": info.st_ino},
            "retention": "Owner verifies required output/recovery and explicitly dispositions retained scratch.",
            "cleanup": "Verify exact directory identity, no active consumers or mounts, recovery and authorized scope; remove only this directory and independently verify absence."}
    setup_failure = "start_receipt_failed"
    try:
        receipt(data, "PENDING_CLEANUP")
        setup_failure = "manifest_write_failed"
        (path / ".theseus-scratch.json").write_text(json.dumps(data, sort_keys=True) + "\n")
    except OSError:
        try:
            if same_directory(root, info) and same_directory(path, identity) and not has_mount(path) and shutil.rmtree.avoids_symlink_attacks:
                shutil.rmtree(path)
        except OSError:
            pass
        try:
            receipt(data, "PENDING_CLEANUP" if os.path.lexists(path) else "REMOVED",
                    reason=setup_failure)
        except OSError:
            # The reporting sink itself may be unavailable; do not launch.
            pass
        return 1
    try:
        interrupted = []
        process = None
        suspended = False

        termination = (signal.SIGINT, signal.SIGTERM, signal.SIGHUP, signal.SIGQUIT)

        def send_group(signum):
            if process is not None:
                try:
                    os.killpg(process.pid, signum)
                except ProcessLookupError:
                    pass

        def relay(signum, _frame):
            interrupted.append(signum)
            send_group(signum)
            # Termination must also reach a previously suspended child.
            send_group(signal.SIGCONT)

        def suspend(_signum, _frame):
            nonlocal suspended
            if not interrupted:
                suspended = True
                send_group(signal.SIGSTOP)

        def resume(_signum, _frame):
            nonlocal suspended
            suspended = False
            send_group(signal.SIGCONT)

        handlers = {sig: relay for sig in termination}
        handlers.update({signal.SIGTSTP: suspend, signal.SIGCONT: resume})
        previous = {sig: signal.signal(sig, handler) for sig, handler in handlers.items()}
        try:
            if interrupted:
                receipt(data, "PENDING_CLEANUP", reason="interrupted_before_launch", signal=interrupted[0])
                return 128 + interrupted[0]
            read_fd, write_fd = os.pipe()
            try:
                process = subprocess.Popen(
                    [sys.executable, "-I", "-S", "-c", _GATED_EXEC, str(read_fd), *command],
                    cwd=path, start_new_session=True, pass_fds=(read_fd,))
                if suspended and not interrupted:
                    send_group(signal.SIGSTOP)
                # The launch decision is made with termination delivery masked.
                # A signal already recorded or pending cancels authorization.
                # Signals after this decision are ordinary running-child termination.
                mask = signal.pthread_sigmask(signal.SIG_BLOCK, termination)
                try:
                    if not interrupted and not signal.sigpending().intersection(termination):
                        os.write(write_fd, b"1")
                finally:
                    signal.pthread_sigmask(signal.SIG_SETMASK, mask)
            finally:
                os.close(read_fd)
                os.close(write_fd)
            if interrupted:
                send_group(interrupted[0])
                send_group(signal.SIGCONT)
            while not interrupted:
                try:
                    process.wait(timeout=0.2)
                    break
                except subprocess.TimeoutExpired:
                    continue
            if interrupted:
                # Bound shutdown even when the command ignores termination.
                deadline = time.monotonic() + 2
                while not group_quiet(process.pid) and time.monotonic() < deadline:
                    process.poll()
                    time.sleep(0.05)
                if not group_quiet(process.pid):
                    try:
                        os.killpg(process.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                process.wait()
                receipt(data, "PENDING_CLEANUP", reason="interrupted", signal=interrupted[0])
                return 128 + interrupted[0]
            code = process.returncode
        finally:
            for sig, handler in previous.items():
                signal.signal(sig, handler)
        if code != 0:
            receipt(data, "PENDING_CLEANUP", reason="command_failed", exit_code=code)
            return code if code > 0 else 128 - code
        if not group_quiet(process.pid):
            receipt(data, "PENDING_CLEANUP", reason="process_group_active")
            return 1
        if not same_directory(root, info) or not same_directory(path, identity) or has_mount(path):
            retained = retained_location(root, info, identity)
            try:
                updated = update_relocated_manifest(retained, root, info, identity, data)
            except OSError:
                updated = False
            receipt(data, "PENDING_CLEANUP", reason="directory_identity_or_mount_changed",
                    retained_path=retained, manifest_updated=updated,
                    retained_device=identity.st_dev, retained_inode=identity.st_ino)
            return 1
        if not shutil.rmtree.avoids_symlink_attacks:
            receipt(data, "PENDING_CLEANUP", reason="safe_rmtree_unavailable")
            return 1
        shutil.rmtree(path)
        if os.path.lexists(path):
            receipt(data, "PENDING_CLEANUP", reason="absence_not_verified")
            return 1
    except (OSError, ValueError) as exc:
        receipt(data, "PENDING_CLEANUP", reason=type(exc).__name__)
        return 1
    receipt(data, "REMOVED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
