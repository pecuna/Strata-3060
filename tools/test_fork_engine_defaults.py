"""GPU-free compiled checks for the owner fork's Qwen routing policy."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(shutil.which("c++"), "a C++ compiler is required")
class RoutingPolicy(unittest.TestCase):
    def test_unset_residency_bias_is_off(self):
        source = r'''
#include "strata/core/sm120_series.hpp"
#include <cstdlib>
int main() {
    const double GiB = 1073741824.0;
    for (double size : {8.0, 12.0, 13.0, 16.0, 72.0}) {
        if (strata::route_prior_default(false, false, size * GiB) != 0.0f) return 10;
    }
    if (strata::route_prior_default(true, false, 12.0 * GiB) != 0.0f) return 11;
    // The fork's default is the original target-model routing on all devices.
    return 0;
}
'''
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)
            cpp = path / "policy.cpp"
            cpp.write_text(source)
            exe = path / "policy"
            built = subprocess.run(["c++", "-std=c++20", "-include", "initializer_list", "-I", str(ROOT / "include"), str(cpp), "-o", str(exe)], capture_output=True, text=True)
            self.assertEqual(built.returncode, 0, built.stdout + built.stderr)
            env = dict(os.environ, STRATA_ROUTE_PRIOR="1.5")
            result = subprocess.run([str(exe)], env=env, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, "fork must retain original routing unless explicitly opted in")


    def test_actual_verifier_resolver_honors_explicit_route_prior(self):
        text = (ROOT / "src/core/verify.cpp").read_text()
        resolver = text.split("inline float g_route_prior() {", 1)[1].split("inline bool g_qfuse()", 1)[0]
        # Compile the actual production function with its HIP no-device branch.
        # This tests override precedence without substituting a duplicate resolver.
        source = '#include <cstdlib>\n#include <cstdio>\n#define STRATA_USE_HIP 1\n'
        source += "inline float g_route_prior() {" + resolver
        source += '\nint main() { std::printf("%.1f", (double)g_route_prior()); }\n'
        with tempfile.TemporaryDirectory() as folder:
            cpp = Path(folder) / "resolver.cpp"
            cpp.write_text(source)
            exe = Path(folder) / "resolver"
            built = subprocess.run(["c++", "-std=c++20", str(cpp), "-o", str(exe)], capture_output=True, text=True)
            self.assertEqual(built.returncode, 0, built.stderr)
            for value, expected in ((None, "0.0"), ("0", "0.0"), ("1.5", "1.5")):
                with self.subTest(value=value):
                    env = dict(os.environ)
                    env.pop("STRATA_ROUTE_PRIOR", None)
                    if value is not None:
                        env["STRATA_ROUTE_PRIOR"] = value
                    result = subprocess.run([str(exe)], env=env, capture_output=True, text=True, check=True)
                    self.assertEqual(result.stdout, expected)


if __name__ == "__main__":
    unittest.main()
