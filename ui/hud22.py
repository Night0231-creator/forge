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
    shell=tk.Frame(app.tab_dashboard,bg=BG)
    shell.pack(fill='both',expand=True,padx=18,pady=14)

    hero=_card(shell,pady=(0,15))
    accent=tk.Frame(hero,bg=PURPLE,width=4)
    accent.pack(side='left',fill='y')
    copy=tk.Frame(hero,bg=SURFACE)
    copy.pack(side='left',fill='both',expand=True,padx=23,pady=20)
    _label(copy,'ASTRONYX / MINIATURE WORKSPACE',fg=t.ACCENT_HOVER,size=9,bold=True).pack(anchor='w')
    _label(copy,'Seu personagem. Sua aventura.',size=20,bold=True).pack(anchor='w',pady=(7,5))
    _label(copy,'Importe um modelo, ajuste a escala e prepare sua miniatura para o TaleSpire.',
           fg=MUTED,size=10,wraplength=570,justify='left').pack(anchor='w')
    buttons=tk.Frame(copy,bg=SURFACE)
    buttons.pack(anchor='w',pady=(15,0))
    action(buttons,'+  Novo personagem',lambda:app._navigate('convert','tab_quick'),True).pack(side='left',padx=(0,9))
    action(buttons,'Abrir Studio 3D  →',lambda:app._navigate('studio','tab_preview')).pack(side='left')

    stats=tk.Frame(shell,bg=BG)
    stats.pack(fill='x',pady=(0,15))
    app.hud_stats=[]
    for label,icon in (('PROJETOS','◈'),('PRONTOS PARA USAR','✓'),('EM PREPARAÇÃO','⋯')):
        outline=tk.Frame(stats,bg=t.BORDER)
        outline.pack(side='left',fill='both',expand=True,padx=(0,9))
        box=tk.Frame(outline,bg=SURFACE)
        box.pack(fill='both',expand=True,padx=1,pady=1)
        heading=tk.Frame(box,bg=SURFACE)
        heading.pack(fill='x',padx=14,pady=(12,3))
        _label(heading,label,fg=MUTED,size=9,bold=True).pack(side='left')
        _label(heading,icon,fg=t.ACCENT_HOVER,size=14,bold=True).pack(side='right')
        number=_label(box,'0',size=24,bold=True)
        number.pack(anchor='w',padx=14,pady=(0,12))
        app.hud_stats.append(number)

    row=tk.Frame(shell,bg=BG)
    row.pack(fill='x',pady=(0,8))
    _label(row,'Projetos recentes',bg=BG,size=15,bold=True).pack(side='left')
    t.hover_button(row,'Ver biblioteca →',lambda:app._navigate('library','tab_library'),
                   compact=True).pack(side='right')
    app.hud_recent=tk.Frame(shell,bg=BG)
    app.hud_recent.pack(fill='both',expand=True)

    footer=tk.Frame(shell,bg=BG)
    footer.pack(fill='x',pady=(12,0))
    _label(footer,'●  PROCESSAMENTO LOCAL · seus arquivos ficam no seu PC',
           bg=BG,fg=GREEN,size=9,bold=True).pack(side='left')
    ttk.Progressbar(footer,variable=app.progress,maximum=100,
                    style='Astronyx.Horizontal.TProgressbar',length=170).pack(side='right')


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
