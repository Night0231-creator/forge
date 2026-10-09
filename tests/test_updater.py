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
