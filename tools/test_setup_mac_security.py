"""GPU/network-free regressions for Mac artifact trust and security options.

    python -m unittest tools.test_setup_mac_security
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from contextlib import ExitStack
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "metal"))
import setup_mac as M  # noqa: E402


class MacFixture(unittest.TestCase):
    def setUp(self):
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.root = Path(self.stack.enter_context(tempfile.TemporaryDirectory()))
        self.data = self.root / "data"
        self.mtp = self.data / "mtp"
        self.mtp.mkdir(parents=True)
        self.prepared = self.mtp / "mtp-q2_0.gguf"
        self.prepared.write_bytes(b"old prepared fixture")
        self.exe = self.root / "build-metal" / "strata"
        self.exe.parent.mkdir()
        self.exe.write_bytes(b"fixture executable")
        self.pack = self.data / "packs" / "q2_0"
        (self.pack / "tokenizer").mkdir(parents=True)
        (self.pack / "native_experts.txt").touch()
        (self.pack / "tokenizer" / "vocab.json").write_text("{}")
        self.models = self.data / "models" / "Q2_0"
        self.models.mkdir(parents=True)
        for name in M.model_shard_names("Q2_0"):
            (self.models / name).write_bytes(b"fixture shard")
        self.cfg_path = self.root / "strata-q2_0.json"
        self.cfg_path.write_text(json.dumps({
            "exe": str(self.exe), "args": ["--native", str(next(self.models.iterdir()))],
            "backend": "metal", "port": 8080,
        }))
        self.patch(M, "ROOT", self.root)
        self.patch(M.S, "ROOT", self.root)
        self.patch(M.S, "data_folder", return_value=(self.data, []))
        self.patch(M, "mac_configs", return_value=[self.cfg_path])
        self.mac_info = self.patch(M, "mac_info", return_value={
            "chip": "fixture Apple Silicon", "ram_gb": 128, "macos": "15.0",
            "arm64": True, "clt": "/fixture/CLT", "perf_cores": 8,
        })
        self.patch(M.S, "free_gb", return_value=1000)
        self.pip = self.patch(M.S, "pip_install")
        self.llama = self.patch(M.S, "get_llama_cpp", return_value=self.root / "llama")
        self.build = self.patch(M, "build_engine", return_value=self.exe)
        self.download = self.patch(M.S, "download", side_effect=AssertionError("unexpected download"))
        self.patch(M.S, "done", return_value=True)
        self.patch(M.S, "check_shards")
        self.patch(M.S, "refresh_draft_vocab")
        self.patch(M.S, "write_run_script", return_value=self.root / "run-q2_0.sh")
        for name in ("say", "step", "ok", "warn"):
            self.patch(M.S, name)
        self.tool_run = self.patch(M.S, "run", side_effect=self.run_tool)
        self.verifier = self.patch(M.subprocess, "run", return_value=subprocess.CompletedProcess([], 0, ""))
        self.verify = self.patch(M.S, "mtp_corrupt", wraps=M.S.mtp_corrupt)

    def patch(self, obj, name, *args, **kwargs):
        return self.stack.enter_context(mock.patch.object(obj, name, *args, **kwargs))

    def run_tool(self, cmd, **kwargs):
        # Only explicit acquisition/packing is allowed; these are not trusted model bytes.
        tool = Path(cmd[1]).name
        if tool == "mtp_fetch.py":
            self.assertEqual(cmd[2], "fetch")
        elif tool == "mtp_pack.py":
            self.prepared.write_bytes(b"rebuilt prepared fixture")
        else:
            self.fail(f"unexpected tool: {cmd}")

    def setup_mac(self, *args):
        return M.main(["--setup", "--model", "Q2_0", "--vision", "no", "--yes", "--no-start", *args])

    def config(self):
        return json.loads(self.cfg_path.read_text())


class MTPVerification(MacFixture):
    def assert_rebuilt(self):
        self.assertEqual(self.prepared.read_bytes(), b"rebuilt prepared fixture")
        self.assertEqual([Path(c.args[0][1]).name for c in self.tool_run.call_args_list],
                         ["mtp_fetch.py", "mtp_pack.py"])
        self.verify.assert_called_once()
        self.assertEqual(self.verify.call_args.args[0], self.mtp)

    def test_missing_raw_tensors_rebuild_existing_prepared_artifact(self):
        self.assertEqual(self.setup_mac(), 0)
        self.assert_rebuilt()
        self.verifier.assert_not_called()  # shared verifier detects the missing directory itself

    def test_tensor_mismatch_rebuilds_existing_prepared_artifact(self):
        (self.mtp / "tensors").mkdir()
        self.verifier.return_value = subprocess.CompletedProcess([], 3, "pinned digest mismatch")
        self.assertEqual(self.setup_mac(), 0)
        self.assert_rebuilt()
        cmd = self.verifier.call_args.args[0]
        self.assertEqual(cmd[2:], ["verify", "--out", str(self.mtp)])

    def test_verified_existing_artifact_is_reused_without_fetch_or_pack(self):
        (self.mtp / "tensors").mkdir()
        self.assertEqual(self.setup_mac(), 0)
        self.verify.assert_called_once()
        self.verifier.assert_called_once()
        self.tool_run.assert_not_called()
        self.assertEqual(self.prepared.read_bytes(), b"old prepared fixture")

    def test_unexpected_verifier_exit_stops_before_reuse_or_rebuild(self):
        (self.mtp / "tensors").mkdir()
        self.verifier.return_value = subprocess.CompletedProcess([], 2, "fixture verifier error")
        before = self.cfg_path.read_bytes()
        with self.assertRaises(SystemExit):
            self.setup_mac()
        self.tool_run.assert_not_called()
        self.assertEqual(self.cfg_path.read_bytes(), before)
        self.assertEqual(self.prepared.read_bytes(), b"old prepared fixture")

    def test_verifier_exception_propagates_before_reuse_or_rebuild(self):
        (self.mtp / "tensors").mkdir()
        self.verifier.side_effect = OSError("fixture verifier unavailable")
        with self.assertRaisesRegex(OSError, "fixture verifier unavailable"):
            self.setup_mac()
        self.tool_run.assert_not_called()


class SecurityCarry(MacFixture):
    def setUp(self):
        super().setUp()
        (self.mtp / "tensors").mkdir()
        self.old = self.config()
        self.old.update({"host": "127.0.0.1", "api_key": "fixture-old-key",
                         "allowed_hosts": ["fixture.local"], "cors_origins": ["https://fixture.local"],
                         "env": {"FIXTURE_USER_OPTION": "kept"}})
        self.cfg_path.write_text(json.dumps(self.old))
        self.writer = self.patch(M.S, "write_setup_config", wraps=M.S.write_setup_config)

    def assert_security(self, host, api_key):
        cfg = self.config()
        self.assertEqual(cfg.get("api_key"), api_key)
        self.assertEqual(cfg.get("host"), host)
        for key in ("allowed_hosts", "cors_origins"):
            self.assertEqual(cfg.get(key), self.old[key])
        self.assertEqual(cfg["env"].get("FIXTURE_USER_OPTION"), "kept")
        self.writer.assert_called_once()
        self.assertEqual(json.loads(self.cfg_path.with_suffix(".json.bak").read_text()), self.old)

    def test_setup_rerun_retains_security_without_repeating_options(self):
        self.assertEqual(self.setup_mac(), 0)
        self.assert_security("127.0.0.1", "fixture-old-key")

    def test_explicit_host_retains_prior_key_and_access_lists(self):
        self.assertEqual(self.setup_mac("--host", "0.0.0.0"), 0)
        self.assert_security("0.0.0.0", "fixture-old-key")

    def test_explicit_host_and_api_key_override_prior_values(self):
        self.assertEqual(self.setup_mac("--host", "0.0.0.0", "--api-key", "fixture-new-key"), 0)
        self.assert_security("0.0.0.0", "fixture-new-key")

    def test_explicit_empty_api_key_is_not_replaced_by_prior_value(self):
        self.assertEqual(self.setup_mac("--api-key", ""), 0)
        self.assert_security("127.0.0.1", "")


class OrdinaryStart(MacFixture):
    def setUp(self):
        super().setUp()
        cfg = self.config()
        cfg.update({"host": "127.0.0.1", "api_key": "fixture-config-key"})
        self.cfg_path.write_text(json.dumps(cfg))
        self.launch = self.patch(M.subprocess, "call", return_value=17)

    def assert_start(self, options, expected):
        before = self.cfg_path.read_bytes()
        self.assertEqual(M.main(options), 17)
        self.launch.assert_called_once()
        cmd = self.launch.call_args.args[0]
        self.assertEqual(cmd[:6], [sys.executable, str(self.root / "serve" / "server.py"),
                                  "--engine", "strata", "--config", str(self.cfg_path)])
        for flag, value in expected.items():
            self.assertIn(flag, cmd)
            self.assertEqual(cmd[cmd.index(flag) + 1], value)
        for flag in ("--host", "--api-key"):
            if flag not in expected:
                self.assertNotIn(flag, cmd)  # retain server/config defaults when CLI omitted it
        self.assertEqual(self.cfg_path.read_bytes(), before)
        for action in (self.mac_info, self.build, self.pip, self.llama, self.download,
                       self.tool_run, self.verify, self.verifier):
            action.assert_not_called()
        return cmd

    def test_host_and_api_key_reach_server_without_setup(self):
        self.assert_start(["--host", "0.0.0.0", "--api-key", "fixture-cli-key"],
                          {"--host": "0.0.0.0", "--api-key": "fixture-cli-key"})

    def test_api_key_alone_reaches_server_without_setup(self):
        self.assert_start(["--api-key", "fixture-cli-key"], {"--api-key": "fixture-cli-key"})

    def test_host_alone_reaches_server_without_setup(self):
        self.assert_start(["--host", "0.0.0.0"], {"--host": "0.0.0.0"})

    def test_omitted_network_options_keep_config_and_existing_start_flags(self):
        cmd = self.assert_start(["--port", "9090", "--no-browser"], {"--port": "9090"})
        self.assertNotIn("--open", cmd)


if __name__ == "__main__":
    unittest.main()
