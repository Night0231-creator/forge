"""Tk-only, physically proportionate geometric scale comparison.

Shows a schematic unit square and a 1.75-unit humanoid, NOT TaleSpire's
actual creature collider or default scale. Does not modify 3D models.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import messagebox
from pathlib import Path

from core.footprint_calibrator import CalibrationPreview, write_calibration_report

BG='#111320'
PANEL='#1A2030'
MUTED='#ABB2CF'
WHITE='#F3F0FF'
PURPLE='#C19BFF'
GREEN='#51D8B7'
WARNING='#E8B96A'


def _label(parent, text, **kwargs):
    options={'bg':BG,'fg':WHITE,'font':('Segoe UI',10)}
    options.update(kwargs)
    return tk.Label(parent,text=text,**options)


def _panels(win, preview: CalibrationPreview):
    report=preview.report
    top=tk.Canvas(win,bg=PANEL,height=235,highlightthickness=0)
    front=tk.Canvas(win,bg=PANEL,height=235,highlightthickness=0)
    return top,front


def draw_schematics(top: tk.Canvas, front: tk.Canvas, preview: CalibrationPreview):
    """Draw with shared unit scales, so visual comparisons are dimensionally honest."""
    rep=preview.report
    points=preview.points
    w=max(300,top.winfo_width())
    h=max(220,top.winfo_height())
    fw=max(300,front.winfo_width())
    fh=max(220,front.winfo_height())
    top.delete('all')
    front.delete('all')
    # Top-down projection: 1x1 tile centered at estimated foot support.
    spread=max(1.,rep.width,rep.depth,rep.offset_from_center*2)*1.25
    px=min((w-55)/max(spread,1), (h-55)/max(spread,1))
    ox,oy=w/2,h/2+9
    foot_x=rep.ground_center_x
    foot_z=rep.ground_center_z

    def txy(x,z):
        return ox+(x-foot_x)*px,oy+(z-foot_z)*px

    x0,z0=txy(foot_x-.5,foot_z-.5)
    x1,z1=txy(foot_x+.5,foot_z+.5)
    top.create_rectangle(x0,z0,x1,z1,outline=GREEN,width=2,dash=(5,3))
    for x,y,z in points:
        dx,dy=txy(x,z)
        top.create_oval(dx-1,dy-1,dx+1,dy+1,fill=PURPLE,outline='')
    top.create_oval(ox-4,oy-4,ox+4,oy+4,fill=WARNING,outline='')
    top.create_text(12,9,text='VISTA DE CIMA · REFÊRENCIA 1 × 1 UNIDADE',
                    anchor='nw',fill=WHITE,font=('Segoe UI',9,'bold'))
    top.create_text(12,h-13,text='Verde: quadrado teórico · Roxo: vértices · Amarelo: pés estimados',
                    anchor='sw',fill=MUTED,font=('Segoe UI',9))

    # Front view: make reference human and actual model share Y-axis unit scale.
    span=max(rep.height,rep.humanoid_height_reference,.5)*1.16
    unit=(fh-52)/span
    baseline=fh-27
    x_model=fw*.38
    x_human=fw*.79
    front.create_line(10,baseline,fw-10,baseline,fill='#526073',width=1)
    front.create_text(12,9,text='FRENTE · MESMA ESCALA VERTICAL',
                       anchor='nw',fill=WHITE,font=('Segoe UI',9,'bold'))
    for x,y,z in points:
        dx=x_model+(x-foot_x)*unit
        dy=baseline-(y-rep.min_y)*unit
        if 0<=dx<fw and 0<=dy<fh:
            front.create_oval(dx-.8,dy-.8,dx+.8,dy+.8,
                              fill=PURPLE,outline='')
    hh=rep.humanoid_height_reference*unit
    # Silhouette reference is stylized: 1.75 units, not a game-extracted mesh.
    head_y=baseline-hh+hh*.11
    front.create_oval(x_human-hh*.07,head_y-hh*.07,x_human+hh*.07,
                      head_y+hh*.07,outline=GREEN,width=2)
    front.create_line(x_human,head_y+hh*.07,x_human,baseline-hh*.23,
                      fill=GREEN,width=3)
    front.create_line(x_human-hh*.18,baseline-hh*.65,
                      x_human+hh*.18,baseline-hh*.65,fill=GREEN,width=3)
    front.create_line(x_human,baseline-hh*.23,
                      x_human-hh*.13,baseline,fill=GREEN,width=3)
    front.create_line(x_human,baseline-hh*.23,
                      x_human+hh*.13,baseline,fill=GREEN,width=3)
    front.create_text(x_human,baseline-5,anchor='s',text='Ref. humanoide',
                      fill=GREEN,font=('Segoe UI',8,'bold'))
    front.create_text(x_model,baseline-5,anchor='s',text='Sua malha',
                      fill=PURPLE,font=('Segoe UI',8,'bold'))
    front.create_text(12,fh-6,anchor='sw',
                      text=f'Altura real OBJ: {rep.height:.3f} · referência: {rep.humanoid_height_reference:.2f} un.',
                      fill=MUTED,font=('Segoe UI',9))


def show_calibration(parent, preview: CalibrationPreview,
                     project_folder: str | Path) -> tk.Toplevel:
    win=tk.Toplevel(parent)
    win.title('Astronyx • Calibrador Visual 1×1')
    win.geometry('910x790')
    win.minsize(720,690)
    win.configure(bg=BG)
    win.transient(parent)
    win.columnconfigure(0,weight=1)
    _label(win,'Calibrador visual 1×1',font=('Segoe UI',19,'bold'),
           anchor='w').pack(fill='x',padx=19,pady=(17,5))
    _label(win,'Comparação de geometria real com referências desenhadas. '
           'Não altera o modelo nem o .tsMod.',
           fg=MUTED,anchor='w',wraplength=830).pack(fill='x',padx=19,pady=(0,12))
    stats=preview.report
    headline=(f'Altura  {stats.height:.3f} un.     '
              f'Largura  {stats.width:.3f} un.     '
              f'Profundidade  {stats.depth:.3f} un.')
    _label(win,headline,fg=PURPLE,font=('Consolas',11,'bold'),
           anchor='w').pack(fill='x',padx=19,pady=(0,11))
    top,front=_panels(win,preview)
    top.pack(fill='both',expand=True,padx=19,pady=(0,12))
    front.pack(fill='both',expand=True,padx=19,pady=(0,12))
    top.bind('<Configure>',lambda _e:draw_schematics(top,front,preview))
    front.bind('<Configure>',lambda _e:draw_schematics(top,front,preview))
    observations='  •  '+'\n  •  '.join(stats.observations)
    _label(win,observations,fg=WARNING,wraplength=830,justify='left',
           anchor='w').pack(fill='x',padx=19,pady=(0,11))
    _label(win,stats.caveat,fg=MUTED,wraplength=830,justify='left',
           anchor='w',font=('Segoe UI',9)).pack(fill='x',padx=19,pady=(0,12))
    buttons=tk.Frame(win,bg=BG)
    buttons.pack(fill='x',padx=19,pady=(0,19))
    def save():
        try:
            dest=write_calibration_report(project_folder)
            messagebox.showinfo('Diagnóstico salvo',
                                f'Relatório de geometria salvo:\n{dest}\n\n'
                                'O OBJ e o .tsMod não foram modificados.',
                                parent=win)
        except (OSError,ValueError) as exc:
            messagebox.showerror('Falha ao salvar',str(exc),parent=win)
    tk.Button(buttons,text='Salvar análise JSON',command=save,
              bg='#593C8C',fg=WHITE,relief='flat',padx=14,pady=9).pack(side='left')
    tk.Button(buttons,text='Fechar',command=win.destroy,
              bg='#34374D',fg=WHITE,relief='flat',padx=14,pady=9).pack(side='right')
    return win
