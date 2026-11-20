"""Fork-specific guards for the quality-first native import."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class QualityEngineTest(unittest.TestCase):
    def test_version(self):
        self.assertIn('project(strata VERSION 0.1.63 LANGUAGES CXX)', (ROOT / 'CMakeLists.txt').read_text())

    def test_tail_skip_default_is_off_and_covered_by_native_ctest(self):
        cmake = (ROOT / 'cmake/backends/cpu.cmake').read_text()
        self.assertIn('add_test(NAME tail_skip_default_test', cmake)
        source = (ROOT / 'src/program/generate.cpp').read_text()
        self.assertNotIn('set_tail_skip_rank(7)', source, 'serve must not re-enable skipping implicitly')

    def test_qwen_cpu_build_does_not_register_the_separate_split_converter(self):
        cmake = (ROOT / 'cmake/backends/cpu.cmake').read_text()
        self.assertNotIn('add_executable(split_convert_parallel_test', cmake)
        self.assertNotIn('src/split/', cmake)
        self.assertIn('add_test(NAME split_ring_test', cmake)


if __name__ == '__main__':
    unittest.main()
