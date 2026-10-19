"""Benchmark main-path regressions: local fixtures/mocks, no socket or child process."""
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from tools.test_bench_host import SB


class MainLaunch(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.cfg = Path(self.tmp.name) / 'strata-fixture.json'
        self.cfg.write_text(json.dumps({'host': '192.0.2.10', 'port': 9090, 'api_key': 'dummy-private-key'}))

    def test_empty_port_reaches_launch_and_cleans_failed_readiness(self):
        for override in (None, 9191):
            with self.subTest(override=override):
                proc = Mock()
                port = override or 9090
                base = f'http://192.0.2.10:{port}'
                args = ['--config', str(self.cfg), '--quiet']
                if override:
                    args += ['--port', str(override)]
                errors = io.StringIO()
                with patch.object(SB, 'is_strata', return_value=False), \
                     patch.object(SB, 'try_json', return_value=None) as health, \
                     patch.object(SB, 'start_server', return_value=proc) as start, \
                     patch.object(SB, 'wait_ready', return_value=False) as ready, \
                     patch.object(SB, 'stop_server') as stop, \
                     contextlib.redirect_stderr(errors):
                    self.assertEqual(SB.main(args), 1)
                health.assert_called_once_with(base, '/health', 'dummy-private-key', 3)
                start.assert_called_once()
                self.assertEqual(start.call_args.args[:3], (self.cfg, port, None))
                log_path = start.call_args.args[3]
                self.assertFalse(log_path.parent.exists())
                self.assertEqual(ready.call_args.args[:3], (base, 'dummy-private-key', proc))
                stop.assert_called_once_with(proc)
                self.assertNotIn('dummy-private-key', errors.getvalue())

    def test_non_strata_health_reports_port_without_spawning(self):
        errors = io.StringIO()
        with patch.object(SB, 'is_strata', return_value=False), \
             patch.object(SB, 'try_json', return_value={'other_service': True}), \
             patch.object(SB, 'start_server') as start, \
             patch.object(SB, 'stop_server') as stop, \
             contextlib.redirect_stderr(errors):
            self.assertEqual(SB.main(['--config', str(self.cfg), '--quiet']), 2)
        self.assertIn('Port 9090 is used', errors.getvalue())
        start.assert_not_called()
        stop.assert_not_called()


if __name__ == '__main__':
    unittest.main()
