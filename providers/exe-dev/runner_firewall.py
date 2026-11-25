#!/usr/bin/env python3
"""One bounded, operator-owned Azure SQL firewall lease for an exact Actions run."""
import argparse
import ipaddress
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import tempfile
import time

AZ = "/home/exedev/.local/bin/az-owner"


def validate_run(cfg, run):
    expected = {"head_sha": cfg["sha"], "head_branch": cfg["branch"],
                "run_attempt": cfg["attempt"], "event": "push", "path": cfg["workflow"]}
    if any(run.get(k) != v for k, v in expected.items()) or any((run.get(k) or {}).get("full_name","").casefold() != cfg["repo"].casefold() for k in ("repository","head_repository")):
        raise ValueError("run identity mismatch")


def validate_ip(value):
    ip = ipaddress.ip_address(value)
    if ip.version != 4 or not ip.is_global or ip.is_multicast:
        raise ValueError("expected one public unicast IPv4")
    return str(ip)


def lease(cfg, api, receipt, *, timeout=600, clock=time.monotonic, sleep=time.sleep):
    name = f'rs-gh-{cfg["run_id"]}-{cfg["attempt"]}'
    deadline = clock() + timeout
    receipt = Path(receipt)
    # Do not adopt an old rule or overwrite an unresolved receipt.
    if receipt.exists() or api.rule(name) is not None:
        raise RuntimeError("existing lease; reconcile explicitly")
    run = api.run()
    validate_run(cfg, run)
    while run["status"] != "completed":
        if clock() >= deadline:
            raise TimeoutError("run/artifact deadline")
        if run["status"] == "in_progress":
            ip = api.artifact_ip()
            if ip is not None:
                ip = validate_ip(ip)
                break
        sleep(2)
        run = api.run()
        validate_run(cfg, run)
    else:
        return run["conclusion"]
    run = api.run()
    validate_run(cfg, run)
    if run["status"] == "completed":
        return run["conclusion"]
    if run["status"] != "in_progress" or api.rule(name) is not None:
        raise RuntimeError("run not active or rule collision")
    record = dict(cfg, rule=name, ip=ip, state="PENDING_CLEANUP")
    fd = os.open(receipt, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as f:
        json.dump(record, f)
        f.flush()
        os.fsync(f.fileno())

    def save(state):
        record["state"] = state
        # Atomic replacement retains the pre-create receipt on interruption.
        with tempfile.NamedTemporaryFile(mode="w", dir=receipt.parent, delete=False) as f:
            json.dump(record, f)
            f.flush()
            os.fsync(f.fileno())
            temp = f.name
        os.replace(temp, receipt)

    confirmed = False
    try:
        try:
            api.create(name, ip)
        except Exception:
            if api.rule(name) != (ip, ip):
                raise
        if api.rule(name) != (ip, ip):
            raise RuntimeError("rule readback mismatch")
        confirmed = True
        save("ACTIVE")
        while True:
            run = api.run()
            validate_run(cfg, run)
            if run["status"] == "completed":
                record["conclusion"] = run["conclusion"]
                return run["conclusion"]
            if clock() >= deadline:
                raise TimeoutError("run completion deadline")
            sleep(2)
    finally:
        save("PENDING_CLEANUP")
        actual = api.rule(name)
        if actual is not None:
            if actual != (ip, ip):
                raise RuntimeError("rule changed; refuse automatic deletion")
            try:
                api.delete(name)
            except Exception:
                if api.rule(name) is not None:
                    raise
        if api.rule(name) is not None:
            raise RuntimeError("cleanup readback failed")
        if confirmed or actual is not None:
            save("CLEANED")


def command(argv, *, capture=True, timeout=60):
    with subprocess.Popen(argv, stdout=subprocess.PIPE if capture else None,
                          text=True, start_new_session=True) as proc:
        try:
            out, _ = proc.communicate(timeout=timeout)
        except (subprocess.TimeoutExpired, KeyboardInterrupt):
            try:
                os.killpg(proc.pid, signal.SIGINT)
            except ProcessLookupError:
                pass
            try:
                proc.communicate(timeout=10)
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(proc.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                proc.communicate()
            raise
        if proc.returncode:
            raise subprocess.CalledProcessError(proc.returncode, argv)
        return out


class Live:
    def __init__(self, cfg):
        self.cfg = cfg
        self.base = f'repos/{cfg["repo"]}/actions/runs/{cfg["run_id"]}'
        self.target = ["-g", cfg["group"], "-s", cfg["server"]]

    def call(self, argv):
        # No token values or untrusted command strings in shell arguments.
        return json.loads(command(argv))

    def run(self):
        return self.call(["gh", "api", self.base])

    def artifact_ip(self):
        run = self.run()
        validate_run(self.cfg, run)
        if run["status"] != "in_progress":
            return None
        name = f'rs-runner-ip-{self.cfg["attempt"]}'
        result = self.call(["gh", "api", self.base+"/artifacts?per_page=100"])
        if result["total_count"] > 100:
            raise ValueError("artifact inventory exceeds bound")
        matches = [a for a in result["artifacts"] if a["name"] == name and not a["expired"]]
        if not matches:
            return None
        if len(matches) != 1 or not 0 < matches[0]["size_in_bytes"] <= 4096:
            raise ValueError("ambiguous or oversized IP artifact")
        with tempfile.TemporaryDirectory() as folder:
            command(["gh", "run", "download", str(self.cfg["run_id"]), "-R", self.cfg["repo"], "-n", name, "-D", folder], capture=False, timeout=30)
            files = list(Path(folder).iterdir())
            if len(files) != 1 or files[0].name != "ip.txt" or files[0].is_symlink() or not files[0].is_file() or files[0].stat().st_size > 64:
                raise ValueError("invalid IP artifact layout")
            return validate_ip(files[0].read_text(encoding="ascii").strip())

    def rule(self, name):
        rows = self.call([AZ,"sql","server","firewall-rule","list",*self.target,"--only-show-errors","-o","json"])
        matches = [r for r in rows if r["name"] == name]
        if len(matches) > 1:
            raise RuntimeError("ambiguous rule inventory")
        return (matches[0]["startIpAddress"],matches[0]["endIpAddress"]) if matches else None

    def create(self, name, ip):
        self.call([AZ,"sql","server","firewall-rule","create",*self.target,"-n",name,"--start-ip-address",ip,"--end-ip-address",ip,"--only-show-errors","-o","json"])

    def delete(self, name):
        command([AZ,"sql","server","firewall-rule","delete",*self.target,"-n",name,"--only-show-errors"],capture=False)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for key in ("repo","sha","branch","workflow","group","server"):
        p.add_argument("--"+key,required=True)
    for key in ("run-id","attempt"):
        p.add_argument("--"+key,type=int,required=True)
    p.add_argument("--receipt",type=Path,required=True)
    p.add_argument("--timeout",type=int,default=600)
    a = p.parse_args()
    cfg = vars(a).copy()
    receipt,timeout = cfg.pop("receipt"),cfg.pop("timeout")
    if not re.fullmatch(r"[0-9a-f]{40}",a.sha) or not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+",a.repo) or min(a.run_id,a.attempt,timeout)<=0 or timeout>900:
        p.error("invalid identity or timeout")
    def stop(sig,frame):
        raise KeyboardInterrupt("operator terminated")
    signal.signal(signal.SIGTERM,stop)
    result = lease(cfg,Live(cfg),receipt,timeout=timeout)
    print(json.dumps({"conclusion":result,"receipt":str(receipt)}))
    return 0 if result=="success" else 1


if __name__=="__main__":
    raise SystemExit(main())
