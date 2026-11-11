#!/usr/bin/env python3
"""Offline, deterministic Cloud Shell source-contract check. No credentials/network."""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
NEEDED = [
    "README.md", "AGENTS.md", "RULES.md",
    "skills/exe-dev-core-router/SKILL.md",
    "providers/exe-dev/README.md",
    "providers/exe-dev/session_search_drive.py",
    "tests/test_session_search_drive.py",
    "providers/sprites/README.md",
    "providers/marcopolo/README.md",
    "modules/github/README.md",
    "docs/repository-map.md",
    ".github/workflows/repository-map.yml",
]
assert not [p for p in NEEDED if not (ROOT / p).is_file()], "missing required source paths"
rules = (ROOT / "RULES.md").read_text()
skill = (ROOT / "skills/exe-dev-core-router/SKILL.md").read_text()
assert "Project Contract" in rules and "exe.dev" in rules
assert skill.startswith("---\nname: exe-dev-core-router\n")
assert "get_cli_help" in skill and "run_vm_command" in skill
assert "exe.int.exe.xyz/exec" in skill
assert "bash -lc" in skill and "~/.local/bin" in skill
assert "governed wrapper" in skill.lower()
assert "runtime" in skill.lower() and "pinned" in skill.lower()
assert "MCP/control-plane" in skill
assert "provider proxy HTTP" in skill
assert "authoritative postcondition" in skill
assert "Drive" in skill and "base64" in skill
assert "DEGRADED" in skill and "BLOCKED" in skill and "UNKNOWN" in skill
assert "GH_TOKEN" not in skill and "oauth_token:" not in skill
map_wf = (ROOT / ".github/workflows/repository-map.yml").read_text()
assert "dekko==1.9.0" in map_wf
assert "TRACKED_FILES.txt" in map_wf
assert "derived-non-authoritative" in map_wf
assert "persist-credentials: false" in map_wf
assert "SOURCE_SHA" in map_wf
assert "github.com/TeaShaman-cyber/theseus-research" in (ROOT / "README.md").read_text()
result = subprocess.run(
    [sys.executable, "-m", "unittest", "tests.test_session_search_drive"],
    cwd=ROOT,
    check=False,
)
assert result.returncode == 0, "session search recovery adapter tests failed"
print(json.dumps({"status": "PASS", "required_paths": len(NEEDED), "map": "non-authoritative", "tests": "PASS"}, sort_keys=True))
