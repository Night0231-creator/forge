import ast
import unittest
from pathlib import Path

class BlenderPipelineSourceTests(unittest.TestCase):
    def test_syntax_and_modern_smoothing(self):
        code=(Path(__file__).resolve().parents[1]/'core/blender_pipeline.py').read_text(encoding='utf8')
        ast.parse(code)
        self.assertNotIn('obj.data.use_auto_smooth',code)
        self.assertIn('bmesh.ops.recalc_face_normals',code)
        self.assertIn("stats['footprint_scale_applied']",code)
