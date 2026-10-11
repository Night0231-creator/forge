"""Independent Astronyx surface painting workbench with Albedo/MAES layers.

Screen-projected surface brushes share the texture editor's layer/history model.
GPU PBR preview is optional; CPU fallback shows Albedo.
"""
from __future__ import annotations

import math
import tkinter as tk
from pathlib import Path
from tkinter import colorchooser, filedialog, messagebox, ttk
from PIL import Image, ImageColor, ImageDraw, ImageTk
import numpy as np

from ui.paint3d_picker import ProjectedUVPicker
from ui.surface_paint import surface_masks
from core.brushes import stamp_mask
from core.mesh_regions import MeshRegions
from core.version import APP_VERSION

from core.paint_studio import find_albedo
from core.layered_materials import LayeredPaintSession, PRESETS, apply_materials_to_export
from core.footprint_calibrator import find_project_obj
from ui.texture_viewer import TexturedObjViewer

from ui.paint_widgets import (BG, PANEL, FIELD, TEXT, MUTED, ACCENT,
                              BORDER, COLOURS, ToolButton, slider)

PURPLE = ACCENT
GREEN = '#79BF9C'


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

    def destroy(self):
        """Cancel pending renders when a project closes or switches."""
        for name in ('_refresh_id', '_preview_job'):
            job = getattr(self, name, None)
            if job is not None:
                try:
                    self.after_cancel(job)
                except tk.TclError:
                    pass
                setattr(self, name, None)
        if hasattr(self,'_mode_trace'):
            self.mode.trace_remove('write',self._mode_trace)
        super().destroy()

    @staticmethod
    def _label(parent, text, color=TEXT, size=10, bold=False, **kw):
        return tk.Label(parent,text=text,bg=parent.cget('bg'),fg=color,
                        font=('Segoe UI',size,'bold' if bold else 'normal'),**kw)

    @staticmethod
    def _button(parent, title, command, highlight=False):
        return tk.Button(parent,text=title,command=command,
                         bg=PURPLE if highlight else FIELD,fg='white',
                         activebackground='#258AD8',activeforeground='white',
                         relief='flat',padx=10,pady=5,cursor='hand2',bd=0,highlightthickness=0,
                         font=('Segoe UI',9))

    def _make_ui(self):
        """Compact paint dock and a large, uninterrupted miniature viewport."""
        sty=ttk.Style(self)
        sty.configure('PaintStudio.TNotebook',background=PANEL,borderwidth=0,
                      bordercolor=BORDER,lightcolor=PANEL,darkcolor=PANEL)
        sty.configure('PaintStudio.TNotebook.Tab',background=PANEL,foreground=MUTED,
                      font=('Segoe UI',9),padding=(10,7),bordercolor=BORDER,
                      lightcolor=PANEL,darkcolor=PANEL,focuscolor=FIELD)
        sty.configure('PaintStudio.Vertical.TScrollbar',background=FIELD,
                      troughcolor=PANEL,bordercolor=PANEL,lightcolor=PANEL,
                      darkcolor=PANEL,arrowcolor=MUTED,arrowsize=10)
        sty.map('PaintStudio.Vertical.TScrollbar',background=[('active',BORDER)])
        sty.map('PaintStudio.TNotebook.Tab',
                background=[('selected',FIELD)],foreground=[('selected',TEXT)])
        sty.configure('PaintStudio.TCombobox',fieldbackground=FIELD,background=FIELD,
                      foreground=TEXT,arrowcolor=MUTED,bordercolor=BORDER,
                      lightcolor=FIELD,darkcolor=FIELD,
                      padding=4,font=('Segoe UI',9))
        sty.map('PaintStudio.TCombobox',fieldbackground=[('readonly',FIELD)],
                foreground=[('readonly',TEXT)])

        header=tk.Frame(self,bg=PANEL,height=39)
        header.pack(fill='x')
        header.pack_propagate(False)
        if self.on_exit is not None:
            self._button(header,'‹ Projetos',self.on_exit).pack(side='left',padx=(10,8),pady=6)
        self._label(header,self.project.name.replace('_',' '),size=10,bold=True).pack(
            side='left',padx=10)
        self._button(header,'Exportar texturas',self._apply,highlight=True).pack(
            side='right',padx=(5,10),pady=6)
        self._button(header,'Salvar',self._save).pack(side='right',padx=5,pady=6)

        footer=tk.Frame(self,bg=BG,height=29)
        footer.pack(side='bottom',fill='x')
        footer.pack_propagate(False)
        self._label(footer,'',color=MUTED,textvariable=self.status,size=9,anchor='w').pack(
            side='left',fill='x',expand=True,padx=12)
        body=tk.Frame(self,bg=BG)
        body.pack(fill='both',expand=True,padx=10,pady=(10,0))
        body.grid_rowconfigure(0,weight=1)
        body.grid_columnconfigure(0,minsize=306,weight=0)
        body.grid_columnconfigure(1,weight=1,minsize=360)
        body.grid_columnconfigure(2,minsize=0,weight=0)

        self.tools_dock=tk.Frame(body,bg=PANEL,width=306,
                                 highlightbackground=BORDER,highlightthickness=1)
        self.tools_dock.grid(row=0,column=0,sticky='ns',padx=(0,10))
        self.tools_dock.grid_propagate(False)
        self._label(self.tools_dock,'Ferramentas de pintura',size=10,bold=True).pack(
            anchor='w',padx=12,pady=(12,8))
        modes=tk.Frame(self.tools_dock,bg=BG,highlightbackground=BORDER,
                        highlightthickness=1)
        modes.pack(fill='x',padx=10,pady=(0,5))
        self.tool_buttons={}
        for title,key in (('Preenchimento','balde'),('Pincel','pincel'),
                          ('Carimbo','carimbo'),('Selecionar região','regiao'),
                          ('Conta-gotas','conta-gotas'),('Borracha','borracha')):
            button=ToolButton(modes,key,title,lambda k=key:self.mode.set(k))
            button.pack(side='left',expand=True,fill='x',padx=1,pady=2)
            self.tool_buttons[key]=button
            button.bind('<Enter>',lambda _e,t=title:self.tool_caption.set(t),add='+')
            button.bind('<Leave>',lambda _e:self.tool_caption.set(self.tool_buttons[self.mode.get()].title),add='+')
        self.tool_caption=tk.StringVar(value='Pincel')
        self._label(self.tools_dock,'',textvariable=self.tool_caption,size=9,
                    color=MUTED).pack(anchor='w',padx=12,pady=(0,6))
        tabs=ttk.Notebook(self.tools_dock,style='PaintStudio.TNotebook')
        tabs.pack(fill='both',expand=True,padx=5,pady=(0,5))
        self._tool_scroll_pages=[]
        paint=self._tool_tab(tabs,'Pintar')
        materials=self._tool_tab(tabs,'Material')
        layers=self._tool_tab(tabs,'Camadas')
        scene=self._tool_tab(tabs,'Exibir')
        self._paint_tab=paint
        self._build_palette(paint)
        settings=tk.Frame(paint,bg=PANEL)
        settings.pack(fill='x',padx=11,pady=(8,3))
        slider(settings,'Tamanho',self.size,minimum=1)
        slider(settings,'Opacidade',self.opacity,minimum=10)
        slider(settings,'Dureza',self.hardness)
        self._build_surface_options(paint)
        self._build_layers_tab(layers)
        self._build_materials_tab(materials)

        viewport=tk.Frame(body,bg=BG)
        viewport.grid(row=0,column=1,sticky='nsew')
        camera=tk.Frame(viewport,bg=BG,height=29)
        camera.pack(fill='x')
        self._label(camera,'PINTURA 3D',color=MUTED,size=8,bold=True).pack(side='left',padx=8)
        for title,view in (('Frente','frente'),('Lado','lado'),('Topo','topo')):
            self._button(camera,title,lambda v=view:self.viewer.set_camera(v)).pack(
                side='right',padx=2,pady=2)
        self._button(camera,'Enquadrar',self._frame_model).pack(side='right',padx=2,pady=2)
        self.viewer=TexturedObjViewer(viewport,width=740,height=620)
        self.viewer.compare_reference=False
        self.viewer.pack(fill='both',expand=True)
        self._pbr_on=tk.BooleanVar(value=True)
        self._light_level=tk.IntVar(value=100)
        self._emission_level=tk.IntVar(value=100)
        self._ambient_level=tk.IntVar(value=100)
        self._environment=tk.StringVar(value='Estúdio')
        self.show_uv_editor=tk.BooleanVar(value=False)
        self._build_scene_tab(scene)
        try:
            self.viewer.open(find_project_obj(self.project))
            self._frame_model()
        except (OSError,ValueError) as exc:
            self.status.set(str(exc))
        if self.session.maes_image is not None:
            self.viewer.set_materials(self.session.maes_image)
        self.viewer.bind('<ButtonPress-1>',self._paint3d_start)
        self.viewer.bind('<B1-Motion>',self._paint3d_drag)
        self.viewer.bind('<ButtonRelease-1>',self._paint3d_end)
        self.viewer.bind('<ButtonPress-3>',self.viewer._start_drag)
        self.viewer.bind('<B3-Motion>',self.viewer._drag)
        self.viewer.bind('<ButtonRelease-3>',
                         lambda _e:setattr(self.viewer,'last_mouse',None))
        self.viewer.bind('<ButtonPress-2>',self.viewer._start_drag)
        self.viewer.bind('<B2-Motion>',self.viewer._pan)
        self.viewer.bind('<ButtonRelease-2>',
                         lambda _e:setattr(self.viewer,'last_mouse',None))
        bottom=tk.Frame(viewport,bg=BG,height=25)
        bottom.pack(fill='x')
        self._label(bottom,'Esquerdo: pintar   ·   Direito: girar   ·   Meio: mover   ·   Roda: zoom',
                    color=MUTED,size=8).pack(side='left',padx=8,pady=4)
        actions=tk.Frame(bottom,bg=BG)
        actions.pack(side='right')
        self._button(actions,'↶',self._undo).pack(side='left',padx=2)
        self._button(actions,'↷',self._redo).pack(side='left',padx=2)

        self.uv_panel=tk.Frame(body,bg=PANEL,width=280,
                               highlightbackground=BORDER,highlightthickness=1)
        self.uv_panel.grid(row=0,column=2,sticky='nsew',padx=(10,0))
        self.uv_panel.grid_propagate(False)
        self._label(self.uv_panel,'Mapa UV · cor',bold=True,size=10).pack(
            anchor='w',padx=12,pady=(12,8))
        self.canvas=tk.Canvas(self.uv_panel,width=262,height=400,bg=BG,
                              highlightthickness=0)
        self.canvas.pack(fill='both',expand=True,padx=8,pady=(0,8))
        self.canvas.bind('<ButtonPress-1>',self._mouse_down)
        self.canvas.bind('<B1-Motion>',self._mouse_drag)
        self.canvas.bind('<ButtonRelease-1>',lambda _e:setattr(self,'_last',None))
        self.canvas.bind('<Configure>',lambda _e:self._request_refresh())
        tk.Checkbutton(self.uv_panel,text='Mostrar bordas UV',variable=self.show_uv,
                       command=self._request_refresh,bg=PANEL,fg=TEXT,
                       selectcolor=FIELD,activebackground=PANEL,highlightthickness=0,bd=0,
                       activeforeground=TEXT).pack(anchor='w',padx=10,pady=(0,10))
        self.uv_panel.grid_remove()
        self._mode_trace=self.mode.trace_add('write',self._update_tool_buttons)
        self._update_tool_buttons()
        for content,canvas in self._tool_scroll_pages:
            self._route_tool_wheel(content,canvas)

    def _frame_model(self):
        self.viewer.reset()

    def _update_tool_buttons(self,*_args):
        current=self.mode.get()
        for key,button in self.tool_buttons.items():
            button.set_selected(current==key)
        self.tool_caption.set(self.tool_buttons[current].title)
        for frame,modes in ((self._region_options,('regiao','balde')),
                            (self._stamp_options,('carimbo',))):
            if current in modes:
                frame.pack(fill='x',padx=11,pady=(6,3))
            else:
                frame.pack_forget()

    def _build_palette(self,tab):
        self.palette_query=tk.StringVar(value='')
        self.palette_category='Cores'
        search=tk.Entry(tab,textvariable=self.palette_query,bg=FIELD,fg=TEXT,
                         insertbackground=TEXT,relief='flat',highlightthickness=1,
                         highlightbackground=BORDER,highlightcolor=ACCENT,font=('Segoe UI',9))
        search.pack(fill='x',padx=11,pady=(12,5),ipady=5)
        search.bind('<KeyRelease>',lambda _e:self._refresh_palette())
        self._label(tab,'Buscar cor pelo nome',color=MUTED,size=8).pack(anchor='w',padx=11)
        categories=tk.Frame(tab,bg=PANEL)
        categories.pack(fill='x',padx=10,pady=(7,6))
        self.category_buttons={}
        for name in ('Todas','Cores','Metais','Natural'):
            button=tk.Button(categories,text=name,bg=FIELD,fg=MUTED,bd=0,highlightthickness=0,
                             activebackground=ACCENT,activeforeground='white',
                             font=('Segoe UI',8),padx=7,pady=3,cursor='hand2',
                             command=lambda n=name:self._set_palette_category(n))
            button.pack(side='left',padx=1)
            self.category_buttons[name]=button
        self.palette_grid=tk.Frame(tab,bg=BG,highlightbackground=BORDER,highlightthickness=1)
        self.palette_grid.pack(fill='x',padx=10,pady=(0,8))
        for column in range(3): self.palette_grid.grid_columnconfigure(column,weight=1,uniform='colour')
        self._refresh_palette()
        chosen=tk.Frame(tab,bg=PANEL)
        chosen.pack(fill='x',padx=11,pady=3)
        self.colour_chip=tk.Button(chosen,bg=self.color.get(),width=2,relief='flat',
                                   bd=0,highlightthickness=0,command=self._choose_color,cursor='hand2')
        self.colour_chip.pack(side='left',padx=(0,8))
        self._label(chosen,'Cor',color=MUTED,size=9).pack(side='left')
        self.colour_text=tk.StringVar(value=self.color.get())
        field=tk.Entry(chosen,textvariable=self.colour_text,bg=FIELD,fg=TEXT,
                        insertbackground=TEXT,relief='flat',width=10,highlightthickness=1,highlightbackground=BORDER,
                        highlightcolor=ACCENT,font=('Consolas',9))
        field.pack(side='right',ipady=3)
        field.bind('<Return>',lambda _e:self._commit_colour())
        self._button(chosen,'Escolher...',self._choose_color).pack(side='right',padx=5)

    def _set_palette_category(self,name):
        self.palette_category=name
        self._refresh_palette()

    def _refresh_palette(self):
        import unicodedata
        def plain(value):
            return ''.join(c for c in unicodedata.normalize('NFD',value.casefold())
                           if not unicodedata.combining(c))
        query=plain(self.palette_query.get().strip())
        for child in self.palette_grid.winfo_children(): child.destroy()
        choices=[item for item in COLOURS if (self.palette_category=='Todas' or
                 item[2]==self.palette_category) and query in plain(item[0])]
        for i,(name,colour,_category) in enumerate(choices):
            tile=tk.Frame(self.palette_grid,bg=FIELD,cursor='hand2')
            tile.grid(row=i//3,column=i%3,sticky='ew',padx=2,pady=2)
            chip=tk.Canvas(tile,width=12,height=13,bg=FIELD,highlightthickness=0)
            chip.pack(side='left',padx=(4,3),pady=4)
            chip.create_rectangle(0,0,12,13,fill=colour,outline=colour)
            label=self._label(tile,name.replace(' claro',' cl.'),size=8,anchor='w')
            label.pack(side='left',padx=(0,3))
            for widget in (tile,chip,label):
                widget.bind('<Button-1>',lambda _e,c=colour:self._set_color(c))
        if not choices:
            self._label(self.palette_grid,'Nenhuma cor encontrada',color=MUTED,size=9).grid(
                row=0,column=0,columnspan=3,padx=8,pady=14)
        self._route_tool_wheel(self.palette_grid,self._tool_scroll_pages[0][1])
        for name,button in self.category_buttons.items():
            button.configure(bg=ACCENT if name==self.palette_category else FIELD,
                             fg=TEXT if name==self.palette_category else MUTED)

    def _commit_colour(self):
        try:
            rgb=ImageColor.getrgb(self.colour_text.get().strip())
            self._set_color('#%02X%02X%02X'%rgb[:3])
        except ValueError:
            self.colour_text.set(self.color.get())
            self.status.set('Digite uma cor como #366AC5 ou use Escolher.')

    def _build_scene_tab(self,tab):
        self._label(tab,'Iluminação',bold=True,size=10).pack(anchor='w',padx=12,pady=(12,8))
        from ui.gpu_pbr_renderer import ENV_PRESETS
        ttk.Combobox(tab,textvariable=self._environment,values=list(ENV_PRESETS),
                     state='readonly',style='PaintStudio.TCombobox').pack(fill='x',padx=11,pady=5)
        settings=tk.Frame(tab,bg=PANEL)
        settings.pack(fill='x',padx=11,pady=5)
        for title,variable,maximum in (('Luz',self._light_level,300),
                                     ('Ambiente',self._ambient_level,200),
                                     ('Emissão',self._emission_level,300)):
            slider(settings,title,variable,maximum,command=lambda _v:self._apply_lighting())
        self._environment.trace_add('write',lambda *_:self._apply_lighting())
        for text,variable,command in (('Usar prévia GPU',self._pbr_on,self._apply_lighting),
                                     ('Mostrar mapa UV',self.show_uv_editor,self._toggle_uv_panel),
                                     ('Pintar diretamente no 3D',self.paint3d_enabled,None)):
            tk.Checkbutton(tab,text=text,variable=variable,command=command,bg=PANEL,
                           fg=TEXT,selectcolor=FIELD,activebackground=PANEL,
                           activeforeground=TEXT).pack(anchor='w',padx=9,pady=5)
        self._label(tab,'A luz muda apenas a visualização. Suas cores e a textura '
                    'exportada são preservadas.',color=MUTED,wraplength=260,size=9).pack(
            anchor='w',padx=12,pady=12)

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
        self._label(tab,'Camadas de pintura',bold=True,size=10).pack(anchor='w',padx=12,pady=(14,5))
        self.layer_list=tk.Listbox(tab,height=8,bg=FIELD,fg=TEXT,
                                   font=('Segoe UI',9),highlightthickness=0,bd=0,
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
                       selectcolor=FIELD,activebackground=PANEL,highlightthickness=0,bd=0,
                       activeforeground=TEXT).pack(anchor='w',padx=12,pady=(12,5))
        self.layer_opacity=tk.IntVar(value=100)
        settings=tk.Frame(tab,bg=PANEL)
        settings.pack(fill='x',padx=11)
        opacity=slider(settings,'Opacidade',self.layer_opacity)
        opacity.bind('<ButtonRelease-1>',self._layer_opacity_change)
        opacity.bind('<KeyRelease-Left>',self._layer_opacity_change)
        opacity.bind('<KeyRelease-Right>',self._layer_opacity_change)
        self._label(tab,'As camadas são salvas como PNGs separados. '
                    'Mudar visibilidade não modifica o modelo original.',
                    color=MUTED,wraplength=260).pack(anchor='w',padx=12,pady=13)
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
        scroll=ttk.Scrollbar(page,orient='vertical',style='PaintStudio.Vertical.TScrollbar')
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
        self._tool_scroll_pages.append((content,canvas))
        return content

    def _route_tool_wheel(self,parent,canvas):
        def wheel(event):
            delta=-1 if getattr(event,'num',0)==4 else 1 if getattr(event,'num',0)==5 else -int(event.delta/120)
            canvas.yview_scroll(delta,'units')
            return 'break'
        for child in parent.winfo_children():
            child.bind('<MouseWheel>',wheel)
            child.bind('<Button-4>',wheel)
            child.bind('<Button-5>',wheel)
            self._route_tool_wheel(child,canvas)

    def _build_surface_options(self,tab):
        tk.Checkbutton(tab,text='Pintar através do modelo',variable=self.paint_through,
                       bg=PANEL,fg=TEXT,selectcolor=FIELD,activebackground=PANEL,highlightthickness=0,bd=0,
                       activeforeground=TEXT).pack(anchor='w',padx=8,pady=(8,3))
        self._region_options=tk.Frame(tab,bg=PANEL)
        self._label(self._region_options,'Seleção da região',color=MUTED,size=9).pack(anchor='w')
        ttk.Combobox(self._region_options,values=('Geometria','Cor similar'),
                     textvariable=self.region_mode,state='readonly',
                     style='PaintStudio.TCombobox').pack(fill='x',pady=6)
        slider(self._region_options,'Ângulo',self.region_angle,maximum=180)
        slider(self._region_options,'Similaridade',self.tolerance,maximum=50)
        self._button(self._region_options,'Limpar seleção',self._clear_region).pack(fill='x',pady=6)
        self._stamp_options=tk.Frame(tab,bg=PANEL)
        self._label(self._stamp_options,'Carimbo',color=MUTED,size=9).pack(anchor='w')
        ttk.Combobox(self._stamp_options,values=('Estrela','Selo','Runa','PNG personalizado'),
                     textvariable=self.stamp_name,state='readonly',
                     style='PaintStudio.TCombobox').pack(fill='x',pady=6)
        self._button(self._stamp_options,'Carregar PNG…',self._load_custom_stamp).pack(fill='x')

    def _build_materials_tab(self,tab):
        self._label(tab,'Material da região',bold=True,size=10).pack(anchor='w',padx=12,pady=(12,8))
        self.material_name=tk.StringVar(value=list(PRESETS)[0])
        menu=ttk.Combobox(tab,values=list(PRESETS),textvariable=self.material_name,
                          state='readonly',style='PaintStudio.TCombobox')
        menu.pack(fill='x',padx=11,pady=(3,8))
        self._material_channels=[tk.IntVar(value=value) for value in PRESETS[self.material_name.get()]]
        settings=tk.Frame(tab,bg=PANEL)
        settings.pack(fill='x',padx=11,pady=8)
        for title,variable in zip(('Metal','Oclusão','Emissão','Suavidade'),self._material_channels):
            slider(settings,title,variable,maximum=255,percent=True)
        menu.bind('<<ComboboxSelected>>',self._material_preset_selected)
        self._label(tab,'Selecione uma região no modelo e aplique o material.',
                    color=MUTED,wraplength=260,size=9).pack(anchor='w',padx=12,pady=10)
        self._button(tab,'Aplicar na região',self._apply_material,highlight=True).pack(fill='x',padx=11,pady=4)
        self._button(tab,'Limpar seleção',self._clear_region).pack(fill='x',padx=11,pady=4)
        availability=('Textura de material pronta' if self.session.maes_image is not None
                      else 'Converta o modelo para preparar os materiais')
        self._label(tab,availability,color=GREEN if self.session.maes_image is not None
                    else MUTED,wraplength=260,size=9).pack(anchor='w',padx=12,pady=(14,5))

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
        self.status.set(f'Região geométrica: {len(faces)} faces. Ajuste o ângulo na aba Pintar.')
        self._request_refresh()
        self._schedule_preview()

    def _set_color(self,value):
        self.color.set(value)
        if hasattr(self,'colour_chip'):
            self.colour_chip.configure(bg=value)
            self.colour_text.set(value.upper())
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
        self.canvas.create_rectangle(x0,y0,x0+width,y0+height,outline=ACCENT)

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
                    self.status.set('Carregue um PNG na aba Pintar antes de carimbar.')
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
