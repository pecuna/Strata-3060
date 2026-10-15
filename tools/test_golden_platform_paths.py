"""Golden fixtures compare vision executable names across Windows/Linux."""
import unittest
from pathlib import Path
from tools.test_setup_golden import normalize


class VisionExecutableNormalization(unittest.TestCase):
    def test_vision_name_is_platform_independent(self):
        root = Path('/fixture')
        self.assertEqual(normalize('/fixture/engine/strata-vision', root),
                         normalize('/fixture/engine/strata-vision.exe', root))

    def test_non_executable_filename_is_not_rewritten(self):
        root = Path('/fixture')
        self.assertEqual(normalize('/fixture/strata-vision.example', root),
                         '<T>/strata-vision.example')
