"""Golden fixtures compare vision executable names across Windows/Linux."""
import unittest
from pathlib import Path
from unittest.mock import patch
from tools.test_setup_golden import normalize, install, argv_for, PROFILES, setup


class VisionExecutableNormalization(unittest.TestCase):
    def test_vision_name_is_platform_independent(self):
        root = Path('/fixture')
        self.assertEqual(normalize('/fixture/engine/strata-vision', root),
                         normalize('/fixture/engine/strata-vision.exe', root))

    def test_non_executable_filename_is_not_rewritten(self):
        root = Path('/fixture')
        self.assertEqual(normalize('/fixture/strata-vision.example', root),
                         '<T>/strata-vision.example')


class GoldenHardwareIsolation(unittest.TestCase):
    def test_cpu_vision_uses_fixture_not_execution_host_threads(self):
        ram, found = PROFILES['96GB-1x16GB']
        for host_threads in (4, 32):
            with self.subTest(host_threads=host_threads), patch.object(setup.os, 'cpu_count', return_value=host_threads):
                code, out, cfg, _ = install(ram, found, argv_for('unsloth', 'UD-Q4_K_XL'))
                self.assertEqual(code, 0, out[-1000:])
                assert cfg is not None
                self.assertFalse(cfg['vision']['gpu'])
                self.assertEqual(cfg['vision']['threads'], 6)
