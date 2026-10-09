"""Astronyx Mini Forge Studio V2.2.4.

New desktop presentation; intentionally delegates all conversion to unchanged
V1.7 Forge methods and core modules.
"""
from __future__ import annotations

import datetime as dt
import queue
import threading
import sys
import os
import tkinter as tk
import webbrowser
from pathlib import Path
from tkinter import ttk, messagebox

import app as legacy
from core.library import scan_library, Miniature
from core.preferences import open_output_folder
from core.version import APP_VERSION
from ui import hud22
from ui import theme as polish
from ui.texture_viewer import TexturedObjViewer
from core.updater import find_update, download_installer, run_installer, UpdateError, is_portable


# Shared visual palette. Conversion modules and data paths remain unchanged.
legacy.BG = polish.BG
legacy.PANEL = polish.PANEL
legacy.FIELD = polish.RAISED
legacy.BORDER = polish.BORDER
legacy.FG = polish.TEXT
legacy.MUTED = polish.MUTED
legacy.ACCENT = polish.ACCENT
legacy.ACCENT2 = polish.ACCENT
legacy.GREEN = polish.GREEN
SIDEBAR = polish.SIDEBAR
PANEL = polish.PANEL
FG = polish.TEXT
MUTED = polish.MUTED
ACCENT = polish.ACCENT
GREEN = polish.GREEN



class UpdateInterface:
    """Asynchronous checks: no network requests on the Tk thread."""

    def _begin_updates(self):
        self.update_events = queue.Queue()
        self._checking_updates = False
        self._downloading_update = False
        self._update_window = None
        self.after(120, self._poll_updates)
        self.after(1800, lambda: self._check_updates(False))

    def _check_updates(self, manual=True):
        if self._checking_updates or self._downloading_update:
            return
        self._checking_updates = True
        def work():
            try:
                self.update_events.put(('check', find_update(), manual))
            except Exception as ex:
                self.update_events.put(('error', str(ex), manual))
        threading.Thread(target=work, daemon=True).start()

    def _poll_updates(self):
        try:
            while True:
                event = self.update_events.get_nowait()
                if event[0] == 'check':
                    self._checking_updates = False
                    if event[1]:
                        self._show_update(event[1])
                    elif event[2]:
                        messagebox.showinfo('Atualizações', 'Você já está na versão mais recente.')
                elif event[0] == 'error':
                    self._checking_updates = False
                    self._downloading_update = False
                    if self._update_window and self._update_window.winfo_exists():
                        self._update_status.set('Não foi possível atualizar: ' + event[1])
                        self._update_download_btn.configure(state='normal')
                    elif event[2]:
                        messagebox.showwarning('Atualizações', event[1])
                elif event[0] == 'progress':
                    if self._update_window and self._update_window.winfo_exists():
                        self._update_status.set('Baixando: %d%%' % (event[1] * 100 / max(1,event[2])))
                elif event[0] == 'ready':
                    self._downloading_update = False
                    if self.busy:
                        self._update_status.set('Termine a conversão antes de atualizar.')
                        self._update_download_btn.configure(state='normal')
                    else:
                        try:
                            run_installer(event[1])
                            self._close()
                        except Exception as ex:
                            self._update_status.set('Instalador não iniciado: ' + str(ex))
                            self._update_download_btn.configure(state='normal')
        except queue.Empty:
            pass
        if self.winfo_exists():
            self.after(120, self._poll_updates)

    def _show_update(self, release):
        if self._update_window and self._update_window.winfo_exists():
            self._update_window.destroy()
        win=tk.Toplevel(self)
        self._update_window=win
        win.title('Atualização disponível • Astronyx')
        win.configure(bg=PANEL)
        win.geometry('540x345')
        win.transient(self)
        tk.Label(win,text='✦ Nova versão disponível',bg=PANEL,fg='#B998FF',
                 font=('Segoe UI',17,'bold')).pack(anchor='w',padx=22,pady=(18,5))
        tk.Label(win,text=f'Instalada: {APP_VERSION}   →   Nova: {release.version}',bg=PANEL,fg=FG).pack(anchor='w',padx=22)
        notes=tk.Text(win,bg='#10111F',fg=FG,height=8,wrap='word',relief='flat',padx=10,pady=7)
        notes.pack(fill='both',expand=True,padx=22,pady=12)
        notes.insert('1.0',release.notes or 'Correções e melhorias.')
        notes.config(state='disabled')
        self._update_status=tk.StringVar(value='Download verificado por SHA-256 antes de executar.')
        tk.Label(win,textvariable=self._update_status,bg=PANEL,fg=MUTED,wraplength=495).pack(anchor='w',padx=22)
        controls=tk.Frame(win,bg=PANEL)
        controls.pack(fill='x',padx=22,pady=12)
        self._button(controls,'Mais tarde',win.destroy,padx=10,pady=7).pack(side='left')
        self._button(controls,'Ver Release',lambda:webbrowser.open(release.page),padx=10,pady=7).pack(side='left',padx=8)
        name='Ver download portável' if is_portable() else ('Baixar e instalar' if sys.platform=='win32' and getattr(sys,'frozen',False) else 'Abrir página de download')
        self._update_download_btn=self._button(controls,name,lambda:self._download_update(release),accent=True,padx=10,pady=7)
        self._update_download_btn.pack(side='right')

    def _download_update(self, release):
        if self.busy:
            messagebox.showwarning('Conversão em andamento','Finalize a conversão antes da atualização.')
            return
        if is_portable() or sys.platform!='win32' or not getattr(sys,'frozen',False):
            webbrowser.open(release.page)
            return
        if self._downloading_update:
            return
        self._downloading_update=True
        self._update_download_btn.configure(state='disabled')
        self._update_status.set('Baixando com verificação de integridade...')
        def work():
            try:
                file=download_installer(release,progress=lambda n,t:self.update_events.put(('progress',n,t)))
                self.update_events.put(('ready',file))
            except Exception as ex:
                self.update_events.put(('error',str(ex),True))
        threading.Thread(target=work,daemon=True).start()


class Studio(UpdateInterface, legacy.Forge):
    viewer_class = TexturedObjViewer
    NAV = [
        ('home', '⌂', 'Dashboard', 'tab_dashboard'),
        ('studio', '◈', 'Studio 3D', 'tab_preview'),
        ('library', '▦', 'Biblioteca', 'tab_library'),
        ('convert', '⬡', 'Converter', 'tab_quick'),
        ('scale', '⚙', 'Ferramentas', 'tab_conv'),
        ('export', '↗', 'Gerar .tsMod', 'tab_cmd'),
        ('install', '↓', 'Instalar no TaleSpire', 'tab_tsmod'),
        ('help', '?', 'Ajuda e tutorial', 'tab_guide'),
    ]

    def __init__(self):
        self.library_entries: list[Miniature] = []
        self.library_cards: list[tk.Widget] = []
        self.library_image_refs = []
        self.gallery_columns = 3
        self._active_nav_key = 'home'
        super().__init__()
        self._begin_updates()
        self.title('Astronyx Mini Forge Studio V2.2.4 • Meshy → TaleSpire')
        if os.name == 'nt':
            try:
                self.iconbitmap(str(legacy.BASE / 'assets' / 'astronyx.ico'))
            except tk.TclError:
                pass
        self.geometry('1280x840')
        self.minsize(1020, 690)
        self.after(80, self.refresh_library)
        self.bind('<Control-o>', lambda _event: self._pick_source())
        self.bind('<Control-l>', lambda _event: self._navigate('library', 'tab_library'))
        self.bind('<Control-r>', lambda _event: self.refresh_library())

    def _draw(self):
        """Rebuild only UI layout; core workflow stays in parent class."""
        polish.apply_studio_style(self)
        body = tk.Frame(self, bg=legacy.BG)
        body.pack(fill='both', expand=True)
        sidebar = tk.Frame(body, bg=SIDEBAR, width=225)
        sidebar.pack(side='left', fill='y')
        sidebar.pack_propagate(False)

        brand = tk.Frame(sidebar, bg=SIDEBAR)
        brand.pack(fill='x', padx=20, pady=(21, 18))
        tk.Label(brand, text='✦  ASTRONYX', fg=polish.ACCENT_HOVER, bg=SIDEBAR,
                 font=('Segoe UI', 17, 'bold')).pack(anchor='w')
        tk.Label(brand, text='MINI FORGE  /  V2.2.4', fg=polish.SUBTLE, bg=SIDEBAR,
                 font=('Segoe UI', 9, 'bold')).pack(anchor='w', pady=(6, 0))
        tk.Frame(sidebar, height=1, bg=polish.BORDER).pack(fill='x', padx=18, pady=(0, 12))

        self.nav_buttons = {}
        self.nav_indicators = {}
        for key, icon, label, target in self.NAV:
            if key in ('home', 'scale'):
                tk.Label(sidebar,text='WORKSPACE' if key=='home' else 'FERRAMENTAS',
                         fg=polish.SUBTLE,bg=SIDEBAR,
                         font=('Segoe UI',8,'bold')).pack(anchor='w',padx=23,
                         pady=(2,7) if key=='home' else (15,8))
            row = tk.Frame(sidebar,bg=SIDEBAR)
            row.pack(fill='x',padx=11,pady=2)
            indicator=tk.Frame(row,bg=SIDEBAR,width=3)
            indicator.pack(side='left',fill='y')
            button=tk.Button(row,text=f'{icon}    {label}',anchor='w',
                command=lambda k=key,t=target:self._navigate(k,t),
                bg=SIDEBAR,fg=polish.MUTED,activebackground=polish.ACCENT_SOFT,
                activeforeground=polish.TEXT,relief='flat',bd=0,padx=12,pady=10,
                font=('Segoe UI',10),cursor='hand2',highlightthickness=0)
            button.pack(side='left',fill='x',expand=True)
            button.bind('<Enter>',lambda e,k=key:self._nav_hover(k,True),add='+')
            button.bind('<Leave>',lambda e,k=key:self._nav_hover(k,False),add='+')
            self.nav_buttons[key]=button
            self.nav_indicators[key]=indicator

        footer=tk.Frame(sidebar,bg=SIDEBAR)
        footer.pack(side='bottom',fill='x',padx=17,pady=(0,21))
        tk.Frame(footer,bg=polish.BORDER,height=1).pack(fill='x',pady=(0,14))
        tk.Label(footer,text='●  CONVERSÃO LOCAL',bg=SIDEBAR,fg=GREEN,
                 font=('Segoe UI',9,'bold')).pack(anchor='w')
        tk.Label(footer,text='Projetos salvos no seu computador',bg=SIDEBAR,
                 fg=polish.SUBTLE,font=('Segoe UI',9)).pack(anchor='w',pady=(4,0))

        main = tk.Frame(body, bg=legacy.BG)
        main.pack(side='left', fill='both', expand=True)
        hero = tk.Frame(main, bg=polish.PANEL, height=106)
        hero.pack(fill='x')
        hero.pack_propagate(False)
        left = tk.Frame(hero, bg=polish.PANEL)
        left.pack(side='left', fill='both', expand=True, padx=(24, 4), pady=(17, 9))
        self.page_title = tk.StringVar(value='Visão geral')
        self.page_subtitle = tk.StringVar(value='Seu espaço de criação e conversão de miniaturas.')
        tk.Label(left, textvariable=self.page_title, bg=polish.PANEL, fg=FG,
                 font=('Segoe UI', 19, 'bold'), anchor='w').pack(anchor='w')
        tk.Label(left, textvariable=self.page_subtitle, bg=polish.PANEL,
                 fg=MUTED, font=('Segoe UI', 10)).pack(anchor='w', pady=(6, 0))
        actions = tk.Frame(hero, bg=polish.PANEL)
        actions.pack(side='right', padx=21, pady=22)
        polish.hover_button(actions,'↻ Detectar programas',self._detect_required,
                           compact=True).pack(side='right')
        polish.hover_button(actions,'⬆ Atualizações',lambda:self._check_updates(True),
                           compact=True).pack(side='right',padx=(0,9))

        status = tk.Frame(main, bg=legacy.BG)
        status.pack(fill='x', padx=22, pady=(13, 0))
        self.status_label = tk.Label(status, bg=legacy.BG, fg=MUTED,
                                    font=('Segoe UI', 10), anchor='w')
        self.status_label.pack(side='left', fill='x', expand=True)
        polish.hover_button(status, 'Pasta de saída  ↗', self._open_destination,
                            compact=True).pack(side='right')

        view = tk.Frame(main, bg=legacy.BG)
        view.pack(fill='both', expand=True, padx=18, pady=(11, 14))
        sty = ttk.Style(self)
        sty.layout('StudioHidden.TNotebook.Tab', [])
        sty.configure('StudioHidden.TNotebook', background=legacy.BG, borderwidth=0)
        self.tabs = ttk.Notebook(view, style='StudioHidden.TNotebook')
        self.tabs.pack(fill='both', expand=True)
        for attr, label in [
            ('tab_dashboard', 'Dashboard'), ('tab_quick', 'Converter'), ('tab_library', 'Biblioteca'),
            ('tab_preview', 'Prévia'), ('tab_conv', 'Ajustes'),
            ('tab_cmd', 'Exportar'), ('tab_tsmod', 'Instalar'),
            ('tab_guide', 'Ajuda')]:
            frame = tk.Frame(self.tabs, bg=legacy.BG)
            setattr(self, attr, frame)
            self.tabs.add(frame, text=label)

        # The same legacy widgets and handlers, just rearranged as pages.
        self.convert_canvas = tk.Canvas(self.tab_conv, bg=legacy.BG, highlightthickness=0)
        self.convert_scroll = tk.Scrollbar(self.tab_conv, orient='vertical',
                                           command=self.convert_canvas.yview)
        self.convert_canvas.configure(yscrollcommand=self.convert_scroll.set)
        self.convert_scroll.pack(side='right', fill='y')
        self.convert_canvas.pack(side='left', fill='both', expand=True)
        self.converter_inner = tk.Frame(self.convert_canvas, bg=legacy.BG)
        self.inner_id = self.convert_canvas.create_window((0, 0),
                               window=self.converter_inner, anchor='nw')
        self.converter_inner.bind('<Configure>', lambda e: self.convert_canvas.configure(
                               scrollregion=self.convert_canvas.bbox('all')))
        self.convert_canvas.bind('<Configure>', lambda e: self.convert_canvas.itemconfigure(
                               self.inner_id, width=e.width))
        self.convert_canvas.bind('<Enter>', lambda e: self.bind_all('<MouseWheel>', self._scroll_wheel))
        self.convert_canvas.bind('<Leave>', lambda e: self.unbind_all('<MouseWheel>'))
        self._draw_quick()
        self._draw_converter()
        self._draw_guide()
        self._draw_tsmod()
        self._draw_cmd_setup()
        self._draw_preview()
        self._draw_library()
        hud22.dashboard(self)
        hud22.inspector(self)
        self.viewer.add_preview_controls(self.tab_preview)
        self.tabs.bind('<<NotebookTabChanged>>', self._tab_switched)
        self._navigate('home', 'tab_dashboard')
        tk.Label(self, text='Ferramenta independente; não afiliada ao TaleSpire, Bouncyrock ou Meshy.',
                 bg=legacy.BG, fg='#656B85', font=('Segoe UI', 8)).pack(side='bottom', pady=(0, 4))

    def _refresh_quick_status(self):
        super()._refresh_quick_status()
        if hasattr(self, 'status_label'):
            blender_ok, cmd_ok = legacy.tool_status(self.blender.get(), self.cmd_executable.get())
            self.status_label.config(
                text=('●  Blender pronto' if blender_ok else '○  Blender não localizado') +
                     '     •     ' + ('●  TaleWeaverCmd pronto' if cmd_ok else '○  TaleWeaverCmd não localizado'),
                fg=GREEN if blender_ok and cmd_ok else '#EAC07B')

    def _nav_hover(self,key,enter):
        if key==self._active_nav_key:
            return
        self.nav_buttons[key].configure(bg=polish.RAISED if enter else SIDEBAR,
                                        fg=polish.TEXT if enter else polish.MUTED)

    def _tab_switched(self, _event=None):
        selected = self.tabs.select()
        page_titles = {
            'tab_dashboard': ('Visão geral','Crie e acompanhe suas miniaturas em um só lugar.'),
            'tab_preview': ('Studio 3D','Inspecione seu modelo, câmera e propriedades antes de exportar.'),
            'tab_library': ('Biblioteca','Todos os personagens preparados e seus arquivos .tsMod.'),
            'tab_quick': ('Nova conversão','Prepare um personagem do Meshy para o TaleSpire.'),
            'tab_conv': ('Ferramentas avançadas','Ajustes de malha, textura e escala para resultados precisos.'),
            'tab_cmd': ('Exportar .tsMod','Gere a miniatura pelo TaleWeaverCmd instalado.'),
            'tab_tsmod': ('Instalar miniatura','Adicione seu personagem à biblioteca local do TaleSpire.'),
            'tab_guide': ('Ajuda e tutorial','Dicas de importação, conversão e instalação.')
        }
        for attr, (title,subtitle) in page_titles.items():
            if selected==str(getattr(self,attr)):
                self.page_title.set(title)
                self.page_subtitle.set(subtitle)
                break
        for key, _, _, target in self.NAV:
            active = str(getattr(self, target)) == selected
            self.nav_buttons[key].configure(bg=polish.ACCENT_SOFT if active else SIDEBAR,
                                            fg=polish.TEXT if active else polish.MUTED,
                                            font=('Segoe UI',10,'bold' if active else 'normal'))
            self.nav_indicators[key].configure(bg=polish.ACCENT if active else SIDEBAR)
            if active:
                self._active_nav_key=key
        if selected==str(self.tab_library):
            self.refresh_library()

    def _navigate(self, key, target):
        self.tabs.select(getattr(self, target))
        self._tab_switched()

    def _draw_library(self):
        parent = self.tab_library
        header = tk.Frame(parent, bg=legacy.BG)
        header.pack(fill='x', padx=6, pady=(8, 16))
        tk.Label(header, text='Minhas miniaturas', bg=legacy.BG, fg=FG,
                 font=('Segoe UI', 20, 'bold')).pack(side='left')
        polish.hover_button(header, '↻ Atualizar', self.refresh_library,
                            compact=True).pack(side='right')
        tk.Label(parent, text='Projetos encontrados na pasta de saída. Nenhum modelo é alterado aqui.',
                 bg=legacy.BG, fg=MUTED, font=('Segoe UI', 10)).pack(anchor='w', padx=7, pady=(0, 12))
        bar = tk.Frame(parent, bg=legacy.BG)
        bar.pack(fill='x', padx=7)
        self.library_summary = tk.StringVar(value='Carregando miniaturas...')
        self.library_search = tk.StringVar(value='')
        self.library_filter = tk.StringVar(value='Todos')
        filters = tk.Frame(parent, bg=legacy.BG)
        filters.pack(fill='x', padx=7, pady=(6, 8))
        tk.Label(filters, text='Pesquisar', bg=legacy.BG, fg=MUTED).pack(side='left', padx=(0, 9))
        ttk.Entry(filters, textvariable=self.library_search, width=32,style='Astronyx.TEntry').pack(side='left', padx=(0, 14))
        ttk.Combobox(filters, textvariable=self.library_filter,
                     values=('Todos', 'Prontos', 'Em preparação'),
                     state='readonly', width=18,style='Astronyx.TCombobox').pack(side='left')
        self.library_search.trace_add('write', lambda *_: self._render_library_entries())
        self.library_filter.trace_add('write', lambda *_: self._render_library_entries())
        tk.Label(bar, textvariable=self.library_summary, bg=legacy.BG, fg=GREEN,
                 font=('Segoe UI', 10, 'bold')).pack(side='left')
        self.library_scroll = tk.Canvas(parent, bg=legacy.BG, highlightthickness=0)
        scrollbar = tk.Scrollbar(parent, command=self.library_scroll.yview)
        scrollbar.pack(side='right', fill='y')
        self.library_scroll.configure(yscrollcommand=scrollbar.set)
        self.library_scroll.pack(fill='both', expand=True)
        self.library_frame = tk.Frame(self.library_scroll, bg=legacy.BG)
        self.library_scroll_id = self.library_scroll.create_window((0, 0),
                                                        window=self.library_frame, anchor='nw')
        self.library_frame.bind('<Configure>', lambda e: self.library_scroll.configure(
                               scrollregion=self.library_scroll.bbox('all')))
        self.library_scroll.bind('<Configure>', self._on_library_resize)
        self.library_scroll.bind('<Enter>', lambda e: self.bind_all('<MouseWheel>', self._scroll_wheel))
        self.library_scroll.bind('<Leave>', lambda e: self.unbind_all('<MouseWheel>'))

    def _on_library_resize(self,event):
        self.library_scroll.itemconfigure(self.library_scroll_id,width=event.width)
        columns=polish.gallery_columns(event.width)
        if columns != self.gallery_columns:
            self.gallery_columns=columns
            self._render_library_entries()

    def _render_library_entries(self):
        """Repaint visible cards only; typing never rescans the disk."""
        if not hasattr(self,'library_frame'):
            return
        for child in self.library_frame.winfo_children():
            child.destroy()
        self.library_image_refs=[]
        # Reset column weights when resizing 4 -> 3 -> 2, otherwise an empty
        # previously-used column keeps occupying width.
        for column in range(4):
            self.library_frame.grid_columnconfigure(column,weight=0,uniform='')
        for column in range(self.gallery_columns):
            self.library_frame.grid_columnconfigure(column,weight=1,uniform='gallery')
        entries=self.library_entries
        filtered=hud22.filter_miniatures(entries,self.library_search.get(),
                                          self.library_filter.get())
        ready=sum(bool(item.tsmod) for item in entries)
        self.library_summary.set(f'{len(filtered)} exibidos / {len(entries)} projetos    •    {ready} .tsMod prontos')
        for index,item in enumerate(filtered):
            hud22.gallery_card(self,item,index)
        if not filtered:
            border=tk.Frame(self.library_frame,bg=polish.BORDER)
            border.grid(row=0,column=0,sticky='ew',padx=8,pady=14)
            empty=tk.Frame(border,bg=polish.PANEL)
            empty.pack(fill='x',padx=1,pady=1)
            title=('Nenhuma miniatura encontrada' if entries else 'Sua biblioteca começa aqui')
            detail=('Tente outro nome ou altere o filtro.'
                    if entries else 'Clique em Nova conversão para preparar seu primeiro personagem.')
            tk.Label(empty,text='◈  '+title,bg=polish.PANEL,fg=polish.TEXT,
                     font=('Segoe UI',13,'bold')).pack(padx=20,pady=(22,7))
            tk.Label(empty,text=detail,bg=polish.PANEL,fg=polish.MUTED,
                     font=('Segoe UI',10)).pack(padx=20,pady=(0,22))

    def refresh_library(self):
        if not hasattr(self,'library_frame'):
            return
        self.library_entries=scan_library(self.target.get(),max_items=100)
        self._render_library_entries()
        hud22.refresh_dashboard(self)

    def _library_row(self, item: Miniature):
        box = tk.Frame(self.library_frame, bg=PANEL, highlightbackground=legacy.BORDER,
                       highlightthickness=1)
        box.pack(fill='x', padx=6, pady=6)
        preview = tk.Frame(box, bg='#22263A', width=76, height=75)
        preview.pack(side='left', padx=12, pady=9)
        preview.pack_propagate(False)
        pic = None
        if item.thumbnail and len(self.library_image_refs) < 18 and item.thumbnail.stat().st_size < 3_000_000:
            try:
                raw = tk.PhotoImage(file=str(item.thumbnail))
                scale = max(1, (max(raw.width(), raw.height()) + 62) // 63)
                pic = raw.subsample(scale, scale)
                self.library_image_refs.append(pic)
            except tk.TclError:
                pass
        if pic:
            tk.Label(preview, image=pic, bg='#22263A').pack(expand=True)
        else:
            tk.Label(preview, text='◈', bg='#22263A', fg='#BC97FF',
                     font=('Segoe UI', 27, 'bold')).pack(expand=True)
        info = tk.Frame(box, bg=PANEL)
        info.pack(side='left', fill='both', expand=True, pady=12)
        tk.Label(info, text=item.name.replace('_', ' '), fg=FG, bg=PANEL,
                 font=('Segoe UI', 11, 'bold'), anchor='w').pack(anchor='w')
        time_label = dt.datetime.fromtimestamp(item.updated_at).strftime('%d/%m/%Y %H:%M')
        tk.Label(info, text=('● .tsMod pronto  •  ' if item.tsmod else '○ Preparação incompleta  •  ')
                            + time_label, fg=GREEN if item.tsmod else '#EDC17B',
                 bg=PANEL, font=('Segoe UI', 9)).pack(anchor='w', pady=(6, 0))
        actions = tk.Frame(box, bg=PANEL)
        actions.pack(side='right', padx=13)
        self._button(actions, 'Abrir pasta', lambda p=item.folder: self._open_library(p),
                     padx=9, pady=6).pack(pady=3, fill='x')
        if item.tsmod:
            self._button(actions, 'Instalar', lambda p=item.tsmod: self._install_library(p),
                         padx=9, pady=6).pack(pady=3, fill='x')
        if item.obj:
            self._button(actions, 'Prévia 3D', lambda p=item.obj: self._load_preview(p),
                         padx=9, pady=6).pack(pady=3, fill='x')

    def _open_library(self, path: Path):
        try:
            open_output_folder(path)
        except OSError as err:
            messagebox.showerror('Não foi possível abrir', str(err))

    def _install_library(self, path: Path):
        self.tsmod_file.set(str(path))
        self._inspect_tsmod()
        self._navigate('install', 'tab_tsmod')

    def _scroll_wheel(self, event):
        if self.tabs.select() == str(self.tab_library):
            self.library_scroll.yview_scroll(-int(event.delta / 120), 'units')
        else:
            super()._scroll_wheel(event)

    def _read_log(self):
        previously_busy = self.busy
        super()._read_log()
        if previously_busy and not self.busy:
            self.refresh_library()


def run_packaged_selftest(report_file: str) -> int:
    """Offline package validation that can run with no graphical desktop session.

    Checks resources and Tcl shipped by PyInstaller. This is not an in-game
    conversion test; Blender and TaleWeaverCmd are third-party executables.
    """
    import json
    import sys
    result = {
        'version': '2.2.4',
        'frozen': bool(getattr(sys, 'frozen', False)),
        'test': 'resource_and_tcl_smoke',
        'checked': {},
    }
    paths = {
        'blender_pipeline.py': legacy.BASE / 'core' / 'blender_pipeline.py',
        'astronyx.ico': legacy.BASE / 'assets' / 'astronyx.ico',
        'exemplo_guerreiro.glb': legacy.BASE / 'assets' / 'exemplo_guerreiro.glb',
    }
    for name, path in paths.items():
        result['checked'][name] = path.is_file() and path.stat().st_size > 0
    try:
        tcl = tk.Tcl()
        result['tcl_version'] = str(tcl.eval('info patchlevel'))
        result['checked']['tcl'] = True
    except Exception as exc:
        result['checked']['tcl'] = False
        result['tcl_error'] = str(exc)
    result['ok'] = all(result['checked'].values())
    if report_file:
        output = Path(report_file)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    elif sys.stdout is not None:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result['ok'] else 1


if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == '--version':
        if sys.stdout:
            print('Astronyx Mini Forge Studio 2.2.4')
        raise SystemExit(0)
    if len(sys.argv) > 1 and sys.argv[1] == '--self-test':
        report = sys.argv[2] if len(sys.argv) > 2 else ''
        raise SystemExit(run_packaged_selftest(report))
    if os.name == 'nt':
        try:
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except (AttributeError, OSError):
            pass
    Studio().mainloop()
