import importlib.util
import pathlib
import subprocess
import unittest
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "providers/exe-dev/motherduck_native.py"


def load():
    spec = importlib.util.spec_from_file_location("motherduck_native", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FakeAPI:
    def __init__(self):
        self.tokens = {}
        self.users = [{"username": "test", "is_service_account": False, "is_deprovisioned": False}]
        self.fail_revoke = False
        self.ambiguous_mint = False

    def __call__(self, path, method="GET", body=None):
        if path == "/v1/users":
            return 200, {"users": self.users, "total_count": len(self.users)}
        if method == "POST":
            self.tokens["canary-id"] = {"id": "canary-id", "name": body["name"]}
            if self.ambiguous_mint:
                return None, {}
            return 200, {"id": "canary-id", "token": "synthetic-token"}
        if method == "DELETE":
            if self.fail_revoke:
                return 503, {}
            self.tokens.pop(path.rsplit("/", 1)[1], None)
            return 200, {}
        return 200, {"tokens": list(self.tokens.values())}


class MotherDuckNativeTest(unittest.TestCase):
    def setUp(self):
        self.m = load()
        self.api = FakeAPI()

    def execute(self, runner):
        return self.m.run_sql(self.api, runner, "my_db", pathlib.Path("/tmp/example.sql"))

    def test_success_revokes_exact_token(self):
        self.api.tokens["existing"] = {"id": "existing", "name": "unrelated"}
        with mock.patch.object(self.m, "run_duckdb", autospec=True) as runner:
            runner.return_value = "42\n"
            self.assertEqual(self.execute(runner), "42\n")
        self.assertEqual(set(self.api.tokens), {"existing"})

    def test_runner_failure_still_revokes(self):
        def fail(*args):
            raise self.m.RouteError("DUCKDB_FAILED")
        with self.assertRaisesRegex(self.m.RouteError, "DUCKDB_FAILED"):
            self.execute(fail)
        self.assertFalse(self.api.tokens)

    def test_ambiguous_identity_does_not_mint(self):
        self.api.users.append({"username": "other", "is_service_account": False, "is_deprovisioned": False})
        with self.assertRaisesRegex(self.m.RouteError, "IDENTITY"):
            self.execute(mock.Mock())
        self.assertFalse(self.api.tokens)

    def test_ambiguous_mint_reconciles_by_name(self):
        self.api.ambiguous_mint = True
        runner = mock.Mock()
        with self.assertRaisesRegex(self.m.RouteError, "MINT"):
            self.execute(runner)
        runner.assert_not_called()
        self.assertFalse(self.api.tokens)

    def test_revoke_failure_cannot_report_success(self):
        self.api.fail_revoke = True
        with self.assertRaisesRegex(self.m.RouteError, "CLEANUP"):
            self.execute(lambda *args: "42\n")
        self.assertTrue(self.api.tokens)

    def test_known_token_revoked_even_when_metadata_readback_fails(self):
        def request(path, method="GET", body=None):
            if method == "GET" and path.endswith("/tokens"):
                return 503, {}
            return self.api(path, method, body)
        with self.assertRaisesRegex(self.m.RouteError, "CLEANUP"):
            self.m.run_sql(request, lambda *args: "42", "my_db", pathlib.Path("/tmp/example.sql"))
        self.assertFalse(self.api.tokens)

    def test_cli_token_only_in_child_environment_and_temp_home_removed(self):
        seen = {}
        def fake_run(args, env):
            seen.update(env)
            self.assertNotIn("synthetic-token", " ".join(args))
            self.assertEqual(seen["motherduck_token"], "synthetic-token")
            self.assertTrue(pathlib.Path(seen["HOME"]).is_dir())
            return "42\n"
        with mock.patch.object(self.m, "bounded_output", side_effect=fake_run):
            self.assertEqual(self.m.run_duckdb("synthetic-token", "my_db", pathlib.Path("/tmp/example.sql")), "42\n")
        self.assertFalse(pathlib.Path(seen["HOME"]).exists())

    def test_oversize_native_output_is_bounded_and_revokes_token(self):
        import os
        import sys

        def runner(*args):
            return self.m.bounded_output(
                [sys.executable, "-c", "import sys;sys.stdout.write('x'*1000000)"],
                dict(os.environ), limit=4096, timeout=5)
        with self.assertRaisesRegex(self.m.RouteError, "OUTPUT_LIMIT"):
            self.execute(runner)
        self.assertFalse(self.api.tokens)

    def test_bounded_native_output_success_and_stderr_limit(self):
        import os
        import sys

        self.assertEqual(self.m.bounded_output(
            [sys.executable, "-c", "print('42')"], dict(os.environ), limit=4096, timeout=5), "42\n")
        with self.assertRaisesRegex(self.m.RouteError, "OUTPUT_LIMIT"):
            self.m.bounded_output(
                [sys.executable, "-c", "import sys;sys.stderr.write('x'*1000000)"],
                dict(os.environ), limit=4096, timeout=5)
