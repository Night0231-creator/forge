"""Compact native controls for the miniature painting desk."""
from __future__ import annotations

import tkinter as tk

BG = '#111115'
PANEL = '#17171C'
FIELD = '#29292F'
BORDER = '#303038'
TEXT = '#E3E3E8'
MUTED = '#94949F'
ACCENT = '#1976C5'

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


class ToolButton(tk.Canvas):
    """Vector icons stay legible across Windows scaling and font choices."""
    def __init__(self, parent, tool, title, command):
        super().__init__(parent, width=43, height=33, bg=BG,
                         highlightthickness=0, takefocus=True, cursor='hand2')
        self.tool, self.title, self.command = tool, title, command
        self.selected = False
        self.hovered = False
        self.bind('<Configure>', lambda _e:self._draw())
        self.bind('<ButtonRelease-1>', self._activate)
        self.bind('<Key-Return>', self._activate)
        self.bind('<Key-space>', self._activate)
        self.bind('<Enter>', lambda _e: self._hover(True))
        self.bind('<Leave>', lambda _e: self._hover(False))
        self.bind('<FocusIn>', lambda _e: self._hover(True))
        self.bind('<FocusOut>', lambda _e: self._hover(False))
        self._draw()

    def _activate(self, _event=None):
        self.command()
        return 'break'

    def _hover(self, value):
        self.hovered = value
        self._draw()

    def set_selected(self, value):
        self.selected = value
        self._draw()

    def _draw(self):
        self.delete('all')
        fill = ACCENT if self.selected else FIELD if self.hovered else BG
        width=max(43,self.winfo_width())
        self.create_rectangle(1, 1, width-1, 32, fill=fill, outline=fill)
        ink = '#FFFFFF' if self.selected else '#B7B7BF'
        if self.tool == 'balde':
            self.create_polygon(14, 13, 21, 6, 29, 14, 22, 21,
                                fill='', outline=ink, width=2)
            self.create_line(15, 9, 23, 17, fill=ink, width=2)
            self.create_polygon(30, 18, 27, 23, 32, 23, fill=ink, outline=ink)
        elif self.tool == 'pincel':
            self.create_polygon(19, 19, 29, 7, 33, 10, 23, 21,
                                fill=ink, outline=ink)
            self.create_oval(12, 20, 22, 26, fill=ink, outline=ink)
        elif self.tool == 'carimbo':
            self.create_rectangle(18, 7, 25, 18, fill=ink, outline=ink)
            self.create_rectangle(13, 18, 30, 22, fill=ink, outline=ink)
            self.create_line(12, 26, 31, 26, fill=ink, width=2)
        elif self.tool == 'regiao':
            self.create_rectangle(12, 8, 31, 26, dash=(3, 2), outline=ink, width=2)
            self.create_line(17, 17, 26, 17, fill=ink, width=1)
            self.create_line(21, 12, 21, 22, fill=ink, width=1)
        elif self.tool == 'conta-gotas':
            self.create_line(15, 24, 28, 11, fill=ink, width=3)
            self.create_line(24, 8, 32, 16, fill=ink, width=3)
            self.create_line(12, 27, 16, 23, fill=ink, width=1)
        else:
            self.create_polygon(12, 21, 24, 8, 33, 17, 24, 27, 18, 27,
                                fill='', outline=ink, width=2)
            self.create_line(17, 16, 27, 23, fill=ink, width=2)
        for item in self.find_all()[1:]: self.move(item,(width-43)/2,0)


def slider(parent, title, variable, maximum=100, minimum=0, command=None,
           percent=False):
    row=tk.Frame(parent,bg=PANEL)
    row.pack(fill='x',pady=(4,1))
    tk.Label(row,text=title,bg=PANEL,fg=MUTED,
             font=('Segoe UI',9)).pack(side='left')
    shown=tk.StringVar(master=row)
    tk.Label(row,textvariable=shown,width=5,anchor='e',bg=PANEL,
             fg=TEXT,font=('Segoe UI',9)).pack(side='right')
    track=tk.Canvas(row,height=20,width=100,bg=PANEL,highlightthickness=0,
                     takefocus=True,cursor='hand2')
    track.pack(side='right',fill='x',expand=True,padx=(9,3))
    def draw(*_args):
        value=variable.get()
        shown.set(f'{round(value/maximum*100)}%' if percent else str(value))
        width=max(20,track.winfo_width())
        x=6+(width-12)*(value-minimum)/max(1,maximum-minimum)
        track.delete('all')
        track.create_line(6,10,width-6,10,fill='#3B3B44',width=3)
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
