"""Compact native controls for the miniature painting desk."""
from __future__ import annotations

import tkinter as tk

from .palette import BG, PANEL, RAISED as FIELD, BORDER, TEXT, MUTED, ACCENT
from .studio_controls import IconButton

# These are colour choices only. MAES materials remain explicit, undoable edits.
COLOURS = (
    ('Branco', '#F1EFEA', 'Cores'), ('Marfim', '#E8DDC8', 'Cores'),
    ('Cinza claro', '#B9BEC5', 'Cores'), ('Cinza', '#7F848D', 'Cores'),
    ('Grafite', '#41434B', 'Cores'), ('Preto', '#202127', 'Cores'),
    ('Vermelho', '#C62B34', 'Cores'), ('Vinho', '#762A38', 'Cores'),
    ('Laranja', '#E7772C', 'Cores'), ('Amarelo', '#E7CA39', 'Cores'),
    ('Lima', '#9BCA40', 'Cores'), ('Verde', '#478E69', 'Cores'),
    ('Turquesa', '#297E83', 'Cores'), ('Ciano', '#54C8D1', 'Cores'),
    ('Azul claro', '#5F9ECD', 'Cores'), ('Azul', '#366AC5', 'Cores'),
    ('Índigo', '#353974', 'Cores'), ('Violeta', '#6C439B', 'Cores'),
    ('Magenta', '#AA3784', 'Cores'), ('Rosa', '#D582A0', 'Cores'),
    ('Aço', '#929FAC', 'Metais'), ('Ouro', '#E4B54C', 'Metais'),
    ('Cobre', '#A76B48', 'Metais'), ('Bronze', '#967344', 'Metais'),
    ('Pele', '#DEAB85', 'Natural'), ('Couro', '#70452F', 'Natural'),
    ('Madeira', '#705139', 'Natural'), ('Pedra', '#858898', 'Natural'),
    ('Tecido', '#613E94', 'Natural'), ('Magia', '#8A64FF', 'Natural'),
)


class ToolButton(IconButton):
    """Painting tool with a vector icon, keyboard focus and delayed hint."""
    pass


def slider(parent, title, variable, maximum=100, minimum=0, command=None,
           percent=False):
    row=tk.Frame(parent,bg=PANEL)
    row.pack(fill='x',pady=(8,3))
    tk.Label(row,text=title,bg=PANEL,fg=MUTED,
             font=('Segoe UI',9)).pack(side='left')
    shown=tk.StringVar(master=row)
    tk.Label(row,textvariable=shown,width=5,anchor='e',bg=PANEL,
             fg=TEXT,font=('Segoe UI',9)).pack(side='right')
    track=tk.Canvas(parent,height=20,width=100,bg=PANEL,highlightthickness=0,
                     takefocus=True,cursor='hand2')
    track.pack(fill='x',pady=(0,2))
    def draw(*_args):
        value=variable.get()
        shown.set(f'{round(value/maximum*100)}%' if percent else str(value))
        width=max(20,track.winfo_width())
        x=6+(width-12)*(value-minimum)/max(1,maximum-minimum)
        track.delete('all')
        track.create_line(6,10,width-6,10,fill=BORDER,width=3)
        track.create_line(6,10,x,10,fill=ACCENT,width=3)
        track.create_oval(x-3,7,x+3,13,fill=TEXT,outline=TEXT)
    def changed(*_args):
        draw()
        if command is not None: command(str(variable.get()))
    def choose(event):
        width=max(20,track.winfo_width())
        fraction=max(0,min(1,(event.x-6)/(width-12)))
        variable.set(round(minimum+(maximum-minimum)*fraction))
        track.focus_set()
        return 'break'
    def step(delta):
        variable.set(max(minimum,min(maximum,variable.get()+delta)))
        return 'break'
    track.bind('<Button-1>',choose)
    track.bind('<B1-Motion>',choose)
    track.bind('<Left>',lambda _e:step(-1))
    track.bind('<Right>',lambda _e:step(1))
    track.bind('<Configure>',draw)
    trace=variable.trace_add('write',changed)
    def cleanup(_event):
        variable.trace_remove('write',trace)
    track.bind('<Destroy>',cleanup)
    draw()
    return track
