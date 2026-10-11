"""End-to-end paint masks: UV seams, occlusion, selection and undo."""
import tempfile
import unittest
from pathlib import Path

import numpy as np
from PIL import Image

from core.brushes import coverage
from core.layered_materials import LayeredPaintSession
from core.mesh_regions import MeshRegions
from ui.paint3d_picker import ProjectedUVPicker
from ui.surface_paint import surface_masks
from ui.texture_renderer import TextureMesh


def mesh(points,faces,uv):
    return TextureMesh(np.array(points,dtype=np.float32),
                       np.array(faces,dtype=np.int32),
                       np.array(uv,dtype=np.float32),Path('Albedo.png'))


def split_plane():
    return mesh([(-1,-1,0),(1,-1,0),(1,1,0),(-1,1,0)],
                [(0,1,2),(0,2,3)],
                [[(.05,.05),(.4,.05),(.4,.4)],
                 [(.6,.6),(.9,.9),(.6,.9)]])


def picker(model):
    return ProjectedUVPicker(model,yaw=0,pitch=0,zoom=1,
                             canvas_width=400,canvas_height=400,
                             show_reference=False)


class SurfacePaintTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.project=Path(self.temp.name)
        (self.project/'TaleWeaverCmd_Source').mkdir()
        folder=self.project/'TaleWeaverLite'
        folder.mkdir()
        Image.new('RGBA',(257,257),'white').save(folder/'Albedo.png')
        Image.new('RGBA',(257,257),(0,255,0,30)).save(folder/'MAES.png')
        self.session=LayeredPaintSession(folder/'Albedo.png',self.project)

    def paint(self,model,start=(200,220),end=None,**options):
        patches=surface_masks(picker(model),start,end or start,(257,257),**options)
        self.session.apply_surface_masks(patches,'#FF0000')
        return np.asarray(self.session.layers[0].pixels)[...,3]

    def test_one_brush_paints_both_uv_islands_without_atlas_bridge(self):
        alpha=self.paint(split_plane(),diameter=50)
        self.assertGreater(alpha[:120,130:].sum(),0)
        self.assertGreater(alpha[130:,:120].sum(),0)
        self.assertEqual(alpha[128,128],0)
        self.assertEqual(alpha[:20,:20].sum(),0)

    def test_continuous_screen_stroke_crosses_seam(self):
        alpha=self.paint(split_plane(),(170,220),(230,220),diameter=14)
        self.assertGreater(alpha[:120,130:].sum(),0)
        self.assertGreater(alpha[130:,:120].sum(),0)
        self.assertEqual(alpha[120:135,120:135].sum(),0)

    def occluded(self):
        return mesh([(-1,-1,-1),(1,-1,-1),(0,1,-1),
                     (-1,-1,1),(1,-1,1),(0,1,1)],
                    [(0,1,2),(3,4,5)],
                    [[(.05,.05),(.4,.05),(.225,.4)],
                     [(.6,.6),(.95,.6),(.775,.95)]])

    def test_opaque_front_face_protects_back_texture(self):
        alpha=self.paint(self.occluded(),diameter=45)
        self.assertEqual(alpha[130:,:120].sum(),0)
        self.assertGreater(alpha[:120,130:].sum(),0)

    def test_paint_through_includes_back_face(self):
        alpha=self.paint(self.occluded(),diameter=45,paint_through=True)
        self.assertGreater(alpha[130:,:120].sum(),0)
        self.assertGreater(alpha[:120,130:].sum(),0)

    def test_front_geometry_with_degenerate_uv_still_occludes_back_face(self):
        model=self.occluded()
        model.texcoords[1]=0
        alpha=self.paint(model,diameter=45)
        self.assertEqual(alpha.sum(),0)

    def test_custom_square_stamp_keeps_corners_and_uv_seams(self):
        alpha=self.paint(split_plane(),diameter=60,stencil=Image.new('L',(32,32),255))
        self.assertGreater(alpha[:120,130:].sum(),0)
        self.assertGreater(alpha[130:,:120].sum(),0)
        # Corresponds to (+24,+24) from brush center, outside the radius-30 circle.
        hit=picker(split_plane()).hit(224,244)
        x,y=hit.pixel(257,257)
        self.assertGreater(alpha[y,x],0)

    def test_coverage_has_soft_edges(self):
        alpha=self.paint(split_plane(),diameter=60,hardness=.2)
        self.assertTrue(np.any((alpha>0)&(alpha<255)))
        values=coverage(np.array([0,2,5,9,11]),10,.2)
        self.assertEqual(values[0],1)
        self.assertGreater(values[2],values[3])
        self.assertEqual(values[-1],0)

    def test_duplicate_face_patches_do_not_double_opacity(self):
        patch=(Image.new('L',(8,8),128),(20,20))
        self.session.apply_surface_masks([patch,patch],'#FF0000')
        self.assertEqual(self.session.layers[0].pixels.getpixel((22,22))[3],128)

    def test_masks_respect_selection_and_undo(self):
        self.session.selection=Image.new('L',(257,257))
        self.session.selection.paste(255,(0,0,130,257))
        before=self.session.image.tobytes()
        self.session.checkpoint()
        alpha=self.paint(split_plane(),diameter=60)
        self.assertEqual(alpha[:,130:].sum(),0)
        self.assertGreater(alpha[:,:130].sum(),0)
        self.assertTrue(self.session.undo())
        self.assertEqual(self.session.image.tobytes(),before)
        self.assertTrue(self.session.redo())
        self.assertNotEqual(self.session.image.tobytes(),before)

    def test_eraser_and_geometry_remain_independent(self):
        model=split_plane()
        original=model.points.copy()
        patches=surface_masks(picker(model),(200,220),(200,220),(257,257),diameter=60)
        self.session.apply_surface_masks(patches,'#FF0000')
        self.session.apply_surface_masks(patches,'#000000',erase=True)
        self.assertEqual(np.asarray(self.session.layers[0].pixels)[...,3].sum(),0)
        np.testing.assert_array_equal(model.points,original)

    def test_custom_material_has_data_alpha_and_undo(self):
        self.session.selection=Image.new('L',(257,257))
        self.session.selection.paste(255,(20,20,40,40))
        self.session.apply_material_values((180,222,80,230))
        self.assertEqual(self.session.maes_image.getpixel((25,25)),(180,222,80,230))
        self.assertEqual(self.session.maes_image.getpixel((50,50)),(0,255,0,30))
        self.session.undo()
        self.assertEqual(self.session.maes_image.getpixel((25,25)),(0,255,0,30))

    def test_bad_brush_and_degenerate_uv_are_rejected_or_skipped(self):
        with self.assertRaises(ValueError):
            surface_masks(picker(split_plane()),(200,220),(200,220),(257,257),hardness=2)
        model=split_plane()
        model.texcoords[:]=0
        self.assertEqual(surface_masks(picker(model),(200,220),(200,220),(257,257)),[])


class GeometryRegionTests(unittest.TestCase):
    def model(self):
        # Duplicate positions mimic an OBJ with split vertices at a UV seam.
        return mesh([(-1,-1,0),(1,-1,0),(1,1,0),
                     (-1,-1,0),(1,1,0),(-1,1,0),
                     (1,-1,0),(1,-1,1),(1,1,0)],
                    [(0,1,2),(3,4,5),(6,7,8)],
                    [[(.05,.05),(.4,.05),(.4,.4)],
                     [(.6,.6),(.9,.9),(.6,.9)],
                     [(.05,.6),(.3,.6),(.3,.9)]])

    def test_welds_uv_seam_but_respects_sharp_edge(self):
        regions=MeshRegions(self.model())
        np.testing.assert_array_equal(regions.region(0,35),[0,1])
        np.testing.assert_array_equal(regions.region(0,100),[0,1,2])

    def test_region_selects_disconnected_atlas_islands(self):
        regions=MeshRegions(self.model())
        mask=np.asarray(regions.mask(regions.region(0,35),(257,257)))
        self.assertGreater(mask[160:,:120].sum(),0)
        self.assertGreater(mask[:100,150:].sum(),0)
        self.assertEqual(mask[128,128],0)

    def test_disconnected_geometry_does_not_flood_uncolored_model(self):
        model=mesh([(-1,-1,0),(1,-1,0),(0,1,0),
                    (-1,-1,2),(1,-1,2),(0,1,2)],
                   [(0,1,2),(3,4,5)],
                   [[(0,0),(.4,0),(.2,.4)],[(.6,.6),(1,.6),(.8,1)]])
        np.testing.assert_array_equal(MeshRegions(model).region(0,180),[0])


if __name__=='__main__':
    unittest.main()
