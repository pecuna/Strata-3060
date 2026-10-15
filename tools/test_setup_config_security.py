"""Credential-bearing generated config backups stay private and untracked."""
import json
import os
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock
import setup

ROOT = Path(__file__).resolve().parents[1]

class ConfigBackupSecurity(unittest.TestCase):
    def fixture(self, root):
        path = root / 'strata-fixture.json'
        old = dict(exe='engine', args=['--spec','2'], api_key='fixture-key')
        path.write_text(json.dumps(old))
        path.chmod(0o600)
        return path, old, dict(exe='engine',args=['--spec','4'])

    def test_new_backup_is_private_even_with_permissive_umask(self):
        with tempfile.TemporaryDirectory() as directory:
            path, old, new = self.fixture(Path(directory))
            previous = os.umask(0o022)
            try:
                setup.write_setup_config(path,new)
            finally:
                os.umask(previous)
            backup = path.with_suffix('.json.bak')
            self.assertEqual(stat.S_IMODE(backup.stat().st_mode), 0o600)
            self.assertEqual(json.loads(backup.read_text()),old)

    def test_existing_backup_link_never_overwrites_its_target(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            path,old,new=self.fixture(root)
            target=root/'unrelated';target.write_text('untouched')
            backup=path.with_suffix('.json.bak');backup.symlink_to(target)
            setup.write_setup_config(path,new)
            self.assertEqual(target.read_text(),'untouched')
            self.assertFalse(backup.is_symlink())
            self.assertEqual(json.loads(backup.read_text()),old)
            self.assertEqual(stat.S_IMODE(backup.stat().st_mode),0o600)

    def test_primary_config_is_private_and_never_uses_predictable_tmp(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);path,old,new=self.fixture(root)
            target=root/'unrelated';target.write_text('untouched')
            path.with_suffix('.json.tmp').symlink_to(target)
            setup.write_config(path,new)
            self.assertEqual(target.read_text(),'untouched')
            self.assertEqual(stat.S_IMODE(path.stat().st_mode),0o600)
            self.assertEqual(json.loads(path.read_text()),new)

    def test_primary_write_failure_preserves_original_and_cleans_temp(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);path,old,new=self.fixture(root)
            with mock.patch.object(setup.os,'replace',side_effect=OSError('fixture failure')):
                with self.assertRaises(OSError):
                    setup.write_config(path,new)
            self.assertEqual(json.loads(path.read_text()),old)
            self.assertEqual(list(root.glob('.strata-config-*')),[])

    def test_generated_backups_are_git_ignored(self):
        result=subprocess.run(['git','check-ignore','--no-index','strata-fixture.json.bak'],
                              cwd=ROOT,capture_output=True,text=True)
        self.assertEqual(result.returncode,0)

    def test_failed_backup_install_cleans_private_temporary_file(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);path,old,new=self.fixture(root)
            original_replace = setup.os.replace
            def refuse_backup(source, destination):
                if str(destination).endswith('.bak'):
                    raise OSError('fixture failure')
                return original_replace(source, destination)
            with mock.patch.object(setup.os,'replace',side_effect=refuse_backup):
                setup.write_setup_config(path,new)
            self.assertEqual(list(root.glob('.strata-config-*')),[])
