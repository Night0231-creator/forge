import tempfile
import unittest
from pathlib import Path

from core.scale_profile import (
    BASECOAT_VISUAL_PRESET_NAME, is_meshy_model, preset_values,
    suggested_calibration_height,
)
from core.geometry import ObjStats, suggest_safe_factor
from core.scale_audit import audit_scale


class BasecoatVisualPresetTests(unittest.TestCase):
    def test_preset_is_visual_only_not_binary_scale_extraction(self):
        self.assertIn('Basecoat', BASECOAT_VISUAL_PRESET_NAME)
        data = preset_values()
        self.assertEqual(data['height'], '1.75')
        self.assertEqual(data['target_height'], '1.75')
        self.assertTrue(data['auto_scale'])
        self.assertTrue(data['cmd_enabled'])
        self.assertFalse(data['plugin'])
        self.assertEqual(data['resolution'], '2048')

    def test_valid_meshy_file_detection_and_manual_entry(self):
        with tempfile.TemporaryDirectory() as tmp:
            model = Path(tmp) / 'Warrior GLB.GLB'
            model.write_bytes(b'fixture')
            self.assertTrue(is_meshy_model(str(model)))
            self.assertFalse(is_meshy_model(str(Path(tmp) / 'not_found.glb')))
            self.assertFalse(is_meshy_model(str(Path(tmp) / 'texture.png')))

    def test_wings_do_not_shrink_character_or_double_scale(self):
        # Reference height is 1.75. 6-unit wings must not make the body tiny.
        wide = ObjStats(6, 3, (-3, 0, -.5), (3, 1.75, .5))
        self.assertAlmostEqual(suggest_safe_factor(wide), 1.0)
        report = audit_scale(wide)
        self.assertAlmostEqual(report.effective_height, 1.75)
        self.assertFalse(report.footprint_limited)
        self.assertAlmostEqual(report.effective_width, 6.0)

    def test_calibration_is_explicit_bounded_and_increases_height(self):
        self.assertAlmostEqual(suggested_calibration_height(1.75,1.25),2.188)
        self.assertAlmostEqual(suggested_calibration_height(2.188,1.25),2.735)
        for ratio in (-1, 0, float('nan'), 200):
            with self.assertRaises(ValueError):
                suggested_calibration_height(1.75,ratio)


if __name__ == '__main__':
    unittest.main()
