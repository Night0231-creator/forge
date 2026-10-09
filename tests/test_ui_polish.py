"""Presentation contract tests without opening the conversion engine."""
import ast
import unittest
from pathlib import Path
from types import SimpleNamespace
from ui.theme import gallery_columns
from ui.hud22 import filter_miniatures

class VisualPolishTests(unittest.TestCase):
    def test_responsive_columns(self):
        self.assertEqual([gallery_columns(w) for w in (400,540,820,1170)], [1,2,3,4])
    def test_filtered_search_casefold(self):
        models=[SimpleNamespace(name='Eclipse_Warlord',tsmod='x'),
                SimpleNamespace(name='Ice_Dragon',tsmod=None)]
        self.assertEqual([x.name for x in filter_miniatures(models,'eClIpSe')], ['Eclipse_Warlord'])
        self.assertEqual(len(filter_miniatures(models,'','Prontos')),1)
    def test_studio_and_ui_are_syntactically_valid(self):
        root=Path(__file__).resolve().parents[1]
        for path in ('studio.py','ui/hud22.py','ui/theme.py'):
            with self.subTest(path=path):
                ast.parse((root/path).read_text(encoding='utf8'))
    def test_no_pipeline_changes_needed(self):
        root=Path(__file__).resolve().parents[1]
        source=(root/'studio.py').read_text(encoding='utf8')
        self.assertIn('def _on_library_resize',source)
        self.assertIn('self._render_library_entries()',source)
