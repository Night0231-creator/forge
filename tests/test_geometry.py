import json
import math
import tempfile
import unittest
from pathlib import Path
from core.geometry import inspect_obj, suggest_factor
from core.taleweavercmd import prepare_cmd_input


CUBE = '''# A small Y-up character model
v -0.2 0 -0.1
v 0.2 0 -0.1
v 0 1.75 0
v 0 1.0 0.1
vt 0 0
vn 0 1 0
f 1/1/1 2/1/1 3/1/1
f -3/-1/1 -2/-1/1 -1/-1/1
'''


class TestGeometry(unittest.TestCase):
    def test_obj_y_up_bounds(self):
        with tempfile.TemporaryDirectory() as folder:
            p = Path(folder)/'model.obj'
            p.write_text(CUBE, encoding='utf-8')
            result = inspect_obj(p)
            self.assertEqual(result.vertices, 4)
            self.assertEqual(result.faces, 2)
            self.assertEqual(result.height, 1.75)
            stats, verts, faces = inspect_obj(p, max_faces=100)
            self.assertEqual(stats.height, 1.75)
            self.assertEqual(len(verts), 4)
            self.assertEqual(len(faces), 2)
            self.assertEqual(faces[-1], (1,2,3))

    def test_auto_reference_14_units_produces_factor_8(self):
        self.assertAlmostEqual(suggest_factor(1.75, 14), 8)
        self.assertAlmostEqual(suggest_factor(7, 14), 2)
        self.assertAlmostEqual(suggest_factor(1.75, 7), 4)

    def test_invalid_dimension_is_rejected(self):
        for h in (0, -1, float('nan'), float('inf')):
            with self.assertRaises(ValueError):
                suggest_factor(h)
        with self.assertRaises(ValueError):
            suggest_factor(1.75, float('inf'))

    def test_auto_stage_works_and_preserves_editable_metadata(self):
        with tempfile.TemporaryDirectory() as folder:
            dest = Path(folder)/'Hero'
            src = dest/'TaleWeaverCmd_Source'
            src.mkdir(parents=True)
            (src/'Hero.obj').write_text(CUBE, encoding='utf-8')
            for filename in ('Albedo.png','MAES.png','Normal.png','thumbnail.png'):
                (src/filename).write_bytes(b'TEST')
            stage = prepare_cmd_input(dest,'Hero',height=1.75,target_height=14)
            actual = inspect_obj(stage/'model.obj')
            self.assertAlmostEqual(actual.height,14)
            params = json.loads((stage/'params.json').read_text())
            self.assertAlmostEqual(params['PointsOfInterest']['Head']['y'],12.46)
            params['PointsOfInterest']['Spell']['x']=1.42
            (stage/'params.json').write_text(json.dumps(params), encoding='utf-8')
            stage = prepare_cmd_input(dest,'Hero',height=1.75,preserve_params=True,target_height=7)
            after = json.loads((stage/'params.json').read_text())
            self.assertAlmostEqual(after['PointsOfInterest']['Spell']['x'],.71)
            self.assertAlmostEqual(inspect_obj(stage/'model.obj').height,7)
            self.assertEqual(inspect_obj(src/'Hero.obj').height,1.75)


if __name__ == '__main__':
    unittest.main()
