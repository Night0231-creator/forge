"""Visual components for Astronyx Studio V2.2 preview.

These widgets call existing conversion handlers; they never alter 3D assets.
"""
import tkinter as tk
from tkinter import ttk
from datetime import datetime

BG = '#0D101B'
SURFACE = '#1B1D2D'
SURFACE2 = '#25263A'
PURPLE = '#7545D5'
MUTED = '#A2A4BA'
WHITE = '#F4F2FF'
GREEN = '#72D6B2'


def filter_miniatures(items, query='', status='Todos'):
    key = (query or '').strip().casefold()
    return [item for item in items
            if (not key or key in item.name.replace('_', ' ').casefold())
            and (status != 'Prontos' or bool(item.tsmod))
            and (status != 'Em preparação' or not item.tsmod)]


def action(parent, label, command, primary=False):
    return tk.Button(parent, text=label, command=command, cursor='hand2',
                     bg=PURPLE if primary else SURFACE2,
                     fg=WHITE, activebackground='#9364EA',
                     activeforeground=WHITE, relief='flat', bd=0,
                     font=('Segoe UI', 10, 'bold'), padx=14, pady=9)


def dashboard(app):
    home=app.tab_dashboard
    shell=tk.Frame(home,bg=BG)
    shell.pack(fill='both',expand=True,padx=14,pady=14)
    hero=tk.Frame(shell,bg=SURFACE)
    hero.pack(fill='x',pady=(0,15))
    tk.Label(hero,text='ASTRONYX · CHARACTER STUDIO',bg=SURFACE,fg='#B995FF',
             font=('Segoe UI',9,'bold')).pack(anchor='w',padx=20,pady=(17,0))
    tk.Label(hero,text='Sua próxima miniatura começa aqui.',bg=SURFACE,fg=WHITE,
             font=('Segoe UI',19,'bold')).pack(anchor='w',padx=20,pady=(6,5))
    tk.Label(hero,text='Do Meshy para o TaleSpire. Sem alterar o motor de conversão.',
             bg=SURFACE,fg=MUTED,font=('Segoe UI',10)).pack(anchor='w',padx=20)
    buttons=tk.Frame(hero,bg=SURFACE)
    buttons.pack(anchor='w',padx=20,pady=(13,18))
    action(buttons,'+ Novo personagem',lambda:app._navigate('convert','tab_quick'),True).pack(side='left',padx=(0,9))
    action(buttons,'Abrir editor 3D',lambda:app._navigate('studio','tab_preview')).pack(side='left')
    stats=tk.Frame(shell,bg=BG)
    stats.pack(fill='x',pady=(0,16))
    app.hud_stats=[]
    for label in ('TOTAL DE PROJETOS','.TSMOD PRONTOS','EM PREPARAÇÃO'):
        box=tk.Frame(stats,bg=SURFACE)
        box.pack(side='left',fill='x',expand=True,padx=(0,9))
        number=tk.Label(box,text='0',bg=SURFACE,fg=WHITE,font=('Segoe UI',22,'bold'))
        number.pack(anchor='w',padx=16,pady=(12,0))
        tk.Label(box,text=label,bg=SURFACE,fg=MUTED,font=('Segoe UI',9,'bold')).pack(
            anchor='w',padx=16,pady=(0,12))
        app.hud_stats.append(number)
    row=tk.Frame(shell,bg=BG)
    row.pack(fill='x')
    tk.Label(row,text='Projetos recentes',bg=BG,fg=WHITE,font=('Segoe UI',16,'bold')).pack(side='left')
    action(row,'Ver biblioteca →',lambda:app._navigate('library','tab_library')).pack(side='right')
    app.hud_recent=tk.Frame(shell,bg=BG)
    app.hud_recent.pack(fill='both',expand=True,pady=(12,0))
    footer=tk.Frame(shell,bg=BG)
    footer.pack(fill='x',pady=(6,0))
    tk.Label(footer,text='Conversão local · Blender + TaleWeaverCmd',bg=BG,fg=MUTED).pack(side='left')
    ttk.Progressbar(footer,variable=app.progress,maximum=100,
                    style='Forge.Horizontal.TProgressbar',length=165).pack(side='right')


def refresh_dashboard(app):
    if not hasattr(app,'hud_recent'):
        return
    items=getattr(app,'library_entries',[])
    count=len(items)
    ready=sum(bool(x.tsmod) for x in items)
    for label,value in zip(app.hud_stats,(count,ready,count-ready)):
        label.configure(text=str(value))
    for child in app.hud_recent.winfo_children():
        child.destroy()
    if not items:
        tk.Label(app.hud_recent,text='Ainda não há projetos. Importe seu primeiro personagem!',
                 bg=BG,fg=MUTED,font=('Segoe UI',11)).pack(anchor='w',pady=16)
    for item in items[:4]:
        box=tk.Frame(app.hud_recent,bg=SURFACE)
        box.pack(fill='x',pady=(0,6))
        tk.Label(box,text=item.name.replace('_',' '),bg=SURFACE,fg=WHITE,
                 font=('Segoe UI',11,'bold')).pack(side='left',padx=13,pady=12)
        action(box,'Abrir',lambda p=item.folder:app._open_library(p)).pack(side='right',padx=8,pady=6)
        tk.Label(box,text='● PRONTO' if item.tsmod else '○ PREPARANDO',bg=SURFACE,
                 fg=GREEN if item.tsmod else '#EDC17B').pack(side='right',padx=9)


def inspector(app):
    holder=app.tab_preview.winfo_children()[0]
    children=holder.winfo_children()
    # Insert the new controls above the existing OBJ preview viewport.
    cols=next((x for x in children if isinstance(x,tk.Frame) and any(
               hasattr(y,'open') for y in x.winfo_children())),None)
    panel=tk.Frame(holder,bg=SURFACE)
    if cols is not None:
        panel.pack(fill='x',pady=(0,9),before=cols)
    else:
        panel.pack(fill='x',pady=(0,9))
    tk.Label(panel,text='INSPETOR',bg=SURFACE,fg='#B995FF',
             font=('Segoe UI',9,'bold')).pack(side='left',padx=12)
    for name,var in (('Altura',app.height),('Rotação',app.rotation),('Triângulos',app.tris)):
        group=tk.Frame(panel,bg=SURFACE)
        group.pack(side='left',padx=8,pady=9)
        tk.Label(group,text=name,bg=SURFACE,fg=MUTED,font=('Segoe UI',8)).pack(anchor='w')
        ttk.Entry(group,textvariable=var,width=8).pack(anchor='w')
    action(panel,'Converter →',lambda:app._navigate('convert','tab_quick'),True).pack(side='right',padx=10)


def gallery_card(app,item,index):
    col=index%3
    app.library_frame.grid_columnconfigure(col,weight=1,uniform='minis')
    frame=tk.Frame(app.library_frame,bg=SURFACE)
    frame.grid(row=index//3,column=col,sticky='nsew',padx=6,pady=6)
    area=tk.Frame(frame,bg=SURFACE2,height=125)
    area.pack(fill='x',padx=9,pady=(9,5))
    area.pack_propagate(False)
    img=None
    if item.thumbnail and len(app.library_image_refs)<45:
        try:
            if item.thumbnail.stat().st_size<3_000_000:
                raw=tk.PhotoImage(file=str(item.thumbnail))
                factor=max(1,(max(raw.width(),raw.height())+119)//120)
                img=raw.subsample(factor,factor)
                app.library_image_refs.append(img)
        except (OSError,tk.TclError):
            pass
    tk.Label(area,image=img,text='' if img else '◈',bg=SURFACE2,fg='#B995FF',
             font=('Segoe UI',30)).pack(expand=True)
    tk.Label(frame,text=item.name.replace('_',' ')[:32],bg=SURFACE,fg=WHITE,
             font=('Segoe UI',10,'bold')).pack(anchor='w',padx=11,pady=(3,0))
    stamp=datetime.fromtimestamp(item.updated_at).strftime('%d/%m/%Y')
    tk.Label(frame,text=('● Pronto' if item.tsmod else '○ Em preparação')+' · '+stamp,
             bg=SURFACE,fg=GREEN if item.tsmod else '#EDC17B',
             font=('Segoe UI',8)).pack(anchor='w',padx=11,pady=(4,7))
    bar=tk.Frame(frame,bg=SURFACE)
    bar.pack(fill='x',padx=7,pady=(0,8))
    action(bar,'Pasta',lambda p=item.folder:app._open_library(p)).pack(side='left')
    if item.tsmod:
        action(bar,'Instalar',lambda p=item.tsmod:app._install_library(p),True).pack(side='right')
    elif item.obj:
        action(bar,'Prévia',lambda p=item.obj:app._load_preview(p)).pack(side='right')
