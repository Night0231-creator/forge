"""Exercise the real desktop editor on Windows CI or an available X display."""
import os
import tempfile
import time
import threading
import tkinter as tk
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
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
        self.wait_edits()

    def wait_edits(self):
        deadline=time.perf_counter()+10
        while self.panel._edits.busy and time.perf_counter()<deadline:
            self.root.update()
            time.sleep(.002)
        self.assertFalse(self.panel._edits.busy,'Editing worker did not finish')

    def event(self):
        pick=self.panel._picker_for_camera()
        return SimpleNamespace(x=float(pick.x.mean()),y=float(pick.y.mean()))

    def test_real_click_fills_geometry_across_uv_seam_and_undo(self):
        self.panel.mode.set('regiao')
        self.panel._paint3d_start(self.event())
        self.wait_edits()
        self.assertIsNotNone(self.panel.session.selection)
        self.panel.mode.set('balde')
        self.panel.color.set('#00AAFF')
        self.panel._paint3d_start(self.event())
        self.wait_edits()
        self.assertEqual(self.panel.session.pick(70,200),'#00AAFF')
        self.assertEqual(self.panel.session.pick(180,65),'#00AAFF')
        self.panel._undo()
        self.wait_edits()
        self.assertEqual(self.panel.session.pick(70,200),'#FFFFFF')

    def test_surface_stroke_and_custom_material_callbacks(self):
        event=self.event()
        self.panel._paint3d_start(event)
        self.panel._paint3d_drag(SimpleNamespace(x=event.x+30,y=event.y))
        self.panel._paint3d_end(event)
        self.wait_edits()
        self.assertIsNotNone(self.panel.session.layers[0].pixels.getbbox())
        self.panel.mode.set('regiao')
        self.panel._paint3d_start(event)
        for variable,value in zip(self.panel._material_channels,(120,240,75,180)):
            variable.set(value)
        self.panel._apply_material()
        self.wait_edits()
        self.assertEqual(self.panel.session.maes_image.getpixel((70,200)),(120,240,75,180))
        self.panel._undo()
        self.wait_edits()
        self.assertEqual(self.panel.session.maes_image.getpixel((70,200)),(0,255,0,30))
        self.assertGreater(self.panel.viewer.winfo_width(),400)

    def test_automatic_effect_is_queued_with_captured_settings_and_survives_save_undo(self):
        gate=threading.Event();self.addCleanup(gate.set)
        self.panel._queue_edit(lambda:gate.wait(5))
        self.panel._shading_preset((60,45))
        self.assertIsNone(self.panel.session.automatic_shading.maps)
        self.panel.shadow_amount.set(10);self.panel.highlight_amount.set(5)
        gate.set();self.wait_edits()
        shade=self.panel.session.automatic_shading
        self.assertTrue(shade.enabled)
        self.assertEqual((shade.shadows,shade.highlights),(60,45))
        self.panel.mode.set('pincel');self.panel.color.set('#CC2200')
        event=self.event();self.panel._paint3d_start(event);self.panel._paint3d_end(event)
        self.wait_edits();painted=self.panel.session.image.tobytes()
        self.assertIs(self.panel.session.automatic_shading.maps,shade.maps)
        self.panel._undo();self.wait_edits()
        self.assertNotEqual(self.panel.session.image.tobytes(),painted)
        self.panel._redo();self.panel._save();self.wait_edits()
        with Image.open(self.panel.saved) as saved:
            self.assertEqual(saved.convert('RGBA').tobytes(),painted)
        self.panel.auto_shading.set(False);self.panel._configure_shading();self.wait_edits()
        self.assertFalse(self.panel.session.automatic_shading.enabled)
        self.panel._undo();self.wait_edits()
        self.assertTrue(self.panel.auto_shading.get())
        self.assertEqual(self.panel.session.image.tobytes(),painted)

    def test_failed_shading_preparation_resets_controls_without_discarding_paint(self):
        from unittest.mock import patch
        before=self.panel.session.image.tobytes()
        with patch('ui.painting_studio.build_shading_maps',side_effect=ValueError('UV inválido')), \
             patch('ui.painting_studio.messagebox.showerror') as error:
            self.panel._shading_preset((60,45));self.wait_edits()
            error.assert_called_once()
        self.assertFalse(self.panel.auto_shading.get())
        self.assertIn('UV inválido',self.panel.shading_status.get())
        self.assertEqual(self.panel.session.image.tobytes(),before)
        self.assertEqual(len(self.panel.session.history),0)

    def test_material_choice_is_captured_before_queued_brush_and_undo_save(self):
        from core.material_palette import MATERIALS
        gold=next(c for c in MATERIALS if c.name=='Ouro')
        self.panel._choose_material(gold)
        self.assertTrue(self.panel.paint_material.get())
        gate=threading.Event();self.addCleanup(gate.set)
        self.panel._queue_edit(lambda:gate.wait(5))
        event=self.event()
        self.panel._paint3d_start(event);self.panel._paint3d_end(event)
        # Changing the current controls must not change an already queued stroke.
        self.panel._choose_material(next(c for c in MATERIALS if c.name=='Couro'))
        gate.set();self.wait_edits()
        self.assertTrue(self.panel.session.maes_dirty)
        material=self.panel.session.maes_image.copy()
        pixels=list(material.getdata())
        self.assertIn((gold.metallic,255,gold.emission,gold.smoothness),pixels)
        self.assertNotIn((0,255,0,70),pixels)
        self.panel._undo();self.wait_edits()
        self.assertFalse(self.panel.session.maes_dirty)
        self.panel._redo();self.panel._save();self.wait_edits()
        with Image.open(self.panel.session.material_draft) as saved:
            self.assertEqual(saved.convert('RGBA').tobytes(),material.tobytes())

    def test_pointer_events_use_cached_settings_and_traces_are_removed_on_close(self):
        from contextlib import ExitStack
        self.panel.size.set(26);self.panel.opacity.set(80);self.panel.paint_material.set(True)
        self.assertEqual(self.panel._paint_options()[1:3],(26,.8))
        traces=list(self.panel._control_traces)
        event=self.event()
        with ExitStack() as stack:
            for variable,_ in traces:
                stack.enter_context(patch.object(variable,'get',side_effect=AssertionError('Tcl read during pointer event')))
            self.panel._paint3d_start(event)
            self.panel._paint3d_drag(SimpleNamespace(x=event.x+10,y=event.y))
            self.panel._paint3d_end(event)
            self.wait_edits()
        self.assertTrue(self.panel.session.maes_dirty)
        self.panel.destroy()
        for variable,trace in traces:
            self.assertNotIn(trace,str(variable.trace_info()))

    def test_automatic_bucket_can_fill_a_second_part_without_clearing_selection(self):
        self.panel.region_angle.set(0)
        self.panel.mode.set('balde')
        # The fixture is coplanar, so use a separate disconnected second face.
        from ui.texture_renderer import TextureMesh
        import numpy as np
        old=self.panel.viewer._mesh
        points=np.vstack((old.points,old.points[[0,2,3]]+np.array([3,0,0])))
        faces=np.array([[0,1,2],[4,5,6]],np.int32)
        self.panel.viewer._mesh=TextureMesh(points,faces,old.texcoords,old.texture_path)
        self.panel.viewer.yaw=self.panel.viewer.pitch=0
        picker=self.panel._picker_for_camera()
        for index,colour in ((0,'#FF0000'),(1,'#0000FF')):
            self.panel.color.set(colour)
            self.panel._paint3d_start(SimpleNamespace(x=float(picker.x[index].mean()),y=float(picker.y[index].mean())))
            self.wait_edits()
            self.assertIsNone(self.panel.session.selection)
        self.assertEqual(self.panel.session.pick(70,200),'#FF0000')
        self.assertEqual(self.panel.session.pick(180,65),'#0000FF')

    def test_closing_editor_cancels_pending_texture_and_preview_renders(self):
        self.panel._request_refresh()
        self.panel._schedule_preview()
        jobs={self.panel._refresh_id,self.panel._preview_job}
        self.assertNotIn(None,jobs)
        self.assertTrue(jobs.issubset(set(self.root.tk.call('after','info'))))
        self.panel.destroy()
        self.assertFalse(jobs.intersection(self.root.tk.call('after','info')))
        self.root.update()

    def test_queued_undo_redo_and_save_include_the_complete_stroke(self):
        event=self.event()
        self.panel.color.set('#FF0000')
        self.panel._paint3d_start(event)
        self.panel._paint3d_drag(SimpleNamespace(x=event.x+25,y=event.y))
        self.panel._paint3d_end(event)
        self.panel._undo()
        self.panel._redo()
        self.panel._save()
        self.wait_edits()
        self.assertIsNotNone(self.panel.session.layers[0].pixels.getbbox())
        with Image.open(self.panel.saved) as saved:
            self.assertEqual(saved.convert('RGBA').tobytes(),self.panel.session.image.tobytes())
        self.panel._undo();self.wait_edits()
        self.assertIsNone(self.panel.session.layers[0].pixels.getbbox())

    def test_compatible_cursor_does_not_invalidate_the_rendering_worker(self):
        self.panel.viewer.set_lighting(gpu=False)
        fallback=self.panel.viewer._fallback
        ticket=fallback._paint_ticket
        for x in range(30):self.panel.viewer.set_brush_cursor(200+x,200,30)
        self.assertEqual(fallback._paint_ticket,ticket)
        self.assertEqual(len(fallback.find_withtag('brush-cursor')),1)
        self.panel.viewer.clear_brush_cursor()
        self.assertEqual(fallback.find_withtag('brush-cursor'),())

    def test_save_finishes_if_editor_closes_with_a_pending_stroke(self):
        gate=threading.Event();self.addCleanup(gate.set)
        panel=self.panel;session=panel.session
        panel._queue_edit(lambda:gate.wait(5))
        panel.color.set('#FF0000')
        panel._paint3d_start(self.event())
        panel._save()
        panel.destroy();gate.set()
        panel._closing_edit.result(timeout=10)
        target=panel.project/'Pintura/Albedo_editado.png'
        self.assertTrue(target.is_file())
        with Image.open(target) as saved:
            self.assertEqual(saved.convert('RGBA').tobytes(),session.image.tobytes())
        self.assertIsNotNone(session.layers[0].pixels.getbbox())
        self.root.update()

    def test_tool_shortcuts_respect_text_fields_and_unrelated_controls(self):
        tool=self.panel.tool_buttons['pincel']
        self.root.focus_force()
        tool.focus_set()
        self.root.update()
        tool.event_generate('<KeyPress-g>')
        self.root.update()
        self.assertEqual(self.panel.mode.get(),'balde')
        entry=self.panel.palette_search.entry
        entry.focus_set()
        self.root.update()
        entry.event_generate('<KeyPress-b>')
        self.root.update()
        self.assertEqual(self.panel.palette_query.get(),'b')
        self.assertEqual(self.panel.mode.get(),'balde')
        with patch.object(self.panel,'_save') as save:
            entry.event_generate('<Control-KeyPress-s>')
            self.root.update()
            save.assert_not_called()
            tool.focus_set()
            self.root.update()
            tool.event_generate('<Control-KeyPress-s>')
            self.root.update()
            save.assert_called_once()
        outside=tk.Button(self.root,text='Outside editor')
        self.panel._shortcut(SimpleNamespace(widget=outside,keysym='e',state=0))
        self.assertEqual(self.panel.mode.get(),'balde')
        outside.destroy()
        self.panel._shortcut(SimpleNamespace(widget=tool,keysym='b',state=16))
        self.assertEqual(self.panel.mode.get(),'pincel')
        with patch.object(self.panel,'_save') as save:
            self.panel._shortcut(SimpleNamespace(widget=tool,keysym='s',state=4|8))
            self.panel._shortcut(SimpleNamespace(widget=tool,keysym='s',state=4|0x20000))
            save.assert_not_called()

    def test_closing_editor_removes_its_shortcuts_and_tooltip_timer(self):
        sibling=self.root.bind('<KeyPress>',lambda _event:None,add='+')
        binding=self.panel._key_binding[1]
        self.assertIn(binding,self.root.bind('<KeyPress>'))
        hint=self.panel.tool_buttons['pincel'].tooltip
        hint.schedule()
        job=hint.job
        self.assertIn(job,self.root.tk.call('after','info'))
        self.panel.destroy()
        self.assertNotIn(binding,self.root.bind('<KeyPress>'))
        self.assertIn(sibling,self.root.bind('<KeyPress>'))
        self.assertNotIn(job,self.root.tk.call('after','info'))
        self.root.update()


if __name__=='__main__':
    unittest.main()
