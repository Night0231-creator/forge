"""Responsive textured OBJ preview for Astronyx.

Rotating uses the original Tk geometry preview. After idle, a CPU UV/albedo
render is computed off the Tk thread. Blender export pipeline is untouched.
"""
from __future__ import annotations

import queue
from concurrent.futures import ThreadPoolExecutor
import tkinter as tk
from pathlib import Path
import numpy as np
from PIL import Image

from core.preview import ObjViewer
from .studio_scene import PREVIEW_LIMIT, studio_background

try:
    from PIL import ImageTk
    from .texture_renderer import load_obj, read_albedo, draw, PreviewError
    from .gpu_pbr_renderer import render_preview, gpu_available
    TEXTURE_PREVIEW_AVAILABLE = True
except ImportError:
    ImageTk = None
    TEXTURE_PREVIEW_AVAILABLE = False


class TexturedObjViewer(ObjViewer):
    def __init__(self, parent, **kwargs):
        self.display_mode = 'textured'
        self.compare_reference = True
        self.pan_x = 0.
        self.pan_y = 0.
        self._mesh = None
        self._albedo = None
        self._maes = None
        self._normal_map = None
        self.pbr_gpu_enabled = True
        self.light_intensity = 1.0
        self.emission_intensity = 1.0
        self.ambient_intensity = 1.0
        self.environment_preset = 'Estúdio'
        self._backend_label = 'Prévia'
        self._texture_image = None
        self._backdrop_image = None
        self._backdrop_size = None
        self._preview_status = ''
        self._paint_ticket = 0
        self._scheduled = None
        self._worker_busy = False
        self._events = queue.Queue()
        self._pool = ThreadPoolExecutor(max_workers=1,thread_name_prefix='AstronyxGPU')
        self._poll_job = None
        super().__init__(parent, **kwargs)
        self.bind('<ButtonPress-3>', self._start_drag)
        self.bind('<B3-Motion>', self._pan)
        self._poll_job = self.after(33, self._poll)

    def open(self, file: Path):
        self._mesh = None
        self._albedo = None
        self._maes = None
        self._normal_map = None
        self._texture_image = None
        self._preview_status = ''
        super().open(file)
        if not TEXTURE_PREVIEW_AVAILABLE:
            self._preview_status = 'Texturas indisponíveis: instale Pillow e numpy.'
            self.render()
            return
        try:
            self._mesh = load_obj(file)
            self._albedo = read_albedo(self._mesh.texture_path)
            self._maes = self._read_map(self._map_file(file,'MAES'),4)
            self._normal_map = self._read_map(self._map_file(file,'Normal'),3)
            if self._mesh.limited:
                self._preview_status = 'Prévia limitada a 150 mil triângulos; não altera o arquivo final.'
            else:
                self._preview_status = 'Albedo + MAES · GPU automática / CPU reserva'
        except (OSError, ValueError, MemoryError) as exc:
            self._preview_status = str(exc)
        self.render()

    @staticmethod
    def _map_file(obj,kind):
        obj=Path(obj)
        names=(('MAES.png','metallic_ao_emis_smoothness.png')
               if kind=='MAES' else ('Normal.png','normals.png'))
        for folder in (obj.parent,obj.parent.parent/'TaleWeaverLite',
                       obj.parent.parent/'Entrada_TaleWeaverCmd'):
            for name in names:
                p=folder/name
                if p.is_file():
                    return p
        return None

    @staticmethod
    def _read_map(path,components):
        if path is None:
            return None
        with Image.open(path) as raw:
            if raw.width*raw.height > 4096*4096:
                raise PreviewError('Textura de material excede 4096x4096.')
            if components==4:
                data=raw.convert('RGBA')
            else:
                data=raw.convert('RGB')
            data.thumbnail((1024,1024),Image.Resampling.LANCZOS)
            return np.asarray(data,dtype=np.uint8).copy()

    def set_materials(self,maes=None,normal=None):
        """Refresh on-GPU materials without altering exported texture files."""
        if maes is not None:
            if isinstance(maes,Image.Image):
                copy=maes.convert('RGBA')
                copy.thumbnail((1024,1024),Image.Resampling.LANCZOS)
                self._maes=np.asarray(copy,dtype=np.uint8).copy()
            else:
                self._maes=np.asarray(maes,dtype=np.uint8).copy()
        if normal is not None:
            self._normal_map=np.asarray(normal,dtype=np.uint8).copy()
        self.render()

    def set_lighting(self,*,light=None,emission=None,gpu=None,
                     ambient=None,environment=None):
        if light is not None:
            self.light_intensity=max(0.,min(4.,float(light)))
        if emission is not None:
            self.emission_intensity=max(0.,min(5.,float(emission)))
        if gpu is not None:
            self.pbr_gpu_enabled=bool(gpu)
        if ambient is not None:
            self.ambient_intensity=max(0.,min(3.,float(ambient)))
        if environment is not None:
            from .gpu_pbr_renderer import ENV_PRESETS
            if environment not in ENV_PRESETS:
                raise ValueError('Ambiente desconhecido')
            self.environment_preset=environment
        self.render()

    def _project(self, xyz, width, height, center, units):
        x, y, d = super()._project(xyz,width,height,center,units)
        return x + self.pan_x, y + self.pan_y, d

    def _pan(self,event):
        if self.last_mouse is not None:
            self.pan_x += event.x-self.last_mouse[0]
            self.pan_y += event.y-self.last_mouse[1]
        self.last_mouse = (event.x,event.y)
        self.render()

    def render(self):
        """Keep the last texture visible during brush and camera changes.

        The original implementation repainted ~1600 Tk geometry polygons
        on every mouse move, then replaced them with GPU output; this caused
        flicker and main-thread stalls despite an accelerated GPU worker.
        """
        self._paint_ticket+=1
        if self._scheduled is not None:
            try: self.after_cancel(self._scheduled)
            except tk.TclError: pass
            self._scheduled=None
        textured=(self.display_mode=='textured' and self._mesh is not None
                  and self._albedo is not None)
        if textured and self._texture_image is not None:
            self.delete('all')
            width,height=self.winfo_width(),self.winfo_height()
            self._draw_backdrop(width,height)
            self.create_image(width//2,height//2,image=self._texture_image)
            self.create_text(12,max(height-15,1),anchor='sw',
                             text=self._backend_label+' · prévia em atualização',
                             fill='#9999A5',font=('Segoe UI',9))
        elif textured:
            # An asynchronous frame may take a moment; show a clear loading
            # state rather than the misleading dark 1600-face geometry view.
            self.delete('all')
            width,height=self.winfo_width(),self.winfo_height()
            self._draw_backdrop(width,height)
            self.create_text(width//2,height//2-13,
                             text='Preparando prévia colorida…',
                             fill='#DDDEE6',font=('Segoe UI',13,'bold'))
            self.create_text(width//2,height//2+15,
                             text='Renderização GPU ou CPU de reserva',
                             fill='#9EA9C2',font=('Segoe UI',10))
        else:
            super().render()
            if self.display_mode == 'wireframe':
                for item in self.find_all():
                    if self.type(item) == 'polygon':
                        self.itemconfigure(item,fill='',outline='#997DD8',width=.6)
        if textured:
            self._scheduled=self.after(50 if self.pbr_gpu_enabled else 180,
                                       self._start_texture)

    def _draw_backdrop(self,width,height):
        if ImageTk is None:
            return
        size=(max(1,width),max(1,height))
        if self._backdrop_size != size:
            self._backdrop_image=ImageTk.PhotoImage(studio_background(*size),master=self)
            self._backdrop_size=size
        self.create_image(width//2,height//2,image=self._backdrop_image)

    def _start_texture(self):
        self._scheduled = None
        if self._worker_busy or self.display_mode != 'textured':
            return
        if self._mesh is None or self._albedo is None:
            return
        ticket = self._paint_ticket
        canvas_size=(self.winfo_width(),self.winfo_height())
        width = min(PREVIEW_LIMIT,max(160,canvas_size[0]))
        height = min(PREVIEW_LIMIT,max(160,canvas_size[1]))
        args=(self._mesh,self._albedo,self._maes,self._normal_map,
              self.yaw,self.pitch,self.zoom,width,height,self.pan_x,self.pan_y,
              self.compare_reference,self.light_intensity,self.emission_intensity,
              not self.pbr_gpu_enabled,self.ambient_intensity,self.environment_preset)
        self._worker_busy = True

        def worker():
            try:
                frame,status=render_preview(*args,canvas_size=canvas_size)
                self._events.put((ticket,frame,status,None))
            except Exception as exc:
                self._events.put((ticket,None,None,str(exc)))
        try:
            self._pool.submit(worker)
        except RuntimeError:
            self._worker_busy=False

    def _poll(self):
        try:
            while True:
                ticket,image,backend,error = self._events.get_nowait()
                self._worker_busy=False
                if ticket != self._paint_ticket or self.display_mode != 'textured':
                    # A newer camera position wins. Do not display obsolete frames.
                    if self._scheduled is None and self.display_mode == 'textured':
                        self._scheduled=self.after(40,self._start_texture)
                    continue
                if error is not None:
                    self._preview_status='Falha na renderização: '+error[:100]
                    self.display_mode='geometry'
                    self.render()
                elif image is not None and ImageTk is not None:
                    self._backend_label=backend or 'Prévia'
                    self._texture_image=ImageTk.PhotoImage(image,master=self)
                    width,height=self.winfo_width(),self.winfo_height()
                    self.delete('all')
                    self._draw_backdrop(width,height)
                    self.create_image(width//2,height//2,image=self._texture_image)
                    if self.stats:
                        self.create_text(12,12,anchor='nw',
                                         text=f'{self.stats.vertices:,} vértices · {self.stats.faces:,} faces',
                                         fill='#F4F2FF',font=('Consolas',10))
                    self.create_text(12,max(height-15,1),anchor='sw',
                                     text=(self._backend_label+' · Referência 1×1' if self.compare_reference
                                          else self._backend_label+' · botão direito: girar · roda: zoom'),
                                     fill='#9999A5',font=('Segoe UI',9))
        except queue.Empty:
            pass
        try:
            if self.winfo_exists():
                self._poll_job=self.after(33,self._poll)
        except tk.TclError:
            return

    def destroy(self):
        if self._poll_job is not None:
            try: self.after_cancel(self._poll_job)
            except tk.TclError: pass
            self._poll_job=None
        if self._scheduled is not None:
            try: self.after_cancel(self._scheduled)
            except tk.TclError: pass
        self._pool.shutdown(wait=False,cancel_futures=True)
        super().destroy()

    def toggle_reference(self):
        """Toggle the comparative visual ruler in textured preview only."""
        self.compare_reference = not self.compare_reference
        if hasattr(self, 'reference_button'):
            self.reference_button.configure(
                text=('Humanoide 1×1: ligado' if self.compare_reference
                      else 'Humanoide 1×1: desligado'))
        self.render()

    def set_mode(self,mode):
        if mode not in ('geometry','textured','wireframe'):
            raise ValueError('Modo de prévia inválido')
        if mode == 'textured' and not TEXTURE_PREVIEW_AVAILABLE:
            self.display_mode='geometry'
            self._preview_status='Pillow/numpy não estão instalados; prévia geométrica disponível.'
        else:
            self.display_mode=mode
        self.render()

    def set_camera(self,view):
        views={'frente':(0.,0.),'lado':(1.5707963268,0.),
               'topo':(0.,1.40),'perspectiva':(.5,.24)}
        if view not in views:
            raise ValueError('Vista de câmera desconhecida')
        self.yaw,self.pitch=views[view]
        self.pan_x=self.pan_y=0
        self.render()

    def reset(self):
        self.pan_x = self.pan_y = 0.
        super().reset()

    def add_preview_controls(self, parent):
        """Toolbar appended above existing OBJ viewport and original controls."""
        holder=parent.winfo_children()[0]
        row=tk.Frame(holder,bg='#1B1D2D')
        children=holder.winfo_children()
        viewport=next((v for v in children if isinstance(v,tk.Frame) and
            any(isinstance(w,ObjViewer) for w in v.winfo_children())),None)
        row.pack(fill='x',pady=(0,8),before=viewport if viewport is not None else None)
        tk.Label(row,text='PRÉVIA',bg='#1B1D2D',fg='#B995FF',
                 font=('Segoe UI',9,'bold')).pack(side='left',padx=(12,8))
        modes=(('Texturas','textured'),('Sólido','geometry'),('Aramado','wireframe'))
        for name,mode in modes:
            tk.Button(row,text=name,command=lambda m=mode:self.set_mode(m),
                      bg='#303047',fg='#F4F2FF',activebackground='#7545D5',
                      activeforeground='white',relief='flat',bd=0,padx=9,pady=6,
                      cursor='hand2').pack(side='left',padx=3,pady=7)
        self.reference_button=tk.Button(
            row,text='Humanoide 1×1: ligado',command=self.toggle_reference,
            bg='#4D357C',fg='#FFFFFF',activebackground='#7545D5',
            activeforeground='white',relief='flat',bd=0,padx=10,pady=6,
            cursor='hand2')
        self.reference_button.pack(side='left',padx=(15,3),pady=7)
        camera=tk.Frame(holder,bg='#1B1D2D')
        camera.pack(fill='x',pady=(0,8),before=viewport if viewport is not None else None)
        tk.Label(camera,text='CÂMERA',bg='#1B1D2D',fg='#B995FF',
                 font=('Segoe UI',9,'bold')).pack(side='left',padx=(12,8))
        for name,view in (('Frente','frente'),('Lado','lado'),
                          ('Topo','topo'),('Perspectiva','perspectiva')):
            tk.Button(camera,text=name,command=lambda v=view:self.set_camera(v),
                      bg='#303047',fg='#F4F2FF',activebackground='#7545D5',
                      activeforeground='white',relief='flat',bd=0,padx=9,pady=6,
                      cursor='hand2').pack(side='left',padx=3,pady=7)
        tk.Label(camera,text='Botão direito: mover',bg='#1B1D2D',fg='#9B9DB6',
                 font=('Segoe UI',9)).pack(side='right',padx=9)
