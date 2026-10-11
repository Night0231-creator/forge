"""Astronyx unified Mini Forge workbench.

This is the default screen of the Windows EXE. It reuses the existing
conversion pipeline, library, TaleSpire installer and V2.4 paint engine
without requiring users to navigate between separate painting windows.
"""
from __future__ import annotations

from pathlib import Path
import tkinter as tk
from tkinter import messagebox

from core.footprint_calibrator import find_project_obj
from core.paint_studio import find_albedo
from ui.painting_studio import PaintingStudio
from ui.texture_viewer import TexturedObjViewer

BG='#0C101B'
SURFACE='#191E2E'
SIDEBAR='#141A29'
RAISED='#252C40'
FG='#F0F0FF'
MUTED='#A4ACC5'
PURPLE='#9068F5'
LILAC='#C3ABFF'
GREEN='#69D8B3'
BORDER='#333B56'


class UnifiedStudio(tk.Frame):
    def __init__(self,parent,app):
        super().__init__(parent,bg=BG)
        self.app=app
        self.projects=[]
        self.current=None
        self.workspace_editor=None
        self.project_view=None
        self.preview=None
        self._make_shell()
        self._show_welcome()

    def _text(self,parent,value,*,size=10,bold=False,color=FG,**kw):
        return tk.Label(parent,text=value,bg=parent.cget('bg'),fg=color,
                        font=('Segoe UI',size,'bold' if bold else 'normal'),**kw)

    def _button(self,parent,text,command,*,accent=False):
        return tk.Button(parent,text=text,command=command,bg=PURPLE if accent else RAISED,
                         fg='#FFFFFF',relief='flat',activeforeground='white',
                         activebackground='#684DD0',highlightthickness=0,
                         cursor='hand2',padx=14,pady=10,font=('Segoe UI',10,'bold'))

    def _make_shell(self):
        header=tk.Frame(self,bg=SURFACE,height=76)
        header.pack(fill='x',padx=11,pady=(9,8))
        header.pack_propagate(False)
        title=tk.Frame(header,bg=SURFACE)
        title.pack(side='left',fill='both',expand=True,padx=17,pady=10)
        self._text(title,'PAINTING WORKSPACE',size=15,bold=True,color=LILAC).pack(anchor='w')
        self._text(title,'Importe, pinte e prepare miniaturas para o TaleSpire em um só lugar.',
                   size=9,color=MUTED).pack(anchor='w',pady=(3,0))
        self._button(header,'+ Novo modelo Meshy',self._create_new,accent=True).pack(
            side='right',padx=(7,14),pady=15)
        self._button(header,'↻ Atualizar',self._refresh_external).pack(
            side='right',padx=(0,6),pady=15)

        self.workarea=tk.Frame(self,bg=BG)
        self.workarea.pack(fill='both',expand=True,padx=11,pady=(0,9))
        self.home=tk.Frame(self.workarea,bg=BG)
        self.home.pack(fill='both',expand=True)
        self.editor_frame=tk.Frame(self.workarea,bg=BG)

    def _create_new(self):
        self.app._navigate('quick','tab_dashboard')

    def _refresh_external(self):
        self.app.refresh_library()

    def _show_welcome(self):
        for child in self.home.winfo_children():
            child.destroy()
        empty=tk.Frame(self.home,bg=SURFACE,highlightbackground=BORDER,highlightthickness=1)
        empty.pack(fill='both',expand=True)
        card=tk.Frame(empty,bg=SURFACE)
        card.place(relx=.5,rely=.44,anchor='center')
        self._text(card,'◈',size=42,color=PURPLE,bold=True).pack()
        self._text(card,'Sua bancada de miniaturas',size=24,bold=True).pack(pady=(4,10))
        self._text(card,'Comece com um GLB/ZIP do Meshy ou abra um projeto convertido.\n'
                   'A pintura 3D ficará integrada a esta tela.',
                   color=MUTED,size=11,justify='center').pack(pady=(0,18))
        self._button(card,'+ Importar modelo Meshy',self._create_new,accent=True).pack(pady=4)

    def _valid_project(self,entry):
        if entry is None or entry.obj is None:
            return False
        try:
            return find_albedo(entry.folder).is_file() and find_project_obj(entry.folder).is_file()
        except (OSError,ValueError):
            return False

    def refresh(self,entries,preferred=None):
        # Never destroy an editor with unsaved paint in progress.
        self.projects=[item for item in entries if self._valid_project(item)]
        if self.workspace_editor is not None:
            return
        selected=next((item for item in self.projects
                       if self.current is not None and item.folder==self.current.folder),None)
        if selected is None and preferred:
            selected=next((item for item in self.projects if item.folder==Path(preferred)),None)
        if selected is None:
            selected=self.projects[0] if self.projects else None
        if selected is None:
            self.current=None
            self._show_welcome()
            return
        self._build_home()
        self._select_project(selected)

    def _build_home(self):
        for widget in self.home.winfo_children():
            widget.destroy()
        layout=tk.Frame(self.home,bg=BG)
        layout.pack(fill='both',expand=True)
        layout.grid_columnconfigure(0,weight=0,minsize=220)
        layout.grid_columnconfigure(1,weight=1,minsize=400)
        layout.grid_columnconfigure(2,weight=0,minsize=238)
        layout.grid_rowconfigure(0,weight=1)

        left=tk.Frame(layout,bg=SIDEBAR,width=221,highlightbackground=BORDER,
                      highlightthickness=1)
        left.grid(row=0,column=0,sticky='ns',padx=(0,8))
        left.grid_propagate(False)
        self._text(left,'MINHA BIBLIOTECA',size=9,bold=True,color=LILAC).pack(
            anchor='w',padx=13,pady=(19,6))
        self._text(left,'Selecione uma miniatura',size=9,color=MUTED).pack(
            anchor='w',padx=13,pady=(0,9))
        self.project_list=tk.Listbox(left,bg=RAISED,fg=FG,
                                     selectbackground='#654DB3',
                                     selectforeground='white',relief='flat',
                                     highlightthickness=0,
                                     activestyle='none',font=('Segoe UI',10),
                                     exportselection=False)
        self.project_list.pack(fill='both',expand=True,padx=9,pady=(0,11))
        self.project_list.bind('<<ListboxSelect>>',self._list_select)
        self._button(left,'Abrir biblioteca completa',
                     lambda:self.app._navigate('library','tab_library')).pack(
                         fill='x',padx=9,pady=(0,14))
        for item in self.projects:
            self.project_list.insert(tk.END,item.name.replace('_',' ')[:28])

        center=tk.Frame(layout,bg='#12182A',highlightbackground=BORDER,
                        highlightthickness=1)
        center.grid(row=0,column=1,sticky='nsew')
        upper=tk.Frame(center,bg=SURFACE,height=47)
        upper.pack(fill='x')
        upper.pack_propagate(False)
        self.model_name=self._text(upper,'MINIATURA 3D',size=11,bold=True)
        self.model_name.pack(side='left',padx=13,pady=13)
        self._text(upper,'Prévia texturizada',color=MUTED,size=9).pack(
            side='right',padx=13)
        self.preview=TexturedObjViewer(center,width=630,height=570)
        self.preview.pack(fill='both',expand=True,padx=4,pady=4)
        bottom=tk.Frame(center,bg=SURFACE)
        bottom.pack(fill='x')
        self._text(bottom,'Mouse: girar • roda: zoom • botão direito: mover',
                   size=9,color=MUTED).pack(side='left',padx=11,pady=11)
        self._button(bottom,'Pintar →',self.open_editor,accent=True).pack(
            side='right',padx=9,pady=5)

        inspector=tk.Frame(layout,bg=SIDEBAR,width=238,highlightbackground=BORDER,
                           highlightthickness=1)
        inspector.grid(row=0,column=2,sticky='ns',padx=(8,0))
        inspector.grid_propagate(False)
        self._text(inspector,'PROJETO',size=10,bold=True,color=LILAC).pack(
            anchor='w',padx=14,pady=(20,8))
        self.active_label=self._text(inspector,'Nenhum modelo',size=12,bold=True,
                                     wraplength=208,justify='left')
        self.active_label.pack(anchor='w',padx=14,pady=(0,9))
        self.project_status=self._text(inspector,'',color=GREEN,size=9,
                                       wraplength=207,justify='left')
        self.project_status.pack(anchor='w',padx=14,pady=(0,15))
        self._text(inspector,'FLUXO RECOMENDADO',size=9,color=MUTED,bold=True).pack(
            anchor='w',padx=14,pady=(10,7))
        for value in ('01  Importar Meshy', '02  Pintar no 3D',
                      '03  Exportar .tsMod', '04  Instalar no TaleSpire'):
            self._text(inspector,value,size=10,color=FG).pack(
                anchor='w',padx=14,pady=7)
        tk.Frame(inspector,bg=BORDER,height=1).pack(fill='x',padx=12,pady=16)
        self._button(inspector,'◈ Pintar miniatura',self.open_editor,
                     accent=True).pack(fill='x',padx=11,pady=(0,8))
        self._button(inspector,'Preparar .tsMod',lambda:self.app._navigate(
            'export','tab_cmd')).pack(fill='x',padx=11,pady=(0,8))
        self._button(inspector,'Instalar no jogo',self._install_current).pack(
            fill='x',padx=11,pady=(0,8))
        self._button(inspector,'Configurações avançadas',lambda:self.app._navigate(
            'scale','tab_conv')).pack(fill='x',padx=11)

    def _list_select(self,_event):
        if not self.project_list.curselection():
            return
        index=int(self.project_list.curselection()[0])
        if 0<=index<len(self.projects):
            self._select_project(self.projects[index])

    def _select_project(self,item):
        self.current=item
        if not hasattr(self,'project_list'):
            return
        for i,candidate in enumerate(self.projects):
            if candidate.folder==item.folder:
                if self.project_list.curselection() != (i,):
                    self.project_list.selection_clear(0,tk.END)
                    self.project_list.selection_set(i)
                break
        self.model_name.configure(text=item.name.replace('_',' ')[:50])
        self.active_label.configure(text=item.name.replace('_',' ')[:32])
        self.project_status.configure(
            text='● .tsMod disponível' if item.tsmod else '○ Arquivos preparados')
        try:
            self.preview.open(find_project_obj(item.folder))
        except (OSError,ValueError) as exc:
            self.model_name.configure(text='Prévia indisponível: '+str(exc)[:70])

    def open_editor(self):
        item=self.current
        if not self._valid_project(item):
            messagebox.showinfo('Selecione um projeto',
                 'Converta um modelo Meshy antes de abrir o editor 3D.',parent=self)
            return
        self.home.pack_forget()
        self.editor_frame.pack(fill='both',expand=True)
        for widget in self.editor_frame.winfo_children():
            widget.destroy()
        try:
            editor=PaintingStudio(self.editor_frame,item.folder,
                                  on_apply=lambda:self.app.refresh_library(),
                                  on_exit=self.close_editor)
            editor.pack(fill='both',expand=True)
            self.workspace_editor=editor
        except (OSError,ValueError) as exc:
            self.editor_frame.pack_forget()
            self.home.pack(fill='both',expand=True)
            messagebox.showerror('Não foi possível abrir o editor',str(exc),parent=self)

    def close_editor(self):
        # The user must explicitly save to persist; don't silently throw away paint.
        if not messagebox.askyesno('Voltar aos projetos',
                  'Voltar à biblioteca? Alterações que não foram salvas serão perdidas.',
                  parent=self):
            return
        if self.workspace_editor is not None:
            self.workspace_editor.destroy()
            self.workspace_editor=None
        self.editor_frame.pack_forget()
        self.home.pack(fill='both',expand=True)
        self.app.refresh_library()

    def _install_current(self):
        if self.current is None or self.current.tsmod is None:
            messagebox.showinfo('Exportação necessária',
                       'Gere um arquivo .tsMod antes de instalar a miniatura.',
                       parent=self)
            return
        self.app._install_library(self.current.tsmod)
