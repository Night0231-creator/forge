"""Astronyx Mini Forge Studio V2.0.

New desktop presentation; intentionally delegates all conversion to unchanged
V1.7 Forge methods and core modules.
"""
from __future__ import annotations

import datetime as dt
import os
import tkinter as tk
import webbrowser
from pathlib import Path
from tkinter import ttk, messagebox

import app as legacy
from core.library import scan_library, Miniature
from core.preferences import open_output_folder


SIDEBAR = '#10111F'
PANEL = legacy.PANEL
FG = legacy.FG
MUTED = legacy.MUTED
ACCENT = legacy.ACCENT
GREEN = legacy.GREEN


class Studio(legacy.Forge):
    NAV = [
        ('home', '✦', 'Início rápido', 'tab_quick'),
        ('library', '▦', 'Minhas miniaturas', 'tab_library'),
        ('preview', '◈', 'Prévia 3D', 'tab_preview'),
        ('scale', '⚙', 'Ajustes avançados', 'tab_conv'),
        ('export', '⬡', 'Gerar .tsMod', 'tab_cmd'),
        ('install', '↓', 'Instalar no TaleSpire', 'tab_tsmod'),
        ('help', '?', 'Ajuda e tutorial', 'tab_guide'),
    ]

    def __init__(self):
        self.library_entries: list[Miniature] = []
        self.library_cards: list[tk.Widget] = []
        self.library_image_refs = []
        super().__init__()
        self.title('Astronyx Mini Forge Studio 2.0.2 • Meshy → TaleSpire')
        if os.name == 'nt':
            try:
                self.iconbitmap(str(legacy.BASE / 'assets' / 'astronyx.ico'))
            except tk.TclError:
                pass
        self.geometry('1190x800')
        self.minsize(955, 670)
        self.after(80, self.refresh_library)
        self.bind('<Control-o>', lambda _event: self._pick_source())
        self.bind('<Control-l>', lambda _event: self._navigate('library', 'tab_library'))
        self.bind('<Control-r>', lambda _event: self.refresh_library())

    def _draw(self):
        """Rebuild only UI layout; core workflow stays in parent class."""
        body = tk.Frame(self, bg=legacy.BG)
        body.pack(fill='both', expand=True)
        sidebar = tk.Frame(body, bg=SIDEBAR, width=224)
        sidebar.pack(side='left', fill='y')
        sidebar.pack_propagate(False)

        brand = tk.Frame(sidebar, bg=SIDEBAR)
        brand.pack(fill='x', padx=21, pady=(23, 20))
        tk.Label(brand, text='✦  ASTRONYX', fg='#B998FF', bg=SIDEBAR,
                 font=('Segoe UI', 17, 'bold')).pack(anchor='w')
        tk.Label(brand, text='MINI FORGE  /  STUDIO 2.0.2', fg='#8387A9', bg=SIDEBAR,
                 font=('Segoe UI', 9, 'bold')).pack(anchor='w', pady=(6, 0))
        tk.Frame(sidebar, height=1, bg='#30314D').pack(fill='x', padx=18, pady=(0, 13))

        self.nav_buttons = {}
        for key, icon, label, target in self.NAV:
            button = tk.Button(sidebar, text=f'{icon}    {label}', anchor='w',
                        command=lambda key=key, target=target: self._navigate(key, target),
                        bg=SIDEBAR, fg='#B0B3CB', activebackground='#302650',
                        activeforeground='#FDFBFF', relief='flat', bd=0, padx=14, pady=13,
                        font=('Segoe UI', 10, 'bold'), cursor='hand2')
            button.pack(fill='x', padx=11, pady=2)
            self.nav_buttons[key] = button

        tk.Label(sidebar, text='CONVERSÃO LOCAL', bg=SIDEBAR, fg=GREEN,
                 font=('Segoe UI', 9, 'bold')).pack(side='bottom', anchor='w', padx=21, pady=(0, 22))
        tk.Label(sidebar, text='Sem pagar por personagem', bg=SIDEBAR, fg='#8C91AE',
                 font=('Segoe UI', 9)).pack(side='bottom', anchor='w', padx=21, pady=(0, 4))

        main = tk.Frame(body, bg=legacy.BG)
        main.pack(side='left', fill='both', expand=True)
        hero = tk.Frame(main, bg='#15152A', height=106)
        hero.pack(fill='x')
        hero.pack_propagate(False)
        left = tk.Frame(hero, bg='#15152A')
        left.pack(side='left', fill='both', expand=True, padx=(24, 4), pady=(17, 9))
        tk.Label(left, text='Seu estúdio de miniaturas 3D', bg='#15152A', fg=FG,
                 font=('Segoe UI', 20, 'bold'), anchor='w').pack(anchor='w')
        tk.Label(left, text='Meshy  →  Blender  →  TaleWeaverCmd  →  TaleSpire',
                 bg='#15152A', fg='#9A93BE', font=('Segoe UI', 10)).pack(anchor='w', pady=(6, 0))
        actions = tk.Frame(hero, bg='#15152A')
        actions.pack(side='right', padx=21, pady=22)
        self._button(actions, '↻  Detectar programas', self._detect_required,
                     padx=12, pady=9).pack(side='right')

        status = tk.Frame(main, bg=legacy.BG)
        status.pack(fill='x', padx=22, pady=(13, 0))
        self.status_label = tk.Label(status, bg=legacy.BG, fg=MUTED,
                                    font=('Segoe UI', 10), anchor='w')
        self.status_label.pack(side='left', fill='x', expand=True)
        self._button(status, 'Pasta de saída  ↗', self._open_destination,
                     padx=9, pady=7).pack(side='right')

        view = tk.Frame(main, bg=legacy.BG)
        view.pack(fill='both', expand=True, padx=18, pady=(11, 14))
        sty = ttk.Style(self)
        sty.layout('StudioHidden.TNotebook.Tab', [])
        sty.configure('StudioHidden.TNotebook', background=legacy.BG, borderwidth=0)
        self.tabs = ttk.Notebook(view, style='StudioHidden.TNotebook')
        self.tabs.pack(fill='both', expand=True)
        for attr, label in [
            ('tab_quick', 'Início'), ('tab_library', 'Biblioteca'),
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
        self.tabs.bind('<<NotebookTabChanged>>', self._tab_switched)
        self._navigate('home', 'tab_quick')
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

    def _tab_switched(self, _event=None):
        selected = self.tabs.select()
        for key, _, _, target in self.NAV:
            active = str(getattr(self, target)) == selected
            self.nav_buttons[key].configure(bg='#2B2149' if active else SIDEBAR,
                                            fg='#FFFFFF' if active else '#B0B3CB')
        if selected == str(self.tab_library):
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
        self._button(header, 'Atualizar biblioteca', self.refresh_library,
                     padx=12, pady=8).pack(side='right')
        tk.Label(parent, text='Projetos encontrados na pasta de saída. Nenhum modelo é alterado aqui.',
                 bg=legacy.BG, fg=MUTED, font=('Segoe UI', 10)).pack(anchor='w', padx=7, pady=(0, 12))
        bar = tk.Frame(parent, bg=legacy.BG)
        bar.pack(fill='x', padx=7)
        self.library_summary = tk.StringVar(value='Carregando miniaturas...')
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
        self.library_scroll.bind('<Configure>', lambda e: self.library_scroll.itemconfigure(
                               self.library_scroll_id, width=e.width))
        self.library_scroll.bind('<Enter>', lambda e: self.bind_all('<MouseWheel>', self._scroll_wheel))
        self.library_scroll.bind('<Leave>', lambda e: self.unbind_all('<MouseWheel>'))

    def refresh_library(self):
        if not hasattr(self, 'library_frame'):
            return
        for widget in self.library_frame.winfo_children():
            widget.destroy()
        self.library_image_refs = []
        self.library_entries = scan_library(self.target.get(), max_items=100)
        ready = sum(bool(item.tsmod) for item in self.library_entries)
        self.library_summary.set(f'{len(self.library_entries)} projetos    •    {ready} miniaturas .tsMod prontas')
        if not self.library_entries:
            canvas = tk.Frame(self.library_frame, bg=PANEL, highlightbackground=legacy.BORDER,
                              highlightthickness=1)
            canvas.pack(fill='x', pady=12, padx=6)
            tk.Label(canvas, text='✦  Sua biblioteca começa aqui', bg=PANEL, fg=FG,
                     font=('Segoe UI', 15, 'bold')).pack(pady=(25, 8))
            tk.Label(canvas, text='Converta seu primeiro personagem na aba Início rápido.\n'
                                  'As miniaturas vão aparecer aqui automaticamente.',
                     bg=PANEL, fg=MUTED, font=('Segoe UI', 10), justify='center').pack(pady=(0, 26))
        for item in self.library_entries:
            self._library_row(item)

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
        'version': '2.0.2',
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
            print('Astronyx Mini Forge Studio 2.0.2')
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
