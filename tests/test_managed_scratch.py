import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "providers/exe-dev/managed_scratch.py"

class ManagedScratchTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.sibling = self.root / "untouched"
        self.sibling.write_text("keep")

    def invoke(self, code):
        env = {**os.environ, "HOME": str(self.root)}
        result = subprocess.run([sys.executable, str(SCRIPT), "--owner", "example/repo#14",
                                 "--source", "fixture", "--purpose", "test", "--",
                                 sys.executable, "-c", code], env=env, text=True,
                                capture_output=True, timeout=10)
        return result

    def test_success_removes_only_owned_scratch(self):
        result = self.invoke("from pathlib import Path; Path('data').write_text('test')")
        self.assertEqual(result.returncode, 0, result.stderr)
        receipt = json.loads(result.stderr.splitlines()[-1])
        self.assertEqual(receipt["status"], "REMOVED")
        self.assertFalse(Path(receipt["path"]).exists())
        self.assertEqual(self.sibling.read_text(), "keep")

    def test_failure_retains_data_and_owner(self):
        result = self.invoke("from pathlib import Path; Path('evidence').write_text('failure'); raise SystemExit(7)")
        self.assertEqual(result.returncode, 7, result.stderr)
        receipt = json.loads(result.stderr.splitlines()[-1])
        self.assertEqual(receipt["status"], "PENDING_CLEANUP")
        directory = Path(receipt["path"])
        self.assertEqual((directory / "evidence").read_text(), "failure")
        self.assertEqual(receipt["owner"], "example/repo#14")

    def test_symlink_in_scratch_does_not_delete_external_file(self):
        result = self.invoke("import os; from pathlib import Path; Path('link').symlink_to(Path(os.environ['HOME'])/'untouched')")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.sibling.read_text(), "keep")

    def test_lingering_foreground_group_retains_scratch(self):
        result = self.invoke("import subprocess,sys; subprocess.Popen([sys.executable,'-c','import time; time.sleep(2)'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)")
        self.assertNotEqual(result.returncode, 0)
        receipt = json.loads(result.stderr.splitlines()[-1])
        self.assertEqual(receipt["status"], "PENDING_CLEANUP")
        self.assertTrue(Path(receipt["path"]).is_dir())

    def test_replaced_directory_is_not_deleted(self):
        result = self.invoke("import os; from pathlib import Path; p=Path.cwd(); p.rename(p.with_name(p.name+'-old')); p.mkdir(); (p/'new').write_text('keep')")
        self.assertNotEqual(result.returncode, 0)
        receipt = json.loads(result.stderr.splitlines()[-1])
        self.assertEqual(receipt["status"], "PENDING_CLEANUP")
        self.assertEqual((Path(receipt["path"])/"new").read_text(), "keep")
        retained = Path(receipt["retained_path"])
        self.assertEqual(retained, Path(receipt["path"]).with_name(Path(receipt["path"]).name + "-old"))
        manifest = json.loads((retained / ".theseus-scratch.json").read_text())
        self.assertEqual(manifest["path"], str(retained))
        self.assertEqual(manifest["original_path"], receipt["path"])

    def test_sigterm_and_sigint_reach_child_and_retain_scratch(self):
        import signal
        import time

        for sig in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP, signal.SIGQUIT):
            with self.subTest(signal=sig):
                marker = self.root / "ready"
                marker.unlink(missing_ok=True)
                code = ("import os,signal,time; from pathlib import Path; "
                        "signal.signal(signal.SIGTERM,lambda *a:exit(23)); "
                        "signal.signal(signal.SIGINT,lambda *a:exit(23)); signal.signal(signal.SIGHUP,lambda *a:exit(23)); signal.signal(signal.SIGQUIT,lambda *a:exit(23)); "
                        "Path(os.environ['HOME'],'ready.tmp').write_text(str(os.getpid())); Path(os.environ['HOME'],'ready.tmp').rename(Path(os.environ['HOME'],'ready')); "
                        "time.sleep(30)")
                env = {**os.environ, "HOME": str(self.root)}
                with subprocess.Popen([sys.executable, str(SCRIPT), "--owner", "example/repo#14",
                                       "--source", "fixture", "--purpose", "signal test", "--",
                                       sys.executable, "-c", code], env=env,
                                      stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) as process:
                    deadline = time.monotonic() + 5
                    child = None
                    try:
                        while not marker.exists() and time.monotonic() < deadline:
                            time.sleep(.01)
                        child = int(marker.read_text())
                        process.send_signal(sig)
                        _, stderr = process.communicate(timeout=3)
                        self.assertEqual(process.returncode, 128 + sig)
                        with self.assertRaises(ProcessLookupError):
                            os.kill(child, 0)
                        r = json.loads(stderr.splitlines()[-1])
                        self.assertEqual(r["status"], "PENDING_CLEANUP")
                        self.assertTrue(Path(r["path"]).exists())
                    finally:
                        if child is not None:
                            try:
                                os.kill(child, signal.SIGKILL)
                            except ProcessLookupError:
                                pass
                        if process.poll() is None:
                            process.kill()
                            process.wait()

    def test_group_with_only_zombies_is_quiet(self):
        import importlib.util
        from unittest.mock import patch, Mock
        spec = importlib.util.spec_from_file_location("managed_scratch", SCRIPT)
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        proc = Mock()
        proc.name = "123"
        proc.joinpath.return_value.read_text.return_value = "123 (fixture) Z 1 456 456 0"
        with patch.object(m.os, "killpg"), patch.object(m.Path, "iterdir", return_value=iter([proc])):
            self.assertTrue(m.group_quiet(456))

    def test_manifest_failure_keeps_classified_receipt(self):
        import importlib.util
        import contextlib
        import io
        from unittest.mock import patch
        spec = importlib.util.spec_from_file_location("managed_scratch", SCRIPT)
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        err = io.StringIO()
        with patch.object(m.Path, "home", return_value=self.root), patch.object(m.Path, "write_text", side_effect=OSError("disk full")), patch.object(m.sys, "argv", [str(SCRIPT),"--owner","example/repo#14","--source","fixture","--purpose","test","--","true"]), contextlib.redirect_stderr(err):
            self.assertNotEqual(m.main(), 0)
        r=json.loads(err.getvalue().splitlines()[-1])
        self.assertEqual(r["owner"],"example/repo#14")
        self.assertFalse(Path(r["path"]).exists())

    def test_unwritable_start_receipt_does_not_leave_unclassified_scratch(self):
        with open("/dev/full", "w") as sink:
            result = subprocess.run([sys.executable, str(SCRIPT), "--owner", "example/repo#14",
                                     "--source", "fixture", "--purpose", "test", "--",
                                     "true"], env={**os.environ, "HOME": str(self.root)},
                                    stdout=subprocess.DEVNULL, stderr=sink, timeout=5)
        self.assertNotEqual(result.returncode, 0)
        scratch = self.root / ".cache" / "theseus-managed-scratch"
        self.assertEqual(list(scratch.iterdir()), [])

    def test_retained_manifest_has_standalone_lifecycle(self):
        result = self.invoke("raise SystemExit(7)")
        r = json.loads(result.stderr.splitlines()[-1])
        manifest = json.loads((Path(r["path"]) / ".theseus-scratch.json").read_text())
        for field in ("host", "runtime", "class", "retention", "cleanup", "evidence"):
            self.assertTrue(manifest[field], field)
        self.assertEqual(manifest["class"], "PENDING_CLEANUP")

    def test_termination_before_spawn_and_during_spawn_never_executes(self):
        import contextlib
        import importlib.util
        import io
        import signal
        from unittest.mock import patch
        spec = importlib.util.spec_from_file_location("managed_scratch", SCRIPT)
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        original_popen = subprocess.Popen
        original_signal = signal.signal
        for phase in ("before", "during"):
            with self.subTest(phase=phase):
                marker = self.root / ("ran-" + phase)
                argv = [str(SCRIPT), "--owner", "example/repo#14", "--source", "fixture",
                        "--purpose", "test", "--", sys.executable, "-c",
                        "from pathlib import Path; Path(" + repr(str(marker)) + ").touch()"]
                def register(sig, handler):
                    result = original_signal(sig, handler)
                    if phase == "before" and sig == signal.SIGQUIT and callable(handler):
                        signal.getsignal(signal.SIGTERM)(signal.SIGTERM, None)
                    return result
                def spawn(*args, **kwargs):
                    child = original_popen(*args, **kwargs)
                    if phase == "during":
                        # Let a nongated child execute before reporting the
                        # termination to the wrapper, without racing the OS.
                        try:
                            child.wait(timeout=.15)
                        except subprocess.TimeoutExpired:
                            pass
                        signal.getsignal(signal.SIGTERM)(signal.SIGTERM, None)
                    return child
                err = io.StringIO()
                with patch.object(m.Path, "home", return_value=self.root), patch.object(m.sys, "argv", argv), patch.object(m.signal, "signal", side_effect=register), patch.object(m.subprocess, "Popen", side_effect=spawn) as popen, contextlib.redirect_stderr(err):
                    self.assertEqual(m.main(), 128 + signal.SIGTERM)
                if phase == "before":
                    popen.assert_not_called()
                self.assertFalse(marker.exists())

    def test_job_control_stops_and_resumes_child_group(self):
        import signal
        import time
        marker = self.root / "job-ready"
        code = ("import os,time; from pathlib import Path; p=Path(os.environ['HOME'],'job-ready'); "
                "p.write_text(str(os.getpid())); time.sleep(30)")
        with subprocess.Popen([sys.executable, str(SCRIPT), "--owner", "example/repo#14",
                               "--source", "fixture", "--purpose", "job control", "--",
                               sys.executable, "-c", code], env={**os.environ, "HOME": str(self.root)},
                              stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True,
                              start_new_session=True) as proc:
            child = None
            def state(pid):
                return Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()[0]
            def wait_for(predicate):
                end = time.monotonic() + 2
                while time.monotonic() < end:
                    if predicate():
                        return True
                    time.sleep(.02)
                return False
            try:
                self.assertTrue(wait_for(lambda: marker.exists() and marker.stat().st_size > 0))
                child = int(marker.read_text())
                proc.send_signal(signal.SIGTSTP)
                self.assertTrue(wait_for(lambda: state(proc.pid) != "T" and state(child) == "T"))
                proc.send_signal(signal.SIGCONT)
                self.assertTrue(wait_for(lambda: state(proc.pid) != "T" and state(child) != "T"))
                proc.send_signal(signal.SIGTSTP)
                self.assertTrue(wait_for(lambda: state(child) == "T"))
                proc.send_signal(signal.SIGTERM)
                proc.communicate(timeout=4)
                self.assertEqual(proc.returncode, 128 + signal.SIGTERM)
            finally:
                if proc.poll() is None:
                    proc.send_signal(signal.SIGCONT)
                    proc.kill()
                    proc.wait()
                if child is not None:
                    try:
                        os.kill(child, signal.SIGKILL)
                    except ProcessLookupError:
                        pass

    def test_interactive_terminal_is_rejected_before_allocation(self):
        import pty
        import select
        import time
        import signal
        pid, fd = pty.fork()
        if pid == 0:
            os.execve(sys.executable, [sys.executable, str(SCRIPT), "--owner", "example/repo#14",
                       "--source", "fixture", "--purpose", "test", "--", "true"],
                      {**os.environ, "HOME": str(self.root)})
        output = bytearray()
        deadline = time.monotonic() + 5
        status = None
        try:
            while time.monotonic() < deadline:
                if select.select([fd], [], [], .05)[0]:
                    try:
                        output.extend(os.read(fd, 4096))
                    except OSError:
                        pass
                done, value = os.waitpid(pid, os.WNOHANG)
                if done:
                    status = value
                    break
            self.assertIsNotNone(status)
            self.assertEqual(os.waitstatus_to_exitcode(status), 2, output.decode(errors="replace"))
            self.assertIn(b"non-interactive", output)
            self.assertFalse((self.root / ".cache" / "theseus-managed-scratch").exists())
        finally:
            os.close(fd)
            if status is None:
                os.kill(pid, signal.SIGKILL)
                os.waitpid(pid, 0)
