import ast
import unittest
from pathlib import Path


class UnityHandoffUiTests(unittest.TestCase):
    def test_ui_exposes_unity_route_without_modifying_cmd_schema(self):
        root = Path(__file__).resolve().parents[1]
        ui = (root/'app.py').read_text(encoding='utf-8')
        ast.parse(ui)
        self.assertIn('def _prepare_twl_handoff(self):', ui)
        self.assertIn('Preparar TaleWeaverLite (Transform visual + Default Scale 1×1)', ui)
        self.assertIn('default_scale=1', ui)
        cmd = (root/'core/taleweavercmd.py').read_text(encoding='utf-8')
        self.assertNotIn("'DefaultScale':", cmd)
        self.assertNotIn("'Default Scale':", cmd)
