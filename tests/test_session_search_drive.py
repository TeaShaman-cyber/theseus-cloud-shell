import hashlib
import importlib.util
import json
import pathlib
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "providers" / "exe-dev" / "session_search_drive.py"


def load():
    spec = importlib.util.spec_from_file_location("session_search_drive", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class FakeDrive:
    def __init__(self):
        self.files = {}
        self.next_id = 1
        self.corrupt_next_readback = False
        self.corrupt_after_update = False

    def list_by_kind(self, kind):
        return [
            {"id": file_id}
            for file_id, row in self.files.items()
            if row["kind"] == kind
        ]

    def create_bytes(self, content, *, kind):
        file_id = f"f{self.next_id}"
        self.next_id += 1
        self.files[file_id] = {"kind": kind, "content": bytes(content)}
        return file_id

    def update_bytes(self, file_id, content):
        self.files[file_id]["content"] = bytes(content)
        if self.corrupt_after_update:
            self.corrupt_after_update = False
            self.corrupt_next_readback = True

    def download_bytes(self, file_id):
        value = self.files[file_id]["content"]
        if self.corrupt_next_readback:
            self.corrupt_next_readback = False
            return value + b"x"
        return value

    def download_to_path(self, file_id, path):
        target = pathlib.Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(self.download_bytes(file_id))
        target.chmod(0o600)
        return target


class SessionSearchDriveAdapterTest(unittest.TestCase):
    def setUp(self):
        self.m = load()

    def test_current_pointer_discovery_fails_closed_on_zero_or_multiple(self):
        with self.assertRaisesRegex(ValueError, "RECOVERY_POINTER_UNAVAILABLE"):
            self.m.select_single_current_pointer([])
        with self.assertRaisesRegex(ValueError, "RECOVERY_POINTER_AMBIGUOUS"):
            self.m.select_single_current_pointer([{"id": "a"}, {"id": "b"}])
        self.assertEqual(
            self.m.select_single_current_pointer([{"id": "a"}])["id"],
            "a",
        )

    def test_receipt_publish_is_immutable_and_readback_verified(self):
        drive = FakeDrive()
        file_id = self.m.publish_immutable_receipt(drive, b"receipt-v1")
        self.assertEqual(drive.download_bytes(file_id), b"receipt-v1")
        self.assertEqual(
            drive.files[file_id]["kind"],
            self.m.RECEIPT_KIND,
        )

    def test_pointer_bootstrap_creates_one_current_pointer(self):
        drive = FakeDrive()
        self.m.publish_current_pointer(drive, b"current-v1")
        rows = drive.list_by_kind(self.m.POINTER_KIND)
        self.assertEqual(len(rows), 1)
        self.assertEqual(drive.download_bytes(rows[0]["id"]), b"current-v1")

    def test_pointer_update_replaces_content_only_after_readback(self):
        drive = FakeDrive()
        pointer_id = drive.create_bytes(b"old", kind=self.m.POINTER_KIND)
        self.m.publish_current_pointer(drive, b"new")
        self.assertEqual(drive.download_bytes(pointer_id), b"new")

    def test_pointer_readback_mismatch_restores_previous_content(self):
        drive = FakeDrive()
        pointer_id = drive.create_bytes(b"old", kind=self.m.POINTER_KIND)
        drive.corrupt_after_update = True
        with self.assertRaisesRegex(ValueError, "RECOVERY_POINTER_READBACK_MISMATCH"):
            self.m.publish_current_pointer(drive, b"new")
        self.assertEqual(drive.download_bytes(pointer_id), b"old")

    def test_fresh_runtime_recovers_only_from_current_pointer_chain(self):
        class FakeHandoff:
            @staticmethod
            def validate_locator(locator):
                if locator.get("schema") != "locator":
                    raise ValueError("bad locator")

            @staticmethod
            def load_verified_handoff(locator_path, receipt_path):
                locator = json.loads(pathlib.Path(locator_path).read_text())
                receipt = json.loads(pathlib.Path(receipt_path).read_text())
                if locator["receipt"]["drive_file_id"] != "receipt":
                    raise ValueError("bad receipt id")
                return {"locator": locator, "receipt": receipt}

            @staticmethod
            def verify_artifact_file(path, descriptor):
                payload = pathlib.Path(path).read_bytes()
                if len(payload) != descriptor["size_bytes"]:
                    raise ValueError("size")
                if hashlib.sha256(payload).hexdigest() != descriptor["sha256"]:
                    raise ValueError("digest")
                return pathlib.Path(path)

            @staticmethod
            def verify_local_recovery(**kwargs):
                pathlib.Path(kwargs["corpus_lock_out"]).write_text("{}")
                return {
                    "status": "VERIFIED",
                    "sqlite_schema_version": "session-search-corpus-v2",
                    "corpus_lock_created": True,
                }

        drive = FakeDrive()
        projection = b"sqlite-bytes"
        evidence = b"evidence-bytes"
        drive.files["projection"] = {"kind": "artifact", "content": projection}
        drive.files["evidence"] = {"kind": "artifact", "content": evidence}
        receipt = {
            "artifacts": {
                "projection_transport": {
                    "drive_file_id": "projection",
                    "sha256": hashlib.sha256(projection).hexdigest(),
                    "size_bytes": len(projection),
                    "encoding": "identity",
                },
                "accepted_evidence": {
                    "drive_file_id": "evidence",
                    "sha256": hashlib.sha256(evidence).hexdigest(),
                    "size_bytes": len(evidence),
                },
            }
        }
        drive.files["receipt"] = {
            "kind": self.m.RECEIPT_KIND,
            "content": json.dumps(receipt).encode(),
        }
        locator = {
            "schema": "locator",
            "receipt": {"drive_file_id": "receipt"},
        }
        drive.files["pointer"] = {
            "kind": self.m.POINTER_KIND,
            "content": json.dumps(locator).encode(),
        }

        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            result = self.m.recover_current(
                drive,
                FakeHandoff,
                workdir=root / "fresh",
                corpus_lock_out=root / "current-corpus.json",
            )
            self.assertEqual(result["status"], "VERIFIED")
            self.assertTrue((root / "current-corpus.json").is_file())

    def test_pointer_update_failure_does_not_delete_previous_pointer(self):
        class FailingDrive(FakeDrive):
            def update_bytes(self, file_id, content):
                raise RuntimeError("boom")

        drive = FailingDrive()
        pointer_id = drive.create_bytes(b"old", kind=self.m.POINTER_KIND)
        with self.assertRaisesRegex(RuntimeError, "boom"):
            self.m.publish_current_pointer(drive, b"new")
        self.assertEqual(drive.download_bytes(pointer_id), b"old")


if __name__ == "__main__":
    unittest.main()
