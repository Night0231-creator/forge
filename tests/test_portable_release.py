"""Release compatibility and distribution contracts."""
import unittest
from pathlib import Path
from core.version import APP_VERSION

ROOT=Path(__file__).resolve().parents[1]

class PortableDistributionTests(unittest.TestCase):
    def test_version(self):
        self.assertEqual(APP_VERSION,'2.2.4')
    def test_portable_does_not_use_onefile(self):
        script=(ROOT/'tools/build_portable_windows.ps1').read_text(encoding='utf8')
        self.assertIn('--onedir',script)
        self.assertNotIn('--onefile',script)
        self.assertIn('--contents-directory',script)
    def test_release_includes_zip_and_installer(self):
        flow=(ROOT/'.github/workflows/build-windows.yml').read_text(encoding='utf8')
        self.assertIn('AstronyxMiniForgeStudio-Portable-v2.2.4-Win10-Win11-x64.zip',flow)
        self.assertIn('Setup-v2.2.4.exe',flow)
        self.assertIn('needs: [windows, compatibility]',flow)
    def test_updater_handles_portable(self):
        from core.updater import is_portable
        self.assertIsInstance(is_portable(),bool)
    def test_installer_publisher_and_version(self):
        info=(ROOT/'installer/AstronyxMiniForgeStudio.iss').read_text(encoding='utf8')
        self.assertIn('2.2.4',info)
        self.assertIn('PrivilegesRequired=lowest',info)
