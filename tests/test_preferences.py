"""Tests for the destination chooser and open-folder preferences (stdlib only)."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from core.preferences import load_preferences, save_preferences, open_output_folder


class TestPreferences(unittest.TestCase):
    def test_new_install_auto_opens_by_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = load_preferences(Path(tmp) / 'settings.json')
            self.assertTrue(data['open_after_conversion'])
            self.assertEqual(data['output_root'], '')

    def test_previous_version_settings_migrate(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'settings.json'
            path.write_text(json.dumps({'blender': r'C:\Blender\blender.exe',
                                        'output_root': r'D:\Meus Personagens'}), encoding='utf-8')
            data = load_preferences(path)
            self.assertTrue(data['open_after_conversion'])
            self.assertEqual(data['output_root'], r'D:\Meus Personagens')

    def test_remember_checked_and_unchecked_settings(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'prefs' / 'settings.json'
            for option in (False, True):
                save_preferences(path, output_root=r'D:\Minis\Astronyx',
                                 blender=r'C:\Blender\blender.exe', open_after_conversion=option)
                data = load_preferences(path)
                self.assertEqual(data['open_after_conversion'], option)
                self.assertEqual(data['output_root'], r'D:\Minis\Astronyx')

    def test_corrupt_settings_do_not_crash(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'settings.json'
            path.write_text('[wrong]', encoding='utf-8')
            self.assertTrue(load_preferences(path)['open_after_conversion'])
            path.write_text('{invalid json', encoding='utf-8')
            self.assertTrue(load_preferences(path)['open_after_conversion'])

    def test_open_folder_requires_existing_folder(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(FileNotFoundError):
                open_output_folder(Path(tmp) / 'not_created')

    def test_open_folder_uses_list_argument(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / 'Miniatura & 01'
            folder.mkdir()
            with patch('core.preferences.os.name', 'posix'), \
                 patch('core.preferences.sys.platform', 'linux'), \
                 patch('core.preferences.subprocess.Popen') as proc:
                open_output_folder(folder)
                proc.assert_called_once_with(['xdg-open', str(folder)])


if __name__ == '__main__':
    unittest.main()
