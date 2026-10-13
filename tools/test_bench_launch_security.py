"""Credential-bearing benchmark launch artifacts are private and short-lived."""
import json
import os
import stat
import tempfile
import unittest
from pathlib import Path
from unittest import mock
from tools import strata_bench as bench


class BenchmarkLaunchSecurity(unittest.TestCase):
    def fixture(self, root):
        cfg = root / "original.json"
        cfg.write_text(json.dumps({"api_key": "fixture-not-a-secret", "args":
                                  ["--expert-profile-save", "profile.bin", "--spec", "4"]}))
        return cfg

    def test_private_random_config_and_log_cleaned_after_exit(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            cfg = self.fixture(root)
            log = root / "run.log"
            victim = root / "victim"
            victim.write_text("unchanged")
            log.with_suffix(".config.json").symlink_to(victim)
            proc = mock.Mock()
            proc.poll.return_value = 0
            old = os.umask(0)
            try:
                with mock.patch.object(bench.subprocess, "Popen", return_value=proc) as spawn:
                    actual = bench.start_server(cfg, 8080, None, log)
                args = spawn.call_args.args[0]
                used = Path(args[args.index("--config") + 1])
                self.assertNotEqual(used, log.with_suffix(".config.json"))
                self.assertEqual(stat.S_IMODE(used.stat().st_mode), 0o600)
                self.assertEqual(stat.S_IMODE(log.stat().st_mode), 0o600)
                self.assertEqual(json.loads(used.read_text())["api_key"], "fixture-not-a-secret")
                self.assertNotIn("--expert-profile-save", json.loads(used.read_text())["args"])
                bench.stop_server(actual)
                self.assertFalse(used.exists())
                self.assertEqual(victim.read_text(), "unchanged")
                self.assertIn("--expert-profile-save", json.loads(cfg.read_text())["args"])
            finally:
                os.umask(old)

    def test_spawn_failure_removes_temporary_config(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            cfg = self.fixture(root)
            captured = []
            def refuse(cmd, **kwargs):
                captured.append(Path(cmd[cmd.index("--config") + 1]))
                raise OSError("fixture spawn refused")
            with mock.patch.object(bench.subprocess, "Popen", side_effect=refuse):
                with self.assertRaises(OSError):
                    bench.start_server(cfg, 8080, None, root / "run.log")
            self.assertFalse(captured[0].exists())

    def test_preexisting_log_symlink_is_not_followed(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            cfg = self.fixture(root)
            victim = root / "victim"
            victim.write_text("unchanged")
            log = root / "run.log"
            log.symlink_to(victim)
            with mock.patch.object(bench.subprocess, "Popen") as spawn:
                with self.assertRaises(FileExistsError):
                    bench.start_server(cfg, 8080, None, log)
                spawn.assert_not_called()
            self.assertEqual(victim.read_text(), "unchanged")


if __name__ == "__main__":
    unittest.main()
