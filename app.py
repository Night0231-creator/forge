"""Astronyx Mini Forge v1.7 — local Meshy to TaleSpire workflow.
Python stdlib UI. Requires separately installed Blender for 3D conversion.
"""
from __future__ import annotations

import json
import math
import os
import queue
import shutil
import subprocess
import sys
import tempfile
import threading
import tkinter as tk
import webbrowser
import zipfile
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from core.helpers import (SUPPORTED, create_instructions, find_blender,
                          safe_slug, validate_config, write_manifest)
from core.tsmod import guess_talespire_content_folder, inspect_tsmod, install_tsmod
from core.discovery import tool_status
from core.archive import extract_meshy_zip
from core.preview import ObjViewer
from core.geometry import inspect_obj, suggest_factor
from core.scale_audit import audit_scale
from core.quality_notes import quality_notes
from core.preferences import load_preferences, open_output_folder, save_preferences
from core.taleweavercmd import find_taleweavercmd, nearby_readme, run_taleweavercmd

BASE = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent))
ACCENT = '#A673FF'
ACCENT2 = '#6F44CF'
BG = '#0B0D15'
PANEL = '#151827'
FIELD = '#23263A'
FG = '#F1F2FC'
MUTED = '#A2A5BF'
BORDER = '#34364E'
GREEN = '#4DE0B3'


def user_config_file() -> Path:
    loc = Path(os.environ.get('LOCALAPPDATA', str(Path.home()))) / 'AstronyxMiniForge'
    loc.mkdir(parents=True, exist_ok=True)
    return loc / 'settings.json'


class Forge(tk.Tk):
    viewer_class = ObjViewer  # Subclasses can replace the GUI preview; exporter untouched.
    def __init__(self):
        super().__init__()
        self.title('Astronyx Mini Forge · Meshy para TaleSpire')
        self.geometry('1000x865')
        self.minsize(820, 670)
        self.configure(bg=BG)
        self.log_events: queue.Queue[tuple] = queue.Queue()
        self.worker: threading.Thread | None = None
        self.process: subprocess.Popen | None = None
        self.busy = False
        self.last_output: Path | None = None
        self.config_file = user_config_file()
        stored = load_preferences(self.config_file)
        default_root = Path.home() / 'Documents' / 'Astronyx Minis'
        self.source = tk.StringVar(value='')
        self.target = tk.StringVar(value=stored['output_root'] or str(default_root))
        self.blender = tk.StringVar(value=stored['blender'] or find_blender() or '')
        self.cmd_enabled = tk.BooleanVar(value=stored['cmd_enabled'] if self.config_file.exists() else True)
        self.cmd_executable = tk.StringVar(value=stored['cmd_executable'] or find_taleweavercmd() or '')
        self.name = tk.StringVar(value='')
        self.auto_open = tk.BooleanVar(value=stored['open_after_conversion'])
        self.install_after = tk.BooleanVar(value=stored['install_after_conversion'])
        self.output_preview = tk.StringVar(value='')
        self.name.trace_add('write', lambda *_: self._update_output_preview())
        self.target.trace_add('write', lambda *_: self._update_output_preview())
        self._update_output_preview()
        self.scale_factor = tk.StringVar(value=str(stored.get('scale_factor', '1')))
        self.auto_scale = tk.BooleanVar(value=stored.get('auto_scale', True))
        self.target_height = tk.StringVar(value=stored.get('target_height','1.75'))
        self.quality = tk.StringVar(value='Alta')
        self.preview_info = tk.StringVar(value='Converta um modelo ou abra o OBJ preparado.')
        self._thumbnail_img = None
        self.height = tk.StringVar(value='1.75')
        self.rotation = tk.StringVar(value='0')
        self.tris = tk.StringVar(value='100000')
        self.resolution = tk.StringVar(value='2048')
        self.plugin = tk.BooleanVar(value=True)
        self.tsmod_file = tk.StringVar(value='')
        self.tsmod_folder = tk.StringVar(value=str(stored.get('tsmod_folder') or guess_talespire_content_folder() or ''))
        self.tsmod_details = tk.StringVar(value='Selecione um arquivo .tsMod para verificar sua origem.')
        self.progress = tk.IntVar(value=0)
        self.message = tk.StringVar(value='Pronto para preparar sua primeira miniatura.')
        self.quick_status = tk.StringVar(value='Verificando programas...')
        self.blender.trace_add('write', lambda *_: self._refresh_quick_status())
        self.cmd_executable.trace_add('write', lambda *_: self._refresh_quick_status())
        self._style()
        self._draw()
        self._refresh_quick_status()
        self.protocol('WM_DELETE_WINDOW', self._close)
        self._read_job = self.after(100, self._read_log)

    def _style(self):
        style = ttk.Style(self)
        style.theme_use('clam')
        style.configure('TNotebook', background=BG, borderwidth=0)
        style.configure('TNotebook.Tab', background=PANEL, foreground=MUTED, padding=(22, 11), font=('Segoe UI', 10, 'bold'))
        style.map('TNotebook.Tab', background=[('selected', ACCENT2)], foreground=[('selected', '#FFFFFF')])
        style.configure('TEntry', fieldbackground=FIELD, foreground=FG, background=FIELD,
                        insertcolor=FG, bordercolor=BORDER, lightcolor=BORDER,
                        relief='flat', padding=(9, 9), font=('Segoe UI', 10))
        style.configure('TCombobox', fieldbackground=FIELD, background=FIELD, foreground=FG,
                        selectbackground=FIELD, selectforeground=FG, bordercolor=BORDER,
                        arrowsize=16, padding=8, font=('Segoe UI', 10))
        style.map('TCombobox', fieldbackground=[('readonly', FIELD)], foreground=[('readonly', FG)])
        style.configure('TCheckbutton', background=PANEL, foreground=FG, font=('Segoe UI', 10))
        style.map('TCheckbutton', background=[('active', PANEL)], foreground=[('active', FG)])
        style.configure('Forge.Horizontal.TProgressbar', thickness=12, background=ACCENT,
                        troughcolor=FIELD, borderwidth=0)

    def _label(self, parent, txt, **kw):
        return tk.Label(parent, text=txt, bg=kw.get('bg', PANEL), fg=kw.get('fg', MUTED),
                        font=kw.get('font', ('Segoe UI', 9, 'bold')),
                        anchor=kw.get('anchor', 'w'), justify='left', wraplength=kw.get('wraplength', 750))

    def _button(self, parent, text, command, accent=False, **kw):
        background = ACCENT2 if accent else FIELD
        btn = tk.Button(parent, text=text, command=command, bg=background, fg=FG,
                        activebackground=ACCENT if accent else BORDER, activeforeground='#FFF',
                        relief='flat', bd=0, padx=kw.get('padx', 16), pady=kw.get('pady', 10),
                        font=('Segoe UI', 10, 'bold'), cursor='hand2')
        return btn

    def _draw(self):
        header = tk.Canvas(self, height=116, highlightthickness=0, bg='#100F20')
        header.pack(fill='x')
        header.create_rectangle(0, 0, 1200, 6, fill=ACCENT, outline='')
        header.create_oval(735, -140, 1120, 230, fill='#1C1643', outline='')
        header.create_oval(835, -70, 1120, 205, fill='#271A5E', outline='')
        header.create_text(31, 35, anchor='w', text='ASTRONYX  /  MINI FORGE',
                           fill=FG, font=('Segoe UI', 24, 'bold'))
        header.create_text(34, 78, anchor='w', text='MESHY AI  →  BLENDER  →  TALEWEAVERCMD  →  TALESPIRE',
                           fill='#BAA8E8', font=('Segoe UI', 10, 'bold'))
        header.create_text(935, 92, anchor='e', text='VERSÃO 2.2.2  •  WINDOWS',
                           fill='#C3B5F3', font=('Segoe UI', 9, 'bold'))
        content = tk.Frame(self, bg=BG)
        content.pack(fill='both', expand=True, padx=22, pady=(14, 12))
        self.tabs = ttk.Notebook(content)
        self.tabs.pack(fill='both', expand=True)
        self.tab_quick = tk.Frame(self.tabs, bg=BG)
        self.tab_conv = tk.Frame(self.tabs, bg=BG)
        self.tab_guide = tk.Frame(self.tabs, bg=BG)
        self.tab_tsmod = tk.Frame(self.tabs, bg=BG)
        self.tab_cmd = tk.Frame(self.tabs, bg=BG)
        self.tab_preview = tk.Frame(self.tabs, bg=BG)
        self.tabs.add(self.tab_quick, text='  INÍCIO RÁPIDO  ')
        self.tabs.add(self.tab_conv, text='  AJUSTES AVANÇADOS  ')
        self.tabs.add(self.tab_preview, text='  PRÉVIA 3D  ')
        self.tabs.add(self.tab_cmd, text='  GERAR .TSMOD  ')
        self.tabs.add(self.tab_tsmod, text='  INSTALAR .TSMOD  ')
        self.tabs.add(self.tab_guide, text='  COMO USAR  ')
        # Scrollable conversion area keeps every control usable on smaller monitors.
        self.convert_canvas = tk.Canvas(self.tab_conv, bg=BG, highlightthickness=0)
        self.convert_scroll = tk.Scrollbar(self.tab_conv, orient='vertical',
                                           command=self.convert_canvas.yview)
        self.convert_canvas.configure(yscrollcommand=self.convert_scroll.set)
        self.convert_scroll.pack(side='right', fill='y')
        self.convert_canvas.pack(side='left', fill='both', expand=True)
        self.converter_inner = tk.Frame(self.convert_canvas, bg=BG)
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
        self._label(self, 'Astronyx Mini Forge é independente; não é uma ferramenta oficial da Bouncyrock, Meshy ou TaleSpire.',
                    bg=BG, fg='#7C829E', font=('Segoe UI', 9)).pack(side='bottom', anchor='center', pady=(0, 7))

    def _card(self, parent, heading):
        outer = tk.Frame(parent, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
        title = tk.Frame(outer, bg=PANEL)
        title.pack(fill='x', padx=17, pady=(12, 7))
        self._label(title, heading, fg=FG, font=('Segoe UI', 11, 'bold')).pack(anchor='w')
        body = tk.Frame(outer, bg=PANEL)
        body.pack(fill='x', padx=17, pady=(0, 13))
        return outer, body

    def _field(self, parent, label, var, browse=None, width=None):
        self._label(parent, label).pack(anchor='w', pady=(4, 5))
        line = tk.Frame(parent, bg=PANEL)
        line.pack(fill='x', pady=(0, 7))
        entry = ttk.Entry(line, textvariable=var, width=width)
        entry.pack(side='left', fill='x', expand=True)
        if browse:
            self._button(line, 'Procurar', browse, padx=14, pady=8).pack(side='left', padx=(8, 0))
        return entry

    def _draw_quick(self):
        """Beginner workflow using the same state and conversion pipeline as advanced view."""
        self.quick_canvas = tk.Canvas(self.tab_quick, bg=BG, highlightthickness=0)
        quick_scroll = tk.Scrollbar(self.tab_quick, orient='vertical', command=self.quick_canvas.yview)
        self.quick_canvas.configure(yscrollcommand=quick_scroll.set)
        quick_scroll.pack(side='right', fill='y')
        self.quick_canvas.pack(side='left', fill='both', expand=True)
        shell = tk.Frame(self.quick_canvas, bg=BG)
        window_id = self.quick_canvas.create_window((0, 0), window=shell, anchor='nw')
        shell.bind('<Configure>', lambda e: self.quick_canvas.configure(scrollregion=self.quick_canvas.bbox('all')))
        self.quick_canvas.bind('<Configure>', lambda e: self.quick_canvas.itemconfigure(window_id, width=max(100, e.width - 20)))
        self.quick_canvas.bind('<Enter>', lambda e: self.bind_all('<MouseWheel>', self._scroll_wheel))
        self.quick_canvas.bind('<Leave>', lambda e: self.unbind_all('<MouseWheel>'))

        top = tk.Frame(shell, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
        top.pack(fill='x', pady=(0, 10))
        self._label(top, 'CRIAR UMA MINIATURA PARA TALESPIRE', fg=FG,
                    font=('Segoe UI', 17, 'bold')).pack(anchor='w', padx=19, pady=(17, 4))
        self._label(top, 'Selecione o modelo do Meshy e clique em converter. '
                    'Os programas serão detectados automaticamente. Arquivos .ZIP também funcionam.',
                    fg=MUTED, wraplength=840, font=('Segoe UI', 10)).pack(anchor='w', padx=19, pady=(0, 16))

        card, body = self._card(shell, '01  ·  Seu personagem do Meshy')
        card.pack(fill='x', pady=(0, 10))
        self._field(body, 'ARQUIVO .BLEND / .GLB / .FBX / .OBJ / .ZIP', self.source, self._pick_source)
        self._field(body, 'NOME DA MINIATURA', self.name)
        self._field(body, 'PASTA ONDE SALVAR', self.target, self._pick_target)

        card, body = self._card(shell, '02  ·  Programas necessários')
        card.pack(fill='x', pady=(0, 10))
        tk.Label(body, textvariable=self.quick_status, bg=PANEL, fg=FG,
                 font=('Segoe UI', 10), justify='left', anchor='w', wraplength=780).pack(fill='x', pady=(1, 11))
        buttons = tk.Frame(body, bg=PANEL)
        buttons.pack(anchor='w')
        self._button(buttons, 'Detectar novamente', self._detect_required, padx=11, pady=7).pack(side='left', padx=(0, 8))
        self._button(buttons, 'Indicar Blender', self._pick_blender, padx=11, pady=7).pack(side='left', padx=(0, 8))
        self._button(buttons, 'Indicar TaleWeaverCmd', self._pick_cmd, padx=11, pady=7).pack(side='left')

        card, body = self._card(shell, '03  ·  Criar miniatura')
        card.pack(fill='x', pady=(0, 6))
        self._label(body, 'Tamanho inicial de humanoide: 1,75 unidade (escala 1x). Evite valores como 14: '
                    'eles podem fazer o jogo tratar o personagem como gigante. Ajuste em GERAR .TSMOD.',
                    fg=MUTED, wraplength=805, font=('Segoe UI', 9)).pack(anchor='w', pady=(3, 12))
        actions = tk.Frame(body, bg=PANEL)
        actions.pack(fill='x')
        self.quick_convert_btn = self._button(actions, 'GERAR MINIATURA .TSMOD', self._start_quick,
                                              accent=True, padx=18, pady=14)
        self.quick_convert_btn.pack(side='left', padx=(0, 10))
        self._button(actions, 'Abrir resultado', self._open_result, padx=13, pady=14).pack(side='left')
        ttk.Progressbar(body, variable=self.progress, maximum=100,
                        style='Forge.Horizontal.TProgressbar').pack(fill='x', pady=(17, 9))
        tk.Label(body, textvariable=self.message, bg=PANEL, fg=FG,
                 font=('Segoe UI', 10), justify='left', anchor='w', wraplength=805).pack(fill='x', pady=(0, 11))
        self._label(body, 'Se acontecer algum erro, use a aba AJUSTES AVANÇADOS para ver o log, '
                    'ou GERAR .TSMOD para repetir somente a última etapa.',
                    fg=MUTED, wraplength=780).pack(anchor='w')

    def _refresh_quick_status(self):
        blender_ok, cmd_ok = tool_status(self.blender.get(), self.cmd_executable.get())
        blender_text = 'Encontrado' if blender_ok else 'NÃO ENCONTRADO — instale ou indique blender.exe'
        cmd_text = 'Encontrado' if cmd_ok else 'NÃO ENCONTRADO — abra pasta Tools do TaleSpire'
        self.quick_status.set(f'Blender: {blender_text}\nTaleWeaverCmd: {cmd_text}')

    def _detect_required(self):
        blender = find_blender()
        cmd = find_taleweavercmd()
        if blender and not Path(self.blender.get()).is_file():
            self.blender.set(blender)
        if cmd and not Path(self.cmd_executable.get()).is_file():
            self.cmd_executable.set(cmd)
        self._refresh_quick_status()
        self._save_settings()
        if not all(tool_status(self.blender.get(), self.cmd_executable.get())):
            messagebox.showinfo('Configuração inicial',
                'É necessário instalar o Blender e ter TaleSpire instalado pela Steam.\n\n'
                'Caso os programas não sejam detectados, clique em Indicar Blender ou Indicar TaleWeaverCmd.')

    def _start_quick(self):
        # The beginner workflow always attempts a genuine .tsMod; never silently
        # declare success after producing only OBJ/texture files.
        blender_ok, cmd_ok = tool_status(self.blender.get(), self.cmd_executable.get())
        if not blender_ok or not cmd_ok:
            self._detect_required()
            blender_ok, cmd_ok = tool_status(self.blender.get(), self.cmd_executable.get())
            if not blender_ok or not cmd_ok:
                return
        self.cmd_enabled.set(True)
        self.auto_scale.set(True)
        self._run()

    def _draw_converter(self):
        first, body = self._card(self.converter_inner, '01  ·  Modelo e destinos')
        first.pack(fill='x', pady=(13, 11), padx=(3, 3))
        self._field(body, 'PERSONAGEM DO MESHY  ·  .BLEND / .GLB / .GLTF / .FBX / .OBJ / .STL / .ZIP', self.source, self._pick_source)
        test_btn = self._button(body, 'Usar guerreiro de exemplo (GLB)', self._use_example, padx=11, pady=5)
        test_btn.pack(anchor='w', pady=(0, 6))
        self._field(body, 'NOME DA MINIATURA', self.name)
        self._label(body, 'ESCOLHA ONDE SALVAR OS ARQUIVOS CONVERTIDOS', fg=ACCENT).pack(anchor='w', pady=(6, 5))
        destination_row = tk.Frame(body, bg=PANEL)
        destination_row.pack(fill='x', pady=(0, 7))
        ttk.Entry(destination_row, textvariable=self.target).pack(side='left', fill='x', expand=True)
        self._button(destination_row, 'ESCOLHER PASTA', self._pick_target, accent=True,
                     padx=12, pady=8).pack(side='left', padx=(8, 0))
        self._button(destination_row, 'Abrir pasta', self._open_destination,
                     padx=12, pady=8).pack(side='left', padx=(8, 0))
        self._label(body, 'PASTA FINAL DO PERSONAGEM', fg=MUTED).pack(anchor='w', pady=(5, 2))
        tk.Label(body, textvariable=self.output_preview, bg=PANEL, fg=GREEN,
                 font=('Segoe UI', 9), anchor='w', justify='left', wraplength=800).pack(fill='x', pady=(0, 7))
        ttk.Checkbutton(body,
            text='Abrir automaticamente a pasta com os arquivos quando a conversão terminar',
            variable=self.auto_open, command=self._save_settings).pack(anchor='w', pady=(4, 13))
        ttk.Checkbutton(body,text='Instalar automaticamente o .tsMod no TaleSpire quando a conversão funcionar',
            variable=self.install_after, command=self._save_settings).pack(anchor='w',pady=(1,12))
        self._field(body, 'EXECUTÁVEL DO BLENDER  ·  NECESSÁRIO PARA CONVERSÃO', self.blender, self._pick_blender)

        second, body = self._card(self.converter_inner, '02  ·  Ajustes de modelagem')
        second.pack(fill='x', pady=(0, 11), padx=3)
        row = tk.Frame(body, bg=PANEL)
        row.pack(fill='x')
        settings = [
            ('ALTURA (UNIDADES)', self.height, '1.75'),
            ('GIRAR EM Z (GRAUS)', self.rotation, '0'),
            ('MÁX. TRIÂNGULOS', self.tris, '100000'),
        ]
        for index, (title, variable, default) in enumerate(settings):
            cell = tk.Frame(row, bg=PANEL)
            cell.pack(side='left', fill='x', expand=True, padx=(0 if index == 0 else 12, 0))
            self._label(cell, title).pack(anchor='w', pady=(2, 5))
            ttk.Entry(cell, textvariable=variable, width=12).pack(fill='x')
        options = tk.Frame(body, bg=PANEL)
        options.pack(fill='x', pady=(13, 0))
        self._label(options, 'RESOLUÇÃO DAS TEXTURAS').pack(side='left', padx=(0, 12))
        ttk.Combobox(options, textvariable=self.resolution, values=('512', '1024', '2048', '4096'),
                     state='readonly', width=7).pack(side='left', padx=(0, 17))
        ttk.Checkbutton(options, text='Exportar também para CustomMiniPlugin (com mod)',
                        variable=self.plugin).pack(side='left')
        quality_line = tk.Frame(body, bg=PANEL)
        quality_line.pack(fill='x', pady=(13, 0))
        self._label(quality_line,'PERFIL DE QUALIDADE').pack(side='left',padx=(0,12))
        combo=ttk.Combobox(quality_line, textvariable=self.quality, values=('Leve','Equilibrado','Alta','Ultra'),state='readonly',width=15)
        combo.pack(side='left')
        combo.bind('<<ComboboxSelected>>', self._apply_quality)
        self._label(quality_line,'(preenche triângulos e resolução; você ainda pode personalizar)',fg=MUTED).pack(side='left',padx=12)
        self._label(body, 'A malha será centralizada, alinhada ao chão, triangulada e otimizada. ' 
                    'Edição detalhada de rosto, corpo e acessórios é feita no Blender.',
                    fg=MUTED, wraplength=900,
                    font=('Segoe UI', 9)).pack(anchor='w', pady=(11, 2))

        third, body = self._card(self.converter_inner, '03  ·  Converter e acompanhar')
        third.pack(fill='both', expand=True, pady=(0, 2), padx=3)
        row = tk.Frame(body, bg=PANEL)
        row.pack(fill='x')
        self.convert_btn = self._button(row, 'INICIAR CONVERSÃO', self._run, accent=True, padx=18)
        self.convert_btn.pack(side='left', padx=(0, 10))
        self.cancel_btn = self._button(row, 'Cancelar', self._cancel, padx=14)
        self.cancel_btn.config(state='disabled')
        self.cancel_btn.pack(side='left', padx=(0, 10))
        self._button(row, 'Abrir resultado', self._open_result).pack(side='right')
        self._button(row, 'Prévia 3D', self._preview_last, padx=10).pack(side='right', padx=8)
        ttk.Progressbar(body, variable=self.progress, maximum=100,
                        style='Forge.Horizontal.TProgressbar').pack(fill='x', pady=(14, 7))
        self._label(body, 'STATUS', fg=ACCENT, font=('Segoe UI', 9, 'bold')).pack(anchor='w')
        self._label(body, '', fg=FG, font=('Segoe UI', 9)).pack_forget()
        tk.Label(body, textvariable=self.message, fg=FG, bg=PANEL,
                 font=('Segoe UI', 10), anchor='w', justify='left').pack(fill='x', pady=(2, 9))
        self.console = tk.Text(body, height=5, bg='#0F1220', fg='#A6E5D8', bd=0,
                               highlightthickness=0, font=('Consolas', 9), state='disabled', wrap='word',
                               padx=12, pady=9)
        self.console.pack(fill='both', expand=True)

    def _scroll_wheel(self, event):
        if self.tabs.select() == str(self.tab_conv):
            self.convert_canvas.yview_scroll(-int(event.delta / 120), 'units')
        elif self.tabs.select() == str(self.tab_quick):
            self.quick_canvas.yview_scroll(-int(event.delta / 120), 'units')

    def _apply_quality(self, _event=None):
        faces, resolution = {'Leve': ('18000','1024'),
                             'Equilibrado': ('45000','2048'),
                             'Alta': ('100000','2048'),
                             'Ultra': ('120000','4096')}[self.quality.get()]
        self.tris.set(faces)
        self.resolution.set(resolution)

    def _draw_preview(self):
        holder = tk.Frame(self.tab_preview,bg=BG)
        holder.pack(fill='both',expand=True,padx=9,pady=12)
        top = tk.Frame(holder,bg=BG)
        top.pack(fill='x',pady=(0,10))
        self._button(top,'Abrir OBJ preparado',self._choose_preview_obj,accent=True).pack(side='left',padx=(0,8))
        self._button(top,'Último personagem',self._preview_last).pack(side='left',padx=(0,8))
        self._button(top,'Restaurar câmera',lambda: self.viewer.reset()).pack(side='left')
        self._label(holder,'Prévia geométrica 3D (sem texturas). Gire com o mouse e use a roda para zoom. '
                          'O retrato ao lado é renderizado pelo Blender com as texturas.',
                    bg=BG,wraplength=850).pack(anchor='w',pady=(0,10))
        cols = tk.Frame(holder,bg=BG)
        cols.pack(fill='both',expand=True)
        self.viewer = self.viewer_class(cols,width=530,height=460)
        self.viewer.pack(side='left',fill='both',expand=True)
        side = tk.Frame(cols,bg=PANEL,width=290)
        side.pack(side='right',fill='y',padx=(10,0))
        side.pack_propagate(False)
        self._label(side,'THUMBNAIL',fg=FG).pack(anchor='w',padx=12,pady=(15,8))
        self.thumbnail_label=tk.Label(side,text='Aguardando arquivo',bg='#0F1220',fg=MUTED,width=32,height=15)
        self.thumbnail_label.pack(padx=12)
        self._label(side,'DETALHES DA MALHA',fg=FG).pack(anchor='w',padx=12,pady=(20,8))
        tk.Label(side,textvariable=self.preview_info,bg=PANEL,fg=MUTED,
                 justify='left',anchor='nw',wraplength=255,font=('Segoe UI',10)).pack(fill='x',padx=12)
        self._label(holder,'O tamanho recomendado é uma estimativa baseada no seu teste, não uma '
                  'escala oficial. Confira a miniatura no TaleSpire.',bg=BG,wraplength=900).pack(anchor='w',pady=(10,0))

    def _choose_preview_obj(self):
        filename=filedialog.askopenfilename(title='Selecione o OBJ preparado',
                 filetypes=[('Modelo OBJ','*.obj'),('Todos','*.*')])
        if filename:
            self._load_preview(Path(filename))

    def _preview_last(self):
        folder=self.last_output
        if not folder:
            root=Path(self.target.get().strip().strip('"')).expanduser()
            folder=root/safe_slug(self.name.get())
        obj=folder/'TaleWeaverCmd_Source'/(folder.name+'.obj')
        if not obj.is_file():
            messagebox.showinfo('Prévia 3D','Converta o personagem primeiro ou selecione um OBJ preparado.')
            return
        self._load_preview(obj)

    def _load_preview(self,obj):
        try:
            self.viewer.open(obj)
            stats=self.viewer.stats
            try:
                suggested=f'{suggest_factor(stats.height,1.75):.2f}x'
            except ValueError:
                suggested='fora do intervalo automático'
            text=(f'{stats.vertices:,} vértices\n{stats.faces:,} faces\n'
                  f'Altura preparada: {stats.height:.2f} un.\n'
                  f'Tamanho humano sugerido: {suggested}')
            self.preview_info.set(text)
            thumb=obj.parent/'thumbnail.png'
            if thumb.is_file():
                pic=tk.PhotoImage(file=str(thumb))
                size=max(1,math.ceil(max(pic.width(),pic.height())/256))
                self._thumbnail_img=pic.subsample(size,size)
                self.thumbnail_label.config(image=self._thumbnail_img,text='',width=256,height=256)
            else:
                self._thumbnail_img=None
                self.thumbnail_label.config(image='',text='Miniatura PNG ainda não gerada')
            self.tabs.select(self.tab_preview)
        except (OSError,ValueError,tk.TclError) as error:
            messagebox.showerror('Não foi possível abrir prévia',str(error))

    def _draw_guide(self):
        box, body = self._card(self.tab_guide, 'Guia rápido  ·  Meshy → TaleSpire')
        box.pack(fill='both', expand=True, padx=5, pady=17)
        lines = [
            ('1. Exporte do Meshy', 'Escolha um .blend, GLB/FBX/OBJ ou ZIP exportado pelo Meshy. Arquivos ZIP com modelo e texturas são extraídos automaticamente.'),
            ('2. Instale Blender', 'O Mini Forge usa Blender em segundo plano para converter geometria e gerar texturas. Instale o Blender gratuito e aponte para blender.exe.'),
            ('3. Gere o personagem', 'Na aba INÍCIO RÁPIDO, escolha o modelo, o nome e a pasta. Clique GERAR MINIATURA .TSMOD. Para configurações mais detalhadas, use AJUSTES AVANÇADOS.'),
            ('4. TaleWeaverCmd: configure uma vez', 'No TaleSpire instalado pela Steam, procure Tools/TaleWeaverCmd/Windows. Na aba GERAR .TSMOD, escolha TaleWeaverCmd.exe. O Mini Forge cria params.json e configura automaticamente o comando -srcDir.'),
            ('5. Entre no TaleSpire', 'No jogo: Settings → Open Settings Directory → LocalContentPacks. Copie o .tsMod salvo, depois localize a mini no navegador de criaturas.'),
            ('Sem pagar conversão', 'O processamento é local, com Blender gratuito e TaleWeaverCmd incluído no TaleSpire. Não precisa de assinatura de conversão. Os pontos de efeitos são estimados automaticamente para personagens em pé.'),
            ('Instalar .tsMod já pronto', 'Use a aba INSTALAR .TSMOD para conferir o cabeçalho e copiar o arquivo para LocalContentPacks. O TaleSpire precisa estar instalado.'),
        ]
        for heading, content in lines:
            self._label(body, heading, fg=ACCENT, font=('Segoe UI', 11, 'bold')).pack(anchor='w', pady=(9, 1))
            self._label(body, content, fg=FG, font=('Segoe UI', 10), wraplength=790).pack(anchor='w', pady=(0, 7))
        buttons = tk.Frame(body, bg=PANEL)
        buttons.pack(fill='x', pady=(16, 3))
        self._button(buttons, 'TaleWeaverLite oficial ↗', lambda: webbrowser.open('https://talespire.com/taleweaverlite-install-guide'),
                     accent=True).pack(side='left', padx=(0, 9))
        self._button(buttons, 'Blender ↗', lambda: webbrowser.open('https://www.blender.org/download/')).pack(side='left', padx=(0, 9))
        self._button(buttons, 'Editar no Blender', self._open_blender).pack(side='left', padx=(0, 9))
        self._button(buttons, 'Basecoat ↗', lambda: webbrowser.open('https://store.steampowered.com/app/4468700/Basecoat_Mini_Painting_Studio/')).pack(side='left')

    def _draw_tsmod(self):
        card, body = self._card(self.tab_tsmod, 'Arquivo .tsMod pronto para o TaleSpire')
        card.pack(fill='both', expand=True, padx=5, pady=17)
        self._label(body, 'Analise seu .tsMod e instale na pasta oficial LocalContentPacks.',
                    fg=FG, font=('Segoe UI', 10)).pack(anchor='w', pady=(1, 18))
        self._field(body, 'ARQUIVO .TSMOD', self.tsmod_file, self._choose_tsmod)
        self._button(body, 'Verificar arquivo', self._inspect_tsmod, accent=True).pack(anchor='w', pady=(4, 12))
        tk.Label(body, textvariable=self.tsmod_details, bg='#0F1220', fg=FG,
                 justify='left', anchor='nw', wraplength=700,
                 font=('Consolas', 10), padx=14, pady=14).pack(fill='x', pady=(0, 17))
        self._field(body, 'PASTA LOCALCONTENTPACKS DO TALESPIRE',
                    self.tsmod_folder, self._choose_tsmod_folder)
        self._label(body, 'Dica: no TaleSpire, abra Settings → Open Settings Directory, depois LocalContentPacks. '
                    'Selecione essa pasta acima se não for detectada automaticamente.',
                    fg=MUTED, wraplength=780).pack(anchor='w', pady=(3, 12))
        self._button(body, 'INSTALAR NO TALESPIRE', self._install_tsmod,
                     accent=True).pack(anchor='w', pady=(2, 15))
        self._label(body, 'O arquivo de origem é preservado. Ao substituir um existente, '
                    'uma cópia de segurança é criada. Reconhecer o cabeçalho não garante '
                    'que a miniatura abrirá no jogo.', fg=MUTED,
                    wraplength=780).pack(anchor='w')

    def _draw_cmd_setup(self):
        card, body = self._card(self.tab_cmd, 'TaleWeaverCmd  ·  exportação oficial automática')
        card.pack(fill='both', expand=True, padx=5, pady=16)
        self._label(body,
            'Integração configurada usando o README.txt oficial! O Mini Forge gera model.obj, '
            'quatro texturas PNG e params.json, e executa -srcDir automaticamente.',
            fg=GREEN, font=('Segoe UI', 11, 'bold'), wraplength=850).pack(anchor='w', pady=(3, 16))
        ttk.Checkbutton(body, text='Gerar .tsMod automaticamente após preparar o personagem',
                        variable=self.cmd_enabled, command=self._save_settings).pack(anchor='w', pady=(0, 14))
        self._field(body, 'LOCALIZE O TALEWEAVERCMD.EXE DO SEU TALESPIRE',
                    self.cmd_executable, self._pick_cmd)
        self._label(body,'ESCALA AUTOMÁTICA (referência visual, não valor oficial)',fg=ACCENT).pack(anchor='w',pady=(6,5))
        ttk.Checkbutton(body,text='Ativar ajuste automático pela altura do personagem',
                        variable=self.auto_scale,command=self._save_settings).pack(anchor='w',pady=(0,8))
        refrow=tk.Frame(body,bg=PANEL)
        refrow.pack(fill='x',pady=(0,12))
        self._label(refrow,'ALTURA ALVO NO TALESPIRE').pack(side='left',padx=(0,12))
        ref=ttk.Combobox(refrow,textvariable=self.target_height,values=('1.25','1.75','2','2.5','3.5'),width=9)
        ref.pack(side='left')
        ref.bind('<<ComboboxSelected>>',lambda _e:self._save_settings())
        self._label(refrow,'1,75 = ponto inicial humanoide; confira o resultado dentro do TaleSpire',fg=MUTED).pack(side='left',padx=12)
        self._label(body, 'MULTIPLICADOR MANUAL (usado se desmarcar escala automática)', fg=ACCENT).pack(anchor='w', pady=(6, 5))
        choices = ttk.Combobox(body, textvariable=self.scale_factor, values=('0.75', '1', '1.25', '1.5', '2', '2.5', '3', '4'), width=12)
        choices.pack(anchor='w', pady=(0, 4))
        choices.bind('<<ComboboxSelected>>', lambda _event: self._save_settings())
        self._label(body, 'No modo manual, comece em 1x e aumente em passos pequenos, como 1,25x. '
                    'Evite 8x: o TaleSpire pode tratar a miniatura como gigante.',
                    fg=MUTED, wraplength=840).pack(anchor='w', pady=(0, 15))
        toolbar = tk.Frame(body, bg=PANEL)
        toolbar.pack(fill='x', pady=(0, 16))
        self._button(toolbar, 'Detectar na Steam', self._detect_cmd, padx=11, pady=8).pack(side='left', padx=(0, 9))
        self._button(toolbar, 'Abrir README.txt', self._show_readme, padx=11, pady=8).pack(side='left')
        self._label(body, 'COMANDO EXECUTADO AUTOMATICAMENTE', fg=ACCENT).pack(anchor='w', pady=(10, 5))
        tk.Label(body, text='TaleWeaverCmd.exe -srcDir "<pasta do personagem>\\Entrada_TaleWeaverCmd"',
                 bg='#0F1220', fg=FG, font=('Consolas', 10), anchor='w',
                 padx=13, pady=12).pack(fill='x', pady=(0, 10))
        self._label(body, 'Pontos Head / Spell / Hit / Torch calculados aproximadamente a partir '
                    'da altura do personagem. Para criaturas muito diferentes de humanoides, '
                    'você pode ajustar Entrada_TaleWeaverCmd/params.json manualmente antes '
                    'de executar novamente. O TaleSpire continua sendo o teste final.',
                    fg=MUTED, font=('Segoe UI', 10), wraplength=840).pack(anchor='w', pady=(0, 19))
        self._button(body, 'Diagnosticar escala 1×1 de uma miniatura preparada',
                     self._diagnose_scale, padx=11, pady=8).pack(anchor='w', pady=(0, 10))
        self._button(body, 'Gerar .tsMod de uma pasta já preparada', self._rerun_cmd,
                     accent=True).pack(anchor='w', pady=(4, 12))
        self._label(body, 'Ao repetir a geração, não é necessário passar pelo Blender outra vez. '
                    'A miniatura .tsMod anterior é preservada em uma cópia .bak. '
                    'O TaleWeaverCmd e o Blender não são distribuídos dentro do Mini Forge.',
                    fg=MUTED, wraplength=850).pack(anchor='w')

    def _pick_cmd(self):
        path = filedialog.askopenfilename(title='Selecione TaleWeaverCmd.exe',
                    filetypes=[('Executáveis', '*.exe'), ('Todos', '*.*')])
        if path:
            self.cmd_executable.set(path)
            self._save_settings()

    def _detect_cmd(self):
        found = find_taleweavercmd()
        if found:
            self.cmd_executable.set(found)
            self._save_settings()
            messagebox.showinfo('Encontrado', found)
        else:
            messagebox.showinfo('Não localizado',
                'Abra Steam → TaleSpire → Gerenciar → Explorar arquivos locais. '
                'Depois procure Tools\\TaleWeaverCmd\\Windows\\TaleWeaverCmd.exe e selecione em Procurar.')

    def _show_readme(self):
        exe = self.cmd_executable.get().strip().strip('"')
        readme = nearby_readme(exe) if exe else None
        if readme:
            try:
                os.startfile(str(readme)) if os.name == 'nt' else open_output_folder(readme.parent)
            except OSError as ex:
                messagebox.showerror('README', str(ex))
        else:
            messagebox.showinfo('README não encontrado',
                'Procure README.txt dentro de Tools\\TaleWeaverCmd\\Windows. '
                'Se não encontrar, envie o arquivo para conferir os argumentos corretos.')

    def _validated_scale(self) -> float:
        import math
        try:
            value = float(self.scale_factor.get().strip().replace(',', '.'))
        except ValueError:
            raise ValueError('Use um numero, por exemplo 1, 8 ou 10.')
        if not math.isfinite(value) or not 0.1 <= value <= 100:
            raise ValueError('Escolha um multiplicador entre 0,1 e 100.')
        return value

    def _auto_height(self):
        if not self.auto_scale.get():
            return None
        try:
            value=float(self.target_height.get().strip().replace(',','.'))
        except ValueError:
            raise ValueError('A altura alvo precisa ser um número: 1,75 ou 2, por exemplo.')
        if not math.isfinite(value) or not 0.5 <= value <= 40:
            raise ValueError('Altura alvo: use um valor entre 0,5 e 40.')
        return value

    def _diagnose_scale(self):
        """Preview the automatic scaling formula; never touch the model."""
        root = Path(self.target.get()).expanduser()
        folder = filedialog.askdirectory(
            title='Pasta da miniatura com TaleWeaverCmd_Source',
            initialdir=str(root) if root.is_dir() else str(Path.home()))
        if not folder:
            return
        destination = Path(folder)
        obj = destination / 'TaleWeaverCmd_Source' / (destination.name + '.obj')
        try:
            target = float(self.target_height.get().strip().replace(',', '.'))
            report = audit_scale(inspect_obj(obj), target)
        except (OSError, ValueError) as exc:
            messagebox.showerror('Não foi possível diagnosticar', str(exc))
            return
        title = ('Escala 1×1: base limita a altura' if report.footprint_limited
                 else 'Escala 1×1: dimensões dentro da referência')
        messagebox.showwarning(title, report.summary()) if report.footprint_limited else messagebox.showinfo(title, report.summary())

    def _rerun_cmd(self):
        if self.busy:
            return
        exe = Path(self.cmd_executable.get().strip().strip('"'))
        if not exe.is_file():
            messagebox.showwarning('Selecione TaleWeaverCmd',
                'Escolha TaleWeaverCmd.exe na pasta de instalação do TaleSpire.')
            return
        root = Path(self.target.get()).expanduser()
        folder = filedialog.askdirectory(
            title='Selecione a pasta do personagem que contém TaleWeaverCmd_Source',
            initialdir=str(root) if root.is_dir() else str(Path.home()))
        if not folder:
            return
        destination = Path(folder)
        if not (destination / 'TaleWeaverCmd_Source' / (destination.name + '.obj')).is_file():
            messagebox.showerror('Pasta incorreta',
                'Selecione a pasta da miniatura gerada pelo Mini Forge, contendo TaleWeaverCmd_Source.')
            return
        height = 1.75
        manifest = destination / 'conversao.json'
        try:
            if manifest.is_file():
                config = json.loads(manifest.read_text(encoding='utf-8'))
                height = float(config.get('settings', {}).get('height', height))
        except (ValueError, OSError, TypeError):
            pass
        try:
            scale_factor = self._validated_scale()
            auto_height = self._auto_height()
        except ValueError as ex:
            messagebox.showerror('Escala inválida', str(ex))
            return
        self._save_settings()
        self.busy = True
        self.progress.set(95)
        self.message.set('Gerando .tsMod sem repetir o processamento 3D...')
        self.convert_btn.config(state='disabled')
        self.quick_convert_btn.config(state='disabled')
        self.cancel_btn.config(state='normal')
        self.worker = threading.Thread(target=self._cmd_only_thread,
            args=(exe, destination, height, scale_factor, auto_height), daemon=True)
        self.worker.start()

    def _cmd_only_thread(self, exe, folder, height, scale_factor, auto_height):
        try:
            result = run_taleweavercmd(exe, folder, folder.name, height, preserve_params=True,
                scale_factor=scale_factor, target_height=auto_height,
                on_line=lambda line: self.log_events.put(('log', '[CMD] ' + line)),
                on_process=lambda proc: setattr(self, 'process', proc))
            self.log_events.put(('success', str(folder), {'vertices': '—', 'triangles': '—'}, str(result)))
        except Exception as ex:
            self.log_events.put(('partial', str(folder), str(ex)))
        finally:
            self.process = None

    def _choose_tsmod(self):
        path = filedialog.askopenfilename(title='Escolha a miniatura pronta',
                 filetypes=[('Miniaturas TaleSpire', '*.tsMod'), ('Todos', '*.*')])
        if path:
            self.tsmod_file.set(path)
            self._inspect_tsmod()

    def _inspect_tsmod(self):
        try:
            result = inspect_tsmod(self.tsmod_file.get().strip().strip('"'))
        except (ValueError, OSError) as error:
            self.tsmod_details.set(f'ERRO: {error}')
            return
        self.tsmod_details.set(
            f'Arquivo: {result["filename"]}\n'
            f'Tamanho: {result["size_mb"]} MB\n'
            f'Cabeçalho conhecido: {"SIM" if result["recognized_header"] else "NÃO"}\n'
            f'Versão (cabeçalho): {result["format_version"] if result["recognized_header"] else "indefinida"}\n'
            f'Exportador: {result["producer"]}\n'
            f'Informação embutida: {result["description"] or "nenhuma identificada"}\n\n'
            f'{result["warning"]}')

    def _choose_tsmod_folder(self):
        folder = filedialog.askdirectory(title='Escolha a pasta LocalContentPacks do TaleSpire')
        if folder:
            self.tsmod_folder.set(folder)
            self._save_settings()

    def _install_tsmod(self):
        file = self.tsmod_file.get().strip().strip('"')
        folder = self.tsmod_folder.get().strip().strip('"')
        try:
            if not file:
                raise ValueError('Selecione um .tsMod primeiro.')
            if not folder:
                raise ValueError('Selecione a pasta LocalContentPacks no TaleSpire.')
            target = Path(folder) / Path(file).name
            replace = False
            if target.is_file() and Path(file).resolve() != target.resolve():
                if not messagebox.askyesno('Arquivo já existe',
                     f'{target.name} já está instalado. Deseja substituir?\n\n'
                     'Uma cópia do arquivo anterior será preservada.'):
                    return
                replace = True
            dest = install_tsmod(file, folder, replace=replace)
            messagebox.showinfo('Miniatura instalada',
                f'Arquivo instalado em:\n{dest}\n\nAbra o TaleSpire e procure a miniatura na biblioteca.')
        except (ValueError, OSError) as error:
            messagebox.showerror('Não foi possível instalar', str(error))

    def _use_example(self):
        sample = BASE / 'assets' / 'exemplo_guerreiro.glb'
        if sample.is_file():
            self.source.set(str(sample))
            self.name.set('Astronyx_Guerreiro_Exemplo')
        else:
            messagebox.showerror('Exemplo não encontrado', str(sample))

    def _pick_source(self):
        result = filedialog.askopenfilename(title='Escolher arquivo 3D do Meshy',
                   filetypes=[('Modelos 3D', '*.blend *.glb *.gltf *.fbx *.obj *.stl *.zip'), ('Todos os arquivos', '*.*')])
        if result:
            self.source.set(result)
            if not self.name.get():
                self.name.set(safe_slug(Path(result).stem))

    def _update_output_preview(self):
        root = self.target.get().strip().strip('"')
        if not root:
            self.output_preview.set('Selecione uma pasta de destino.')
            return
        name = safe_slug(self.name.get() or (Path(self.source.get()).stem if self.source.get() else 'SuaMiniatura'))
        self.output_preview.set(str(Path(root).expanduser() / name))

    def _pick_target(self):
        root = Path(self.target.get().strip().strip('"')).expanduser()
        while not root.is_dir() and root != root.parent:
            root = root.parent
        result = filedialog.askdirectory(title='Escolha onde salvar suas miniaturas',
                                         initialdir=str(root) if root.is_dir() else str(Path.home()))
        if result:
            self.target.set(result)
            self._save_settings()

    def _open_destination(self):
        root = self.target.get().strip().strip('"')
        if not root:
            messagebox.showwarning('Selecione o destino', 'Escolha uma pasta para salvar as miniaturas.')
            return
        try:
            Path(root).expanduser().mkdir(parents=True, exist_ok=True)
            open_output_folder(Path(root))
        except OSError as error:
            messagebox.showerror('Não foi possível abrir a pasta', str(error))

    def _pick_blender(self):
        result = filedialog.askopenfilename(title='Encontre blender.exe',
                    filetypes=[('Blender', 'blender.exe' if os.name == 'nt' else '*'), ('Todos', '*.*')])
        if result:
            self.blender.set(result)

    def _open_blender(self):
        exe = self.blender.get().strip()
        if not Path(exe).is_file():
            messagebox.showinfo('Instale Blender', 'Instale o Blender e escolha o caminho do executável na aba Converter.')
            return
        try:
            subprocess.Popen([exe], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except OSError as ex:
            messagebox.showerror('Blender', str(ex))

    def _open_result(self):
        folder = self.last_output
        if not folder:
            messagebox.showinfo('Resultado', 'Converta um personagem antes de abrir o resultado.')
            return
        try:
            open_output_folder(folder)
        except OSError as error:
            messagebox.showerror('Não foi possível abrir o resultado', str(error))

    def _log(self, line):
        self.console.config(state='normal')
        self.console.insert('end', line + '\n')
        self.console.see('end')
        self.console.config(state='disabled')

    def _save_settings(self):
        try:
            save_preferences(self.config_file, output_root=self.target.get(),
                             blender=self.blender.get(),
                             open_after_conversion=self.auto_open.get(),
                             cmd_enabled=self.cmd_enabled.get(),
                             cmd_executable=self.cmd_executable.get(),
                             scale_factor=self.scale_factor.get(),
                             auto_scale=self.auto_scale.get(), target_height=self.target_height.get(),
                             install_after_conversion=self.install_after.get(),
                             tsmod_folder=self.tsmod_folder.get())
        except OSError:
            pass

    def _run(self):
        if self.busy:
            return
        try:
            cfg = validate_config({
                'source': self.source.get(), 'output_root': self.target.get(),
                'name': self.name.get() or Path(self.source.get()).stem,
                'height': self.height.get().replace(',', '.'),
                'rotation': self.rotation.get().replace(',', '.'),
                'tris': self.tris.get(), 'texture_size': self.resolution.get(),
                'create_plugin': self.plugin.get(),
            })
        except (ValueError, TypeError) as error:
            messagebox.showerror('Verifique os campos', str(error))
            return
        try:
            scale_factor = self._validated_scale()
            auto_height = self._auto_height()
        except ValueError as ex:
            messagebox.showerror('Escala inválida', str(ex))
            return
        exe = self.blender.get().strip().strip('"')
        if not Path(exe).is_file():
            messagebox.showerror('Blender não encontrado', 'Instale Blender, depois escolha blender.exe.\n\nhttps://www.blender.org/download/')
            return
        if self.install_after.get() and not self.cmd_enabled.get():
            messagebox.showwarning('Ative o conversor','Instalação automática exige a geração de .tsMod na aba GERAR .TSMOD.')
            return
        if self.install_after.get() and not Path(self.tsmod_folder.get().strip()).is_dir():
            messagebox.showwarning('LocalContentPacks não localizada',
                'Abra INSTALAR .TSMOD e indique a pasta LocalContentPacks do TaleSpire antes de ativar instalação automática.')
            return
        if self.cmd_enabled.get():
            if not Path(self.cmd_executable.get().strip().strip('"')).is_file():
                self.tabs.select(self.tab_cmd)
                messagebox.showwarning('Configuração TaleWeaverCmd incompleta',
                    'Na aba GERAR .TSMOD, escolha TaleWeaverCmd.exe. Os arquivos e comandos já estão configurados automaticamente.')
                return
        cfg['create_taleweavercmd'] = True
        output = Path(cfg['output_root']) / cfg['name']
        if output.exists() and any(output.iterdir()):
            if not messagebox.askyesno('Pasta já existe',
                'Já existem arquivos com esse nome. Deseja atualizar os arquivos gerados?\n\nOutros arquivos não serão apagados.'):
                return
        self._save_settings()
        self.last_output = None
        self.progress.set(0)
        self.message.set('Iniciando Blender em segundo plano...')
        self.busy = True
        self.convert_btn.config(state='disabled')
        self.cancel_btn.config(state='normal')
        self._log('─' * 44)
        self._log(f'Arquivo: {Path(cfg["source"]).name}')
        self._log(f'Pasta: {output}')
        cmd_setup = {'enabled': self.cmd_enabled.get(), 'exe': self.cmd_executable.get().strip().strip('"'), 'scale_factor': scale_factor, 'auto_height': auto_height,
                    'install_after': self.install_after.get(), 'content_folder': self.tsmod_folder.get().strip()}
        self.worker = threading.Thread(target=self._convert_thread, args=(exe, cfg, cmd_setup), daemon=True)
        self.worker.start()

    def _convert_thread(self, exe, cfg, cmd_setup):
        config_file = None
        archive_tmp = None
        try:
            if Path(cfg['source']).suffix.lower() == '.zip':
                archive_tmp = tempfile.TemporaryDirectory(prefix='astronyx_meshy_')
                original_source = cfg['source']
                extracted = extract_meshy_zip(Path(original_source), Path(archive_tmp.name))
                cfg['source_archive'] = original_source
                cfg['source'] = str(extracted)
                self.log_events.put(('log', 'ZIP extraído: ' + extracted.name))
            with tempfile.NamedTemporaryFile('w', suffix='.json', prefix='amf_',
                                             encoding='utf-8', delete=False) as tmp:
                config_file = tmp.name
                json.dump(cfg, tmp, ensure_ascii=False)
            cmd = [exe, '--background', '--disable-autoexec', '--threads', '4', '--python',
                   str(BASE / 'core' / 'blender_pipeline.py'), '--', config_file]
            self.process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                              stdin=subprocess.DEVNULL, encoding='utf-8', errors='replace',
                              bufsize=1, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            tail = []
            for line in self.process.stdout:
                line = line.strip()
                if line.startswith('AMF_PROGRESS|'):
                    _, number, msg = line.split('|', 2)
                    self.log_events.put(('progress', int(number), msg))
                elif line.startswith('AMF_ERROR|'):
                    self.log_events.put(('log', 'ERRO: ' + line[10:]))
                    tail.append(line)
                elif line.startswith('AMF_WARNING|'):
                    self.log_events.put(('log', 'Aviso: ' + line[12:]))
                else:
                    tail.append(line)
                    if len(tail) > 14:
                        tail.pop(0)
            returncode = self.process.wait()
            if returncode != 0:
                msg = '\n'.join(tail[-7:]).strip() or 'Blender retornou erro.'
                self.log_events.put(('error', msg))
                return
            dest = Path(cfg['output_root']) / cfg['name']
            stats_path = dest / 'blender_stats.json'
            stats = json.loads(stats_path.read_text(encoding='utf-8'))
            for note in quality_notes(stats):
                self.log_events.put(('log', '[QUALIDADE] ' + note))
            create_instructions(dest, cfg['name'], stats)
            write_manifest(dest, cfg, stats)
            stats_path.unlink(missing_ok=True)
            tsmod_path = None
            cmd_error = None
            if cmd_setup['enabled']:
                try:
                    self.log_events.put(('progress', 96, 'Gerando .tsMod com TaleWeaverCmd...'))
                    tsmod_path = run_taleweavercmd(
                        Path(cmd_setup['exe']), dest, cfg['name'], cfg['height'],
                        scale_factor=cmd_setup['scale_factor'], target_height=cmd_setup['auto_height'],
                        on_line=lambda line: self.log_events.put(('log', '[CMD] ' + line)),
                        on_process=lambda proc: setattr(self, 'process', proc))
                    self.log_events.put(('log', 'Arquivo final: ' + str(tsmod_path)))
                    if cmd_setup['install_after']:
                        try:
                            installed=install_tsmod(tsmod_path,cmd_setup['content_folder'],replace=True)
                            self.log_events.put(('log','Instalado no TaleSpire: '+str(installed)))
                        except (ValueError,OSError) as problem:
                            self.log_events.put(('log','AVISO: .tsMod foi gerado, mas a instalação automática falhou: '+str(problem)))
                    manifest_path = dest / 'conversao.json'
                    if manifest_path.is_file():
                        manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
                        manifest['official_tsmod_created'] = True
                        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
                except Exception as error:
                    cmd_error = str(error)
                    self.log_events.put(('log', 'ERRO no TaleWeaverCmd: ' + cmd_error))
            # Portable zip for moving prepared assets and final file if present.

            zip_path = dest / (cfg['name'] + '_ARQUIVOS_PREPARADOS.zip')
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as archive:
                for f in sorted(dest.rglob('*')):
                    if f.is_file() and f != zip_path:
                        archive.write(f, f.relative_to(dest))
            if cmd_error:
                self.log_events.put(('partial', str(dest), cmd_error))
            else:
                self.log_events.put(('success', str(dest), stats, str(tsmod_path) if tsmod_path else ''))
        except Exception as error:
            self.log_events.put(('error', str(error)))
        finally:
            self.process = None
            if archive_tmp is not None:
                archive_tmp.cleanup()
            if config_file:
                try:
                    os.unlink(config_file)
                except OSError:
                    pass

    def _read_log(self):
        try:
            while True:
                item = self.log_events.get_nowait()
                if item[0] == 'progress':
                    _, number, message = item
                    self.progress.set(number)
                    self.message.set(message)
                    self._log(f'[{number:>3}%] {message}')
                elif item[0] == 'log':
                    self._log(item[1])
                elif item[0] == 'success':
                    _, path, stats, tsmod_path = item
                    self.busy = False
                    self.convert_btn.config(state='normal')
                    self.quick_convert_btn.config(state='normal')
                    self.cancel_btn.config(state='disabled')
                    self.last_output = Path(path)
                    self.progress.set(100)
                    self.message.set(f'Concluído! {".tsMod pronto" if tsmod_path else "Arquivos preparados"}: {path}')
                    self._log(f'Concluído: {stats["vertices"]} vértices, {stats["triangles"]} triângulos.')
                    self._log(f'Arquivo .tsMod criado: {tsmod_path}' if tsmod_path else f'Arquivos preparados em: {path} (ainda não é .tsMod).')
                    self._log('Prévia disponível na aba PRÉVIA 3D.')
                    if self.auto_open.get():
                        try:
                            open_output_folder(self.last_output)
                        except OSError as error:
                            self._log(f'A conversão terminou, mas não foi possível abrir a pasta: {error}')
                            messagebox.showwarning('Arquivos preparados',
                                f'Conversão concluída!\n\nAbra a pasta manualmente em:\n{path}\n\n'
                                f'Detalhes: {error}')
                    else:
                        messagebox.showinfo('Miniatura preparada!',
                            f'Arquivos salvos em:\n{path}\n\n'
                            + ('Miniatura .tsMod criada! ' + tsmod_path if tsmod_path else 'Arquivos preparados. Geração .tsMod não foi ativada.'))
                elif item[0] == 'partial':
                    _, path, err = item
                    self.busy = False
                    self.convert_btn.config(state='normal')
                    self.quick_convert_btn.config(state='normal')
                    self.cancel_btn.config(state='disabled')
                    self.last_output = Path(path)
                    self.progress.set(95)
                    self.message.set('Malha preparada. Falhou a etapa de geração .tsMod.')
                    self._log('A etapa final falhou; OBJ e texturas estão preservados.')
                    messagebox.showwarning('Etapa final não concluída',
                        'O Blender preparou os arquivos, mas o TaleWeaverCmd falhou.\n\n'
                        + err[-1800:] + '\n\nPasta: ' + path)
                elif item[0] == 'error':
                    self.busy = False
                    self.convert_btn.config(state='normal')
                    self.quick_convert_btn.config(state='normal')
                    self.cancel_btn.config(state='disabled')
                    self.message.set('Erro durante a conversão; confira o log.')
                    self._log('ERRO: ' + item[1])
                    messagebox.showerror('Não foi possível converter',
                        item[1][-1200:] + '\n\nVerifique a compatibilidade do arquivo no Blender.')
        except queue.Empty:
            pass
        self._read_job = self.after(100, self._read_log)

    def _cancel(self):
        if self.busy and self.process:
            if messagebox.askyesno('Cancelar conversão', 'Deseja interromper o Blender? Arquivos parciais podem permanecer na pasta de saída.'):
                try:
                    self.process.terminate()
                    self.message.set('Conversão interrompida.')
                except OSError:
                    pass

    def _close(self):
        if self.busy:
            messagebox.showwarning('Conversão em andamento', 'Cancele a conversão antes de fechar a ferramenta.')
            return
        self._save_settings()
        self.destroy()

    def destroy(self):
        # Avoid orphaned Tk after-callbacks when users close/reopen the window.
        job = getattr(self, '_read_job', None)
        if job is not None:
            try:
                self.after_cancel(job)
            except tk.TclError:
                pass
            self._read_job = None
        super().destroy()


if __name__ == '__main__':
    Forge().mainloop()
