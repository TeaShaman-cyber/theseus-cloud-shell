"""Verify retained synthetic experiment receipts; no network or inference."""
import hashlib
import json
from pathlib import Path

root = Path(__file__).resolve().parent
manifest = json.loads((root / "manifest.json").read_text())
for path, entry in manifest["files"].items():
    assert hashlib.sha256((root / path).read_bytes()).hexdigest() == entry["sha256"], path
def obs(name):
    return json.loads((root / "observations" / (name + ".json")).read_text())
for name in ("mpt-release", "mpt-head", "brain", "brain-stream", "llm-bounded", "aichat"):
    assert all(len(row["requests"]) == len(row["case"]) for row in obs(name)), name
assert all(len(row["requests"]) == 3 for row in obs("llm") if row["case"] in (["rate"], ["server"]))
assert obs("live-llm")["status"] == 400
brain = obs("live-brain-compare")["responses"]
assert len(brain) == 2 and all(x["ok"] and x["finish_reason"] == "stop" for x in brain)
assert sum(x["usage"]["total_tokens"] for x in brain) == 2172
mco = obs("live-mco")
assert mco["status"] == "partial" and mco["exit_code"] == 1
assert [x["status"] for x in mco["outputs"]] == ["success", "failed"]
wire = [json.loads(line) for line in (root / "observations/live-mco-wire.jsonl").read_text().splitlines()]
assert len([x for x in wire if x["event"] == "dispatch"]) == 3
assert sum(x["usage"]["total_tokens"] for x in wire if x["event"] == "terminal_metadata" and x["usage"]) == 3450
assert any(x.get("status") == 429 for x in wire if x["event"] == "upstream_error")
assert wire[-1]["stopped"]
print("ADVISOR_RECEIPTS_PASS; live multi-agent acceptance PARTIAL")
