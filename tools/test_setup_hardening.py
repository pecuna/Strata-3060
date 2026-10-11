"""Offline regressions for owner-fork installer security boundaries."""
from __future__ import annotations

import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock
import urllib.error

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import setup


class PinnedDownloads(unittest.TestCase):
    def test_pinned_hf_404_never_requests_main_or_marks_complete(self):
        pin = "b0bd645043aaba5be9c6afd67fbf768a15bba5ae"
        for host in ("https://huggingface.co", "https://hf-mirror.com"):
            url = f"{host}/owner/model/resolve/{pin}/model.gguf"
            calls = []

            def missing(req, **kwargs):
                calls.append(req.full_url)
                raise urllib.error.HTTPError(req.full_url, 404, "not found", {}, None)

            with self.subTest(host=host), tempfile.TemporaryDirectory() as d, \
                    mock.patch.object(setup.urllib.request, "urlopen", side_effect=missing), \
                    mock.patch.object(setup.time, "sleep"), \
                    mock.patch.object(setup, "model_source", return_value="hf"), \
                    contextlib.redirect_stdout(io.StringIO()):
                dst = Path(d) / "model.gguf"
                with self.assertRaises(SystemExit):
                    setup.download(url, dst)
                self.assertTrue(calls)
                self.assertEqual(set(calls), {url})
                self.assertFalse(dst.exists())
                self.assertFalse(dst.with_name(dst.name + ".done").exists())


class ModelVerification(unittest.TestCase):
    def test_skip_env_cannot_bypass_the_pinned_model_hash(self):
        data = b"a wrong pinned model"
        with tempfile.TemporaryDirectory() as d, \
                mock.patch.dict(os.environ, {"STRATA_SKIP_SHA256": "1"}), \
                contextlib.redirect_stdout(io.StringIO()):
            shard = Path(d) / "model.gguf"
            shard.write_bytes(data)
            with self.assertRaises(SystemExit):
                setup.verify_sha256(shard, len(data), hashlib.sha256(b"expected model").hexdigest())
            self.assertFalse(shard.exists())
            self.assertFalse(shard.with_name(shard.name + ".done").exists())


class MTPVerifierErrors(unittest.TestCase):
    def test_verifier_failure_includes_captured_diagnostic(self):
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)
            (folder / "tensors").mkdir()
            out = io.StringIO()
            with mock.patch.object(setup.subprocess, "run", return_value=mock.Mock(returncode=1, stdout="fixture verifier crashed")), \
                    contextlib.redirect_stdout(out), self.assertRaises(SystemExit):
                setup.mtp_corrupt(folder)
            self.assertIn("fixture verifier crashed", out.getvalue())

    def test_unexpected_verifier_exit_never_counts_as_verified(self):
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)
            (folder / "tensors").mkdir()
            for code in (1, 2, -9):
                with self.subTest(code=code), \
                        mock.patch.object(setup.subprocess, "run", return_value=mock.Mock(returncode=code)), \
                        contextlib.redirect_stdout(io.StringIO()), \
                        self.assertRaisesRegex(SystemExit, "1"):
                    setup.mtp_corrupt(folder)


class OrdinaryStartEnginePolicy(unittest.TestCase):
    def test_missing_gpu_code_requires_explicit_setup_without_mutation(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            eng = root / "engine"
            eng.mkdir()
            (eng / "BUILD.json").write_text(json.dumps({"archs": [80]}))
            card = {"index": 0, "name": "Test GPU", "arch": 86}
            cfg = {"exe": str(eng / setup.EXE), "args": [], "cuda": 13}
            with mock.patch.object(setup, "ROOT", root), \
                    mock.patch.object(setup, "engine_runs_on", return_value=False), \
                    mock.patch.object(setup, "gpu_info", return_value=card), \
                    mock.patch.object(setup, "get_llama_cpp", return_value=root / "llama") as dependency, \
                    mock.patch.object(setup, "build_engine") as build, \
                    mock.patch.object(setup, "write_config") as write, \
                    contextlib.redirect_stdout(io.StringIO()), self.assertRaises(SystemExit):
                setup.ensure_engine_for([card], root / "config.json", cfg, True)
            dependency.assert_not_called()
            build.assert_not_called()
            write.assert_not_called()

    def test_old_gpu_does_not_implicitly_download_cuda12(self):
        card = {"index": 0, "name": "Test Pascal", "arch": 61}
        with mock.patch.object(setup, "use_cuda12") as migrate, \
                contextlib.redirect_stdout(io.StringIO()), self.assertRaises(SystemExit):
            setup.ensure_engine_for([card], ROOT / "test-never-written.json", {"cuda": 13}, True)
        migrate.assert_not_called()


class ExistingConfigLaunch(unittest.TestCase):
    def test_existing_configs_never_implicitly_update_the_engine(self):
        for count, argv in ((1, []), (2, []), (1, ["--calibrate"]), (1, ["--build"])):
            with self.subTest(count=count, argv=argv), tempfile.TemporaryDirectory() as d:
                root = Path(d)
                configs = [root / f"strata-model-{i}.json" for i in range(count)]
                for config in configs:
                    config.write_text(json.dumps({"args": [], "model_name": config.stem}))
                with mock.patch.object(sys, "argv", ["setup.py", *argv]), \
                        mock.patch.object(setup, "ROOT", root), \
                        mock.patch.object(setup, "data_folder", return_value=(root, [])), \
                        mock.patch.object(setup, "installed_configs", return_value=configs), \
                        mock.patch.object(setup, "start_gpus", return_value=None), \
                        mock.patch.object(setup, "ask", return_value="1"), \
                        mock.patch.object(setup, "calibrate_config", return_value=True), \
                        mock.patch.object(setup, "update_installed_engine") as update, \
                        mock.patch.object(setup, "start", return_value=0) as start, \
                        mock.patch.object(setup.urllib.request, "urlopen", side_effect=AssertionError("network")), \
                        contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(setup.main(), 0)
                    update.assert_not_called()
                    start.assert_called_once()
                    self.assertEqual(start.call_args.args[0], configs[0])


if __name__ == "__main__":
    unittest.main()
