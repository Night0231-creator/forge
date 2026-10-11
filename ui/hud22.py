"""Astronyx Mini Forge HUD polish.

Presentation-only views: conversion, assets, and project database stay unchanged.
"""
from __future__ import annotations

from datetime import datetime
import tkinter as tk
from tkinter import ttk

from . import theme as t

try:
    from PIL import Image, ImageTk, ImageOps
except ImportError:
    Image = ImageTk = ImageOps = None

BG=t.BG
SURFACE=t.PANEL
SURFACE2=t.RAISED
PURPLE=t.ACCENT
MUTED=t.MUTED
WHITE=t.TEXT
GREEN=t.GREEN


def filter_miniatures(items, query='', status='Todos'):
    key=(query or '').strip().casefold()
    return [x for x in items
            if (not key or key in x.name.replace('_',' ').casefold())
            and (status != 'Prontos' or bool(x.tsmod))
            and (status != 'Em preparação' or not x.tsmod)]


def action(parent, label, command, primary=False):
    return t.hover_button(parent,label,command,primary=primary)


def _label(parent,text,*,bg=SURFACE,fg=WHITE,size=10,bold=False,**kw):
    return tk.Label(parent,text=text,bg=bg,fg=fg,
                    font=('Segoe UI',size,'bold' if bold else 'normal'),**kw)


def _card(parent,fill='x',**pack_opts):
    outer=tk.Frame(parent,bg=t.BORDER)
    outer.pack(fill=fill,**pack_opts)
    inner=tk.Frame(outer,bg=SURFACE)
    inner.pack(fill='both',expand=True,padx=1,pady=1)
    return inner


def dashboard(app):
    """Essentials-first home: one import, one conversion button, clear progress."""
    shell=tk.Frame(app.tab_dashboard,bg=BG)
    shell.pack(fill='both',expand=True,padx=20,pady=13)

    hero=_card(shell,pady=(0,13))
    copy=tk.Frame(hero,bg=SURFACE)
    copy.pack(fill='x',padx=22,pady=16)
    _label(copy,'ASTRONYX MINI FORGE',fg=t.ACCENT_HOVER,size=9,bold=True,
           anchor='center').pack(fill='x')
    _label(copy,'Do Meshy direto para o TaleSpire',size=20,bold=True,
           anchor='center').pack(fill='x',pady=(5,5))
    _label(copy,'Escolha um arquivo .GLB ou .ZIP do Meshy. O Mini Forge prepara o personagem no seu PC.',
           fg=MUTED,size=10,wraplength=680,justify='center',
           anchor='center').pack(fill='x')

    frame=tk.Frame(shell,bg=t.BORDER,padx=1,pady=1)
    frame.pack(fill='x',pady=(0,13))
    area=tk.Frame(frame,bg=SURFACE2,cursor='hand2')
    area.pack(fill='x')
    app.hud_drop_area=area
    badge=_label(area,'⬇',bg=SURFACE2,fg=t.ACCENT_HOVER,size=24,bold=True,anchor='center')
    badge.pack(fill='x',pady=(17,2))
    heading=_label(area,'01  •  SOLTE SEU MODELO AQUI',bg=SURFACE2,
                   size=12,bold=True,anchor='center')
    heading.pack(fill='x')
    app.hud_drop_filename=tk.StringVar(value='Nenhum arquivo selecionado')
    filename=_label(area,'',bg=SURFACE2,fg=MUTED,size=10,
                    textvariable=app.hud_drop_filename,anchor='center',
                    wraplength=620,justify='center')
    filename.pack(fill='x',padx=14,pady=(8,9))
    buttons=tk.Frame(area,bg=SURFACE2)
    buttons.pack(pady=(0,18))
    choose=action(buttons,'Escolher GLB ou ZIP',app._pick_source,True)
    choose.pack()
    app.hud_drop_widgets=(area,badge,heading,filename)
    for widget in app.hud_drop_widgets:
        widget.bind('<Button-1>',lambda _event:app._pick_source(),add='+')

    step=_card(shell,pady=(0,13))
    line=tk.Frame(step,bg=SURFACE)
    line.pack(fill='x',padx=18,pady=(13,8))
    _label(line,'02  •  GERAR MINIATURA',size=11,bold=True).pack(side='left')
    _label(line,'Processo local pelo Blender + TaleWeaverCmd',fg=MUTED,size=9).pack(side='right')
    actions=tk.Frame(step,bg=SURFACE)
    actions.pack(fill='x',padx=18,pady=(0,11))
    app.hud_generate_button=action(actions,'GERAR .TSMOD',app._start_quick,True)
    app.hud_generate_button.pack(side='left',padx=(0,9))
    action(actions,'Abrir resultado',app._open_result).pack(side='left',padx=(0,9))
    action(actions,'Calibrar 1×1',app._calibrate_1x1).pack(side='left',padx=(0,9))
    action(actions,'Mais opções',lambda:app._navigate('convert','tab_quick')).pack(side='left')
    ttk.Progressbar(step,variable=app.progress,maximum=100,
                    style='Astronyx.Horizontal.TProgressbar').pack(fill='x',padx=18,pady=(0,7))
    _label(step,'',textvariable=app.message,fg=MUTED,size=9,
           anchor='center',justify='center',wraplength=660).pack(fill='x',padx=18,pady=(0,14))

    row=tk.Frame(shell,bg=BG)
    row.pack(fill='x',pady=(0,7))
    _label(row,'Seus últimos personagens',bg=BG,size=12,bold=True).pack(side='left')
    t.hover_button(row,'Ver biblioteca →',lambda:app._navigate('library','tab_library'),
                   compact=True).pack(side='right')
    app.hud_recent=tk.Frame(shell,bg=BG)
    app.hud_recent.pack(fill='both',expand=True)

    app.hud_stats=[]
    app.hud_status_ready=_label(shell,'●  Processamento local: os modelos ficam no seu PC.',
                                bg=BG,fg=GREEN,size=9,anchor='center')
    app.hud_status_ready.pack(fill='x',pady=(5,0))

def refresh_dashboard(app):
    if not hasattr(app,'hud_recent'):
        return
    entries=getattr(app,'library_entries',[])
    ready=sum(bool(item.tsmod) for item in entries)
    for number,value in zip(app.hud_stats,(len(entries),ready,len(entries)-ready)):
        number.config(text=str(value))
    for widget in app.hud_recent.winfo_children():
        widget.destroy()
    if not entries:
        box=_card(app.hud_recent,pady=6)
        _label(box,'Sua galeria começa com o primeiro personagem.',size=11,bold=True).pack(
            anchor='w',padx=16,pady=(15,5))
        _label(box,'Crie um projeto para aparecer aqui automaticamente.',fg=MUTED).pack(
            anchor='w',padx=16,pady=(0,15))
        return
    for item in entries[:3]:
        inner=_card(app.hud_recent,pady=4)
        _label(inner,item.name.replace('_',' ')[:48],size=10,bold=True).pack(
            side='left',padx=16,pady=12)
        t.hover_button(inner,'Abrir pasta ↗',lambda p=item.folder:app._open_library(p),
                       compact=True).pack(side='right',padx=10,pady=6)
        _label(inner,'● .tsMod pronto' if item.tsmod else '○ Em preparação',
               fg=GREEN if item.tsmod else t.YELLOW,size=9,bold=True).pack(side='right',padx=7)


def inspector(app):
    container=app.tab_preview.winfo_children()[0]
    children=container.winfo_children()
    viewport=next((v for v in children if isinstance(v,tk.Frame) and any(
        hasattr(x,'open') for x in v.winfo_children())),None)
    outline=tk.Frame(container,bg=t.BORDER)
    outline.pack(fill='x',pady=(0,10),before=viewport if viewport is not None else None)
    bar=tk.Frame(outline,bg=SURFACE)
    bar.pack(fill='x',padx=1,pady=1)
    _label(bar,'PROPRIEDADES',fg=t.ACCENT_HOVER,size=9,bold=True).pack(
        side='left',padx=(14,17))
    for name,variable in (('ALTURA',app.height),('ROTAÇÃO',app.rotation),('TRIÂNGULOS',app.tris)):
        group=tk.Frame(bar,bg=SURFACE)
        group.pack(side='left',padx=(0,14),pady=10)
        _label(group,name,fg=MUTED,size=8,bold=True).pack(anchor='w',pady=(0,3))
        ttk.Entry(group,textvariable=variable,width=9,style='Astronyx.TEntry').pack(anchor='w')
    t.hover_button(bar,'Converter  →',lambda:app._navigate('convert','tab_quick'),
                   primary=True,compact=True).pack(side='right',padx=11,pady=11)


def _thumbnail(card,item,app):
    area=tk.Frame(card,bg=SURFACE2,height=146)
    area.pack(fill='x',padx=11,pady=(11,10))
    area.pack_propagate(False)
    image=None
    if item.thumbnail and len(app.library_image_refs)<70:
        try:
            if item.thumbnail.stat().st_size <= 5_000_000:
                if Image and ImageTk:
                    with Image.open(item.thumbnail) as opened:
                        if opened.width*opened.height<=10_000_000:
                            thumb=ImageOps.contain(opened.convert('RGBA'),(236,133),Image.Resampling.LANCZOS)
                            image=ImageTk.PhotoImage(thumb,master=area)
                else:
                    original=tk.PhotoImage(file=str(item.thumbnail),master=area)
                    reduction=max(1,(max(original.width(),original.height())+132)//133)
                    image=original.subsample(reduction,reduction)
        except (OSError,ValueError,tk.TclError):
            image=None
    if image is not None:
        app.library_image_refs.append(image)
        tk.Label(area,image=image,bg=SURFACE2).pack(expand=True)
    else:
        _label(area,'◈',bg=SURFACE2,fg=t.ACCENT_HOVER,size=35,bold=True).pack(expand=True)


def gallery_card(app,item,index):
    columns=max(1,getattr(app,'gallery_columns',3))
    col=index%columns
    row=index//columns
    app.library_frame.grid_columnconfigure(col,weight=1,uniform='gallery')
    outline=tk.Frame(app.library_frame,bg=t.BORDER)
    outline.grid(row=row,column=col,sticky='nsew',padx=7,pady=7)
    card=tk.Frame(outline,bg=SURFACE)
    card.pack(fill='both',expand=True,padx=1,pady=1)
    _thumbnail(card,item,app)
    _label(card,item.name.replace('_',' ')[:34],size=10,bold=True,anchor='w').pack(
        fill='x',padx=12)
    stamp=datetime.fromtimestamp(item.updated_at).strftime('%d/%m/%Y')
    _label(card,('● .tsMod pronto' if item.tsmod else '○ Em preparação')+'  ·  '+stamp,
           fg=GREEN if item.tsmod else t.YELLOW,size=9,anchor='w').pack(
        fill='x',padx=12,pady=(5,10))
    buttons=tk.Frame(card,bg=SURFACE)
    buttons.pack(fill='x',padx=10,pady=(0,11))
    t.hover_button(buttons,'Pasta ↗',lambda p=item.folder:app._open_library(p),
                   compact=True).pack(side='left')
    if item.tsmod:
        t.hover_button(buttons,'Instalar',lambda p=item.tsmod:app._install_library(p),
                       primary=True,compact=True).pack(side='right')
    elif item.obj:
        t.hover_button(buttons,'Prévia',lambda p=item.obj:app._load_preview(p),
                       compact=True).pack(side='right')
