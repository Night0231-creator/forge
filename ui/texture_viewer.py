"""Responsive textured OBJ preview for Astronyx.

Rotating uses the original Tk geometry preview. After idle, a CPU UV/albedo
render is computed off the Tk thread. Blender export pipeline is untouched.
"""
from __future__ import annotations

import queue
import threading
import tkinter as tk
from pathlib import Path

from core.preview import ObjViewer

try:
    from PIL import ImageTk
    from .texture_renderer import load_obj, read_albedo, draw, PreviewError
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
        self._texture_image = None
        self._preview_status = ''
        self._paint_ticket = 0
        self._scheduled = None
        self._worker_busy = False
        self._events = queue.Queue()
        self._poll_job = None
        super().__init__(parent, **kwargs)
        self.bind('<ButtonPress-3>', self._start_drag)
        self.bind('<B3-Motion>', self._pan)
        self._poll_job = self.after(100, self._poll)

    def open(self, file: Path):
        self._mesh = None
        self._albedo = None
        self._preview_status = ''
        super().open(file)
        if not TEXTURE_PREVIEW_AVAILABLE:
            self._preview_status = 'Texturas indisponíveis: instale Pillow e numpy.'
            self.render()
            return
        try:
            self._mesh = load_obj(file)
            self._albedo = read_albedo(self._mesh.texture_path)
            if self._mesh.limited:
                self._preview_status = 'Prévia limitada a 150 mil triângulos; não altera o arquivo final.'
            else:
                self._preview_status = 'Textura albedo + UV · prévia CPU'
        except (OSError, ValueError, MemoryError) as exc:
            self._preview_status = str(exc)
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
        """Show responsive shaded geometry immediately, texture after idle."""
        self._paint_ticket += 1
        if self._scheduled is not None:
            try:
                self.after_cancel(self._scheduled)
            except tk.TclError:
                pass
            self._scheduled = None
        super().render()
        if self.display_mode == 'wireframe':
            for item in self.find_all():
                if self.type(item) == 'polygon':
                    self.itemconfigure(item, fill='', outline='#997DD8', width=.6)
        if self._preview_status and self.stats:
            self.create_text(15,35,anchor='nw',text=self._preview_status,
                             fill='#E6D7FF',font=('Segoe UI',9))
        if self.display_mode == 'textured' and self._mesh is not None and self._albedo is not None:
            self._scheduled = self.after(250, self._start_texture)

    def _start_texture(self):
        self._scheduled = None
        if self._worker_busy or self.display_mode != 'textured':
            return
        if self._mesh is None or self._albedo is None:
            return
        ticket = self._paint_ticket
        width = min(720,max(160,self.winfo_width()))
        height = min(720,max(160,self.winfo_height()))
        args=(self._mesh,self._albedo,self.yaw,self.pitch,self.zoom,width,height,
              self.pan_x,self.pan_y,False,self.compare_reference,1.75)
        self._worker_busy = True

        def worker():
            try:
                result = draw(*args)
                self._events.put((ticket,result,None))
            except Exception as exc:
                self._events.put((ticket,None,str(exc)))
        threading.Thread(target=worker,daemon=True).start()

    def _poll(self):
        try:
            while True:
                ticket,image,error = self._events.get_nowait()
                self._worker_busy=False
                if ticket != self._paint_ticket or self.display_mode != 'textured':
                    # A newer camera position wins. Do not display obsolete frames.
                    if self._scheduled is None and self.display_mode == 'textured':
                        self._scheduled=self.after(100,self._start_texture)
                    continue
                if error is not None:
                    self._preview_status='Falha na renderização: '+error[:100]
                    self.display_mode='geometry'
                    self.render()
                elif image is not None and ImageTk is not None:
                    self._texture_image=ImageTk.PhotoImage(image,master=self)
                    width,height=self.winfo_width(),self.winfo_height()
                    self.delete('all')
                    self.create_rectangle(0,0,width,height,fill='#111522',outline='')
                    self.create_image(width//2,height//2,image=self._texture_image)
                    if self.stats:
                        self.create_text(12,12,anchor='nw',
                                         text=f'{self.stats.vertices:,} vértices · {self.stats.faces:,} faces',
                                         fill='#F4F2FF',font=('Consolas',10))
                    self.create_text(12,max(height-15,1),anchor='sw',
                                     text='Albedo + UV · arraste para girar · referência humanoide visual 1×1' if self.compare_reference else
                                          'Albedo + UV · arraste para girar · botão direito: mover · roda: zoom',
                                     fill='#D6CAE8',font=('Segoe UI',9))
        except queue.Empty:
            pass
        try:
            if self.winfo_exists():
                self._poll_job=self.after(100,self._poll)
        except tk.TclError:
            return

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
