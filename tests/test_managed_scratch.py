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
