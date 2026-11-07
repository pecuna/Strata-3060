"""Source-only 0.1.58 backport gates; no GPU or network required."""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
BASE = "83ed4f4fab751703e0284ecc75f8cf4ecd4c891c"


class Engine0157Import(unittest.TestCase):
    def test_native_version_and_qwen_only_guard(self):
        text = (ROOT / "CMakeLists.txt").read_text()
        self.assertIn("project(strata VERSION 0.1.58 LANGUAGES CXX)", text)
        self.assertIn("This fork imports the Qwen engine only; STRATA_BUILD_DSV41 is unsupported", text)
        self.assertFalse((ROOT / "src/dsv41").exists())
        self.assertFalse((ROOT / "src/split").exists())

    def test_application_and_acquisition_bytes_preserved(self):
        # Compare every baseline tracked application/acquisition file, not just entry points.
        paths = subprocess.check_output(
            ["git", "ls-tree", "-r", "--name-only", BASE, "serve", "setup.py", "setup.sh", "update.sh", "sycl", "metal", "tools/mtp_fetch.py", "tools/mtp_verify.py"],
            cwd=ROOT, text=True,
        ).splitlines()
        self.assertGreater(len(paths), 50)
        for path in paths:
            with self.subTest(path=path):
                before = subprocess.check_output(["git", "show", f"{BASE}:{path}"], cwd=ROOT)
                self.assertEqual(hashlib.sha256(before).digest(), hashlib.sha256((ROOT / path).read_bytes()).digest())

    @unittest.skipUnless(shutil.which("g++"), "g++ required for native policy gates")
    def test_actual_sm86_defaults_and_pcie_overrides(self):
        # Compile/link the production NVIDIA-default resolver and PCIe rule, not a mock.
        source = r'''
#include "strata/core/nv_defaults.hpp"
#include "strata/core/pcie_share_rule.hpp"
#include <cassert>
#include <cstdlib>
#include <string>
int main() {
    using namespace strata;
    using namespace strata::core;
    unsetenv("STRATA_NV_KQ_DEFAULT"); unsetenv("STRATA_MMQ_KQ");
    unsetenv("STRATA_DEFAULTS"); unsetenv("STRATA_EMULATE_CC");
    assert(nv_kq_default_env(8, 6, false).size() == 1);
    assert(nv_kq_default_env(7, 5, false).empty());
    assert(nv_kq_default_env(8, 6, true).empty());
    setenv("STRATA_NV_KQ_DEFAULT", "0", 1);
    assert(nv_kq_default_env(8, 6, false).empty());
    unsetenv("STRATA_NV_KQ_DEFAULT");
    setenv("STRATA_MMQ_KQ", "0", 1);
    assert(apply_nv_kq_default(8, 6).empty());
    assert(std::string(std::getenv("STRATA_MMQ_KQ")) == "0");
    unsetenv("STRATA_MMQ_KQ");
    assert(apply_nv_kq_default(8, 6).size() == 1);
    assert(std::string(std::getenv("STRATA_MMQ_KQ")) == "1");
    assert(pcie_auto_split_default(false, true, false, nullptr));
    assert(!pcie_auto_split_default(false, true, false, "0"));
    assert(!pcie_auto_split_default(false, true, true, nullptr));
    assert(!pcie_auto_split_default(true, true, false, nullptr));
    assert(pcie_auto_split_default(true, true, false, "1"));
    assert(pcie_k_rule_default(true, false, nullptr));
    assert(!pcie_k_rule_default(true, false, "0"));
    assert(pcie_share_ceiling(true, false, nullptr) == 0.95);
    assert(pcie_share_ceiling(true, true, nullptr) == 0.60);
    assert(pcie_share_ceiling(true, false, "0.5") == 0.5);
    assert(pcie_share_ceiling(true, false, "2") == 1.0);
    assert(pcie_share_ceiling(true, false, "0") == 0.1);
}
'''
        with tempfile.TemporaryDirectory() as directory:
            cpp = Path(directory) / "policy.cpp"
            exe = Path(directory) / "policy"
            cpp.write_text(source)
            built = subprocess.run(["g++", "-std=c++20", "-UNDEBUG", "-I", str(ROOT / "include"), str(cpp), str(ROOT / "src/core/nv_defaults.cpp"), "-o", str(exe)], capture_output=True, text=True, timeout=60)
            self.assertEqual(built.returncode, 0, built.stderr)
            env = {k: v for k, v in os.environ.items() if not k.startswith("STRATA_")}
            run = subprocess.run([str(exe)], env=env, capture_output=True, text=True, timeout=10)
            self.assertEqual(run.returncode, 0, run.stderr)


if __name__ == "__main__":
    unittest.main()
