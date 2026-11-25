#!/usr/bin/env python3
"""Native DuckDB SQL-file runner with a provider-held MotherDuck credential."""
import argparse
import json
import os
from pathlib import Path
import resource
import subprocess
import sys
import tempfile
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen
import uuid

BASE = "https://motherduck.int.exe.xyz"


class RouteError(RuntimeError):
    pass


def api(path, method="GET", body=None):
    request = Request(BASE + path,
                      data=None if body is None else json.dumps(body).encode(),
                      method=method,
                      headers={"Content-Type": "application/json", "Accept": "application/json"})
    try:
        with urlopen(request, timeout=12) as response:
            raw = response.read()
            return response.status, json.loads(raw) if raw else {}
    except HTTPError as exc:
        return exc.code, {}
    except (URLError, TimeoutError, OSError, ValueError):
        return None, {}


def token_rows(request, path):
    status, data = request(path)
    if status != 200 or not isinstance(data, dict) or not isinstance(data.get("tokens"), list) or data.get("next_page_token"):
        raise RouteError("TOKEN_CLEANUP_READBACK_FAILED")
    if any(not isinstance(row, dict) for row in data["tokens"]):
        raise RouteError("TOKEN_CLEANUP_READBACK_FAILED")
    return data["tokens"]


def token_id(row):
    value = row.get("token_id") or row.get("id")
    return value if isinstance(value, str) and value else None


def run_sql(request, runner, database, sql_file):
    status, data = request("/v1/users")
    users = data.get("users") if isinstance(data, dict) else None
    if status != 200 or not isinstance(users, list) or len(users) != 1 or data.get("total_count") != 1 or data.get("next_page_token"):
        raise RouteError("IDENTITY_NOT_UNIQUE")
    user = users[0]
    if not isinstance(user, dict) or user.get("is_service_account") is not False or user.get("is_deprovisioned") is not False or not isinstance(user.get("username"), str) or not user["username"]:
        raise RouteError("IDENTITY_NOT_AUTHORIZED")
    path = "/v1/users/" + quote(user["username"], safe="") + "/tokens"
    name = "theseus-native-" + uuid.uuid4().hex
    issued_id = None
    try:
        status, created = request(path, "POST", {"name": name, "token_type": "read_write", "ttl": 300})
        if isinstance(created, dict):
            issued_id = token_id(created)
            token = created.get("token")
        else:
            token = None
        if status not in (200, 201) or not isinstance(token, str) or not token:
            raise RouteError("TOKEN_MINT_FAILED")
        return runner(token, database, sql_file)
    finally:
        # Reconcile even when the mint response was lost; never repeat the POST.
        rows = token_rows(request, path)
        matched = [row for row in rows if row.get("name") == name]
        if len(matched) > 1 or (matched and not token_id(matched[0])):
            raise RouteError("TOKEN_CLEANUP_AMBIGUOUS")
        if matched:
            found = token_id(matched[0])
            if issued_id and found != issued_id:
                raise RouteError("TOKEN_CLEANUP_ID_MISMATCH")
            issued_id = found
        if issued_id:
            status, _ = request(path + "/" + quote(issued_id, safe=""), "DELETE")
            rows = token_rows(request, path)
            if status != 200 or any(token_id(row) == issued_id or row.get("name") == name for row in rows):
                raise RouteError("TOKEN_CLEANUP_UNVERIFIED")


def run_duckdb(token, database, sql_file):
    with tempfile.TemporaryDirectory(prefix="theseus-md-", dir="/dev/shm") as home:
        env = {k: v for k, v in os.environ.items() if "motherduck" not in k.lower() and k != "DUCK_API_KEY"}
        env.update(HOME=home, XDG_CONFIG_HOME=home + "/config",
                   XDG_CACHE_HOME=home + "/cache", XDG_DATA_HOME=home + "/data",
                   XDG_STATE_HOME=home + "/state", motherduck_token=token)
        try:
            p = subprocess.run(
                ["/usr/local/bin/duckdb", "md:" + database, "-batch", "-bail",
                 "-csv", "-header", "-no-init", "-f", str(sql_file)],
                env=env, stdin=subprocess.DEVNULL, capture_output=True,
                text=True, timeout=240)
        except (OSError, subprocess.TimeoutExpired):
            raise RouteError("DUCKDB_EXECUTION_FAILED") from None
        if p.returncode != 0:
            raise RouteError("DUCKDB_FAILED")
        return p.stdout


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("database")
    parser.add_argument("sql_file", type=Path)
    args = parser.parse_args()
    if not args.database.isidentifier() or not args.sql_file.is_file():
        parser.error("expected database identifier and existing SQL file")
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    try:
        output = run_sql(api, run_duckdb, args.database, args.sql_file.resolve())
    except RouteError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except Exception:
        print("ROUTE_UNVERIFIED", file=sys.stderr)
        return 1
    print(output, end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
