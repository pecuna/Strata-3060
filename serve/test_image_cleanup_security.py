"""Regression tests for temporary image-job cleanup (no GPU or model files needed)."""
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from serve import images as images_api


class ImageJobCleanup(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.gen = images_api.ImageGen({
            "exe": str(root / "missing-sd-cli"),
            "diffusion_model": "unused-diffusion.gguf", "vae": "unused-vae", "llm": "unused-llm.gguf",
            "out_dir": str(root / "out"),
        })
        self.job = images_api.parse_request({"prompt": "cleanup regression", "seed": 1}, self.gen.cfg)

    def assert_job_cleaned(self):
        self.assertEqual(list(self.gen.dir.iterdir()), [], "failed image job left temporary files behind")
        self.assertIsNone(self.gen.progress)

    def test_repeated_spawn_failure_leaves_no_job_directories(self):
        for attempt in range(3):
            with self.subTest(attempt=attempt):
                with self.assertRaisesRegex(images_api.ImageJobFailed, "sd-cli did not start"):
                    self.gen.run(self.job)
                self.assert_job_cleaned()

    def test_log_open_failure_cleans_job_directory(self):
        with mock.patch.object(images_api, "open", create=True, side_effect=OSError("log open failed")):
            with self.assertRaisesRegex(OSError, "log open failed"):
                self.gen.run(self.job)
        self.assert_job_cleaned()

    def test_log_close_failure_cleans_job_directory(self):
        proc = mock.Mock(stdout=iter(()), returncode=0)
        proc.poll.return_value = 0
        log = mock.mock_open()
        log.return_value.__exit__.side_effect = OSError("log close failed")
        with mock.patch.object(images_api, "open", log, create=True), \
                mock.patch.object(images_api.subprocess, "Popen", return_value=proc):
            with self.assertRaisesRegex(OSError, "log close failed"):
                self.gen.run(self.job)
        self.assert_job_cleaned()

    def test_log_read_failure_cleans_job_directory(self):
        proc = mock.Mock(stdout=iter(()), returncode=0)
        proc.poll.return_value = 0
        with mock.patch.object(images_api.subprocess, "Popen", return_value=proc), \
                mock.patch.object(Path, "read_text", side_effect=OSError("log read failed")):
            with self.assertRaisesRegex(OSError, "log read failed"):
                self.gen.run(self.job)
        self.assert_job_cleaned()


if __name__ == "__main__":
    unittest.main()
