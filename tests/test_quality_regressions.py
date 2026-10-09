"""Safety checks for v2.0.2 new scale and mesh quality defaults."""
import json
import tempfile
import unittest
from pathlib import Path
from core.preferences import load_preferences, save_preferences
from core.geometry import suggest_factor
from core.helpers import validate_config

class QualityRegressionTests(unittest.TestCase):
    def test_legacy_giant_preset_migrates_to_one_to_one(self):
        with tempfile.TemporaryDirectory() as t:
            path = Path(t) / 'settings.json'
            path.write_text(json.dumps({'scale_factor':'8','auto_scale':True,'target_height':'14'}),encoding='utf-8')
            prefs=load_preferences(path)
            self.assertEqual(prefs['target_height'],'1.75')
            self.assertEqual(prefs['scale_factor'],'1')

    def test_explicit_custom_presets_remain(self):
        with tempfile.TemporaryDirectory() as t:
            path=Path(t)/'settings.json'
            save_preferences(path, output_root=t, blender='', open_after_conversion=True,
                             target_height='2.5', scale_factor='1.25')
            prefs=load_preferences(path)
            self.assertEqual(prefs['target_height'],'2.5')
            self.assertEqual(prefs['scale_factor'],'1.25')

    def test_new_default_reference_not_eight_times(self):
        self.assertAlmostEqual(suggest_factor(1.75),1.0)

    def test_source_quality_defaults(self):
        with tempfile.TemporaryDirectory() as t:
            src=Path(t)/'hero.glb'
            src.write_bytes(b'stub')
            cfg=validate_config({'source':str(src),'output_root':str(Path(t)/'out')})
            self.assertEqual(cfg['tris'],100000)
            self.assertEqual(cfg['texture_size'],2048)

if __name__=='__main__':
    unittest.main()
