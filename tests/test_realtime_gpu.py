"""Render/picking alignment, incremental uploads and idle-budget regressions."""
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

import numpy as np
from PIL import Image

from core.layered_materials import LayeredPaintSession
from ui.gpu_pbr_renderer import GPUPreview
from ui.paint3d_picker import ProjectedUVPicker
from ui.realtime_policy import FrameBudget, TextureDamage
from ui.realtime_viewer import RealtimeObjViewer, NATIVE_FS, texture_patch, preview_size, OpenGLFrame
from ui.texture_renderer import TextureMesh


class RealtimePolicyTests(unittest.TestCase):
    @unittest.skipIf(OpenGLFrame is None,'Native runtime unavailable')
    def test_old_driver_is_rejected_before_moderngl_initializes(self):
        from ui.realtime_viewer import NativeSurface
        surface=NativeSurface.__new__(NativeSurface)
        surface.ctx=None
        for version in (None,b'1.1.0',b'3.2 Mesa'):
            with patch('OpenGL.GL.glGetString',return_value=version), \
                    patch('moderngl.create_context') as create:
                with self.assertRaises(RuntimeError):surface.initgl()
                create.assert_not_called()

    def test_frame_limit_and_adaptation_are_bounded(self):
        b=FrameBudget()
        b.record(1.,20.)
        self.assertEqual(b.delay_ms(1.01),24)
        b.configure(60,'Auto')
        for i in range(120):
            b.record(i,40.)
        self.assertEqual(b.scale,.5)
        b.configure(30,'Alta')
        for i in range(20):b.record(i,100.)
        self.assertEqual(b.scale,1.)
        with self.assertRaises(ValueError):b.configure(120,'Leve')

    def test_damage_accumulates_and_clears_between_frames(self):
        d=TextureDamage((2048,2048))
        self.assertIsNone(d.consume())
        d.mark((5,6,10,11));d.mark((1500,1500,1505,1505))
        boxes=d.consume()
        self.assertEqual(len(boxes),2)
        self.assertLess(sum((x1-x0)*(y1-y0) for x0,y0,x1,y1 in boxes),40000)
        self.assertEqual(d.consume(),[])
        d.mark();self.assertIsNone(d.consume())

    def test_session_marks_brush_and_history_without_changing_exports(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            (root/'TaleWeaverLite').mkdir()
            (root/'TaleWeaverCmd_Source').mkdir()
            source=root/'TaleWeaverLite/Albedo.png'
            Image.new('RGBA',(512,512),(80,70,60,255)).save(source)
            before=source.read_bytes()
            s=LayeredPaintSession(source,root)
            self.assertIsNone(s.preview_damage.consume())
            s.checkpoint();s.stroke((20,20),(25,25),'#FF0000',size=12)
            self.assertTrue(s.preview_damage.consume())
            s.undo();self.assertIsNone(s.preview_damage.consume())
            self.assertEqual(source.read_bytes(),before)

    def test_small_update_matches_full_resize_on_non_square_textures(self):
        rng=np.random.default_rng(7)
        image=Image.fromarray(rng.integers(0,256,(257,513,3),dtype=np.uint8))
        for size in ((513,257),(256,128),(128,64)):
            full=np.asarray(image.resize(size,Image.Resampling.BILINEAR))
            box,part=texture_patch(image,size,(150,75,170,100))
            x0,y0,x1,y1=box
            self.assertLessEqual(np.abs(part.astype(int)-full[y0:y1,x0:x1].astype(int)).max(),1)
        self.assertEqual(preview_size((4096,2048),2048),(2048,1024))


class RealtimeGPUTests(unittest.TestCase):
    def setUp(self):
        import moderngl
        try:
            self.ctx=moderngl.create_context(standalone=True,backend='egl',require=330)
        except Exception:
            try:self.ctx=moderngl.create_context(standalone=True,require=330)
            except Exception as exc:self.skipTest('OpenGL 3.3: '+str(exc)[:90])
        self.gpu=GPUPreview(self.ctx,fragment_shader=NATIVE_FS)
        self.selection=np.zeros((1,1,1),np.uint8)
        self.gpu._texture('selection',self.selection,1).use(location=3)
        self.gpu.program['u_selection'].value=3
        self.mesh=TextureMesh(np.array([[-1,-1,0],[1,-1,0],[0,1,0]],np.float32),
                              np.array([[0,1,2]],np.int32),
                              np.array([[[0,0],[1,0],[.5,1]]],np.float32),Path('none'))

    def tearDown(self):
        if hasattr(self,'gpu'):self.gpu.release()
        if hasattr(self,'ctx'):self.ctx.release()

    def test_direct_draw_matches_picking_above_old_900px_limit(self):
        albedo=np.full((32,32,3),200,np.uint8)
        width,height=1280,1000
        target=self.ctx.simple_framebuffer((width,height),components=4)
        try:
            self.ctx.viewport=(0,0,width,height)
            self.gpu.render_to(target,self.mesh,albedo,None,None,0,0,1,width,height)
            pixels=np.frombuffer(target.read(components=4),np.uint8).reshape(height,width,4)[::-1]
            picker=ProjectedUVPicker(self.mesh,yaw=0,pitch=0,zoom=1,
                                      canvas_width=width,canvas_height=height,
                                      show_reference=False,preview_limit=None)
            for x,y in ((640,550),(640,310),(480,700),(5,5)):
                self.assertEqual(picker.hit(x,y) is not None,bool(pixels[y,x,3]))
        finally:target.release()

    def test_incremental_upload_orientation_reuses_texture_and_bytes(self):
        v=RealtimeObjViewer.__new__(RealtimeObjViewer)
        v._paint_source=Image.new('RGB',(256,256),(30,80,110))
        v._texture_max=2048;v._damage=None;v._paint_pending=True
        v._albedo=np.zeros((256,256,3),np.uint8)
        v._selection_source=None;v.upload_bytes=0
        v._upload_paint(self.gpu)
        texture=self.gpu.tex_cache['albedo'][1]
        first_bytes=v.upload_bytes
        v._paint_source.paste((220,15,30),(20,25,32,35))
        v._damage=[(20,25,32,35)];v._paint_pending=True
        v._upload_paint(self.gpu)
        self.assertIs(texture,self.gpu.tex_cache['albedo'][1])
        self.assertLess(v.upload_bytes-first_bytes,256*256*3//10)
        result=np.frombuffer(texture.read(alignment=1),np.uint8).reshape(256,256,3)[::-1]
        np.testing.assert_array_equal(result,np.asarray(v._paint_source))

    def test_material_patches_keep_data_alpha_and_reuse_the_gpu_texture(self):
        from types import SimpleNamespace
        v=SimpleNamespace(_using_fallback=False,_maes=None,_material_damage=[],
                          _material_pending=False,upload_bytes=0,render=lambda:None)
        full=np.zeros((256,256,4),np.uint8);full[:]=(230,137,25,0)
        RealtimeObjViewer.update_materials(v,full)
        RealtimeObjViewer._upload_materials(v,self.gpu)
        texture=self.gpu.tex_cache['maes'][1];before=v.upload_bytes
        patch=np.zeros((10,12,4),np.uint8);patch[:]=(40,137,220,255)
        RealtimeObjViewer.update_materials(v,patches=[((20,25,32,35),patch)])
        RealtimeObjViewer._upload_materials(v,self.gpu)
        self.assertIs(texture,self.gpu.tex_cache['maes'][1])
        self.assertEqual(v.upload_bytes-before,10*12*4)
        result=np.frombuffer(texture.read(alignment=1),np.uint8).reshape(256,256,4)[::-1]
        np.testing.assert_array_equal(result,v._maes)
        self.assertEqual(tuple(result[0,0]),(230,137,25,0))


if __name__=='__main__':unittest.main()
