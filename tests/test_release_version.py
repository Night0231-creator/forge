"""Release consistency checks without requiring Windows."""
import unittest
from pathlib import Path
from core.version import APP_VERSION
ROOT=Path(__file__).resolve().parents[1]
class ReleaseVersionTests(unittest.TestCase):
    def test_version_is_22(self):
        self.assertEqual(APP_VERSION,'2.2.6')
    def test_installer_version_matches(self):
        iss=(ROOT/'installer/AstronyxMiniForgeStudio.iss').read_text(encoding='utf8')
        self.assertIn('#define StudioVersion "2.2.6"',iss)
        self.assertIn('Setup-v2.2.6',iss)
        self.assertIn('PrivilegesRequired=lowest',iss)
    def test_windows_metadata(self):
        info=(ROOT/'installer/windows_version_info.txt').read_text(encoding='utf8')
        self.assertIn('CompanyName',info)
        self.assertIn("'2.2.6.0'",info)
    def test_release_names(self):
        yml=(ROOT/'.github/workflows/build-windows.yml').read_text(encoding='utf8')
        self.assertIn('Setup-v2.2.6.exe',yml)
        self.assertIn('SHA256SUMS.txt',yml)
