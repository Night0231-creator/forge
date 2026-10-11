"""Worker previews are immutable, incremental and faithful to source pixels."""
import tempfile
import unittest
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageChops
from core.layered_materials import LayeredPaintSession,_flood_mask
from ui.paint_updates import PaintUpdates
from ui.realtime_viewer import RealtimeObjViewer,preview_size
from types import SimpleNamespace


class PaintUpdatesTests(unittest.TestCase):
    def session(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup)
        root=Path(tmp.name);(root/'TaleWeaverCmd_Source').mkdir()
        folder=root/'TaleWeaverLite';folder.mkdir()
        Image.new('RGBA',(513,257),'#203040').save(folder/'Albedo.png')
        Image.new('RGBA',(513,257),(40,220,0,50)).save(folder/'MAES.png')
        return LayeredPaintSession(folder/'Albedo.png',root)

    def test_partial_publication_matches_full_resize_without_mutating_older_frame(self):
        session=self.session();updates=PaintUpdates(session,maximum=160)
        first=updates.prepare();old=first.full.tobytes();display=first.full.copy()
        session.stroke((125,95),(220,107),'#ff9900',size=26,opacity=.7)
        partial=updates.prepare()
        self.assertIsNone(partial.full);self.assertTrue(partial.patches)
        for box,patch in partial.patches:display.paste(patch,box)
        expected=session.image.resize(updates.size,Image.Resampling.BILINEAR).convert('RGB')
        difference=np.abs(np.asarray(display).astype(int)-np.asarray(expected).astype(int))
        self.assertLessEqual(difference.max(),1)
        self.assertEqual(first.full.tobytes(),old)
        session.checkpoint();session.stroke((300,150),(320,156),'blue',size=20)
        session.undo()
        self.assertIsNotNone(updates.prepare().full)

    def test_selection_changes_do_not_require_full_texture_publication(self):
        session=self.session();updates=PaintUpdates(session,maximum=160);updates.prepare()
        session.select_region(0,0)
        selected=updates.prepare()
        self.assertIsNone(selected.full);self.assertEqual(selected.patches,[])
        self.assertEqual(selected.selection.size,updates.size)
        session.clear_region();self.assertIsNone(updates.prepare().selection)

    def test_maes_resize_treats_alpha_as_data(self):
        session=self.session();session.maes_image=Image.new('RGBA',(4096,2),(255,20,30,0))
        session.maes_image.paste((0,220,150,255),(2048,0,4096,2))
        result=PaintUpdates(session).prepare(materials=True)
        self.assertEqual(tuple(result.materials[0,0]),(255,20,30,0))
        self.assertEqual(tuple(result.materials[0,-1]),(0,220,150,255))

    def test_compatible_preview_updates_pixels_without_mutating_worker_snapshot(self):
        image=Image.new('RGB',(2050,1026),'#203040')
        viewer=SimpleNamespace(_using_fallback=True,_paint_pending=False,_damage=None,render=lambda:None)
        RealtimeObjViewer.update_paint(viewer,image,None)
        old=viewer._albedo;before=old.tobytes()
        box=(30,40,160,130);image.paste('#FF2200',box)
        RealtimeObjViewer.update_paint(viewer,image,[box,box])
        expected=np.asarray(image.resize(preview_size(image.size,1024),Image.Resampling.BILINEAR))
        difference=np.abs(viewer._albedo.astype(int)-expected.astype(int))
        self.assertLessEqual(difference.max(),1)
        self.assertEqual(old.tobytes(),before)
        self.assertIsNot(viewer._albedo,old)


class ScanlineSelectionTests(unittest.TestCase):
    def test_matches_pillow_rgb_tolerance_and_four_connected_flood(self):
        rng=np.random.default_rng(21)
        for tolerance in (0,12,60):
            data=rng.integers(20,40,(18,23,3),dtype=np.uint8)
            data[1:17,11]=200;data[9,11]=30
            before=Image.fromarray(data);after=before.copy()
            seed=before.getpixel((2,2));sentinel=tuple((v+128)%256 for v in seed)
            ImageDraw.floodfill(after,(2,2),sentinel,thresh=tolerance)
            expected=ImageChops.difference(before,after).convert('L').point(lambda v:255 if v else 0)
            self.assertEqual(_flood_mask(before,(2,2),tolerance).tobytes(),expected.tobytes())

    def test_disconnected_identical_colors_and_diagonal_contact_stay_separate(self):
        image=Image.new('RGB',(7,7),'black')
        image.paste('white',(0,0,3,3));image.paste('white',(3,3,7,7))
        mask=_flood_mask(image,(0,0),0)
        self.assertEqual(mask.getpixel((2,2)),255);self.assertEqual(mask.getpixel((3,3)),0)
        with self.assertRaises(ValueError):_flood_mask(image,(-1,0),0)
        with self.assertRaises(ValueError):_flood_mask(image,(0,0),61)


if __name__=='__main__':unittest.main()
