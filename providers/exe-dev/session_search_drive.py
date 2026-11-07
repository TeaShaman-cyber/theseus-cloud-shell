#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import urllib.parse
import urllib.request
import uuid

PROPERTY_KEY = "theseus_recovery_kind"
POINTER_KIND = "session-search-current-v1"
RECEIPT_KIND = "session-search-receipt-v1"
DRIVE_API = "https://www.googleapis.com/drive/v3"
DRIVE_UPLOAD_API = "https://www.googleapis.com/upload/drive/v3"


def select_single_current_pointer(rows: list[dict]) -> dict:
    if not rows:
        raise ValueError("RECOVERY_POINTER_UNAVAILABLE")
    if len(rows) != 1:
        raise ValueError("RECOVERY_POINTER_AMBIGUOUS")
    row = rows[0]
    if not isinstance(row, dict) or not row.get("id"):
        raise ValueError("RECOVERY_POINTER_INVALID")
    return row


def publish_immutable_receipt(drive, content: bytes) -> str:
    file_id = drive.create_bytes(content, kind=RECEIPT_KIND)
    if drive.download_bytes(file_id) != content:
        raise ValueError("RECOVERY_RECEIPT_READBACK_MISMATCH")
    return file_id


def publish_current_pointer(drive, content: bytes) -> str:
    rows = drive.list_by_kind(POINTER_KIND)
    if not rows:
        file_id = drive.create_bytes(content, kind=POINTER_KIND)
        if drive.download_bytes(file_id) != content:
            raise ValueError("RECOVERY_POINTER_READBACK_MISMATCH")
        return file_id

    current = select_single_current_pointer(rows)
    file_id = current["id"]
    previous = drive.download_bytes(file_id)
    try:
        drive.update_bytes(file_id, content)
    except Exception:
        # The provider call failed before confirmed completion. Read back before
        # deciding whether restoration is necessary.
        try:
            observed = drive.download_bytes(file_id)
        except Exception:
            raise
        if observed != previous:
            drive.update_bytes(file_id, previous)
            if drive.download_bytes(file_id) != previous:
                raise ValueError("RECOVERY_POINTER_RESTORE_FAILED")
        raise

    observed = drive.download_bytes(file_id)
    if observed != content:
        drive.update_bytes(file_id, previous)
        if drive.download_bytes(file_id) != previous:
            raise ValueError("RECOVERY_POINTER_RESTORE_FAILED")
        raise ValueError("RECOVERY_POINTER_READBACK_MISMATCH")
    return file_id


class GoogleDriveClient:
    def __init__(self, token_command: list[str] | None = None):
        if token_command is None:
            helper = shutil.which("gcloud-keyring")
            if helper is None:
                candidate = pathlib.Path.home() / ".local" / "bin" / "gcloud-keyring"
                if not candidate.is_file():
                    raise RuntimeError("GCLOUD_KEYRING_HELPER_MISSING")
                helper = str(candidate)
            token_command = [helper, "auth", "print-access-token"]
        self.token_command = token_command

    def _token(self) -> str:
        result = subprocess.run(
            self.token_command,
            capture_output=True,
            text=True,
            check=True,
        )
        token = result.stdout.strip()
        if not token:
            raise RuntimeError("DRIVE_TOKEN_EMPTY")
        return token

    def _request(
        self,
        request: urllib.request.Request,
        *,
        expect_json: bool = False,
    ):
        request.add_header("Authorization", f"Bearer {self._token()}")
        with urllib.request.urlopen(request, timeout=60) as response:
            body = response.read()
        if expect_json:
            return json.loads(body.decode("utf-8"))
        return body

    def list_by_kind(self, kind: str) -> list[dict]:
        query = (
            f"properties has {{ key='{PROPERTY_KEY}' and value='{kind}' }} "
            "and trashed = false"
        )
        params = urllib.parse.urlencode(
            {
                "q": query,
                "spaces": "drive",
                "pageSize": 10,
                "fields": "files(id,size,properties)",
            }
        )
        request = urllib.request.Request(f"{DRIVE_API}/files?{params}", method="GET")
        payload = self._request(request, expect_json=True)
        return list(payload.get("files") or [])

    def download_bytes(self, file_id: str) -> bytes:
        encoded = urllib.parse.quote(file_id, safe="")
        request = urllib.request.Request(
            f"{DRIVE_API}/files/{encoded}?alt=media",
            method="GET",
        )
        return self._request(request)

    def download_to_path(self, file_id: str, path: pathlib.Path) -> pathlib.Path:
        target = pathlib.Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        token = self._token()
        encoded = urllib.parse.quote(file_id, safe="")
        request = urllib.request.Request(
            f"{DRIVE_API}/files/{encoded}?alt=media",
            method="GET",
            headers={"Authorization": f"Bearer {token}"},
        )
        fd, tmp_name = tempfile.mkstemp(
            prefix=f".{target.name}.",
            suffix=".part",
            dir=target.parent,
        )
        os.close(fd)
        try:
            with urllib.request.urlopen(request, timeout=120) as response, open(
                tmp_name, "wb"
            ) as handle:
                shutil.copyfileobj(response, handle, length=1024 * 1024)
            os.chmod(tmp_name, 0o600)
            os.replace(tmp_name, target)
        except Exception:
            try:
                os.unlink(tmp_name)
            except FileNotFoundError:
                pass
            raise
        return target

    def _multipart_body(self, content: bytes, *, kind: str) -> tuple[bytes, str]:
        boundary = f"theseus-{uuid.uuid4().hex}"
        metadata = json.dumps(
            {
                "name": f"theseus-recovery-{uuid.uuid4().hex}.json",
                "mimeType": "application/json",
                "properties": {PROPERTY_KEY: kind},
            },
            separators=(",", ":"),
        ).encode("utf-8")
        body = (
            f"--{boundary}\r\n"
            "Content-Type: application/json; charset=UTF-8\r\n\r\n"
        ).encode() + metadata + (
            f"\r\n--{boundary}\r\n"
            "Content-Type: application/json\r\n\r\n"
        ).encode() + content + f"\r\n--{boundary}--\r\n".encode()
        return body, boundary

    def create_bytes(self, content: bytes, *, kind: str) -> str:
        body, boundary = self._multipart_body(content, kind=kind)
        request = urllib.request.Request(
            f"{DRIVE_UPLOAD_API}/files?uploadType=multipart&fields=id",
            data=body,
            method="POST",
            headers={"Content-Type": f"multipart/related; boundary={boundary}"},
        )
        payload = self._request(request, expect_json=True)
        file_id = str(payload.get("id") or "")
        if not file_id:
            raise RuntimeError("DRIVE_CREATE_ID_MISSING")
        return file_id

    def update_bytes(self, file_id: str, content: bytes) -> None:
        encoded = urllib.parse.quote(file_id, safe="")
        request = urllib.request.Request(
            f"{DRIVE_UPLOAD_API}/files/{encoded}?uploadType=media",
            data=content,
            method="PATCH",
            headers={"Content-Type": "application/json"},
        )
        self._request(request)




def _write_private_bytes(path: pathlib.Path, content: bytes) -> pathlib.Path:
    target = pathlib.Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(
        prefix=f".{target.name}.",
        suffix=".tmp",
        dir=target.parent,
    )
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(tmp_name, 0o600)
        os.replace(tmp_name, target)
    except Exception:
        try:
            os.unlink(tmp_name)
        except FileNotFoundError:
            pass
        raise
    return target


def _load_handoff_module(session_search_repo: pathlib.Path):
    repo = pathlib.Path(session_search_repo).expanduser().resolve()
    if not (repo / "session_search" / "recovery_handoff.py").is_file():
        raise ValueError("SESSION_SEARCH_RECOVERY_SOURCE_MISSING")
    sys.path.insert(0, str(repo))
    try:
        from session_search import recovery_handoff
    except Exception:
        sys.path.pop(0)
        raise
    return recovery_handoff


def decode_projection(
    transport_path: pathlib.Path,
    encoding: str,
    output_path: pathlib.Path,
) -> pathlib.Path:
    source = pathlib.Path(transport_path)
    target = pathlib.Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(
        prefix=f".{target.name}.",
        suffix=".decode",
        dir=target.parent,
    )
    os.close(fd)
    try:
        if encoding == "identity":
            shutil.copyfile(source, tmp_name)
        elif encoding == "zstd":
            with open(tmp_name, "wb") as handle:
                subprocess.run(
                    ["zstd", "-d", "-c", str(source)],
                    stdout=handle,
                    stderr=subprocess.PIPE,
                    check=True,
                )
        else:
            raise ValueError("RECOVERY_PROJECTION_ENCODING_UNSUPPORTED")
        os.chmod(tmp_name, 0o600)
        os.replace(tmp_name, target)
    except Exception:
        try:
            os.unlink(tmp_name)
        except FileNotFoundError:
            pass
        raise
    return target


def recover_current(
    drive,
    handoff,
    *,
    workdir: pathlib.Path,
    corpus_lock_out: pathlib.Path,
) -> dict:
    root = pathlib.Path(workdir)
    root.mkdir(parents=True, exist_ok=True)
    os.chmod(root, 0o700)

    pointer = select_single_current_pointer(drive.list_by_kind(POINTER_KIND))
    locator_path = _write_private_bytes(
        root / "current-locator.json",
        drive.download_bytes(pointer["id"]),
    )
    try:
        locator = json.loads(locator_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError("RECOVERY_POINTER_INVALID_JSON") from exc
    handoff.validate_locator(locator)

    receipt_id = locator["receipt"]["drive_file_id"]
    receipt_path = _write_private_bytes(
        root / "accepted-receipt.json",
        drive.download_bytes(receipt_id),
    )
    verified = handoff.load_verified_handoff(locator_path, receipt_path)
    receipt = verified["receipt"]
    artifacts = receipt["artifacts"]

    projection_transport = drive.download_to_path(
        artifacts["projection_transport"]["drive_file_id"],
        root / "projection.transport",
    )
    evidence = drive.download_to_path(
        artifacts["accepted_evidence"]["drive_file_id"],
        root / "accepted-evidence.archive",
    )
    handoff.verify_artifact_file(
        projection_transport,
        artifacts["projection_transport"],
    )
    handoff.verify_artifact_file(
        evidence,
        artifacts["accepted_evidence"],
    )
    projection_db = decode_projection(
        projection_transport,
        artifacts["projection_transport"]["encoding"],
        root / "corpus.sqlite3",
    )
    result = handoff.verify_local_recovery(
        locator_path=locator_path,
        receipt_path=receipt_path,
        projection_transport_path=projection_transport,
        evidence_path=evidence,
        projection_db_path=projection_db,
        corpus_lock_out=corpus_lock_out,
    )
    return {
        "status": result["status"],
        "sqlite_schema_version": result["sqlite_schema_version"],
        "corpus_lock_created": result["corpus_lock_created"],
    }


def publish_from_spec(
    drive,
    handoff,
    *,
    spec: dict,
    workdir: pathlib.Path,
    probe_lock_out: pathlib.Path,
) -> dict:
    root = pathlib.Path(workdir)
    root.mkdir(parents=True, exist_ok=True)
    os.chmod(root, 0o700)

    receipt = handoff.build_receipt(
        projection_transport_path=pathlib.Path(spec["projection_transport_path"]),
        projection_drive_file_id=spec["projection_drive_file_id"],
        projection_db_path=pathlib.Path(spec["projection_db_path"]),
        evidence_path=pathlib.Path(spec["evidence_path"]),
        evidence_drive_file_id=spec["evidence_drive_file_id"],
        source_commit=spec["source_commit"],
        accepted_set_sha256=spec["accepted_set_sha256"],
        verification=spec["verification"],
        source_watermark=spec.get("source_watermark"),
        projection_encoding=spec.get("projection_encoding", "zstd"),
    )
    receipt_path = handoff.write_private_json(root / "accepted-receipt.json", receipt)

    # Re-read the already uploaded transport artifacts before publishing recovery metadata.
    projection_readback = drive.download_to_path(
        receipt["artifacts"]["projection_transport"]["drive_file_id"],
        root / "publish-projection.readback",
    )
    evidence_readback = drive.download_to_path(
        receipt["artifacts"]["accepted_evidence"]["drive_file_id"],
        root / "publish-evidence.readback",
    )
    handoff.verify_artifact_file(
        projection_readback,
        receipt["artifacts"]["projection_transport"],
    )
    handoff.verify_artifact_file(
        evidence_readback,
        receipt["artifacts"]["accepted_evidence"],
    )

    receipt_id = publish_immutable_receipt(drive, receipt_path.read_bytes())
    locator = handoff.build_locator(
        receipt_path,
        receipt_drive_file_id=receipt_id,
    )
    locator_path = handoff.write_private_json(root / "current-locator.json", locator)
    publish_current_pointer(drive, locator_path.read_bytes())

    # Acceptance is not complete until the normal recovery route can start from Drive
    # and recreate a private local corpus lock.
    probe = recover_current(
        drive,
        handoff,
        workdir=root / "fresh-runtime-probe",
        corpus_lock_out=probe_lock_out,
    )
    return {
        "status": "PUBLISHED",
        "receipt_readback": True,
        "pointer_readback": True,
        "fresh_runtime_probe": probe["status"],
        "corpus_lock_created": probe["corpus_lock_created"],
    }


def _read_private_spec(path: pathlib.Path) -> dict:
    try:
        payload = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError("RECOVERY_PUBLISH_SPEC_INVALID") from exc
    if not isinstance(payload, dict):
        raise ValueError("RECOVERY_PUBLISH_SPEC_INVALID")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Publish or recover the private Session Search accepted-corpus handoff through Google Drive."
    )
    parser.add_argument("--session-search-repo", type=pathlib.Path, required=True)
    sub = parser.add_subparsers(dest="command", required=True)

    publish = sub.add_parser("publish")
    publish.add_argument("--spec", type=pathlib.Path, required=True)
    publish.add_argument("--workdir", type=pathlib.Path, required=True)
    publish.add_argument("--probe-lock-out", type=pathlib.Path, required=True)

    recover = sub.add_parser("recover")
    recover.add_argument("--workdir", type=pathlib.Path, required=True)
    recover.add_argument("--corpus-lock-out", type=pathlib.Path, required=True)

    args = parser.parse_args()
    handoff = _load_handoff_module(args.session_search_repo)
    drive = GoogleDriveClient()
    if args.command == "publish":
        result = publish_from_spec(
            drive,
            handoff,
            spec=_read_private_spec(args.spec),
            workdir=args.workdir,
            probe_lock_out=args.probe_lock_out,
        )
    else:
        result = recover_current(
            drive,
            handoff,
            workdir=args.workdir,
            corpus_lock_out=args.corpus_lock_out,
        )
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
