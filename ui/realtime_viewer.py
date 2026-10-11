"""Native, event-driven OpenGL viewport with an automatic legacy fallback.

The GL window presents frames without framebuffer readback or ImageTk.
Source geometry, UVs and export textures remain in the existing Forge pipeline.
"""
from __future__ import annotations

import math
import os
import re
import time
import tkinter as tk
from pathlib import Path

import numpy as np
from PIL import Image

from ui.gpu_pbr_renderer import GPUPreview, FS
from ui.realtime_policy import FrameBudget
from ui.texture_renderer import load_obj, read_albedo
from ui.texture_viewer import TexturedObjViewer

try:
    from pyopengltk import OpenGLFrame
except (ImportError, OSError):
    OpenGLFrame = None


FULLSCREEN_VS = '''#version 330
out vec2 uv;
void main() {
    vec2 p=vec2((gl_VertexID<<1)&2,gl_VertexID&2);
    uv=p;
    gl_Position=vec4(p*2.0-1.0,0.0,1.0);
}'''
BACKGROUND_FS = '''#version 330
in vec2 uv;
out vec4 fragColor;
uniform vec2 resolution;
void main() {
    vec3 color=mix(vec3(.051,.067,.094),vec3(.078,.106,.145),1.0-uv.y);
    float y=1.0-uv.y;
    if(y>.43) {
        float t=(y-.43)/.57;
        float horizontal=abs(fract(sqrt(t)*18.0+.5)-.5);
        float x=(uv.x-.5)*12.0/max(t,.015);
        float vertical=abs(fract(x+.5)-.5);
        float grid=max(1.0-smoothstep(.01,.035,horizontal),
                       1.0-smoothstep(.01,.035,vertical));
        color=mix(color,vec3(.114,.145,.192),grid*.55);
    }
    fragColor=vec4(color,1.0);
}'''
CURSOR_FS = '''#version 330
in vec2 uv;
out vec4 fragColor;
uniform vec2 resolution;
uniform vec3 cursor;
void main() {
    vec2 pixel=vec2(uv.x,1.0-uv.y)*resolution;
    float ring=abs(length(pixel-cursor.xy)-cursor.z);
    if(cursor.z<=0.0 || ring>1.25) discard;
    fragColor=vec4(vec3(.72,.84,1.0),1.0);
}'''
NATIVE_FS = FS.replace('uniform sampler2D u_albedo;',
                      'uniform sampler2D u_albedo;\nuniform sampler2D u_selection;')
NATIVE_FS = NATIVE_FS.replace(
    'vec3 color=pow(texture(u_albedo,v_uv).rgb,vec3(2.2));',
    'vec3 sampleColor=texture(u_albedo,v_uv).rgb;\n'
    'sampleColor=mix(sampleColor,vec3(.506,.812,.988),'
    'texture(u_selection,v_uv).r*.22);\n'
    'vec3 color=pow(sampleColor,vec3(2.2));')


def preview_size(size, maximum):
    ratio=min(1.0,maximum/max(size))
    return tuple(max(1,round(value*ratio)) for value in size)


def texture_patch(source, target_size, box):
    """Match whole-image bilinear resize, including its sampling halo."""
    sw,sh=source.size
    tw,th=target_size
    x0=max(0,math.floor(box[0]*tw/sw)-2)
    y0=max(0,math.floor(box[1]*th/sh)-2)
    x1=min(tw,math.ceil(box[2]*tw/sw)+2)
    y1=min(th,math.ceil(box[3]*th/sh)+2)
    part=source.resize((x1-x0,y1-y0),Image.Resampling.BILINEAR,
                       box=(x0*sw/tw,y0*sh/th,x1*sw/tw,y1*sh/th)).convert('RGB')
    return (x0,y0,x1,y1),np.asarray(part,dtype=np.uint8).copy()


if OpenGLFrame is not None:
    class NativeSurface(OpenGLFrame):
        """GL context and resources are owned by the Tk GUI thread."""
        def __init__(self,parent,viewer,**kw):
            self.viewer=viewer
            self.ctx=None
            self.gpu=None
            self.target=None
            self.target_size=None
            self.programs=[]
            self.closed=False
            super().__init__(parent,**kw)

        def tkMap(self,event):
            if self.closed:
                return
            try:
                super().tkMap(event)
                self.viewer.render()
            except (Exception, SystemExit) as exc:
                self.viewer._native_failed(exc)

        def tkResize(self,event):
            self.width,self.height=event.width,event.height
            self.viewer.render()

        def tkExpose(self,event):
            self.viewer.render()

        def initgl(self):
            if self.ctx is not None:
                return
            # Windows without a vendor driver exposes Microsoft's OpenGL 1.1.
            # Detect it before ModernGL queries modern entry points; some old
            # drivers terminate the process rather than raising a Python error.
            from OpenGL import GL
            version=GL.glGetString(GL.GL_VERSION)
            match=re.match(rb'(\d+)\.(\d+)',version or b'')
            if not match or tuple(map(int,match.groups()))<(3,3):
                raise RuntimeError('OpenGL 3.3 indisponível; usar prévia compatível.')
            import moderngl
            from _moderngl import DefaultLoader
            self.ctx=moderngl.create_context(require=330,context=DefaultLoader())
            self.gpu=GPUPreview(self.ctx,fragment_shader=NATIVE_FS)
            for shader in (BACKGROUND_FS,CURSOR_FS):
                program=self.ctx.program(vertex_shader=FULLSCREEN_VS,fragment_shader=shader)
                self.programs.append((program,self.ctx.vertex_array(program,[])))
            self.gpu.program['u_selection'].value=3
            self.viewer.renderer_name=self.ctx.info.get('GL_RENDERER','OpenGL')

        def draw_frame(self):
            if self.closed or not self.context_created or not self.winfo_ismapped():
                return False
            self.tkMakeCurrent()
            w,h=max(1,self.winfo_width()),max(1,self.winfo_height())
            self.ctx.viewport=(0,0,w,h)
            # Detect each resize: the default framebuffer size is window-owned.
            screen=self.ctx.detect_framebuffer(0)
            scale=self.viewer.budget.scale
            size=(max(1,round(w*scale)),max(1,round(h*scale)))
            if size!=self.target_size:
                if self.target is not None:
                    self.target.release()
                self.target=self.ctx.simple_framebuffer(size,components=4)
                self.target_size=size
            target=self.target
            target.use()
            target.clear(0,0,0,1,depth=1)
            self.ctx.viewport=(0,0,*size)
            self.ctx.disable(self.gpu.gl.DEPTH_TEST)
            program,vao=self.programs[0]
            vao.render(vertices=3)
            owner=self.viewer
            if owner._mesh is not None and owner._albedo is not None:
                owner._upload_paint(self.gpu)
                owner._upload_materials(self.gpu)
                selection=owner._selection_data
                self.gpu._texture('selection',selection,1).use(location=3)
                self.gpu.render_to(target,owner._mesh,owner._albedo,owner._maes,
                                   owner._normal_map,owner.yaw,owner.pitch,owner.zoom,w,h,
                                   owner.pan_x,owner.pan_y,owner.light_intensity,
                                   owner.emission_intensity,owner.ambient_intensity,
                                   owner.environment_preset,clear=False)
            if owner.brush_cursor is not None:
                self.ctx.disable(self.gpu.gl.DEPTH_TEST)
                program,vao=self.programs[1]
                program['resolution'].value=(float(w),float(h))
                program['cursor'].value=owner.brush_cursor
                vao.render(vertices=3)
            # GPU-to-GPU blit: never read the pixels into Python during interaction.
            screen.use()
            # ModernGL copy_framebuffer copies matching pixel regions; explicit
            # GL blit scales the render target to the full native window.
            from OpenGL import GL
            GL.glBindFramebuffer(GL.GL_READ_FRAMEBUFFER,target.glo)
            GL.glBindFramebuffer(GL.GL_DRAW_FRAMEBUFFER,0)
            GL.glBlitFramebuffer(0,0,*size,0,0,w,h,GL.GL_COLOR_BUFFER_BIT,GL.GL_LINEAR)
            self.tkSwapBuffers()
            return True

        def destroy(self):
            if self.closed:
                return
            self.closed=True
            if self.ctx is not None:
                try:
                    # Hidden widgets must also release using their own context.
                    if os.name=='nt':
                        from OpenGL.WGL import wglMakeCurrent
                        wglMakeCurrent(self._OpenGLFrame__window,self._OpenGLFrame__context)
                    else:
                        from OpenGL import GLX
                        GLX.glXMakeCurrent(self._OpenGLFrame__window,self._wid,
                                           self._OpenGLFrame__context)
                    if self.gpu is not None:
                        self.gpu.release()
                    if self.target is not None:
                        self.target.release()
                    for program,vao in self.programs:
                        vao.release();program.release()
                    self.ctx.release()
                except Exception:
                    pass
            # pyopengltk has no context teardown. Release its platform handles.
            if hasattr(self,'_OpenGLFrame__context'):
                try:
                    if os.name=='nt':
                        import ctypes
                        from OpenGL.WGL import wglMakeCurrent,wglDeleteContext
                        wglMakeCurrent(None,None)
                        wglDeleteContext(self._OpenGLFrame__context)
                        release=ctypes.windll.user32.ReleaseDC
                        release.argtypes=[ctypes.c_void_p,ctypes.c_void_p]
                        release(self.winfo_id(),self._OpenGLFrame__window)
                    else:
                        from OpenGL import GLX
                        from pyopengltk.linux import _x11lib
                        display=self._OpenGLFrame__window
                        GLX.glXMakeCurrent(display,0,None)
                        GLX.glXDestroyContext(display,self._OpenGLFrame__context)
                        _x11lib.XCloseDisplay(display)
                except Exception:
                    pass
            super().destroy()


class RealtimeObjViewer(tk.Frame):
    """PaintingStudio-compatible viewport. Legacy preview is a lazy fallback."""
    def __init__(self,parent,on_status=None,**kw):
        super().__init__(parent,bg='#0D1118',highlightthickness=0,**kw)
        self.on_status=on_status
        self.budget=FrameBudget()
        self._job=None
        self._closed=False
        self._failed=False
        self._using_fallback=False
        self._bindings={}
        self._native=None
        self._fallback=None
        self._path=None
        self._mesh=self._albedo=self._maes=self._normal_map=None
        self._selection_data=np.zeros((1,1,1),dtype=np.uint8)
        self._selection_source=None
        self._paint_source=None
        self._paint_pending=False
        self._damage=None
        self._material_damage=[]
        self._material_pending=False
        self._texture_max=2048
        self.yaw,self.pitch,self.zoom=.5,.24,1.
        self.pan_x=self.pan_y=0.
        self.compare_reference=False
        self.last_mouse=None
        self.light_intensity=self.emission_intensity=self.ambient_intensity=1.
        self.environment_preset='Estúdio'
        self.pbr_gpu_enabled=True
        self.renderer_name=''
        self.frame_count=0
        self.last_render_ms=0.
        self.upload_bytes=0
        self.brush_cursor=None
        if (OpenGLFrame is not None and (os.name=='nt' or tk.TkVersion<9)
                and os.environ.get('ASTRONYX_LEGACY_PREVIEW')!='1'):
            self._native=NativeSurface(self,self,width=kw.get('width',740),height=kw.get('height',620))
            self._native.pack(fill='both',expand=True)
        else:
            self._failed=True
            self._activate_fallback()
        self.bind('<MouseWheel>',self._wheel)
        self.bind('<Button-4>',lambda _e:self._zoom(1.13))
        self.bind('<Button-5>',lambda _e:self._zoom(1/1.13))
        super().bind('<Map>',lambda _e:self.render(),add='+')
        self._notify('GPU nativa · preparando' if not self._failed else 'Prévia compatível')

    @property
    def projection_limit(self):
        from ui.studio_scene import PREVIEW_LIMIT
        return PREVIEW_LIMIT if self._using_fallback else None

    def bind(self,sequence=None,func=None,add=None):
        result=super().bind(sequence,func,add)
        if func is not None:
            self._bindings[sequence]=(func,add)
            for child in (self._native,self._fallback):
                if child is not None:
                    child.bind(sequence,func,add)
        return result

    def _notify(self,value):
        if self.on_status:
            self.on_status(value)

    def open(self,file):
        self._path=Path(file)
        self._mesh=load_obj(self._path)
        self._albedo=read_albedo(self._mesh.texture_path,self._texture_max).copy()
        self._maes=TexturedObjViewer._read_map(TexturedObjViewer._map_file(file,'MAES'),4)
        self._normal_map=TexturedObjViewer._read_map(TexturedObjViewer._map_file(file,'Normal'),3)
        if self._using_fallback:
            self._fallback.open(file)
        self.render()

    def _native_failed(self,error):
        if self._failed or self._closed:
            return
        self._failed=True
        self._notify('Prévia compatível · OpenGL nativo indisponível')
        # Avoid destroying a native handle while its Map/Expose callback runs.
        self.after_idle(self._activate_fallback)

    def _activate_fallback(self):
        if self._closed:
            return
        if self._native is not None:
            self._native.pack_forget()
            if self._failed:
                self._native.destroy()
                self._native=None
        if self._fallback is None:
            self._fallback=TexturedObjViewer(self,width=740,height=620)
            self._fallback.compare_reference=False
            if self._path is not None:
                self._fallback.open(self._path)
            for sequence,(func,add) in self._bindings.items():
                self._fallback.bind(sequence,func,add)
        self._using_fallback=True
        self._fallback.pack(fill='both',expand=True)
        self._notify('Prévia compatível · meta '+str(self.budget.fps)+' FPS')
        if self._paint_source is not None:
            self.update_paint(self._paint_source,None,self._selection_source)
        self.render()

    def _restore_native(self):
        if self._failed or self._native is None:
            return
        if self._fallback is not None:
            self._fallback.destroy()
            self._fallback=None
        self._using_fallback=False
        self._native.pack(fill='both',expand=True)
        if self._paint_source is not None:
            self.update_paint(self._paint_source,None,self._selection_source)
        self.render()

    def render(self):
        if self._closed:
            return
        if self._using_fallback:
            viewer=self._fallback
            for name in ('yaw','pitch','zoom','pan_x','pan_y','_albedo','_maes',
                         '_normal_map','light_intensity','emission_intensity',
                         'ambient_intensity','environment_preset','pbr_gpu_enabled'):
                setattr(viewer,name,getattr(self,name))
            viewer.render()
            return
        if self._job is None:
            self._job=self.after(self.budget.delay_ms(time.perf_counter()),self._draw)

    def _draw(self):
        self._job=None
        if self._closed or self._using_fallback or self._native is None:
            return
        started=time.perf_counter()
        try:
            if not self._native.draw_frame():
                return
        except Exception as exc:
            self._native_failed(exc)
            return
        self.last_render_ms=(time.perf_counter()-started)*1000
        self.budget.record(started,self.last_render_ms)
        self.frame_count+=1
        self._notify(f'GPU nativa · meta {self.budget.fps} FPS · '
                     f'{self.last_render_ms:.1f} ms · {round(self.budget.scale*100)}%')

    def set_quality(self,quality='Auto',fps=30):
        self.budget.configure(int(fps),quality)
        maximum=1024 if quality=='Leve' else 2048
        if self._texture_max!=maximum:
            self._texture_max=maximum
            if self._paint_source is not None:
                self.update_paint(self._paint_source,None,self._selection_source)
        self.render()

    def update_paint(self,image,damage=None,selection=None):
        self._paint_source=image
        self._selection_source=selection
        # Multiple paint events can arrive before one scheduled frame.
        self._damage=None if (damage is None or (self._paint_pending and self._damage is None)) else (
            sorted(set(tuple(box) for box in (self._damage or [])+list(damage))))
        self._paint_pending=True
        if self._using_fallback:
            size=preview_size(image.size,1024)
            base=getattr(self,'_fallback_base',None)
            if self._damage is None or base is None or base.size!=size:
                base=image.resize(size,Image.Resampling.BILINEAR).convert('RGB')
                self._fallback_base=base
            else:
                for box in self._damage:
                    mapped,data=texture_patch(image,size,box)
                    base.paste(Image.fromarray(data),mapped)
            copy=base
            if selection is not None:
                tint=Image.blend(copy,Image.new('RGB',copy.size,'#81CFFC'),.22)
                copy=Image.composite(tint,copy,selection.resize(copy.size,Image.Resampling.NEAREST))
            # A worker may still be rendering the old array: publish a fresh
            # bounded snapshot, never modify an array that it is reading.
            self._albedo=np.asarray(copy,dtype=np.uint8).copy()
            self._paint_pending=False
            self._damage=[]
        self.render()

    def _upload_paint(self,gpu):
        if not self._paint_pending or self._paint_source is None:
            return
        source=self._paint_source
        size=preview_size(source.size,self._texture_max)
        if self._damage is None or self._albedo.shape[:2]!=(size[1],size[0]):
            self._albedo=np.asarray(source.resize(size,Image.Resampling.BILINEAR).convert('RGB')).copy()
            gpu._texture('albedo',self._albedo,3)
            self.upload_bytes+=self._albedo.nbytes
        else:
            texture=gpu._texture('albedo',self._albedo,3)
            for damage in self._damage:
                box,data=texture_patch(source,size,damage)
                x0,y0,x1,y1=box
                self._albedo[y0:y1,x0:x1]=data
                texture.write(np.ascontiguousarray(np.flipud(data)).tobytes(),
                              viewport=(x0,size[1]-y1,x1-x0,y1-y0),alignment=1)
                self.upload_bytes+=data.nbytes
        selection=self._selection_source
        if selection is None:
            self._selection_data=np.zeros((1,1,1),dtype=np.uint8)
        elif (getattr(self,'_last_selection',None) is not selection
              or getattr(self,'_selection_size',None)!=size):
            mask=selection.resize(size,Image.Resampling.NEAREST)
            self._selection_data=np.asarray(mask,dtype=np.uint8).copy()[...,None]
        self._last_selection=selection
        self._selection_size=size
        self._paint_pending=False
        self._damage=[]

    def set_materials(self,maes=None,normal=None):
        self._maes=None if maes is None else np.asarray(maes.convert('RGBA') if isinstance(maes,Image.Image) else maes).copy()
        self._material_pending=False
        self._material_damage=[]
        if normal is not None:
            self._normal_map=np.asarray(normal).copy()
        self.render()

    def update_materials(self,full=None,patches=()):
        if full is not None:
            self._maes=np.asarray(full,dtype=np.uint8).copy()
            self._material_damage=None
        elif patches and self._maes is not None:
            if self._using_fallback:
                self._maes=self._maes.copy()
            for box,data in patches:
                x0,y0,x1,y1=box
                self._maes[y0:y1,x0:x1]=data
            if self._material_damage is not None:
                self._material_damage=sorted(set(self._material_damage+[tuple(box) for box,_ in patches]))
        self._material_pending=not self._using_fallback
        if self._using_fallback:
            self._material_damage=[]
        self.render()

    def _upload_materials(self,gpu):
        if not self._material_pending or self._maes is None:
            return
        texture=gpu._texture('maes',self._maes,4)
        if self._material_damage is None:
            self.upload_bytes+=self._maes.nbytes
        else:
            height=self._maes.shape[0]
            for x0,y0,x1,y1 in self._material_damage:
                data=self._maes[y0:y1,x0:x1]
                texture.write(np.ascontiguousarray(np.flipud(data)).tobytes(),
                              viewport=(x0,height-y1,x1-x0,y1-y0),alignment=1)
                self.upload_bytes+=data.nbytes
        self._material_pending=False
        self._material_damage=[]

    def set_lighting(self,*,light=None,emission=None,gpu=None,ambient=None,environment=None):
        from ui.gpu_pbr_renderer import _validate_settings
        light=self.light_intensity if light is None else float(light)
        emission=self.emission_intensity if emission is None else float(emission)
        ambient=self.ambient_intensity if ambient is None else float(ambient)
        environment=self.environment_preset if environment is None else environment
        _validate_settings(light,emission,ambient,environment)
        self.light_intensity,self.emission_intensity=light,emission
        self.ambient_intensity,self.environment_preset=ambient,environment
        if gpu is not None:
            self.pbr_gpu_enabled=bool(gpu)
            if not gpu:
                self._activate_fallback()
            elif not self._failed:
                self._restore_native()
        self.render()

    def set_brush_cursor(self,x,y,diameter):
        self.brush_cursor=(float(x),float(y),max(0.,float(diameter)*.5))
        if self._using_fallback:
            self._fallback.set_brush_cursor(x,y,diameter)
        else:
            self.render()

    def clear_brush_cursor(self):
        if self.brush_cursor is not None:
            self.brush_cursor=None
            if self._using_fallback:
                self._fallback.clear_brush_cursor()
            else:
                self.render()

    def _start_drag(self,event):
        self.last_mouse=(event.x,event.y)

    def _drag(self,event):
        if self.last_mouse is not None:
            self.yaw+=(event.x-self.last_mouse[0])*.012
            self.pitch=max(-1.4,min(1.4,self.pitch+(event.y-self.last_mouse[1])*.009))
        self.last_mouse=(event.x,event.y)
        self.render()

    def _pan(self,event):
        if self.last_mouse is not None:
            self.pan_x+=event.x-self.last_mouse[0]
            self.pan_y+=event.y-self.last_mouse[1]
        self.last_mouse=(event.x,event.y)
        self.render()

    def _wheel(self,event):
        if event.delta:
            self._zoom(1.13 if event.delta>0 else 1/1.13)

    def _zoom(self,factor):
        self.zoom=max(.25,min(5.,self.zoom*factor))
        self.render()

    def set_camera(self,view):
        views={'frente':(0.,0.),'lado':(math.pi*.5,0.),'topo':(0.,1.4),'perspectiva':(.5,.24)}
        self.yaw,self.pitch=views[view]
        self.pan_x=self.pan_y=0.
        self.render()

    def reset(self):
        self.yaw,self.pitch,self.zoom=.5,.24,1.
        self.pan_x=self.pan_y=0.
        self.render()

    def destroy(self):
        if self._closed:
            return
        self._closed=True
        if self._job is not None:
            self.after_cancel(self._job)
            self._job=None
        super().destroy()
