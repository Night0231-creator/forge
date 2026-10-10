"""Interface checks: reference feature stays accessible and read-only."""
import ast
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class ReferenceUiTests(unittest.TestCase):
    def test_ui_declares_optional_reference_and_comparison(self):
        code=(ROOT/'app.py').read_text(encoding='utf-8')
        ast.parse(code)
        self.assertIn('self.tsmod_reference = tk.StringVar',code)
        self.assertIn('def _compare_tsmod_reference(self):',code)
        self.assertIn('def _choose_tsmod_reference(self):',code)
        self.assertIn('comparacao_tsmod_referencia.json',code)
        self.assertIn('self.tsmod_canvas.yview_scroll',code)

    def test_reference_check_never_mixes_with_blender_model(self):
        code=(ROOT/'core/tsmod.py').read_text(encoding='utf-8')
        ast.parse(code)
        self.assertIn('def compare_tsmod_reference(',code)
        self.assertIn('not',code.lower())
        self.assertNotIn('bytearray(',code)
