"""Offline regression tests for fail-closed MTP acquisition trust policy."""
import contextlib
import io
import json
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools import test_mtp_fetch as fixture
from tools.test_mtp_fetch import A, B, FetchCase, HASHES, Mirror, M


class TrustPolicy(FetchCase):
    def test_missing_pinned_revision_does_not_fall_back_to_main(self):
        repo = M.REPO
        error = M.urllib.error.HTTPError(repo, 404, "not found", {}, None)
        with mock.patch.object(M.urllib.request, "urlopen", side_effect=error) as open_url, \
                contextlib.redirect_stderr(io.StringIO()), self.assertRaises(M.urllib.error.HTTPError):
            M.resolve_repo()
        self.assertEqual(M.REPO, repo)
        self.assertEqual(open_url.call_count, 1)
        self.assertNotIn("/resolve/main/", open_url.call_args[0][0].full_url)

    def test_changed_sources_cannot_disable_trusted_tensor_hashes(self):
        for repo in ("https://huggingface.co/Qwen/Qwen3.8-Flash-Next/resolve/main/",
                     "https://mirror.invalid/Qwen/Qwen3.8-Flash-Next/resolve/other/",
                     "https://www.modelscope.cn/models/Qwen/Qwen3.8-Flash-Next/resolve/master/"):
            with self.subTest(repo=repo), mock.patch.object(M, "REPO", repo):
                with self.assertRaisesRegex(SystemExit, "is not the checkpoint's"):
                    self.fetch(Mirror(wrong={"mtp.a"}))
                self.assertFalse((self.out / "tensors" / "mtp.a.bin").exists())
                self.assertFalse((self.out / "mtp-manifest.json").exists())

    def test_untrusted_cached_inventory_is_rejected_before_any_tensor_io(self):
        start, end = Mirror.span("model-1.safetensors", "mtp.a")
        row = dict(name="mtp.a", shard="model-1.safetensors", dtype="BF16", shape=[32],
                   start=start, end=end, bytes=64)
        unknown = dict(row, name="mtp.untrusted")
        inv_path = self.out / "mtp-inventory.json"
        inventory = json.dumps(dict(repo=M.REPO, tensors=[row, unknown]))
        inv_path.write_text(inventory)
        with mock.patch.object(M.urllib.request, "urlopen", side_effect=Mirror()) as open_url, \
                contextlib.redirect_stderr(io.StringIO()), \
                self.assertRaisesRegex(SystemExit, "trusted.*sha256"):
            M.fetch(str(self.out), None)
        open_url.assert_not_called()
        self.assertEqual(inv_path.read_text(), inventory)
        self.assertFalse((self.out / "tensors").exists())
        self.assertFalse((self.out / "mtp-manifest.json").exists())

    def test_untrusted_remote_inventory_is_rejected_before_shard_reads(self):
        index = json.dumps({"weight_map": {"mtp.untrusted": "unknown.safetensors"}}).encode()
        files = {"unknown.safetensors": fixture.shard([("mtp.untrusted", A)])}
        mirror = Mirror()
        with mock.patch.object(fixture, "INDEX", index), mock.patch.dict(fixture.FILES, files), \
                mock.patch.object(M.urllib.request, "urlopen", mirror), \
                contextlib.redirect_stdout(io.StringIO()), \
                self.assertRaisesRegex(SystemExit, "trusted.*sha256"):
            M.inventory(str(self.out))
        self.assertEqual(mirror.ranges, [])
        self.assertEqual(list(self.out.iterdir()), [])

    def test_invalid_expected_digest_is_rejected_before_tensor_io(self):
        start, end = Mirror.span("model-1.safetensors", "mtp.a")
        row = dict(name="mtp.a", shard="model-1.safetensors", dtype="BF16", shape=[32],
                   start=start, end=end, bytes=64)
        (self.out / "mtp-inventory.json").write_text(json.dumps(dict(repo=M.REPO, tensors=[row])))
        for digest in (None, "", "not-a-digest", "z" * 64):
            with self.subTest(digest=digest), mock.patch.dict(M.SHA256, {"mtp.a": digest}), \
                    mock.patch.object(M.urllib.request, "urlopen", side_effect=Mirror()) as open_url, \
                    contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaisesRegex(SystemExit, "trusted.*sha256"):
                    M.fetch(str(self.out), None)
                open_url.assert_not_called()
                self.assertFalse((self.out / "tensors").exists())

    def test_verification_rehashes_same_size_same_mtime_corruption(self):
        self.fetch(Mirror())
        self.assertEqual(M.verify(str(self.out)), [])
        path = self.out / "tensors" / "mtp.a.bin"
        import os
        before = path.stat()
        path.write_bytes(b"x" * before.st_size)
        os.utime(path, ns=(before.st_atime_ns, before.st_mtime_ns))
        self.assertEqual(M.verify(str(self.out)), ["mtp.a"])

    def test_missing_tensor_directory_is_not_verified(self):
        self.assertEqual(M.verify(str(self.out)), sorted(M.SHA256))

    def test_honest_alternate_source_keeps_content_hash_enforcement(self):
        with mock.patch.object(M, "REPO", "https://mirror.invalid/Qwen/Qwen3.8-Flash-Next/resolve/main/"):
            self.fetch(Mirror())
            manifest = json.loads((self.out / "mtp-manifest.json").read_text())
            self.assertEqual({r["name"]: r["sha256"] for r in manifest}, HASHES)
            self.assertEqual(M.verify(str(self.out)), [])
            (self.out / "tensors" / "mtp.a.bin").write_bytes(b"x")
            self.assertEqual(M.verify(str(self.out)), ["mtp.a"])

    def test_valid_pinned_partial_tensor_resumes_at_its_suffix(self):
        self.fetch(Mirror())
        (self.out / "tensors" / "mtp.b.bin").write_bytes(B[:10])
        mirror = Mirror()
        self.fetch(mirror)
        start, end = Mirror.span("model-2.safetensors", "mtp.b")
        self.assertEqual(mirror.ranges, [("model-2.safetensors", start + 10, end)])
        self.assertEqual(self.tensor("mtp.b"), B)
        self.assertEqual(M.verify(str(self.out)), [])


if __name__ == "__main__":
    unittest.main()
