"""Geometry-driven influence, continuous paint, history and durable exports."""
import json
from pathlib import Path
import tempfile
import unittest

import numpy as np
from PIL import Image

from core.auto_shading import AutomaticShading, build_shading_maps, geometry_signature
from core.layered_materials import LayeredPaintSession, apply_materials_to_export
from ui.texture_renderer import TextureMesh


def folded_mesh(z=-1, split=False):
    points=np.array([(-1,-1,0),(0,-1,0),(0,1,0),(1,-1,z)],dtype='f4')
    faces=np.array([(0,1,2),(1,3,2)],dtype='i4')
    uv=np.array([[(0,0),(.5,0),(.5,1)],[(.5,0),(1,0),(.5,1)]],dtype='f4')
    if split:
        points=np.concatenate((points,points[[1,2]]))
        faces[1]=(4,3,5)
    return TextureMesh(points,faces,uv,Path('Albedo.png'))


class InfluenceTests(unittest.TestCase):
    def test_convex_edge_highlights_concave_fold_shadows_and_welded_seam(self):
        convex=build_shading_maps(folded_mesh(),(256,256))
        concave=build_shading_maps(folded_mesh(1),(256,256))
        self.assertGreater(convex.getpixel((127,128))[1],100)
        self.assertLess(convex.getpixel((110,128))[1],10)
        self.assertEqual(concave.getpixel((127,128))[1],0)
        self.assertGreater(concave.getpixel((128,128))[0],convex.getpixel((128,128))[0]+80)
        self.assertEqual(build_shading_maps(folded_mesh(split=True),(256,256)).tobytes(),convex.tobytes())

    def test_imported_ao_and_normal_detail_affect_influence_without_changing_data(self):
        mesh=folded_mesh(0)
        maes=Image.new('RGBA',(64,64),(210,255,175,0))
        maes.paste((210,20,175,255),(0,0,32,64))
        original=maes.tobytes()
        maps=build_shading_maps(mesh,(64,64),maes=maes)
        self.assertGreater(maps.getpixel((16,40))[0],maps.getpixel((45,50))[0]+100)
        self.assertEqual(maes.tobytes(),original)
        normal=Image.new('RGB',(64,64),(255,128,128))
        changed=build_shading_maps(mesh,(64,64),normal_map=normal)
        baseline=build_shading_maps(mesh,(64,64))
        self.assertNotEqual(changed.getpixel((20,40))[0],baseline.getpixel((20,40))[0])
        self.assertEqual(normal.getpixel((20,40)),(255,128,128))

    def test_planar_internal_diagonal_and_uv_boundary_do_not_create_highlights(self):
        result=np.asarray(build_shading_maps(folded_mesh(0),(97,61)))
        self.assertEqual(int(result[:,:,1].max()),0)
        self.assertEqual(result[-1,0,2],255)
        self.assertEqual(tuple(result[0,-1]),(0,0,0))

    def test_invalid_and_excessively_overlapping_atlases_fail_with_bounded_work(self):
        mesh=folded_mesh()
        with self.assertRaises(ValueError):
            build_shading_maps(mesh,(1,10))
        broken=TextureMesh(mesh.points,mesh.triangles,np.zeros((2,3,2),'f4'),mesh.texture_path)
        with self.assertRaisesRegex(ValueError,'UV'):
            build_shading_maps(broken,(128,128))
        limited=TextureMesh(mesh.points,mesh.triangles,mesh.texcoords,mesh.texture_path,True)
        with self.assertRaisesRegex(ValueError,'150 mil'):
            build_shading_maps(limited,(128,128))
        count=30000
        repeated=TextureMesh(mesh.points,np.repeat(mesh.triangles[:1],count,axis=0),
            np.repeat(np.array([[(0,0),(1,0),(0,1)]],'f4'),count,axis=0),mesh.texture_path)
        with self.assertRaisesRegex(ValueError,'sobrepostas'):
            build_shading_maps(repeated,(4096,4096))

    def test_partial_application_matches_full_resample_and_preserves_visual_alpha(self):
        rng=np.random.default_rng(42)
        maps=Image.fromarray(rng.integers(0,256,(11,17,3),dtype='u1'))
        shade=AutomaticShading().configure(maps=maps,enabled=True,shadows=75,highlights=65)
        image=Image.new('RGBA',(97,261),(90,150,210,42))
        full=shade.apply(image,image.size)
        for box in ((1,1,21,20),(27,111,81,205),(0,250,97,261)):
            part=shade.apply(image.crop(box),image.size,box)
            error=np.abs(np.asarray(part,dtype='i2')-np.asarray(full.crop(box),dtype='i2'))
            self.assertLessEqual(int(error.max()),1)
        self.assertEqual(full.getchannel('A').getextrema(),(42,42))
        self.assertEqual(shade.configure(enabled=False).apply(image,image.size).tobytes(),image.tobytes())
        with self.assertRaises(ValueError):
            shade.configure(shadows=101)
        with self.assertRaises(ValueError):
            AutomaticShading().configure(enabled=True)


class ShadingSessionTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.project=Path(self.tmp.name)
        for folder in ('TaleWeaverLite','TaleWeaverCmd_Source','Entrada_TaleWeaverCmd'):
            (self.project/folder).mkdir()
        self.obj=self.project/'TaleWeaverCmd_Source/model.obj'
        self.obj.write_text('v -1 -1 0\nv 1 -1 0\nv 0 1 0\n'
            'vt 0 0\nvt 1 0\nvt .5 1\nf 1/1 2/2 3/3\n')
        self.source=self.project/'TaleWeaverLite/Albedo.png'
        for folder,name in (('TaleWeaverLite','Albedo.png'),('TaleWeaverCmd_Source','Albedo.png'),
                            ('Entrada_TaleWeaverCmd','albedo.png')):
            Image.new('RGBA',(97,61),(100,150,180,255)).save(self.project/folder/name)
        Image.new('RGBA',(97,61),(5,220,7,0)).save(self.project/'TaleWeaverLite/MAES.png')
        self.session=LayeredPaintSession(self.source,self.project)
        self.maps=Image.new('RGB',(17,11),(190,110,255))
        self.source_bytes=self.source.read_bytes()
        self.signature=geometry_signature(self.project)

    def enable(self):
        self.session.configure_shading(maps=self.maps,signature=self.signature,
                                       enabled=True,shadows=65,highlights=40)

    def test_new_brush_and_layers_receive_effect_without_baking_it_into_pigment(self):
        self.enable();s=self.session
        before=s.image.tobytes()
        s.checkpoint();s.stroke((30,30),(40,30),'#FF0000',size=12,material=(210,30,180))
        self.assertEqual(s.pick(30,30),'#FF0000')
        self.assertNotEqual(s.image.getpixel((30,30))[:3],(255,0,0))
        self.assertIs(s.history[-1][-1].maps,self.maps)
        s._compose();painted=s.image.tobytes()
        self.assertTrue(s.undo());self.assertEqual(s.image.tobytes(),before)
        self.assertTrue(s.redo());self.assertEqual(s.image.tobytes(),painted)
        s.configure_shading(enabled=False)
        self.assertEqual(s.image.getpixel((30,30)),(255,0,0,255))
        s.configure_shading(enabled=True)
        self.assertEqual(s.image.tobytes(),painted)
        self.assertEqual(s.maes_image.getpixel((30,30)),(210,220,30,180))
        self.assertEqual(self.source.read_bytes(),self.source_bytes)

    def test_partial_recomposition_and_layer_visibility_apply_effect_once(self):
        self.enable();s=self.session
        s.stroke((40,30),(50,30),'#00FF00',size=20,opacity=.6)
        partial=np.asarray(s.image,dtype='i2')
        s._compose()
        self.assertLessEqual(int(np.abs(partial-np.asarray(s.image,dtype='i2')).max()),1)
        s.set_visible(False)
        expected=s.automatic_shading.apply(s.base,s.base.size)
        self.assertEqual(s.image.tobytes(),expected.tobytes())
        s.set_visible(True)
        s.configure_shading(shadows=0,highlights=0)
        self.assertEqual(s.image.tobytes(),s._composite().tobytes())

    def test_color_selection_uses_underlying_paint_across_shadow_variation(self):
        data=np.zeros((11,17,3),dtype='u1');data[:,:,:2]=np.arange(17)[None,:,None]*15
        data[:,:,2]=255
        self.session.configure_shading(maps=Image.fromarray(data),enabled=True)
        self.session.select_region(4,4,tolerance=0)
        self.assertEqual(self.session.selection.getbbox(),(0,0,97,61))
        self.session.bucket(4,4,'#CC4400')
        self.assertEqual(self.session.pick(90,50),'#CC4400')

    def test_save_reopen_export_and_geometry_invalidation(self):
        self.enable();s=self.session
        s.checkpoint();s.stroke((30,30),(30,30),'#AA00DD',size=12)
        draft=s.save_draft(self.project)
        with Image.open(draft) as saved:
            self.assertEqual(saved.convert('RGBA').tobytes(),s.image.tobytes())
        reopened=LayeredPaintSession(self.source,self.project)
        self.assertTrue(reopened.automatic_shading.enabled)
        self.assertEqual(reopened.image.tobytes(),s.image.tobytes())
        self.assertEqual(reopened.pick(30,30),'#AA00DD')
        self.obj.write_text(self.obj.read_text()+'\n# changed geometry source\n')
        invalidated=LayeredPaintSession(self.source,self.project)
        self.assertTrue(invalidated.restored_layers)
        self.assertFalse(invalidated.automatic_shading.enabled)
        self.assertEqual(invalidated.pick(30,30),'#AA00DD')
        changed=apply_materials_to_export(self.project,draft)
        for target in changed:
            with Image.open(target) as saved:
                self.assertEqual(saved.convert('RGBA').tobytes(),s.image.tobytes())
            self.assertTrue(list(target.parent.glob(target.name+'.*.bak')))

    def test_undone_and_malformed_saved_effects_do_not_reappear_or_discard_layers(self):
        self.enable();s=self.session
        s.save_draft(self.project)
        self.assertTrue(s.undo());s.save_draft(self.project)
        self.assertFalse(LayeredPaintSession(self.source,self.project).automatic_shading.enabled)
        self.enable();s.stroke((30,30),(30,30),'#00FF00',size=12);s.save_draft(self.project)
        manifest=self.project/'Pintura/camadas.json'
        data=json.loads(manifest.read_text());data['automatic_shading']['highlights']='bad'
        manifest.write_text(json.dumps(data))
        restored=LayeredPaintSession(self.source,self.project)
        self.assertTrue(restored.restored_layers)
        self.assertFalse(restored.automatic_shading.enabled)
        self.assertEqual(restored.pick(30,30),'#00FF00')

    def test_maes_4k_export_resizes_data_channels_independently_even_at_zero_smoothness(self):
        draft=self.session.save_draft(self.project)
        data=Image.new('RGBA',(4096,4096),(210,190,150,0))
        data.paste((10,30,50,255),(2048,0,4096,4096))
        path=self.project/'Pintura/MAES_editado.png';data.save(path)
        target=self.project/'Entrada_TaleWeaverCmd/metallic_ao_emis_smoothness.png'
        Image.new('RGBA',(32,32)).save(target)
        apply_materials_to_export(self.project,draft,path)
        with Image.open(target) as output:
            self.assertEqual(output.size,(2048,2048))
            self.assertEqual(output.getpixel((10,10)),(210,190,150,0))
            expected=Image.merge('RGBA',[c.resize((2048,2048),Image.Resampling.LANCZOS) for c in data.split()])
            self.assertEqual(output.tobytes(),expected.tobytes())
        from core.taleweavercmd import _copy_compatible_texture
        stage=self.project/'Stage';stage.mkdir()
        staged=stage/'metallic_ao_emis_smoothness.png'
        _copy_compatible_texture(path,staged)
        with Image.open(staged) as output:
            self.assertEqual(output.tobytes(),expected.tobytes())
        from ui.texture_viewer import TexturedObjViewer
        preview=TexturedObjViewer._read_map(path,4)
        self.assertEqual(tuple(preview[10,10]),(210,190,150,0))
        self.assertEqual(tuple(preview[10,-10]),(10,30,50,255))
