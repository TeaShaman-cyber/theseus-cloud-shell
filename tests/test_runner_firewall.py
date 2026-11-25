import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location("runner_firewall", Path(__file__).resolve().parents[1]/"providers/exe-dev/runner_firewall.py")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

class Fake:
    def __init__(self):
        self.rules = {}
        self.states = ["in_progress", "in_progress", "completed"]
        self.sha = "a"*40
        self.ip = "8.8.8.8"
        self.create_error = False
        self.delete_error = False
        self.never_finish = False
    def run(self):
        status = "in_progress" if self.never_finish else self.states.pop(0) if len(self.states)>1 else self.states[0]
        return dict(head_sha=self.sha,head_branch="test",run_attempt=1,event="push",path=".github/workflows/test.yml",repository={"full_name":"owner/repo"},head_repository={"full_name":"owner/repo"},status=status,conclusion="success" if status=="completed" else None)
    def artifact_ip(self):
        return self.ip
    def rule(self,name):
        return self.rules.get(name)
    def create(self,name,ip):
        self.rules[name]=(ip,ip)
        if self.create_error: raise RuntimeError("ambiguous create")
    def delete(self,name):
        if self.delete_error: raise RuntimeError("delete failed")
        self.rules.pop(name,None)

class LeaseTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.receipt=Path(self.tmp.name)/"receipt.json"
        self.cfg=dict(repo="owner/repo",run_id=123,attempt=1,sha="a"*40,branch="test",workflow=".github/workflows/test.yml",group="rg",server="server")
        self.fake=Fake()
        self.t=0
    def clock(self):
        return self.t
    def sleep(self,n):
        self.t+=n
    def invoke(self):
        return m.lease(self.cfg,self.fake,self.receipt,timeout=3,clock=self.clock,sleep=self.sleep)
    def state(self):
        return json.loads(self.receipt.read_text())["state"]
    def test_success_removes_rule(self):
        self.assertEqual(self.invoke(),"success")
        self.assertEqual(self.fake.rules,{})
        self.assertEqual(self.state(),"CLEANED")
    def test_wrong_head_never_mutates(self):
        self.fake.sha="b"*40
        with self.assertRaises(ValueError):self.invoke()
        self.assertEqual(self.fake.rules,{})
    def test_private_ip_rejected(self):
        self.fake.ip="10.0.0.1"
        with self.assertRaises(ValueError):self.invoke()
        self.assertEqual(self.fake.rules,{})
    def test_existing_rule_not_owned(self):
        self.fake.rules["rs-gh-123-1"]=("8.8.8.8","8.8.8.8")
        with self.assertRaises(RuntimeError):self.invoke()
        self.assertEqual(len(self.fake.rules),1)
    def test_ambiguous_create_reconciled(self):
        self.fake.create_error=True
        self.assertEqual(self.invoke(),"success")
        self.assertFalse(self.fake.rules)
    def test_unconfirmed_create_keeps_pending_receipt(self):
        def create(name,ip):
            raise TimeoutError("may still be executing")
        self.fake.create=create
        with self.assertRaises(TimeoutError):self.invoke()
        self.assertFalse(self.fake.rules)
        self.assertEqual(self.state(),"PENDING_CLEANUP")
    def test_reserved_shared_ip_rejected(self):
        self.fake.ip="100.64.0.1"
        with self.assertRaises(ValueError):self.invoke()
        self.assertFalse(self.fake.rules)
    def test_timeout_removes_rule(self):
        self.fake.never_finish=True
        with self.assertRaises(TimeoutError):self.invoke()
        self.assertFalse(self.fake.rules)
        self.assertEqual(self.state(),"CLEANED")
    def test_failed_delete_records_pending(self):
        self.fake.delete_error=True
        with self.assertRaises(RuntimeError):self.invoke()
        self.assertEqual(self.state(),"PENDING_CLEANUP")
        self.assertTrue(self.fake.rules)
    def test_terminal_before_create(self):
        self.fake.states=["completed"]
        self.assertEqual(self.invoke(),"success")
        self.assertFalse(self.fake.rules)
    def test_foreign_head_repo_rejected(self):
        original=self.fake.run
        self.fake.run=lambda:dict(original(),head_repository={"full_name":"fork/repo"})
        with self.assertRaises(ValueError):self.invoke()
        self.assertFalse(self.fake.rules)
    def test_changed_rule_not_deleted(self):
        original=self.fake.create
        def create(name,ip):
            original(name,ip)
            self.fake.rules[name]=("1.1.1.1","1.1.1.1")
        self.fake.create=create
        with self.assertRaises(RuntimeError):self.invoke()
        self.assertEqual(self.state(),"PENDING_CLEANUP")
        self.assertEqual(self.fake.rules["rs-gh-123-1"],("1.1.1.1","1.1.1.1"))
    def test_interrupted_active_lease_cleans(self):
        original=self.fake.run
        def run():
            if self.fake.rules:raise KeyboardInterrupt()
            return original()
        self.fake.run=run
        with self.assertRaises(KeyboardInterrupt):self.invoke()
        self.assertFalse(self.fake.rules)
        self.assertEqual(self.state(),"CLEANED")
    def test_ambiguous_delete_reconciled(self):
        original=self.fake.delete
        def delete(name):
            original(name)
            raise RuntimeError("lost response")
        self.fake.delete=delete
        self.assertEqual(self.invoke(),"success")
        self.assertFalse(self.fake.rules)
        self.assertEqual(self.state(),"CLEANED")
    def test_existing_receipt_not_overwritten(self):
        self.receipt.write_text("unresolved")
        with self.assertRaises(RuntimeError):self.invoke()
        self.assertEqual(self.receipt.read_text(),"unresolved")
        self.assertFalse(self.fake.rules)
    def test_multicast_not_public_unicast(self):
        self.fake.ip="224.0.0.1"
        with self.assertRaises(ValueError):self.invoke()
        self.assertFalse(self.fake.rules)
    def test_attempt_changed(self):
        original=self.fake.run
        self.fake.run=lambda:dict(original(),run_attempt=2)
        with self.assertRaises(ValueError):self.invoke()
        self.assertFalse(self.fake.rules)

if __name__=="__main__":unittest.main()
