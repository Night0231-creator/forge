"""Release guardrails: normalized scale must not call legacy width shrinking."""
import ast
import unittest
from pathlib import Path


class NoTinyMinisSourceTests(unittest.TestCase):
    def test_blender_size_is_not_clamped_to_1_3(self):
        source=(Path(__file__).resolve().parents[1]/'core/blender_pipeline.py').read_text(encoding='utf8')
        ast.parse(source)
        normal=source.split('def normalize_model(',1)[1].split('\ndef optimize(',1)[0]
        self.assertNotIn('enforce_footprint(obj)',normal)
        self.assertIn("'footprint_scale': 1.0",normal)
        self.assertIn('cfg[\'height\'] / height',normal)

    def test_auto_preset_applies_to_meshy_on_source_change(self):
        source=(Path(__file__).resolve().parents[1]/'app.py').read_text(encoding='utf8')
        ast.parse(source)
        self.assertIn("self.source.trace_add('write', self._on_meshy_source_changed)",source)
        self.assertIn('def _apply_basecoat_visual_preset(self):',source)
        self.assertIn('def _increase_visual_size(self):',source)
        self.assertIn("self.auto_import_preset",source)
