"""Independent Astronyx surface painting workbench with Albedo/MAES layers.

Screen-projected surface brushes share the texture editor's layer/history model.
GPU PBR preview is optional; CPU fallback shows Albedo.
"""
from __future__ import annotations

import math
import tkinter as tk
from pathlib import Path
from tkinter import colorchooser, filedialog, messagebox, ttk
from PIL import Image, ImageDraw, ImageTk
import numpy as np

from ui.paint3d_picker import ProjectedUVPicker
from ui.surface_paint import surface_masks
from core.brushes import stamp_mask
from core.mesh_regions import MeshRegions
from core.version import APP_VERSION

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


class PaintingStudio(tk.Frame):
    def __init__(self, parent, project: str | Path, on_apply=None, on_exit=None):
        self.project = Path(project).resolve()
        self.session = LayeredPaintSession(find_albedo(self.project),self.project)
        super().__init__(parent,bg=BG)
        self.on_exit = on_exit
        self.mode = tk.StringVar(value='pincel')
        self.color = tk.StringVar(value='#8E65EB')
        self.size = tk.IntVar(value=20)
        self.opacity = tk.IntVar(value=100)
        self.tolerance = tk.IntVar(value=12)
        self.hardness = tk.IntVar(value=75)
        self.paint_through = tk.BooleanVar(value=False)
        self.region_mode = tk.StringVar(value='Geometria')
        self.region_angle = tk.IntVar(value=35)
        self._regions = None
        self._region_mesh = None
        self._current_hit = None
        self.stamp_name=tk.StringVar(value='Estrela')
        self.stamp_image=None
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
        """Unified dock: tools / broad 3D canvas / collapsible UV inspector."""
        sty=ttk.Style(self)
        sty.configure('PaintStudio.TNotebook',background=PANEL,borderwidth=0)
        sty.configure('PaintStudio.TNotebook.Tab',background=FIELD,foreground=TEXT,
                      font=('Segoe UI',9,'bold'),padding=(6,9))
        sty.map('PaintStudio.TNotebook.Tab',
                background=[('selected',PURPLE)],foreground=[('selected','#FFFFFF')])

        header=tk.Frame(self,bg='#111525',height=63)
        header.pack(fill='x')
        header.pack_propagate(False)
        line=tk.Frame(header,bg='#111525')
        line.pack(fill='both',expand=True,padx=14)
        if self.on_exit is not None:
            self._button(line,'← Projetos',self.on_exit).pack(side='left',padx=(0,14))
        self._label(line,'◈ ASTRONYX  /  PAINT STUDIO',color=TEXT,size=15,bold=True).pack(
            side='left',pady=13)
        self._label(line,f'ESTÚDIO 3D  ·  V{APP_VERSION}',color='#B89EFA',size=9,bold=True).pack(
            side='left',padx=14)
        self._button(line,'Exportar texturas',self._apply,highlight=True).pack(
            side='right',pady=10)
        self._button(line,'Salvar projeto',self._save).pack(side='right',padx=8,pady=10)

        footer=tk.Frame(self,bg='#111525',height=41)
        footer.pack(side='bottom',fill='x')
        footer.pack_propagate(False)
        self._label(footer,'',color=MUTED,textvariable=self.status,wraplength=1100,
                    size=9).pack(side='left',fill='x',expand=True,padx=16,pady=10)

        body=tk.Frame(self,bg=BG)
        body.pack(fill='both',expand=True,padx=10,pady=10)
        body.grid_rowconfigure(0,weight=1)
        body.grid_columnconfigure(0,minsize=244,weight=0)
        body.grid_columnconfigure(1,weight=1,minsize=460)
        body.grid_columnconfigure(2,minsize=0,weight=0)

        # Left tool and layer docks.
        tools=tk.Frame(body,bg=PANEL,width=246,highlightbackground='#303754',
                       highlightthickness=1)
        tools.grid(row=0,column=0,sticky='ns',padx=(0,9))
        tools.grid_propagate(False)
        tabs=ttk.Notebook(tools,style='PaintStudio.TNotebook')
        tabs.pack(fill='both',expand=True,pady=5,padx=5)
        right=self._tool_tab(tabs,'Pintar')
        layers_tab=self._tool_tab(tabs,'Camadas')
        materials_tab=self._tool_tab(tabs,'Material')
        options_tab=self._tool_tab(tabs,'Opções')
        self._build_surface_options(options_tab)
        self._build_layers_tab(layers_tab)
        self._build_materials_tab(materials_tab)
        self._label(right,'PINTURA',bold=True,color='#BFA7FF').pack(
            anchor='w',padx=12,pady=(10,8))
        for title,key in (('Pincel','pincel'),('Preenchimento','balde'),
                          ('Conta-gotas','conta-gotas'),('Borracha','borracha'),
                          ('Selecionar região','regiao'),('Carimbo','carimbo')):
            tk.Radiobutton(right,text=title,value=key,variable=self.mode,
                           bg=PANEL,fg=TEXT,selectcolor=FIELD,
                           activebackground=PANEL,activeforeground=TEXT,
                           anchor='w',font=('Segoe UI',10)).pack(fill='x',padx=11,pady=4)
        self._label(right,'TAMANHO',color=MUTED,size=9,bold=True).pack(
            anchor='w',padx=12,pady=(14,0))
        tk.Scale(right,from_=1,to=100,orient='horizontal',variable=self.size,
                 bg=PANEL,fg=TEXT,troughcolor=FIELD,highlightthickness=0).pack(
            fill='x',padx=9)
        self._label(right,'OPACIDADE',color=MUTED,size=9,bold=True).pack(
            anchor='w',padx=12,pady=(6,0))
        tk.Scale(right,from_=10,to=100,orient='horizontal',variable=self.opacity,
                 bg=PANEL,fg=TEXT,troughcolor=FIELD,highlightthickness=0).pack(
            fill='x',padx=9)
        self._label(right,'SIMILARIDADE',color=MUTED,size=9,bold=True).pack(
            anchor='w',padx=12,pady=(6,0))
        tk.Scale(right,from_=0,to=50,orient='horizontal',variable=self.tolerance,
                 bg=PANEL,fg=TEXT,troughcolor=FIELD,highlightthickness=0).pack(
            fill='x',padx=9)
        self._label(right,'PALETA RÁPIDA',bold=True,size=9,color=MUTED).pack(
            anchor='w',padx=12,pady=(10,6))
        palette=tk.Frame(right,bg=PANEL)
        palette.pack(padx=12,anchor='w')
        for i,(name,code) in enumerate(PALETTE.items()):
            swatch=tk.Button(palette,bg=code,width=3,height=1,relief='flat',
                            command=lambda c=code:self._set_color(c))
            swatch.grid(row=i//4,column=i%4,padx=3,pady=3)
            swatch.bind('<Enter>',lambda _e,n=name:self.status.set('Material / cor: '+n))
        self._button(right,'Escolher cor…',self._choose_color).pack(
            fill='x',padx=11,pady=(11,5))
        actions=tk.Frame(right,bg=PANEL)
        actions.pack(fill='x',padx=8,pady=(6,10))
        self._button(actions,'↶ Desfazer',self._undo).pack(side='left',padx=3)
        self._button(actions,'↷ Refazer',self._redo).pack(side='left',padx=3)
        for button in actions.winfo_children():
            button.configure(font=('Segoe UI',9),padx=5)

        # The 3D model now dominates the window instead of sharing space 50/50.
        viewport=tk.Frame(body,bg='#121626',highlightbackground='#303754',
                          highlightthickness=1)
        viewport.grid(row=0,column=1,sticky='nsew')
        vheader=tk.Frame(viewport,bg='#1B2032',height=46)
        vheader.pack(fill='x')
        vheader.pack_propagate(False)
        self._label(vheader,'VISUALIZAÇÃO 3D',bold=True,color=TEXT,size=10).pack(
            side='left',padx=13,pady=12)
        self.show_uv_editor=tk.BooleanVar(value=False)
        tk.Checkbutton(vheader,text='Mostrar mapa UV',variable=self.show_uv_editor,
                       command=self._toggle_uv_panel,bg='#1B2032',fg=TEXT,
                       selectcolor=FIELD,activebackground='#1B2032',
                       activeforeground=TEXT).pack(side='right',padx=13)
        self.viewer=TexturedObjViewer(viewport,width=640,height=580)
        self.viewer.compare_reference=False
        self.viewer.pack(fill='both',expand=True,padx=5,pady=5)
        self._pbr_on=tk.BooleanVar(value=True)
        self._light_level=tk.IntVar(value=100)
        self._emission_level=tk.IntVar(value=100)
        self._ambient_level=tk.IntVar(value=100)
        self._environment=tk.StringVar(value='Estúdio')
        try:
            self.viewer.open(find_project_obj(self.project))
        except (OSError,ValueError) as exc:
            self._label(viewport,str(exc),color=MUTED,wraplength=580).pack(pady=8)
        if self.session.maes_image is not None:
            self.viewer.set_materials(self.session.maes_image)
        self.viewer.bind('<ButtonPress-1>',self._paint3d_start)
        self.viewer.bind('<B1-Motion>',self._paint3d_drag)
        self.viewer.bind('<ButtonRelease-1>',self._paint3d_end)
        self.viewer.bind('<ButtonPress-3>',self.viewer._start_drag)
        self.viewer.bind('<B3-Motion>',self.viewer._drag)
        self.viewer.bind('<ButtonRelease-3>',
                         lambda _e:setattr(self.viewer,'last_mouse',None))
        lighting=tk.Frame(viewport,bg='#1B2032')
        lighting.pack(fill='x',padx=9)
        tk.Checkbutton(lighting,text='GPU / PBR',variable=self._pbr_on,
                       command=self._apply_lighting,bg='#1B2032',fg=TEXT,
                       selectcolor=FIELD,activebackground='#1B2032',
                       activeforeground=TEXT).pack(side='left',padx=(3,8))
        self._label(lighting,'Luz',color=MUTED,size=9).pack(side='left')
        tk.Scale(lighting,from_=0,to=300,resolution=10,orient='horizontal',
                 variable=self._light_level,command=lambda _v:self._apply_lighting(),
                 length=135,showvalue=False,bg='#1B2032',fg=TEXT,
                 troughcolor=FIELD,highlightthickness=0).pack(side='left',padx=(4,12))
        self._label(lighting,'Emissão',color=MUTED,size=9).pack(side='left')
        tk.Scale(lighting,from_=0,to=300,resolution=10,orient='horizontal',
                 variable=self._emission_level,command=lambda _v:self._apply_lighting(),
                 length=125,showvalue=False,bg='#1B2032',fg=TEXT,
                 troughcolor=FIELD,highlightthickness=0).pack(side='left',padx=4)
        ambience=tk.Frame(viewport,bg='#1B2032')
        ambience.pack(fill='x',padx=9)
        self._label(ambience,'Ambiente',color=MUTED,size=9).pack(side='left',padx=(3,8))
        from ui.gpu_pbr_renderer import ENV_PRESETS
        ttk.Combobox(ambience,textvariable=self._environment,
                     values=list(ENV_PRESETS),state='readonly',
                     width=15).pack(side='left',padx=(0,9))
        self._label(ambience,'Intensidade',color=MUTED,size=9).pack(side='left')
        tk.Scale(ambience,from_=0,to=200,resolution=10,orient='horizontal',
                 variable=self._ambient_level,command=lambda _v:self._apply_lighting(),
                 length=140,showvalue=False,bg='#1B2032',fg=TEXT,
                 troughcolor=FIELD,highlightthickness=0).pack(side='left',padx=(4,12))
        self._environment.trace_add('write',lambda *_:self._apply_lighting())
        vfoot=tk.Frame(viewport,bg='#1B2032')
        vfoot.pack(fill='x')
        self.paint3d_enabled=tk.BooleanVar(value=True)
        tk.Checkbutton(vfoot,text='Pintar no 3D',variable=self.paint3d_enabled,
                       bg='#1B2032',fg='#8FE7C3',selectcolor=FIELD,
                       activebackground='#1B2032',activeforeground=TEXT).pack(
            side='left',padx=13,pady=8)
        self._label(vfoot,'Esquerdo: pintar   •   Direito: girar   •   Roda: zoom',
                    color=MUTED,size=9).pack(side='right',padx=13)

        # Optional UV inspector. Hidden by default to maximize model area.
        self.uv_panel=tk.Frame(body,bg=PANEL,width=295,
                               highlightbackground='#303754',highlightthickness=1)
        self.uv_panel.grid(row=0,column=2,sticky='nsew',padx=(9,0))
        self.uv_panel.grid_propagate(False)
        self._label(self.uv_panel,'MAPA UV  /  ALBEDO',bold=True,color=TEXT,size=10).pack(
            anchor='w',padx=12,pady=(14,10))
        self.canvas=tk.Canvas(self.uv_panel,width=278,height=400,
                              bg='#101423',highlightbackground=FIELD,
                              highlightthickness=1)
        self.canvas.pack(fill='both',expand=True,padx=8,pady=(0,8))
        self.canvas.bind('<ButtonPress-1>',self._mouse_down)
        self.canvas.bind('<B1-Motion>',self._mouse_drag)
        self.canvas.bind('<ButtonRelease-1>',lambda _e:setattr(self,'_last',None))
        self.canvas.bind('<Configure>',lambda _e:self._request_refresh())
        tk.Checkbutton(self.uv_panel,text='Bordas UV',variable=self.show_uv,
                       command=self._request_refresh,bg=PANEL,fg=TEXT,
                       selectcolor=FIELD,activebackground=PANEL,
                       activeforeground=TEXT).pack(anchor='w',padx=10,pady=(0,12))
        self.uv_panel.grid_remove()

    def _apply_lighting(self):
        if hasattr(self,'viewer'):
            self.viewer.set_lighting(light=self._light_level.get()/100,
                                     emission=self._emission_level.get()/100,
                                     ambient=self._ambient_level.get()/100,
                                     environment=self._environment.get(),
                                     gpu=self._pbr_on.get())

    def _toggle_uv_panel(self):
        if self.show_uv_editor.get():
            self.uv_panel.grid()
            self._request_refresh()
        else:
            self.uv_panel.grid_remove()

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
                    color=MUTED,wraplength=206).pack(anchor='w',padx=12,pady=13)
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

    def _tool_tab(self,tabs,title):
        """Keep every tool reachable on smaller Windows displays."""
        page=tk.Frame(tabs,bg=PANEL)
        tabs.add(page,text=title)
        scroll=ttk.Scrollbar(page,orient='vertical')
        scroll.pack(side='right',fill='y')
        canvas=tk.Canvas(page,bg=PANEL,highlightthickness=0,
                         yscrollcommand=scroll.set,width=200)
        canvas.pack(fill='both',expand=True)
        scroll.configure(command=canvas.yview)
        content=tk.Frame(canvas,bg=PANEL)
        item=canvas.create_window(0,0,anchor='nw',window=content)
        content.bind('<Configure>',lambda _e:canvas.configure(scrollregion=canvas.bbox('all')))
        canvas.bind('<Configure>',lambda e:canvas.itemconfigure(item,width=e.width))
        canvas.bind('<MouseWheel>',lambda e:canvas.yview_scroll(-int(e.delta/120),'units'))
        return content

    def _build_surface_options(self,tab):
        self._label(tab,'PINCEL DE SUPERFÍCIE',bold=True,color='#BFA7FF').pack(
            anchor='w',padx=12,pady=(14,8))
        self._label(tab,'Dureza da borda',color=MUTED).pack(anchor='w',padx=12)
        tk.Scale(tab,from_=0,to=100,orient='horizontal',variable=self.hardness,
                 bg=PANEL,fg=TEXT,troughcolor=FIELD,highlightthickness=0).pack(fill='x',padx=9)
        tk.Checkbutton(tab,text='Pintar através do modelo',variable=self.paint_through,
                       bg=PANEL,fg=TEXT,selectcolor=FIELD,
                       activebackground=PANEL,activeforeground=TEXT).pack(anchor='w',padx=9,pady=5)
        self._label(tab,'No 3D, tamanho em pixels da tela. Girar o modelo permite '
                    'pintar outros lados. Pintar através inclui as superfícies ocultas.',
                    color=MUTED,wraplength=206,size=9).pack(anchor='w',padx=12,pady=(2,12))
        self._label(tab,'SELEÇÃO E PREENCHIMENTO',bold=True,size=9).pack(anchor='w',padx=12)
        ttk.Combobox(tab,values=('Geometria','Cor similar'),
                     textvariable=self.region_mode,state='readonly',width=20).pack(fill='x',padx=11,pady=8)
        self._label(tab,'Limite de ângulo entre faces',color=MUTED,size=9).pack(anchor='w',padx=12)
        tk.Scale(tab,from_=0,to=180,orient='horizontal',variable=self.region_angle,
                 bg=PANEL,fg=TEXT,troughcolor=FIELD,highlightthickness=0).pack(fill='x',padx=9)
        self._label(tab,'Ângulos menores separam bordas. A geometria funciona mesmo '
                    'sem cores; o mapa UV usa a seleção por cor.',
                    color=MUTED,wraplength=206,size=9).pack(anchor='w',padx=12,pady=(2,12))
        self._button(tab,'Limpar seleção',self._clear_region).pack(fill='x',padx=11,pady=4)
        self._label(tab,'CARIMBOS',color=MUTED,size=9,bold=True).pack(anchor='w',padx=12,pady=(14,5))
        ttk.Combobox(tab,values=('Estrela','Selo','Runa','PNG personalizado'),
                     textvariable=self.stamp_name,state='readonly',width=20).pack(fill='x',padx=11,pady=4)
        self._button(tab,'Carregar PNG…',self._load_custom_stamp).pack(fill='x',padx=11,pady=4)

    def _build_materials_tab(self,tab):
        self._label(tab,'MATERIAIS TALESPIRE',bold=True).pack(anchor='w',padx=12,pady=(14,5))
        self.material_name=tk.StringVar(value=list(PRESETS)[0])
        menu=ttk.Combobox(tab,values=list(PRESETS),textvariable=self.material_name,
                          state='readonly',width=22)
        menu.pack(fill='x',padx=10,pady=(3,12))
        self._material_channels = [tk.IntVar(value=value) for value in PRESETS[self.material_name.get()]]
        for title,variable in zip(('Metal','Oclusão ambiente','Emissão','Suavidade'),self._material_channels):
            self._label(tab,title,color=MUTED,size=9).pack(anchor='w',padx=12)
            tk.Scale(tab,from_=0,to=255,orient='horizontal',variable=variable,
                     bg=PANEL,fg=TEXT,troughcolor=FIELD,highlightthickness=0).pack(fill='x',padx=9)
        menu.bind('<<ComboboxSelected>>',self._material_preset_selected)
        self._button(tab,'Aplicar na região',self._apply_material,highlight=True).pack(fill='x',padx=10)
        self._button(tab,'Limpar seleção',self._clear_region).pack(fill='x',padx=10,pady=(8,0))
        self._label(tab,'PASSOS',bold=True).pack(anchor='w',padx=12,pady=(20,5))
        self._label(tab,'1. Na aba Pintar escolha “Selecionar região”. '
                    '2. Clique em uma área do 3D ou da textura. '
                    '3. Volte aqui e aplique um material.',
                    color=MUTED,wraplength=206).pack(anchor='w',padx=12)
        availability=('MAES detectada' if self.session.maes_image is not None
                      else 'MAES ausente: converta o modelo primeiro')
        self._label(tab,availability,color=GREEN if self.session.maes_image is not None
                    else MUTED,wraplength=206).pack(anchor='w',padx=12,pady=(16,0))
        self._label(tab,'A prévia GPU simula o material. Confira o resultado '
                    'no TaleSpire após exportar.',color=MUTED,
                    wraplength=206,size=9).pack(anchor='w',padx=12,pady=(14,0))

    def _material_preset_selected(self,_event=None):
        for variable,value in zip(self._material_channels,PRESETS[self.material_name.get()]):
            variable.set(value)

    def _apply_material(self):
        try:
            self.session.apply_material_values(tuple(int(v.get()) for v in self._material_channels))
            self.viewer.set_materials(self.session.maes_image)
            self.status.set('Material '+self.material_name.get()+
                ' aplicado à região. Salve e reexporte para conferir no TaleSpire.')
        except (OSError,ValueError) as exc:
            messagebox.showwarning('Material',str(exc),parent=self)

    def _clear_region(self):
        self.session.clear_region()
        self._request_refresh()
        self._schedule_preview()
        self.status.set('Seleção de região removida.')

    def _pick_region(self,point):
        active=self.session.select_region(*point,self.tolerance.get())
        self.status.set('Região conectada selecionada para pintura e materiais.'
                        if active else 'Nenhuma região selecionada.')
        self._request_refresh()
        self._schedule_preview()

    def _pick_surface_region(self,hit):
        if self.region_mode.get()=='Cor similar':
            self._pick_region(hit.pixel(*self.session.image.size))
            return
        if self._regions is None or self._region_mesh is not self.viewer._mesh:
            self._regions=MeshRegions(self.viewer._mesh)
            self._region_mesh=self.viewer._mesh
        faces=self._regions.region(hit.triangle,self.region_angle.get())
        self.session.selection=self._regions.mask(faces,self.session.image.size)
        self.status.set(f'Região geométrica: {len(faces)} faces. Ajuste o ângulo em Opções.')
        self._request_refresh()
        self._schedule_preview()

    def _set_color(self,value):
        self.color.set(value)
        self.status.set('Cor selecionada: '+value)

    def _choose_color(self):
        chosen=colorchooser.askcolor(color=self.color.get(),parent=self)
        if chosen and chosen[1]:
            self._set_color(chosen[1])

    def _load_custom_stamp(self):
        filename=filedialog.askopenfilename(parent=self,
                    title='Escolha um carimbo PNG com transparência',
                    filetypes=[('Imagem PNG','*.png')])
        if not filename:
            return
        try:
            if Path(filename).stat().st_size > 8_000_000:
                raise ValueError('O carimbo PNG deve ter no máximo 8 MB.')
            with Image.open(filename) as im:
                if im.width*im.height>1024*1024:
                    raise ValueError('O carimbo deve ter até 1 milhão de pixels.')
                self.stamp_image=im.convert('RGBA')
            self.stamp_name.set('PNG personalizado')
            self.mode.set('carimbo')
            self.status.set('PNG personalizado pronto. Clique no modelo para carimbar.')
        except (OSError,ValueError) as error:
            messagebox.showerror('Carimbo inválido',str(error),parent=self)

    def _stamp_at(self,point):
        shape=self.stamp_name.get()
        use_custom=(shape=='PNG personalizado')
        if use_custom and self.stamp_image is None:
            self.status.set('Carregue um PNG antes de usar o carimbo personalizado.')
            return False
        self.session.stamp(*point,self.color.get(),
                           diameter=max(4,self.size.get()*2),
                           opacity=self.opacity.get()/100,
                           shape=shape,custom=self.stamp_image if use_custom else None)
        return True

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
        elif mode=='carimbo':
            if not self._stamp_at(p):
                return
        else:
            self.session.stroke(p,p,self.color.get(),self.size.get(),
                                self.opacity.get()/100,erase=(mode=='borracha'),
                                hardness=self.hardness.get()/100)
        self._last=p if mode in ('pincel','borracha') else None
        self._request_refresh()
        self._schedule_preview()

    def _mouse_drag(self,event):
        point=self._coords(event)
        if point is None or self._last is None: return
        self.session.stroke(self._last,point,self.color.get(),self.size.get(),
                            self.opacity.get()/100,erase=self.mode.get()=='borracha',
                            hardness=self.hardness.get()/100)
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
        self._current_hit=hit
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
            try:
                self._pick_surface_region(self._current_hit)
            except ValueError as exc:
                self.status.set(str(exc))
            return
        self.session.checkpoint()
        screen=(event.x,event.y)
        try:
            if mode=='balde':
                if self.region_mode.get()=='Geometria' and self.session.selection is None:
                    self._pick_surface_region(self._current_hit)
                self.session.bucket(*point,self.color.get(),self.tolerance.get())
            elif mode=='carimbo':
                custom=self.stamp_name.get()=='PNG personalizado'
                if custom and self.stamp_image is None:
                    self.status.set('Carregue um PNG na aba Opções antes de carimbar.')
                    return
                stencil=stamp_mask(128,self.stamp_name.get(),self.stamp_image if custom else None)
                self._paint_surface(screen,screen,stencil=stencil)
            else:
                self._paint_surface(screen,screen,erase=(mode=='borracha'))
                self._last_3d=screen
        except ValueError as exc:
            self.status.set(str(exc))
            return
        self._request_refresh()
        self._schedule_preview()

    def _paint_surface(self,start,end,erase=False,stencil=None):
        picker=self._picker_for_camera()
        if picker is None:
            return
        distance=math.hypot(end[0]-start[0],end[1]-start[1])
        segments=max(1,math.ceil(distance/150))
        patches=[]
        for i in range(segments):
            a=tuple(start[j]+(end[j]-start[j])*i/segments for j in (0,1))
            b=tuple(start[j]+(end[j]-start[j])*(i+1)/segments for j in (0,1))
            patches.extend(surface_masks(picker,a,b,self.session.image.size,
                diameter=max(4,self.size.get()*2) if stencil is not None else self.size.get(),
                hardness=self.hardness.get()/100,
                paint_through=self.paint_through.get(),stencil=stencil))
        self.session.apply_surface_masks(patches,self.color.get(),self.opacity.get()/100,erase)

    def _paint3d_drag(self,event):
        if not self.paint3d_enabled.get():
            self.viewer._drag(event)
            return
        if self.mode.get() not in ('pincel','borracha') or self._last_3d is None:
            return
        screen=(event.x,event.y)
        try:
            self._paint_surface(self._last_3d,screen,erase=self.mode.get()=='borracha')
            self._last_3d=screen
        except ValueError as exc:
            self.status.set(str(exc))
            self._last_3d=None
            return
        self._request_refresh()
        self._schedule_preview()

    def _paint3d_end(self,_event):
        self._last_3d=None
        self.viewer.last_mouse=None
        self._schedule_preview()

    def _schedule_preview(self):
        if self._preview_job is None:
            self._preview_job=self.after(90,self._refresh_live_preview)

    def _refresh_live_preview(self):
        self._preview_job=None
        if not self.winfo_exists() or self.viewer._mesh is None:
            return
        image=self.session.image.convert('RGB')
        image.thumbnail((1024,1024),Image.Resampling.BILINEAR)
        if self.session.selection is not None:
            selection=self.session.selection.resize(image.size,Image.Resampling.NEAREST)
            tint=Image.blend(image,Image.new('RGB',image.size,'#81CFFC'),.22)
            image=Image.composite(tint,image,selection)
        self.viewer._albedo=np.asarray(image,dtype=np.uint8).copy()
        # The MAES map changes only when a material preset is applied,
        # not on every albedo brush stroke. Avoid repeated 1024px copies.
        self.viewer.render()

    def _undo(self):
        if self.session.undo():
            self._update_layers()
            self._request_refresh()
            self._schedule_preview()
            self.viewer.set_materials(self.session.maes_image)

    def _redo(self):
        if self.session.redo():
            self._update_layers()
            self._request_refresh()
            self._schedule_preview()
            self.viewer.set_materials(self.session.maes_image)

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
    """Open as a complete studio window; embedded mode uses PaintingStudio directly."""
    window=tk.Toplevel(parent)
    window.title(f'Astronyx • Painting Studio V{APP_VERSION}')
    window.configure(bg=BG)
    window.geometry('1440x880')
    window.minsize(1100,690)
    try:
        if window.tk.call('tk','windowingsystem') == 'win32':
            window.state('zoomed')
    except tk.TclError:
        pass
    panel=PaintingStudio(window,project,on_apply=on_apply,on_exit=window.destroy)
    panel.pack(fill='both',expand=True)
    return window
