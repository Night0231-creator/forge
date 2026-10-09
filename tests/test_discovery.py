import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from core.discovery import parse_steam_libraryfolders, find_taleweavercmd, steam_libraries, tool_status


class DiscoveryTests(unittest.TestCase):
    def test_parses_windows_and_unix_library_paths(self):
        text = '"path" "D:\\\\SteamLibrary"\n"path" "/data/steamgames"'
        self.assertEqual([str(p) for p in parse_steam_libraryfolders(text)],
                         ['D:\\SteamLibrary', str(Path('/data/steamgames'))])

    def test_detects_cmd_in_additional_library(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / 'Steam'
            second = Path(temp) / 'OtherGames'
            conf = root / 'steamapps' / 'libraryfolders.vdf'
            conf.parent.mkdir(parents=True)
            conf.write_text('"path" "' + str(second) + '"', encoding='utf-8')
            exe = second / 'steamapps/common/TaleSpire/Tools/TaleWeaverCmd/Windows/TaleWeaverCmd.exe'
            exe.parent.mkdir(parents=True)
            exe.write_bytes(b'EXE')
            self.assertIn(second, steam_libraries([root]))
            self.assertEqual(find_taleweavercmd([root]), str(exe))

    def test_tool_status(self):
        with tempfile.TemporaryDirectory() as tmp:
            exe = Path(tmp) / 'blender.exe'
            exe.touch()
            self.assertEqual(tool_status(str(exe), ''), (True, False))
