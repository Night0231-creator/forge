"""Colour and MAES data share coverage, history, seams and saved drafts."""
import tempfile
import unittest
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw

from core.layered_materials import LayeredPaintSession
from ui.paint_updates import PaintUpdates


class MaterialBrushTests(unittest.TestCase):
    def session(self,size=(64,64),material_size=None):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup)
        root=Path(tmp.name);(root/'TaleWeaverCmd_Source').mkdir()
        folder=root/'TaleWeaverLite';folder.mkdir()
        Image.new('RGBA',size,'#204060').save(folder/'Albedo.png')
        Image.new('RGBA',material_size or size,(10,137,20,0)).save(folder/'MAES.png')
        return LayeredPaintSession(folder/'Albedo.png',root)

    def test_colour_and_finish_share_opacity_and_undo_redo(self):
        s=self.session();before=s.maes_image.tobytes()
        s.checkpoint();s.stroke((25,25),(25,25),'#FF0000',size=12,opacity=.5,
                                material=(250,220,200))
        self.assertEqual(s.maes_image.getpixel((25,25)),(130,137,120,100))
        self.assertEqual(s.pick(25,25),'#902030')
        self.assertEqual(s.maes_image.getpixel((0,0)),(10,137,20,0))
        self.assertTrue(s.undo());self.assertEqual(s.maes_image.tobytes(),before)
        self.assertFalse(s.maes_dirty)
        self.assertTrue(s.redo());self.assertTrue(s.maes_dirty)
        self.assertEqual(s.maes_image.getpixel((25,25)),(130,137,120,100))

    def test_surface_union_does_not_double_opacity_and_respects_selection(self):
        s=self.session();s.selection=Image.new('L',s.image.size)
        ImageDraw.Draw(s.selection).rectangle((0,0,31,63),fill=255)
        mask=Image.new('L',(16,16),128)
        s.apply_surface_masks([(mask,(24,20)),(mask,(24,20))],'#FF0000',material=(250,220,200))
        self.assertEqual(s.maes_image.getpixel((28,25)),(130,137,120,100))
        self.assertEqual(s.maes_image.getpixel((35,25)),(10,137,20,0))
        self.assertEqual(s.pick(35,25),'#204060')

    def test_different_material_resolution_is_aligned_and_ao_retained(self):
        for size in ((32,16),(128,128)):
            with self.subTest(size=size):
                s=self.session(material_size=size)
                s.selection=Image.new('L',(64,64));s.selection.paste(255,(16,16,32,32))
                s.bucket(20,20,'#FFD000',material=(240,0,220))
                rgb=np.asarray(s.maes_image)
                self.assertTrue((rgb[:,:,1]==137).all())
                self.assertEqual(s.maes_image.getpixel((round(20*size[0]/64),round(20*size[1]/64))),
                                 (240,137,0,220))
                self.assertEqual(s.maes_image.getpixel((0,0)),(10,137,20,0))

    def test_stamp_material_and_saved_draft_restore_without_touching_sources(self):
        s=self.session();source=s.material_source.read_bytes();albedo=s.source.read_bytes()
        s.checkpoint();s.stamp(32,32,'#FFAA00',diameter=24,shape='Selo',material=(200,40,190))
        s.save_draft(s.project)
        fresh=LayeredPaintSession(s.source,s.project)
        self.assertEqual(s.image.tobytes(),fresh.image.tobytes())
        self.assertEqual(s.maes_image.tobytes(),fresh.maes_image.tobytes())
        self.assertEqual(s.material_source.read_bytes(),source)
        self.assertEqual(s.source.read_bytes(),albedo)

    def test_partial_worker_material_updates_match_full_resize_and_are_immutable(self):
        s=self.session(size=(4096,2050));u=PaintUpdates(s)
        first=u.prepare();old=first.materials.tobytes();display=first.materials.copy()
        s.stroke((100,110),(180,130),'#FFD000',size=36,opacity=.6,material=(240,0,220))
        update=u.prepare()
        self.assertTrue(update.material_changed);self.assertIsNone(update.materials)
        self.assertTrue(update.material_patches)
        for (x0,y0,x1,y1),data in update.material_patches:
            display[y0:y1,x0:x1]=data
        expected=np.asarray(Image.merge('RGBA',[
            channel.resize(u.materials.size,Image.Resampling.BILINEAR)
            for channel in s.maes_image.split()]))
        self.assertLessEqual(np.abs(display.astype(int)-expected.astype(int)).max(),1)
        self.assertEqual(first.materials.tobytes(),old)
        self.assertLess(sum(data.nbytes for _,data in update.material_patches),display.nbytes//10)
        self.assertFalse(u.prepare().material_changed)

    def test_invalid_or_missing_material_fails_before_pigment_changes(self):
        s=self.session();before=s.image.tobytes()
        for values in ((300,1,2),(1,2),(1.,2,3)):
            with self.assertRaises(ValueError):s.stroke((20,20),(20,20),'red',material=values)
            self.assertEqual(s.image.tobytes(),before)
        s.maes_image=None
        with self.assertRaises(FileNotFoundError):s.stroke((20,20),(20,20),'red',material=(1,2,3))
        self.assertEqual(s.image.tobytes(),before)


if __name__=='__main__':unittest.main()
