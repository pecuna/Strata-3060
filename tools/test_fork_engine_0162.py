"""Candidate-only engine 0.1.62 integration gates (no GPU/network)."""
from pathlib import Path
import ast
import struct
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

import setup

ROOT = Path(__file__).resolve().parents[1]


class Engine0162Integration(unittest.TestCase):
    def test_engine_version_and_unmoved_service_entrypoints(self):
        self.assertRegex((ROOT / 'CMakeLists.txt').read_text(),
                         r'project\(strata VERSION 0\.1\.(?:62|63) LANGUAGES CXX\)')
        for relative in ('setup.py', 'serve/server.py', 'tools/vision/CMakeLists.txt'):
            self.assertTrue((ROOT / relative).is_file(), relative)
        self.assertFalse((ROOT / 'terminal').exists(), 'do not migrate the managed application layout')


    def test_vendored_native_input_changes_and_removal_invalidate_build(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            native = root / 'third_party/strata-ggml/ggml/src/ggml.c'
            native.parent.mkdir(parents=True)
            native.write_text('first input\n')
            with mock.patch.object(setup, 'ROOT', root):
                original = setup.source_hash(setup.ENGINE_SOURCES)
                native.write_text('changed input\n')
                changed = setup.source_hash(setup.ENGINE_SOURCES)
                self.assertNotEqual(original, changed, 'new vendored native sources must be fingerprinted')
                native.unlink()
                removed = setup.source_hash(setup.ENGINE_SOURCES)
                self.assertNotEqual(changed, removed, 'removing a native input must invalidate the build')


    def test_native_builds_do_not_select_removed_mmq_or_vision_ggml(self):
        tree = ast.parse((ROOT / 'setup.py').read_text())
        calls = []
        for node in ast.walk(tree):
            if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                    and node.func.id == 'cmake_build' and len(node.args) >= 4
                    and isinstance(node.args[2], ast.Constant) and node.args[2].value == 'strata'):
                calls.append(node)
                strings = [n.value for n in ast.walk(node.args[3])
                           if isinstance(n, ast.Constant) and isinstance(n.value, str)]
                self.assertFalse(any(s.startswith(('-DSTRATA_GGML_DIR=', '-DSTRATA_MMQ_',
                                                   '-DSTRATA_PREFILL_MMQ=')) for s in strings), strings)
        self.assertEqual(len(calls), 2, 'check both existing CUDA and HIP native build paths')
        # The independent, unchanged image reader still needs its pinned llama.cpp.
        self.assertIn('-DLLAMA_DIR={llama}', (ROOT / 'setup.py').read_text())


    def test_native_gpu_fixtures_prepare_without_a_vision_checkout(self):
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run([sys.executable, str(ROOT / 'tools/iq_fixture.py'),
                                     '--out', directory, '--rows', '2', '--cols', '256'],
                                    cwd=ROOT, capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stderr)
            expected = {
                'IQ2_XXS': (16, 256, 66), 'IQ2_XS': (17, 256, 74),
                'IQ2_S': (22, 256, 82), 'IQ3_XXS': (18, 256, 98),
                'IQ3_S': (21, 256, 110), 'IQ1_M': (29, 256, 56),
                'IQ4_NL': (20, 32, 18), 'IQ4_XS': (23, 256, 136),
                'Q2_0': (42, 64, 18), 'Q3_K': (11, 256, 110),
            }
            folder = Path(directory)
            self.assertEqual({p.stem for p in folder.glob('*.bin')}, set(expected))
            self.assertEqual({p.stem for p in folder.glob('*.f32')}, set(expected))
            for name, (type_id, block_values, block_bytes) in expected.items():
                with self.subTest(fixture=name):
                    blob = (folder / (name + '.bin')).read_bytes()
                    self.assertEqual(struct.unpack('<3i', blob[:12]), (type_id, 2, 256))
                    self.assertEqual(len(blob), 12 + (2 * 256 // block_values) * block_bytes)
                    self.assertEqual((folder / (name + '.f32')).stat().st_size, 2 * 256 * 4)


if __name__ == '__main__':
    unittest.main()
