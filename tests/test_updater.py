import unittest
from core.updater import version_tuple, allowed, manifest_sha, UpdateError
class UpdaterTests(unittest.TestCase):
    def test_version(self):
        self.assertTrue(version_tuple('2.2.0') > version_tuple('2.1.0'))
    def test_origin(self):
        self.assertFalse(allowed('https://evil.example/setup.exe', True))
        self.assertFalse(allowed('http://github.com/Night0231-creator/forge/releases/download/v3/file.exe', True))
    def test_sha(self):
        s='a'*64+'  dist/installer/test.exe'
        self.assertEqual(manifest_sha(s, 'test.exe'), 'a'*64)
        with self.assertRaises(UpdateError):manifest_sha('bad', 'test.exe')


class DistributionModeTests(unittest.TestCase):
    def test_portable_zip_and_installed_app(self):
        import tempfile
        from pathlib import Path
        from unittest.mock import patch
        from core import updater
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            (base / '_internal').mkdir()
            exe = base / 'AstronyxMiniForgeStudio.exe'
            exe.write_bytes(b'test')
            with patch.object(updater.sys, 'platform', 'win32'), \
                 patch.object(updater.sys, 'frozen', True, create=True), \
                 patch.object(updater.sys, 'executable', str(exe)):
                self.assertTrue(updater.is_portable())
                (base / 'unins000.exe').write_bytes(b'test')
                self.assertFalse(updater.is_portable())

    def test_installer_build_is_folder_based(self):
        from pathlib import Path
        root = Path(__file__).resolve().parents[1]
        build = (root / 'tools/build_windows.ps1').read_text(encoding='utf-8')
        self.assertIn('--onedir', build)
        self.assertNotIn('--onefile', build)
        self.assertIn('--contents-directory', build)
        iss = (root / 'installer/AstronyxMiniForgeStudio.iss').read_text(encoding='utf-8')
        self.assertIn('recursesubdirs createallsubdirs', iss)
        self.assertIn('CloseApplications=yes', iss)
