"""V3.0 UI contracts and packaging regressions (no Tk display required)."""
import ast
import os
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]


class UnifiedStudioTests(unittest.TestCase):
    def test_main_exe_defaults_to_unified_studio(self):
        source=(ROOT/'studio.py').read_text(encoding='utf-8')
        ast.parse(source)
        self.assertIn('from ui.studio_workspace import UnifiedStudio',source)
        self.assertIn("('home', '◈', 'Estúdio de Pintura', 'tab_workspace')",source)
        self.assertIn("self.workspace=UnifiedStudio(self.tab_workspace,self)",source)
        self.assertIn("self._navigate('home', 'tab_workspace')",source)
        self.assertIn("self.workspace.refresh(self.library_entries",source)

    def test_editor_is_embeddable_without_second_window(self):
        code=(ROOT/'ui/painting_studio.py').read_text(encoding='utf-8')
        ast.parse(code)
        self.assertIn('class PaintingStudio(tk.Frame):',code)
        self.assertIn('def _toggle_uv_panel(self):',code)
        self.assertIn('self.uv_panel.grid_remove()',code)
        self.assertIn('self.viewer.bind',code)
        self.assertIn('self._build_layers_tab',code)
        self.assertIn('self._build_materials_tab',code)
        self.assertIn("window=tk.Toplevel(parent)",code)
        self.assertIn('panel=PaintingStudio(window,project',code)

    def test_workspace_preserves_standalone_import_and_export(self):
        source=(ROOT/'ui/studio_workspace.py').read_text(encoding='utf-8')
        ast.parse(source)
        self.assertIn('class UnifiedStudio(tk.Frame):',source)
        self.assertIn("self.app._navigate('quick','tab_dashboard')",source)
        self.assertIn('on_exit=self._back_to_library',source)
        self.assertIn("'export','tab_cmd'",source)
        self.assertIn('self.app._install_library(self.current.tsmod)',source)
        self.assertIn('find_albedo(entry.folder)',source)


    @unittest.skipUnless(os.name == 'nt', 'GUI smoke targeted at Windows runner')
    def test_windows_gui_startup_creates_unified_editor_shell(self):
        import tkinter as tk
        try:
            probe=tk.Tk()
        except tk.TclError as exc:
            self.skipTest('Tk display unavailable: '+str(exc))
        else:
            probe.destroy()
        from studio import Studio
        app=Studio()
        jobs={app._startup_library_job,app._poll_update_job,
              app._startup_update_job,app._auto_update_job}
        jobs.discard(None)
        try:
            app.withdraw()
            app.update_idletasks()
            self.assertTrue(hasattr(app,'workspace'))
            self.assertTrue(hasattr(app.workspace,'workarea'))
            self.assertEqual(app.tabs.select(),str(app.tab_workspace))
        finally:
            app.destroy()
        self.assertFalse(jobs.intersection(app.tk.call('after','info')))

    def test_version(self):
        from core.version import APP_VERSION
        self.assertEqual(APP_VERSION,'5.0.0')


if __name__=='__main__':
    unittest.main()
