"""Astronyx Mini Forge HUD polish.

Presentation-only views: conversion, assets, and project database stay unchanged.
"""
from __future__ import annotations

from datetime import datetime
import tkinter as tk
from tkinter import ttk

from . import theme as t
from .studio_controls import draw_icon

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
    """A clear two-step import flow; all actions remain reachable at minimum size."""
    outer=tk.Frame(app.tab_dashboard,bg=BG)
    outer.pack(fill='both',expand=True)
    scroll=ttk.Scrollbar(outer,orient='vertical',style='Astronyx.Vertical.TScrollbar')
    scroll.pack(side='right',fill='y')
    canvas=tk.Canvas(outer,bg=BG,highlightthickness=0,yscrollcommand=scroll.set)
    canvas.pack(fill='both',expand=True)
    scroll.configure(command=canvas.yview)
    shell=tk.Frame(canvas,bg=BG)
    item=canvas.create_window(0,0,anchor='nw',window=shell)
    shell.bind('<Configure>',lambda _e:canvas.configure(scrollregion=canvas.bbox('all')))
    canvas.bind('<Configure>',lambda e:canvas.itemconfigure(item,width=e.width))
    content=tk.Frame(shell,bg=BG)
    content.pack(fill='both',expand=True,padx=22,pady=18)
    _label(content,'NOVO PROJETO',bg=BG,fg=t.SUBTLE,size=8,bold=True).pack(anchor='w')
    _label(content,'Preparar nova miniatura',bg=BG,size=22,bold=True).pack(anchor='w',pady=(5,7))
    _label(content,'Importe seu modelo Meshy e prepare a versão para pintar e jogar.',
           bg=BG,fg=MUTED,size=10).pack(anchor='w',pady=(0,22))
    flow=tk.Frame(content,bg=BG)
    flow.pack(fill='x')
    for column in (0,1): flow.grid_columnconfigure(column,weight=1,uniform='import')
    area=tk.Frame(flow,bg=SURFACE,highlightbackground=t.BORDER,highlightthickness=1)
    area.grid(row=0,column=0,sticky='nsew',padx=(0,8))
    app.hud_drop_area=area
    _label(area,'01  /  MODELO DE ORIGEM',fg=t.SUBTLE,size=8,bold=True).pack(
        anchor='w',padx=18,pady=(18,14))
    badge=tk.Canvas(area,width=46,height=46,bg=SURFACE,highlightthickness=0,cursor='hand2')
    badge.pack(pady=(0,8))
    draw_icon(badge,'import',23,23,32,t.ACCENT)
    heading=_label(area,'Solte seu modelo aqui',size=13,bold=True,anchor='center',cursor='hand2')
    heading.pack(fill='x')
    app.hud_drop_filename=tk.StringVar(value='Nenhum arquivo selecionado')
    filename=_label(area,'',fg=MUTED,size=9,textvariable=app.hud_drop_filename,
                    anchor='center',wraplength=280,justify='center',cursor='hand2')
    filename.pack(fill='x',padx=18,pady=(9,13))
    action(area,'Escolher GLB ou ZIP',app._pick_source,True).pack(pady=(0,8))
    _label(area,'GLB ou ZIP exportado pelo Meshy',fg=t.SUBTLE,size=9).pack(pady=(0,18))
    app.hud_drop_widgets=(area,badge,heading,filename)
    for widget in app.hud_drop_widgets:
        widget.bind('<Button-1>',lambda _event:app._pick_source(),add='+')
    step=tk.Frame(flow,bg=SURFACE,highlightbackground=t.BORDER,highlightthickness=1)
    step.grid(row=0,column=1,sticky='nsew',padx=(8,0))
    _label(step,'02  /  PREPARAÇÃO',fg=t.SUBTLE,size=8,bold=True).pack(
        anchor='w',padx=18,pady=(18,14))
    _label(step,'Pronto para o TaleSpire',size=13,bold=True).pack(anchor='w',padx=18)
    _label(step,'Prepare a miniatura com textura e escala.\nA conversão acontece no seu PC.',
           fg=MUTED,size=9,justify='left').pack(anchor='w',padx=18,pady=(9,17))
    app.hud_generate_button=action(step,'Gerar miniatura .tsMod',app._start_quick,True)
    app.hud_generate_button.pack(fill='x',padx=18,pady=(0,12))
    actions=tk.Frame(step,bg=SURFACE)
    actions.pack(fill='x',padx=18)
    for index,(title,command) in enumerate((('Abrir resultado',app._open_result),
            ('Calibrar 1×1',app._calibrate_1x1),
            ('Mais opções',lambda:app._navigate('convert','tab_quick')))):
        button=t.hover_button(actions,title,command,compact=True)
        button.grid(row=index//2,column=index%2,sticky='ew',padx=(0,5),pady=(0,5))
    actions.grid_columnconfigure(0,weight=1)
    actions.grid_columnconfigure(1,weight=1)
    ttk.Progressbar(step,variable=app.progress,maximum=100,
                    style='Astronyx.Horizontal.TProgressbar').pack(fill='x',padx=18,pady=(10,8))
    _label(step,'',textvariable=app.message,fg=MUTED,size=9,anchor='w',
           justify='left',wraplength=300).pack(fill='x',padx=18,pady=(0,18))
    row=tk.Frame(content,bg=BG)
    row.pack(fill='x',pady=(24,8))
    _label(row,'Projetos recentes',bg=BG,size=12,bold=True).pack(side='left')
    t.hover_button(row,'Ver todos',lambda:app._navigate('library','tab_library'),
                   compact=True).pack(side='right')
    app.hud_recent=tk.Frame(content,bg=BG)
    app.hud_recent.pack(fill='x')
    app.hud_stats=[]
    app.hud_status_ready=_label(content,'Processamento local  ·  Seus modelos ficam no seu PC',
                                bg=BG,fg=t.SUBTLE,size=9,anchor='w')
    app.hud_status_ready.pack(fill='x',pady=(18,0))
    def wheel(event):
        delta=-1 if getattr(event,'num',0)==4 else 1 if getattr(event,'num',0)==5 else -int(event.delta/120)
        canvas.yview_scroll(delta,'units')
        return 'break'
    def route(parent):
        for child in parent.winfo_children():
            child.bind('<MouseWheel>',wheel)
            child.bind('<Button-4>',wheel)
            child.bind('<Button-5>',wheel)
            route(child)
    route(shell)

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
        t.hover_button(inner,'Pintar' if app.workspace._valid_project(item) else 'Abrir pasta',
                       lambda i=item:app._open_painting_project(i) if app.workspace._valid_project(i) else app._open_library(i.folder),
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
    if getattr(item,'thumbnail',None) and len(app.library_image_refs)<70:
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
        placeholder=tk.Canvas(area,width=70,height=70,bg=SURFACE2,highlightthickness=0)
        placeholder.pack(expand=True)
        draw_icon(placeholder,'cube',35,35,44,t.SUBTLE)


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
    buttons.pack(fill='x',padx=12,pady=(2,12))
    buttons.grid_columnconfigure(0,weight=1)
    buttons.grid_columnconfigure(1,weight=1)
    if item.obj and app.workspace._valid_project(item):
        t.hover_button(buttons,'Pintar',lambda i=item:app._open_painting_project(i),
                       primary=True,compact=True).grid(row=0,column=0,columnspan=2,sticky='ew',pady=(0,7))
    elif item.obj:
        t.hover_button(buttons,'Prévia 3D',lambda p=item.obj:app._load_preview(p),
                       compact=True).grid(row=0,column=0,columnspan=2,sticky='ew',pady=(0,7))
    t.hover_button(buttons,'Pasta',lambda p=item.folder:app._open_library(p),
                   compact=True).grid(row=1,column=0,sticky='ew',padx=(0,4))
    if item.tsmod:
        t.hover_button(buttons,'Instalar',lambda p=item.tsmod:app._install_library(p),
                       compact=True).grid(row=1,column=1,sticky='ew',padx=(4,0))
