import json
import tempfile
import unittest
from pathlib import Path
from core.taleweavercmd import resize_obj_vertices, prepare_cmd_input


class TestScale(unittest.TestCase):
    def test_scale_obj_coordinates_only(self):
        with tempfile.TemporaryDirectory() as d:
            a, b = Path(d)/'a.obj', Path(d)/'b.obj'
            a.write_text('v 0.1 0.2 -0.4\nvt 0.1 0.2\nvn 0 1 0\nf 1/1/1 1/1/1 1/1/1\n')
            count = resize_obj_vertices(a, b, 8)
            self.assertEqual(count, 1)
            self.assertIn('v 0.8 1.6 -3.2', b.read_text())
            self.assertIn('vt 0.1 0.2', b.read_text())
            self.assertIn('vn 0 1 0', b.read_text())
            self.assertIn('v 0.1 0.2 -0.4', a.read_text())

    def test_stage_preserves_manual_points_and_rescales(self):
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)/'Hero'
            src = folder/'TaleWeaverCmd_Source'
            src.mkdir(parents=True)
            (src/'Hero.obj').write_text('v 0.1 0.2 0.3\n')
            for name in ('Albedo.png','Normal.png','MAES.png','thumbnail.png'):
                (src/name).write_bytes(b'x')
            stage = prepare_cmd_input(folder,'Hero',1.75,scale_factor=1)
            params = json.loads((stage/'params.json').read_text())
            params['PointsOfInterest']['Head']['x']=0.47
            (stage/'params.json').write_text(json.dumps(params))
            stage = prepare_cmd_input(folder,'Hero',1.75,preserve_params=True,scale_factor=8)
            new = json.loads((stage/'params.json').read_text())
            self.assertEqual(new['PointsOfInterest']['Head']['x'], 3.76)
            self.assertIn('v 0.8 1.6 2.4', (stage/'model.obj').read_text())
            self.assertEqual((src/'Hero.obj').read_text(), 'v 0.1 0.2 0.3\n')
            stage = prepare_cmd_input(folder,'Hero',1.75,preserve_params=True,scale_factor=10)
            newer = json.loads((stage/'params.json').read_text())
            self.assertAlmostEqual(newer['PointsOfInterest']['Head']['x'],4.7)
            self.assertIn('v 1 2 3', (stage/'model.obj').read_text())

    def test_invalid_scale(self):
        with tempfile.TemporaryDirectory() as d:
            a = Path(d)/'a.obj'; b=Path(d)/'b.obj'
            a.write_text('v 1 2 3\n')
            for scale in (0, -1, 101, float('nan'), float('inf')):
                with self.assertRaises(ValueError):
                    resize_obj_vertices(a,b,scale)

if __name__ == '__main__':
    unittest.main()
