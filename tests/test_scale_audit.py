"""Checks that scale diagnosis matches TaleWeaverCmd automatic scaling."""
import json
import tempfile
import unittest
from pathlib import Path

from core.geometry import ObjStats, inspect_obj, suggest_safe_factor
from core.scale_audit import audit_scale
from core.taleweavercmd import prepare_cmd_input


class ScaleAuditTests(unittest.TestCase):
    def test_humanoid_keeps_reference_height(self):
        stats = ObjStats(4, 2, (-.2, 0, -.3), (.2, 1.75, .3))
        report = audit_scale(stats)
        self.assertFalse(report.footprint_limited)
        self.assertEqual(report.status, 'altura_alvo')
        self.assertAlmostEqual(report.effective_height, 1.75)
        self.assertAlmostEqual(report.applied_factor, suggest_safe_factor(stats))
        self.assertIn('collider', report.summary())

    def test_accessories_limit_height_and_report_reason(self):
        stats = ObjStats(4, 2, (-2, 0, -.5), (2, 2, .5))
        report = audit_scale(stats, footprint_limit=1.30)
        self.assertTrue(report.footprint_limited)
        self.assertEqual(report.status, 'base_limitada')
        self.assertAlmostEqual(report.applied_factor, .325)
        self.assertAlmostEqual(report.effective_height, .65)
        self.assertLessEqual(report.effective_width, 1.3)
        self.assertIn('asas', report.explanation().lower())

    def test_invalid_dimensions_still_rejected(self):
        stats = ObjStats(3, 1, (0, 0, 0), (1, 0, 1))
        with self.assertRaises(ValueError):
            audit_scale(stats)
        stats = ObjStats(4, 2, (0, 0, 0), (1, 1.75, 1))
        with self.assertRaises(ValueError):
            audit_scale(stats, footprint_limit=float('nan'))

    def test_staged_scale_audit_is_saved_without_changing_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'Knight'
            folder = root / 'TaleWeaverCmd_Source'
            folder.mkdir(parents=True)
            source = folder / 'Knight.obj'
            original = 'v -2 0 -.5\nv 2 0 .5\nv 0 2 0\nf 1 2 3\n'
            source.write_text(original, encoding='utf-8')
            for png in ('Albedo.png', 'Normal.png', 'MAES.png', 'thumbnail.png'):
                (folder / png).write_bytes(b'fixture')
            stage = prepare_cmd_input(root, 'Knight', target_height=1.75)
            audit = json.loads((root / 'TaleWeaverCmd_escala.json').read_text())['scale_check']
            self.assertFalse(audit['footprint_limited'])
            self.assertAlmostEqual(audit['effective_height'], 1.75)
            self.assertAlmostEqual(audit['effective_height'],
                                   inspect_obj(stage / 'model.obj').height)
            self.assertEqual(source.read_text(encoding='utf-8'), original)

    def test_wide_wings_keep_full_requested_height_by_default(self):
        stats = ObjStats(6, 2, (-3, 0, -.5), (3, 2, .5))
        report = audit_scale(stats)
        self.assertFalse(report.footprint_limited)
        self.assertAlmostEqual(report.effective_height, 1.75)
        self.assertGreater(report.effective_width, 1.30)
        self.assertIn('A altura-alvo foi preservada', report.explanation())


if __name__ == '__main__':
    unittest.main()
