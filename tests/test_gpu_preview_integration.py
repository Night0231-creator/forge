"""Integration checks for GPU context lifecycle, CPU fallback and UI controls."""
import ast
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

class PreviewIntegrationTests(unittest.TestCase):
    def test_gpu_thread_does_not_call_tk(self):
        source=(ROOT/'ui/gpu_pbr_renderer.py').read_text(encoding='utf-8')
        ast.parse(source)
        self.assertIn('create_context(standalone=True,require=330)',source)
        self.assertIn('self._thread_check()',source)
        self.assertIn('_THREAD=threading.local()',source)
        self.assertIn("'CPU · Albedo",source)

    def test_gpu_worker_and_materials_connected(self):
        source=(ROOT/'ui/texture_viewer.py').read_text(encoding='utf-8')
        ast.parse(source)
        self.assertIn('ThreadPoolExecutor(max_workers=1',source)
        self.assertIn('self._pool.submit(worker)',source)
        self.assertIn('def set_materials(',source)
        self.assertIn('def set_lighting(',source)
        self.assertIn('self._backend_label',source)
        self.assertIn('shutdown(wait=False,cancel_futures=True)',source)

    def test_paint_materials_update_gpu_and_cpu_switch(self):
        source=(ROOT/'ui/painting_studio.py').read_text(encoding='utf-8')
        ast.parse(source)
        self.assertIn("('Usar prévia GPU',self._pbr_on,self._apply_lighting)",source)
        self.assertIn('self.viewer.set_materials(self.session.maes_image)',source)
        self.assertIn('self.viewer.set_lighting(',source)
        self.assertIn('self.session.apply_material_values(',source)

    def test_version_and_windows_bundles(self):
        from core.version import APP_VERSION
        self.assertEqual(APP_VERSION,'4.2.0')
        for name in ('build_windows.ps1','build_portable_windows.ps1'):
            content=(ROOT/'tools'/name).read_text(encoding='utf-8')
            self.assertIn('--collect-all moderngl',content)
            self.assertIn('--collect-all glcontext',content)

if __name__=='__main__':
    unittest.main()
