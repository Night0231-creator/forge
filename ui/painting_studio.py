"""Basecoat-inspired, independently designed Astronyx UV painting workbench.

Albedo layers and local MAES presets share the V2.3 3D UV brush.
The 3D CPU preview shows Albedo only, not simulated metallic/emissive shading.
"""
from __future__ import annotations

import math
import tkinter as tk
from pathlib import Path
from tkinter import colorchooser, messagebox, ttk
from PIL import Image, ImageDraw, ImageTk
import numpy as np

from ui.paint3d_picker import ProjectedUVPicker

from core.paint_studio import PALETTE, find_albedo
from core.layered_materials import LayeredPaintSession, PRESETS, apply_materials_to_export
from core.footprint_calibrator import find_project_obj
from ui.texture_viewer import TexturedObjViewer

BG = '#0D101B'
PANEL = '#1B2032'
FIELD = '#282D43'
TEXT = '#F2EEFF'
MUTED = '#A8A3C1'
PURPLE = '#8E65EB'
GREEN = '#64DAB1'


class PaintingStudio(tk.Toplevel):
    def __init__(self, parent, project: str | Path, on_apply=None):
        self.project = Path(project).resolve()
        self.session = LayeredPaintSession(find_albedo(self.project),self.project)
        super().__init__(parent)
        self.title('Astronyx • Painting Studio — Camadas & Materiais V2.4')
        self.configure(bg=BG)
        self.geometry('1320x800')
        self.minsize(1080,680)
        self.transient(parent)
        self.mode = tk.StringVar(value='pincel')
        self.color = tk.StringVar(value='#8E65EB')
        self.size = tk.IntVar(value=20)
        self.opacity = tk.IntVar(value=100)
        self.tolerance = tk.IntVar(value=12)
        self.show_uv = tk.BooleanVar(value=True)
        self.status = tk.StringVar(value='Pinte a textura e salve um rascunho antes de aplicar.')
        self.on_apply = on_apply
        self._last = None
        self._refresh_id = None
        self._photo = None
        self._view = (0,0,1.)
        self._uv_outline = _uv_edges(self.project)
        self.paint3d_enabled = tk.BooleanVar(value=True)
        self._last_3d = None
        self._picker_state = None
        self._picker = None
        self._preview_job = None
        self._make_ui()
        self._render_texture()
        if self.session.restored_layers:
            self.status.set('Camadas da pintura anterior restauradas. A textura MAES é exibida somente após exportar no jogo.')

    @staticmethod
    def _label(parent, text, color=TEXT, size=10, bold=False, **kw):
        return tk.Label(parent,text=text,bg=parent.cget('bg'),fg=color,
                        font=('Segoe UI',size,'bold' if bold else 'normal'),**kw)

    @staticmethod
    def _button(parent, title, command, highlight=False):
        return tk.Button(parent,text=title,command=command,
                         bg=PURPLE if highlight else FIELD,fg='white',
                         activebackground='#6947C4',activeforeground='white',
                         relief='flat',padx=12,pady=8,cursor='hand2',
                         font=('Segoe UI',10,'bold'))

    def _make_ui(self):
        top=tk.Frame(self,bg=BG)
        top.pack(fill='x',padx=18,pady=(14,10))
        self._label(top,'ASTRONYX / PAINTING STUDIO',size=19,bold=True).pack(side='left')
        self._label(top,'Pintura 3D por UV • prévia CPU • exportação TaleSpire',
                    color=MUTED).pack(side='right')

        body=tk.Frame(self,bg=BG)
        body.pack(fill='both',expand=True,padx=16)
        left=tk.Frame(body,bg=PANEL,width=390)
        left.pack(side='left',fill='both',expand=True,padx=(0,10))
        self._label(left,'PINTURA DIRETA NO 3D',bold=True).pack(anchor='w',padx=12,pady=10)
        self.viewer = TexturedObjViewer(left,width=390,height=540)
        self.viewer.compare_reference = False
        self.viewer.pack(fill='both',expand=True,padx=8)
        try:
            self.viewer.open(find_project_obj(self.project))
        except (ValueError, OSError) as exc:
            self._label(left,str(exc),color=MUTED,wraplength=370).pack(padx=12)
        self.viewer.bind('<ButtonPress-1>',self._paint3d_start)
        self.viewer.bind('<B1-Motion>',self._paint3d_drag)
        self.viewer.bind('<ButtonRelease-1>',self._paint3d_end)
        # With 3D paint active the right mouse button rotates the miniature.
        self.viewer.bind('<ButtonPress-3>',self.viewer._start_drag)
        self.viewer.bind('<B3-Motion>',self.viewer._drag)
        self.viewer.bind('<ButtonRelease-3>',lambda _e:setattr(self.viewer,'last_mouse',None))
        tk.Checkbutton(left,text='Pintar diretamente no modelo 3D',
                       variable=self.paint3d_enabled,bg=PANEL,fg=TEXT,selectcolor=FIELD,
                       activebackground=PANEL,activeforeground=TEXT).pack(anchor='w',padx=12,pady=(6,2))
        self._label(left,'Esquerdo: pintar ou selecionar cor • direito: girar • roda: zoom. '
                    'Desmarque para usar o botão esquerdo para girar.',
                    color=MUTED,wraplength=370).pack(anchor='w',padx=12,pady=(0,12))

        center=tk.Frame(body,bg=PANEL,width=590)
        center.pack(side='left',fill='both',expand=True,padx=(0,10))
        self._label(center,'PINTURA NA TEXTURA UV',bold=True).pack(anchor='w',padx=12,pady=10)
        self.canvas=tk.Canvas(center,width=570,height=570,bg='#111524',
                              highlightthickness=1,highlightbackground='#464063')
        self.canvas.pack(fill='both',expand=True,padx=10,pady=(0,9))
        self.canvas.bind('<ButtonPress-1>',self._mouse_down)
        self.canvas.bind('<B1-Motion>',self._mouse_drag)
        self.canvas.bind('<ButtonRelease-1>',lambda _e:setattr(self,'_last',None))
        self.canvas.bind('<Configure>',lambda _e:self._request_refresh())
        tk.Checkbutton(center,text='Mostrar contornos UV (não são pintados)',
                       variable=self.show_uv,command=self._request_refresh,
                       bg=PANEL,fg=TEXT,selectcolor=FIELD,activebackground=PANEL,
                       activeforeground=TEXT).pack(anchor='w',padx=10,pady=(0,12))

        right_container=tk.Frame(body,bg=PANEL,width=280)
        right_container.pack(side='right',fill='y')
        right_container.pack_propagate(False)
        tabs=ttk.Notebook(right_container)
        tabs.pack(fill='both',expand=True,pady=(6,0))
        right=tk.Frame(tabs,bg=PANEL)
        layers_tab=tk.Frame(tabs,bg=PANEL)
        materials_tab=tk.Frame(tabs,bg=PANEL)
        tabs.add(right,text='Pincéis')
        tabs.add(layers_tab,text='Camadas')
        tabs.add(materials_tab,text='Materiais')
        self._build_layers_tab(layers_tab)
        self._build_materials_tab(materials_tab)
        self._label(right,'FERRAMENTAS',bold=True).pack(anchor='w',padx=14,pady=(14,8))
        for title,key in (('Pincel livre','pincel'),('Balde de cores','balde'),
                          ('Conta-gotas','conta-gotas'),('Restaurar original','borracha'),
                          ('Selecionar região similar','regiao')):
            tk.Radiobutton(right,text=title,value=key,variable=self.mode,
                           bg=PANEL,fg=TEXT,selectcolor=FIELD,
                           activebackground=PANEL,activeforeground=TEXT,
                           anchor='w').pack(fill='x',padx=14,pady=3)
        self._label(right,'Tamanho do pincel',color=MUTED).pack(anchor='w',padx=14,pady=(13,0))
        tk.Scale(right,from_=1,to=100,orient='horizontal',variable=self.size,
                 bg=PANEL,fg=TEXT,troughcolor=FIELD,highlightthickness=0).pack(fill='x',padx=12)
        self._label(right,'Opacidade (%)',color=MUTED).pack(anchor='w',padx=14,pady=(6,0))
        tk.Scale(right,from_=10,to=100,orient='horizontal',variable=self.opacity,
                 bg=PANEL,fg=TEXT,troughcolor=FIELD,highlightthickness=0).pack(fill='x',padx=12)
        self._label(right,'Tolerância do balde',color=MUTED).pack(anchor='w',padx=14,pady=(6,0))
        tk.Scale(right,from_=0,to=50,orient='horizontal',variable=self.tolerance,
                 bg=PANEL,fg=TEXT,troughcolor=FIELD,highlightthickness=0).pack(fill='x',padx=12)
        self._label(right,'PALETA',bold=True).pack(anchor='w',padx=14,pady=(10,8))
        palette=tk.Frame(right,bg=PANEL)
        palette.pack(padx=14,anchor='w')
        for i,(name,code) in enumerate(PALETTE.items()):
            b=tk.Button(palette,bg=code,width=3,height=1,relief='flat',
                        command=lambda c=code:self._set_color(c))
            b.grid(row=i//4,column=i%4,padx=4,pady=3)
            # Color description remains accessible on hover.
            b.bind('<Enter>',lambda _e,n=name:self.status.set('Material / cor: '+n))
        self._button(right,'Escolher cor…',self._choose_color).pack(fill='x',padx=14,pady=(10,5))
        actions=tk.Frame(right,bg=PANEL)
        actions.pack(fill='x',padx=10,pady=(5,10))
        self._button(actions,'Desfazer',self._undo).pack(side='left',padx=3)
        self._button(actions,'Refazer',self._redo).pack(side='left',padx=3)
        self._label(right,'Selecione uma região no 3D ou no atlas UV para aplicar material somente nela.',
                    color=MUTED,wraplength=245).pack(fill='x',padx=12,pady=(5,0))

        footer=tk.Frame(self,bg=BG)
        footer.pack(fill='x',padx=18,pady=12)
        self._label(footer,'',color=MUTED,textvariable=self.status,
                    wraplength=780).pack(side='left',fill='x',expand=True)
        self._button(footer,'Salvar rascunho',self._save).pack(side='right',padx=(8,0))
        self._button(footer,'Aplicar na exportação',self._apply,highlight=True).pack(side='right')

    def _build_layers_tab(self,tab):
        self._label(tab,'CAMADAS DE ALBEDO',bold=True).pack(anchor='w',padx=12,pady=(14,5))
        self.layer_list=tk.Listbox(tab,height=10,bg=FIELD,fg=TEXT,
                                   selectbackground=PURPLE,relief='flat',
                                   exportselection=False)
        self.layer_list.pack(fill='x',padx=10,pady=(0,8))
        self.layer_list.bind('<<ListboxSelect>>',self._layer_select)
        options=tk.Frame(tab,bg=PANEL)
        options.pack(anchor='w',padx=7)
        for name,command in (('+',self._layer_add),('−',self._layer_remove),
                             ('↑',lambda:self._layer_move(-1)),
                             ('↓',lambda:self._layer_move(1))):
            self._button(options,name,command).pack(side='left',padx=2)
        self.layer_visible=tk.BooleanVar(value=True)
        tk.Checkbutton(tab,text='Camada visível',variable=self.layer_visible,
                       command=self._layer_visibility,bg=PANEL,fg=TEXT,
                       selectcolor=FIELD,activebackground=PANEL,
                       activeforeground=TEXT).pack(anchor='w',padx=12,pady=(12,5))
        self.layer_opacity=tk.IntVar(value=100)
        self._label(tab,'Opacidade da camada',color=MUTED).pack(anchor='w',padx=12)
        opacity=tk.Scale(tab,from_=0,to=100,orient='horizontal',
                         variable=self.layer_opacity,bg=PANEL,fg=TEXT,
                         troughcolor=FIELD,highlightthickness=0)
        opacity.pack(fill='x',padx=12)
        opacity.bind('<ButtonRelease-1>',self._layer_opacity_change)
        self._label(tab,'As camadas são salvas como PNGs separados. '
                    'Mudar visibilidade não modifica o modelo original.',
                    color=MUTED,wraplength=245).pack(anchor='w',padx=12,pady=13)
        self._update_layers()

    def _update_layers(self):
        if not hasattr(self,'layer_list'):
            return
        self.layer_list.delete(0,tk.END)
        for layer in self.session.layers:
            marker='●' if layer.visible else '○'
            self.layer_list.insert(tk.END,f'{marker} {layer.name} · {layer.opacity}%')
        idx=self.session.active_layer
        self.layer_list.selection_set(idx)
        self.layer_list.activate(idx)
        layer=self.session.layers[idx]
        self.layer_visible.set(layer.visible)
        self.layer_opacity.set(layer.opacity)

    def _layer_select(self,_event):
        if not self.layer_list.curselection():
            return
        self.session.set_active(int(self.layer_list.curselection()[0]))
        layer=self.session.layers[self.session.active_layer]
        self.layer_visible.set(layer.visible)
        self.layer_opacity.set(layer.opacity)

    def _layer_add(self):
        try:
            self.session.add_layer(f'Camada {len(self.session.layers)+1}')
            self._update_layers()
        except ValueError as exc:
            messagebox.showwarning('Camadas',str(exc),parent=self)

    def _layer_remove(self):
        try:
            self.session.remove_layer()
            self._update_layers()
            self._request_refresh()
            self._schedule_preview()
        except ValueError as exc:
            messagebox.showwarning('Camadas',str(exc),parent=self)

    def _layer_move(self,step):
        self.session.move_layer(step)
        self._update_layers()
        self._request_refresh()
        self._schedule_preview()

    def _layer_visibility(self):
        self.session.set_visible(self.layer_visible.get())
        self._update_layers()
        self._request_refresh()
        self._schedule_preview()

    def _layer_opacity_change(self,_event):
        self.session.set_opacity(int(self.layer_opacity.get()))
        self._update_layers()
        self._request_refresh()
        self._schedule_preview()

    def _build_materials_tab(self,tab):
        self._label(tab,'MATERIAIS TALESPIRE',bold=True).pack(anchor='w',padx=12,pady=(14,5))
        self.material_name=tk.StringVar(value=list(PRESETS)[0])
        menu=ttk.Combobox(tab,values=list(PRESETS),textvariable=self.material_name,
                          state='readonly',width=22)
        menu.pack(fill='x',padx=10,pady=(3,12))
        self._button(tab,'Aplicar na região',self._apply_material,highlight=True).pack(fill='x',padx=10)
        self._button(tab,'Limpar seleção',self._clear_region).pack(fill='x',padx=10,pady=(8,0))
        self._label(tab,'PASSOS',bold=True).pack(anchor='w',padx=12,pady=(20,5))
        self._label(tab,'1. Na aba Pincéis selecione “Selecionar região similar”. '
                    '2. Clique em uma área do 3D ou da textura. '
                    '3. Volte aqui e aplique um material.',
                    color=MUTED,wraplength=240).pack(anchor='w',padx=12)
        availability=('MAES detectada' if self.session.maes_image is not None
                      else 'MAES ausente: converta o modelo primeiro')
        self._label(tab,availability,color=GREEN if self.session.maes_image is not None
                    else MUTED,wraplength=245).pack(anchor='w',padx=12,pady=(16,0))
        self._label(tab,'Canais MAES: Vermelho=Metal, Verde=AO, Azul=Emissão, Alfa=Suavidade. '
                    'A prévia 3D mostra apenas as cores Albedo; os efeitos '
                    'de superfície aparecem no TaleSpire após reexportar.',
                    color=MUTED,wraplength=245).pack(anchor='w',padx=12,pady=(14,0))

    def _apply_material(self):
        try:
            self.session.apply_material(self.material_name.get())
            self.status.set('Material '+self.material_name.get()+
                ' aplicado à região. Salve e reexporte para conferir no TaleSpire.')
        except (OSError,ValueError) as exc:
            messagebox.showwarning('Material',str(exc),parent=self)

    def _clear_region(self):
        self.session.clear_region()
        self._request_refresh()
        self.status.set('Seleção de região removida.')

    def _pick_region(self,point):
        active=self.session.select_region(*point,self.tolerance.get())
        self.status.set('Região conectada selecionada para pintura e materiais.'
                        if active else 'Nenhuma região selecionada.')
        self._request_refresh()

    def _set_color(self,value):
        self.color.set(value)
        self.status.set('Cor selecionada: '+value)

    def _choose_color(self):
        chosen=colorchooser.askcolor(color=self.color.get(),parent=self)
        if chosen and chosen[1]:
            self._set_color(chosen[1])

    def _coords(self,event):
        x0,y0,scale=self._view
        x=int((event.x-x0)/scale)
        y=int((event.y-y0)/scale)
        if 0<=x<self.session.image.width and 0<=y<self.session.image.height:
            return (x,y)
        return None

    def _mouse_down(self,event):
        p=self._coords(event)
        if p is None: return
        mode=self.mode.get()
        if mode=='conta-gotas':
            self._set_color(self.session.pick(*p))
            return
        if mode=='regiao':
            self._pick_region(p)
            return
        self.session.checkpoint()
        if mode=='balde':
            self.session.bucket(*p,self.color.get(),self.tolerance.get())
        else:
            self.session.stroke(p,p,self.color.get(),self.size.get(),
                                self.opacity.get()/100,erase=(mode=='borracha'))
        self._last=p if mode in ('pincel','borracha') else None
        self._request_refresh()
        self._schedule_preview()

    def _mouse_drag(self,event):
        point=self._coords(event)
        if point is None or self._last is None: return
        self.session.stroke(self._last,point,self.color.get(),self.size.get(),
                            self.opacity.get()/100,erase=self.mode.get()=='borracha')
        self._last=point
        self._request_refresh()
        self._schedule_preview()

    def _request_refresh(self):
        if self._refresh_id is None:
            self._refresh_id=self.after(40,self._render_texture)

    def _render_texture(self):
        self._refresh_id=None
        if not self.winfo_exists(): return
        cw=max(self.canvas.winfo_width(),200)
        ch=max(self.canvas.winfo_height(),200)
        src=self.session.image
        scale=min((cw-20)/src.width,(ch-20)/src.height)
        width=max(1,round(src.width*scale))
        height=max(1,round(src.height*scale))
        x0=(cw-width)//2
        y0=(ch-height)//2
        self._view=(x0,y0,scale)
        image=src.resize((width,height),Image.Resampling.BILINEAR).convert('RGB')
        if self.session.selection is not None:
            mask=self.session.selection.resize((width,height),Image.Resampling.NEAREST)
            tint=Image.blend(image,Image.new('RGB',image.size,'#AA68EC'),.22)
            image=Image.composite(tint,image,mask)
        if self.show_uv.get():
            # Overlay is preview-only, never written to the painted PNG.
            uv=ImageDraw.Draw(image)
            for a,b in self._uv_outline:
                uv.line((a[0]*width,(1-a[1])*height,
                         b[0]*width,(1-b[1])*height),fill='#4BEBE4',width=1)
        self._photo=ImageTk.PhotoImage(image,master=self)
        self.canvas.delete('all')
        self.canvas.create_image(x0,y0,anchor='nw',image=self._photo)
        self.canvas.create_rectangle(x0,y0,x0+width,y0+height,outline='#A88BFF')

    def _picker_for_camera(self):
        model=self.viewer._mesh
        if model is None:
            return None
        state=(id(model), self.viewer.winfo_width(), self.viewer.winfo_height(),
               self.viewer.yaw, self.viewer.pitch, self.viewer.zoom,
               self.viewer.pan_x, self.viewer.pan_y, self.viewer.compare_reference)
        if self._picker is None or self._picker_state != state:
            self._picker=ProjectedUVPicker(
                model,yaw=self.viewer.yaw,pitch=self.viewer.pitch,zoom=self.viewer.zoom,
                canvas_width=self.viewer.winfo_width(),canvas_height=self.viewer.winfo_height(),
                pan_x=self.viewer.pan_x,pan_y=self.viewer.pan_y,
                show_reference=self.viewer.compare_reference)
            self._picker_state=state
        return self._picker

    def _surface_pixel(self,event):
        picker=self._picker_for_camera()
        hit=picker.hit(event.x,event.y) if picker is not None else None
        if hit is None:
            return None
        return hit.pixel(*self.session.image.size)

    def _paint3d_start(self,event):
        self._last_3d=None
        if not self.paint3d_enabled.get():
            self.viewer._start_drag(event)
            return
        try:
            point=self._surface_pixel(event)
        except ValueError as exc:
            self.status.set(str(exc))
            return
        if point is None:
            self.status.set('Clique sobre uma parte visível do personagem.')
            return
        mode=self.mode.get()
        if mode=='conta-gotas':
            self._set_color(self.session.pick(*point))
            return
        if mode=='regiao':
            self._pick_region(point)
            return
        self.session.checkpoint()
        if mode=='balde':
            self.session.bucket(*point,self.color.get(),self.tolerance.get())
        else:
            self.session.stroke(point,point,self.color.get(),self.size.get(),
                                self.opacity.get()/100,erase=(mode=='borracha'))
            self._last_3d=point
        self._request_refresh()
        self._schedule_preview()

    def _paint3d_drag(self,event):
        if not self.paint3d_enabled.get():
            self.viewer._drag(event)
            return
        if self.mode.get() not in ('pincel','borracha') or self._last_3d is None:
            return
        point=self._surface_pixel(event)
        if point is None:
            self._last_3d=None
            return
        prev=self._last_3d
        # Do not draw long artificial lines across UV seams or disjoint islands.
        threshold=max(self.size.get()*4,int(min(self.session.image.size)*.04))
        linked=((point[0]-prev[0])**2+(point[1]-prev[1])**2) <= threshold**2
        self.session.stroke(prev if linked else point,point,self.color.get(),
                            self.size.get(),self.opacity.get()/100,
                            erase=self.mode.get()=='borracha')
        self._last_3d=point
        self._request_refresh()
        self._schedule_preview()

    def _paint3d_end(self,_event):
        self._last_3d=None
        self.viewer.last_mouse=None
        self._schedule_preview()

    def _schedule_preview(self):
        if self._preview_job is None:
            self._preview_job=self.after(280,self._refresh_live_preview)

    def _refresh_live_preview(self):
        self._preview_job=None
        if not self.winfo_exists() or self.viewer._mesh is None:
            return
        image=self.session.image.convert('RGB')
        image.thumbnail((1024,1024),Image.Resampling.BILINEAR)
        self.viewer._albedo=np.asarray(image,dtype=np.uint8).copy()
        self.viewer.render()

    def _undo(self):
        if self.session.undo():
            self._update_layers()
            self._request_refresh()
            self._schedule_preview()

    def _redo(self):
        if self.session.redo():
            self._update_layers()
            self._request_refresh()
            self._schedule_preview()

    def _save(self):
        try:
            self.saved=None
            self.saved=self.session.save_draft(self.project)
            self.status.set('Rascunho e camadas salvos: '+str(self.saved))
        except (OSError,ValueError) as exc:
            messagebox.showerror('Falha ao salvar',str(exc),parent=self)

    def _apply(self):
        if not messagebox.askyesno('Aplicar pintura',
            'A pintura será copiada para as texturas de exportação com backup. '
            'O arquivo .tsMod existente NÃO será modificado; depois gere novamente o .tsMod. Continuar?',
            parent=self):
            return
        try:
            self._save()
            if not getattr(self,'saved',None): return
            changed=apply_materials_to_export(
                self.project,self.saved,self.session.material_draft if self.session.maes_dirty else None)
            self.status.set('Pintura aplicada em '+str(len(changed))+' textura(s). Reexporte o .tsMod.')
            try:
                self.viewer.open(find_project_obj(self.project))
            except (OSError,ValueError):
                pass
            if self.on_apply: self.on_apply()
        except (OSError,ValueError) as exc:
            messagebox.showerror('Não foi possível aplicar',str(exc),parent=self)


def _uv_edges(project: Path, max_lines: int = 3500):
    """Read OBJ UV topology for a visual overlay; do not modify UV geometry."""
    try:
        obj=find_project_obj(project)
    except (OSError,ValueError):
        return []
    uvs=[]
    edges=[]
    try:
        with obj.open('r',encoding='utf-8-sig',errors='replace') as stream:
            for line in stream:
                if line.startswith('vt '):
                    parts=line.split()
                    if len(parts)>=3:
                        uvs.append((float(parts[1]),float(parts[2])))
                elif line.startswith('f '):
                    indices=[]
                    for token in line.split()[1:]:
                        bits=token.split('/')
                        if len(bits)<2 or not bits[1]: continue
                        idx=int(bits[1])
                        idx=idx-1 if idx>0 else len(uvs)+idx
                        if 0<=idx<len(uvs): indices.append(idx)
                    for i,a in enumerate(indices):
                        if len(edges)>=max_lines: break
                        b=indices[(i+1)%len(indices)]
                        if len(indices)>1:
                            edges.append((uvs[a],uvs[b]))
                    if len(edges)>=max_lines: break
    except (OSError,ValueError,IndexError):
        return []
    return edges


def open_painting_studio(parent,project: str | Path,on_apply=None):
    return PaintingStudio(parent,project,on_apply=on_apply)
