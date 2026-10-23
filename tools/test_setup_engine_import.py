"""Engine-only import regression gates; no GPU, network or production state."""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import setup


class TrellisSourceFingerprint(unittest.TestCase):
    def test_overlay_byte_changes_invalidate_engine_stamp(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            overlay = root / "third_party/ggml-tq/tq.cuh"
            overlay.parent.mkdir(parents=True)
            overlay.write_bytes(b"first")
            with mock.patch.object(setup, "ROOT", root):
                before = setup.source_hash(setup.ENGINE_SOURCES)
                overlay.write_bytes(b"other")
                self.assertNotEqual(before, setup.source_hash(setup.ENGINE_SOURCES))

    def test_overlay_removal_invalidates_engine_stamp(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            overlay = root / "third_party/ggml-tq/tq.cuh"
            overlay.parent.mkdir(parents=True)
            overlay.write_bytes(b"header")
            with mock.patch.object(setup, "ROOT", root):
                before = setup.source_hash(setup.ENGINE_SOURCES)
                overlay.unlink()
                self.assertNotEqual(before, setup.source_hash(setup.ENGINE_SOURCES))


if __name__ == "__main__":
    unittest.main()
