#!/usr/bin/env python3
"""Opt-in lifecycle for newly created, disposable foreground work."""
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import signal
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
    root = Path.home() / ".cache" / "theseus-managed-scratch"
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    info = root.lstat()
    if (root.resolve() != root or not stat.S_ISDIR(info.st_mode)
            or info.st_uid != os.getuid() or info.st_mode & 0o077):
        parser.error("scratch root must be a private, owned, non-symlink directory")
    path = Path(tempfile.mkdtemp(prefix="run-", dir=root))
    identity = path.lstat()
    data = {"path": str(path), "owner": args.owner, "source": args.source,
            "purpose": args.purpose}
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

        def relay(signum, _frame):
            interrupted.append(signum)
            if process is not None:
                try:
                    os.killpg(process.pid, signum)
                except ProcessLookupError:
                    pass

        previous = {sig: signal.signal(sig, relay) for sig in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP, signal.SIGQUIT)}
        try:
            process = subprocess.Popen(command, cwd=path, start_new_session=True)
            if interrupted:
                relay(interrupted[0], None)
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
            receipt(data, "PENDING_CLEANUP", reason="directory_identity_or_mount_changed",
                    retained_path=retained_location(root, info, identity),
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
