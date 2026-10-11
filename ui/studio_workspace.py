"""Astronyx V4: one integrated painting desk rather than a preview page + pop-up.

Models are local; all conversion/export operations delegate to existing tested
Forge components. Independent layout inspired by professional painting tools.
"""
from __future__ import annotations

from pathlib import Path
import tkinter as tk
from tkinter import messagebox, ttk

from core.footprint_calibrator import find_project_obj
from core.paint_studio import find_albedo
from ui.painting_studio import PaintingStudio
from ui.theme import hover_button
from ui.palette import SUBTLE, SIDEBAR as NAV_BG, ACCENT_SOFT
from ui.studio_controls import draw_icon
from core.version import APP_VERSION

from ui.paint_widgets import BG, PANEL, FIELD, TEXT, MUTED, ACCENT, BORDER

SURFACE=PANEL
SIDEBAR=PANEL
RAISED=FIELD
FG=TEXT
PURPLE=ACCENT
GREEN='#79BF9C'


class UnifiedStudio(tk.Frame):
    """A single-window workbench with always-visible, usable paint tools."""
    def __init__(self,parent,app):
        super().__init__(parent,bg=BG)
        self.app=app
        self.projects=[]
        self.current=None
        self.workspace_editor=None
        self._select_guard=False
        self._make_shell()
        self._show_welcome()

    def _text(self,parent,value,*,size=10,bold=False,color=FG,**kw):
        return tk.Label(parent,text=value,bg=parent.cget('bg'),fg=color,
                        font=('Segoe UI',size,'bold' if bold else 'normal'),**kw)

    def _button(self,parent,title,command,accent=False):
        return hover_button(parent,title,command,primary=accent,compact=True)

    def _make_shell(self):
        toolbar=tk.Frame(self,bg=SURFACE,height=44)
        toolbar.pack(fill='x')
        toolbar.pack_propagate(False)
        mark=tk.Canvas(toolbar,width=26,height=28,bg=SURFACE,highlightthickness=0)
        mark.pack(side='left',padx=(14,6))
        draw_icon(mark,'logo',13,14,22,ACCENT)
        self._text(toolbar,'ASTRONYX',size=10,bold=True).pack(side='left',padx=(0,15))
        file_menu=self._menu(toolbar,'Arquivo')
        file_menu.add_command(label='Importar modelo…',command=self._create_new)
        file_menu.add_command(label='Salvar pintura',command=lambda:self._editor_action('_save'))
        file_menu.add_separator()
        file_menu.add_command(label='Projetos',command=self._toggle_projects)
        file_menu.add_command(label='Galeria completa',command=lambda:self.app._navigate('library','tab_library'))
        file_menu.add_command(label='Atualizar lista',command=self._refresh_external)
        prepare=self._menu(toolbar,'Preparar')
        prepare.add_command(label='Importar / converter',command=self._create_new)
        prepare.add_command(label='Ajustes de escala e malha',command=lambda:self.app._navigate('scale','tab_conv'))
        export=self._menu(toolbar,'Exportar')
        export.add_command(label='Texturas pintadas',command=lambda:self._editor_action('_apply'))
        export.add_command(label='Arquivo .tsMod',command=self._export_tsmod)
        export.add_command(label='Instalar no TaleSpire',command=self._install_current)
        help_menu=self._menu(toolbar,'Ajuda')
        help_menu.add_command(label='Documentação',command=lambda:self.app._navigate('help','tab_guide'))
        help_menu.add_command(label='Verificar atualizações',command=lambda:self.app._check_updates(True))
        self._button(toolbar,'Importar modelo',self._create_new,accent=True).pack(
            side='right',padx=(8,12),pady=6)
        self.project_choice=ttk.Combobox(toolbar,state='readonly',width=27,
                                        style='Astronyx.TCombobox')
        self.project_choice.set('Selecionar miniatura')
        self.project_choice.pack(side='right',padx=5,pady=6)
        self.project_choice.bind('<<ComboboxSelected>>',self._choice_select)
        tk.Frame(self,bg=BORDER,height=1).pack(fill='x')
        body=tk.Frame(self,bg=BG)
        body.pack(fill='both',expand=True)
        self.project_rail=tk.Frame(body,bg=SIDEBAR,width=214,
                                   highlightbackground=BORDER,highlightthickness=1)
        self.project_rail.pack_propagate(False)
        self._text(self.project_rail,'Miniaturas',bold=True).pack(anchor='w',padx=12,pady=(12,8))
        self.project_list=tk.Listbox(self.project_rail,bg=BG,fg=FG,
                                     selectbackground=ACCENT_SOFT,selectforeground=TEXT,
                                     relief='flat',highlightthickness=0,activestyle='none',
                                     exportselection=False,font=('Segoe UI',10))
        self.project_list.pack(fill='both',expand=True,padx=8,pady=(0,8))
        self.project_list.bind('<<ListboxSelect>>',self._list_select)
        self._button(self.project_rail,'+ Importar modelo',self._create_new).pack(fill='x',padx=8,pady=4)
        self._button(self.project_rail,'Atualizar lista',self._refresh_external).pack(fill='x',padx=8,pady=4)
        self._button(self.project_rail,'Recolher painel',self._toggle_projects).pack(fill='x',padx=8,pady=(4,10))
        self.workarea=tk.Frame(body,bg=BG)
        self.workarea.pack(side='left',fill='both',expand=True)
        self.home=tk.Frame(self.workarea,bg=BG)
        self.home.pack(fill='both',expand=True)
        self.editor_frame=tk.Frame(self.workarea,bg=BG)
        self.editor_frame.pack(fill='both',expand=True)
        self.editor_frame.pack_forget()

    def _menu(self,parent,title):
        button=tk.Menubutton(parent,text=title,bg=SURFACE,fg=FG,
                             activebackground=FIELD,activeforeground=FG,
                             relief='flat',font=('Segoe UI',9),padx=9,pady=5)
        button.pack(side='left')
        menu=tk.Menu(button,tearoff=False,bg=PANEL,fg=FG,
                     activebackground=ACCENT,activeforeground='white',
                     relief='flat',bd=0,font=('Segoe UI',9))
        button.configure(menu=menu)
        return menu

    def _editor_action(self,name):
        if self.workspace_editor is None:
            messagebox.showinfo('Selecione uma miniatura','Importe ou abra uma miniatura para pintar.',parent=self)
            return
        getattr(self.workspace_editor,name)()

    def _toggle_projects(self):
        if self.project_rail.winfo_manager():
            self.project_rail.pack_forget()
        else:
            self.project_rail.pack(side='left',fill='y',before=self.workarea,padx=(0,5))

    def _choice_select(self,_event=None):
        index=self.project_choice.current()
        if 0<=index<len(self.projects):
            item=self.projects[index]
            if self.current is None or item.folder!=self.current.folder:
                self._select_project(item)

    def _create_new(self):
        self.app._navigate('quick','tab_dashboard')

    def _refresh_external(self):
        self.app.refresh_library()

    def _export_tsmod(self):
        if self.current is None:
            messagebox.showinfo('Selecione uma miniatura','Importe um modelo para exportar.',
                                parent=self)
            return
        self.app._navigate('export','tab_cmd')

    def _show_welcome(self):
        if self.workspace_editor is not None:
            self.workspace_editor.destroy()
            self.workspace_editor=None
        self.editor_frame.pack_forget()
        self.home.pack(fill='both',expand=True)
        for child in self.home.winfo_children():
            child.destroy()
        content=tk.Frame(self.home,bg=BG)
        content.place(relx=.5,rely=.47,anchor='center',relwidth=.78)
        heading=tk.Frame(content,bg=BG)
        heading.pack(fill='x',pady=(0,26))
        self._text(heading,'MINI FORGE STUDIO',color=ACCENT,size=9,bold=True).pack(side='left')
        self._text(heading,f'v{APP_VERSION}',color=SUBTLE,size=9).pack(side='right')
        hero=tk.Frame(content,bg=BG)
        hero.pack(fill='x')
        hero.grid_columnconfigure(0,weight=1)
        hero.grid_columnconfigure(1,weight=0)
        copy=tk.Frame(hero,bg=BG)
        copy.grid(row=0,column=0,sticky='nw')
        self._text(copy,'Dê vida às suas\nminiaturas.',size=30,bold=True,
                   justify='left',anchor='w').pack(anchor='w')
        self._text(copy,'Pinte no 3D, experimente materiais e leve seu\n'
                   'personagem do Meshy para o TaleSpire.',
                   size=11,color=MUTED,justify='left').pack(anchor='w',pady=(14,23))
        actions=tk.Frame(copy,bg=BG)
        actions.pack(anchor='w')
        self._button(actions,'Importar modelo',self._create_new,accent=True).pack(side='left',padx=(0,8))
        self._button(actions,'Meus projetos',lambda:self.app._navigate('library','tab_library')).pack(side='left')
        self._text(copy,'GLB / ZIP  ·  Seus projetos ficam no seu PC',size=9,color=SUBTLE).pack(
            anchor='w',pady=(14,0))
        # Lightweight static vector artwork; no animation or background renderer.
        emblem=tk.Canvas(hero,width=240,height=260,bg=BG,highlightthickness=0)
        emblem.grid(row=0,column=1,sticky='e',padx=(20,0))
        for radius,colour in ((112,NAV_BG),(87,PANEL),(61,ACCENT_SOFT)):
            emblem.create_oval(120-radius,130-radius,120+radius,130+radius,
                               fill=colour,outline=BORDER,width=1)
        draw_icon(emblem,'logo',120,130,78,ACCENT)
        emblem.create_oval(204,89,212,97,fill=ACCENT,outline='')
        emblem.create_oval(33,167,39,173,fill=GREEN,outline='')
        tk.Frame(content,bg=BORDER,height=1).pack(fill='x',pady=(30,22))
        steps=tk.Frame(content,bg=BG)
        steps.pack(fill='x')
        for column,(icon,title,detail) in enumerate((
                ('import','01  Importe','Comece com seu modelo Meshy.'),
                ('pincel','02  Pinte','Cores, camadas e materiais.'),
                ('cube','03  Jogue','Exporte para o TaleSpire.'))):
            steps.grid_columnconfigure(column,weight=1,uniform='step')
            card=tk.Frame(steps,bg=BG)
            card.grid(row=0,column=column,sticky='nsew',padx=(0,16))
            mark=tk.Canvas(card,width=28,height=30,bg=BG,highlightthickness=0)
            mark.pack(anchor='w',pady=(0,8))
            draw_icon(mark,icon,14,15,23,ACCENT)
            self._text(card,title,size=10,bold=True).pack(anchor='w')
            self._text(card,detail,size=9,color=MUTED,wraplength=220,justify='left').pack(
                anchor='w',pady=(5,0))

    def open_project(self,item):
        """Open a gallery item in this editor, preserving the current draft guard."""
        if not self._valid_project(item):
            messagebox.showinfo('Projeto ainda não preparado',
                                'Converta o modelo antes de abrir a pintura.',parent=self)
            return False
        if self.current is not None and self.current.folder==item.folder and self.workspace_editor is not None:
            return True
        return self._select_project(item,first=self.workspace_editor is None)

    def _valid_project(self,entry):
        if entry is None or entry.obj is None:
            return False
        try:
            return find_albedo(entry.folder).is_file() and find_project_obj(entry.folder).is_file()
        except (OSError,ValueError):
            return False

    def refresh(self,entries,preferred=None):
        self.projects=[item for item in entries if self._valid_project(item)]
        self._select_guard=True
        self.project_list.delete(0,tk.END)
        for item in self.projects:
            self.project_list.insert(tk.END,item.name.replace('_',' ')[:27])
        self.project_choice.configure(values=[item.name.replace('_',' ') for item in self.projects])
        self._select_guard=False
        if self.workspace_editor is not None:
            # Keep unsaved active paint intact across filesystem/library refresh.
            self._select_row()
            return
        target=next((item for item in self.projects if preferred and
                     item.folder==Path(preferred)),None)
        if target is None and self.current is not None:
            target=next((item for item in self.projects if
                         item.folder==self.current.folder),None)
        if target is None:
            target=self.projects[0] if self.projects else None
        if target is not None:
            self._select_project(target,first=True)
        else:
            self.current=None
            self._show_welcome()

    def _select_row(self):
        self._select_guard=True
        self.project_list.selection_clear(0,tk.END)
        for i,item in enumerate(self.projects):
            if self.current and item.folder==self.current.folder:
                self.project_list.selection_set(i)
                self.project_list.see(i)
                self.project_choice.current(i)
                break
        self._select_guard=False

    def _list_select(self,_event):
        if self._select_guard or not self.project_list.curselection():
            return
        index=int(self.project_list.curselection()[0])
        if 0 <= index < len(self.projects):
            target=self.projects[index]
            if self.current is not None and self.current.folder==target.folder:
                return
            self._select_project(target)

    def _select_project(self,item,first=False):
        if self.workspace_editor is not None and not first:
            if not messagebox.askyesno('Trocar miniatura',
                'Deseja abrir outra miniatura? Salve o projeto atual antes '
                'de trocar: edições não salvas serão perdidas.',parent=self):
                self._select_row()
                return False
        previous=self.current
        self.current=item
        self._select_row()
        self.home.pack_forget()
        self.editor_frame.pack(fill='both',expand=True)
        if self.workspace_editor is not None:
            self.workspace_editor.destroy()
            self.workspace_editor=None
        try:
            editor=PaintingStudio(self.editor_frame,item.folder,
                                  on_apply=self.app.refresh_library,
                                  on_exit=self._back_to_library)
            editor.pack(fill='both',expand=True)
            self.workspace_editor=editor
            return True
        except Exception as exc:
            self.current=previous
            self._select_row()
            self._show_welcome()
            messagebox.showerror('Não foi possível abrir a pintura',
                                 str(exc),parent=self)
            return False

    def _back_to_library(self):
        self.app._navigate('library','tab_library')

    def open_editor(self):
        if self.workspace_editor is None:
            if self.current:
                self._select_project(self.current,first=True)
            else:
                messagebox.showinfo('Miniatura necessária',
                                    'Importe um modelo Meshy para pintar.',parent=self)

    def close_editor(self):
        self._back_to_library()

    def _install_current(self):
        if self.current is None or self.current.tsmod is None:
            messagebox.showinfo('Exportação necessária',
                  'Gere um arquivo .tsMod antes de instalar a miniatura.',
                  parent=self)
            return
        self.app._install_library(self.current.tsmod)
