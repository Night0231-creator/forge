"""Exercise the real desktop editor on Windows CI or an available X display."""
import os
import tempfile
import tkinter as tk
import unittest
from pathlib import Path
from types import SimpleNamespace
from PIL import Image

from ui.painting_studio import PaintingStudio


@unittest.skipUnless(os.name=='nt' or os.environ.get('DISPLAY'), 'Desktop display required')
class DesktopSurfaceTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        project=Path(self.tmp.name)
        (project/'TaleWeaverLite').mkdir()
        source=project/'TaleWeaverCmd_Source'
        source.mkdir()
        (source/'test.obj').write_text(
            'v -1 -1 0\nv 1 -1 0\nv 1 1 0\nv -1 1 0\n'
            'vt .05 .05\nvt .4 .05\nvt .4 .4\n'
            'vt .6 .6\nvt .9 .9\nvt .6 .9\n'
            'f 1/1 2/2 3/3\nf 1/4 3/5 4/6\n')
        for folder in (source,project/'TaleWeaverLite'):
            Image.new('RGBA',(257,257),'white').save(folder/'Albedo.png')
            Image.new('RGBA',(257,257),(0,255,0,30)).save(folder/'MAES.png')
        self.root=tk.Tk()
        self.addCleanup(self.root.destroy)
        self.root.geometry('1280x720')
        self.panel=PaintingStudio(self.root,project)
        self.panel.pack(fill='both',expand=True)
        self.root.update_idletasks()
        self.root.update()

    def event(self):
        pick=self.panel._picker_for_camera()
        return SimpleNamespace(x=float(pick.x.mean()),y=float(pick.y.mean()))

    def test_real_click_fills_geometry_across_uv_seam_and_undo(self):
        self.panel.mode.set('regiao')
        self.panel._paint3d_start(self.event())
        self.assertIsNotNone(self.panel.session.selection)
        self.panel.mode.set('balde')
        self.panel.color.set('#00AAFF')
        self.panel._paint3d_start(self.event())
        self.assertEqual(self.panel.session.pick(70,200),'#00AAFF')
        self.assertEqual(self.panel.session.pick(180,65),'#00AAFF')
        self.panel._undo()
        self.assertEqual(self.panel.session.pick(70,200),'#FFFFFF')

    def test_surface_stroke_and_custom_material_callbacks(self):
        event=self.event()
        self.panel._paint3d_start(event)
        self.panel._paint3d_drag(SimpleNamespace(x=event.x+30,y=event.y))
        self.panel._paint3d_end(event)
        self.assertIsNotNone(self.panel.session.layers[0].pixels.getbbox())
        self.panel.mode.set('regiao')
        self.panel._paint3d_start(event)
        for variable,value in zip(self.panel._material_channels,(120,240,75,180)):
            variable.set(value)
        self.panel._apply_material()
        self.assertEqual(self.panel.session.maes_image.getpixel((70,200)),(120,240,75,180))
        self.panel._undo()
        self.assertEqual(self.panel.session.maes_image.getpixel((70,200)),(0,255,0,30))
        self.assertGreater(self.panel.viewer.winfo_width(),400)

    def test_closing_editor_cancels_pending_texture_and_preview_renders(self):
        self.panel._request_refresh()
        self.panel._schedule_preview()
        jobs={self.panel._refresh_id,self.panel._preview_job}
        self.assertNotIn(None,jobs)
        self.assertTrue(jobs.issubset(set(self.root.tk.call('after','info'))))
        self.panel.destroy()
        self.assertFalse(jobs.intersection(self.root.tk.call('after','info')))
        self.root.update()


if __name__=='__main__':
    unittest.main()
