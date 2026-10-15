"""Fork acquisition instructions must not silently send users upstream."""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class ForkRoutes(unittest.TestCase):
    def test_web_ui_does_not_claim_network_is_impossible(self):
        text = (ROOT / "serve/web/index.html").read_text()
        self.assertNotIn("Nothing leaves it", text)
        self.assertIn("Configured MCP tools can use the network", text)
        self.assertIn("https://github.com/pecuna/Strata-3060", text)

    def test_dynamic_ui_preserves_network_disclosure(self):
        text = (ROOT / "serve/web/app.js").read_text()
        self.assertNotIn("Nothing leaves it", text)
        self.assertIn("Configured MCP tools can use the network", text)

    def test_archive_update_hints_target_this_fork(self):
        for name in ("update.sh", "UPDATE.bat"):
            with self.subTest(name=name):
                text = (ROOT / name).read_text()
                self.assertIn("https://github.com/pecuna/Strata-3060/archive/refs/heads/main.zip", text)
                self.assertNotIn("https://github.com/Niko1221/Strata/archive/refs/heads/main.zip", text)

    def test_primary_readme_targets_fork_and_accurate_privacy(self):
        text = (ROOT / "README.md").read_text()
        self.assertIn("https://github.com/pecuna/Strata-3060/archive/refs/heads/main.zip", text)
        self.assertIn("Set up Strata on this PC for me: https://github.com/pecuna/Strata-3060", text)
        self.assertIn("docs/FORK_SECURITY.md", text)
        self.assertNotIn("Nothing leaves your PC.", text)
        self.assertNotIn('src="https://cdn.buymeacoffee.com/', text)


if __name__ == "__main__":
    unittest.main()
