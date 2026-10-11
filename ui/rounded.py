"""Small rounded Tk Canvas controls, without new runtime dependencies.

Tk ttk/Frame corners are rectangular on Windows. These canvas controls paint
their own 9px radius corners while keeping variables, keyboard shortcuts and
enabled/disabled state accessible. Only visual widgets use this module.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import font as tkfont
from .palette import (SIDEBAR, RAISED, BORDER, TEXT, MUTED, SUBTLE,
                      ACCENT, ACCENT_SOFT)


def rounded_points(width: float, height: float, radius: float) -> tuple[float, ...]:
    """Return bounded control points for a smooth, rounded rectangle."""
    if width <= 0 or height <= 0:
        raise ValueError("Dimensões inválidas para borda arredondada.")
    r = max(0., min(float(radius), width / 2, height / 2))
    return (r, 0, width-r, 0, width, 0, width, r,
            width, height-r, width, height, width-r, height,
            r, height, 0, height, 0, height-r, 0, r, 0, 0)


def _rounded_shape(canvas, width, height, radius, color, border=None):
    """Canvas corner smoothing, inset to preserve the outer border."""
    if width < 3 or height < 3:
        return
    canvas.create_polygon(*rounded_points(width-1, height-1, radius),
                          fill=color, outline=border or color,
                          width=1, smooth=True, splinesteps=18)


class RoundedButton(tk.Canvas):
    """A themeable centered button with Tk-style config(state=...)."""
    def __init__(self, parent, text, command, *, bg=RAISED,
                 hover=BORDER, fg=TEXT, parent_bg=None,
                 padx=15, pady=9, font=('Segoe UI', 10, 'bold'),
                 radius=10, width=None, height=None, text_inset=14, **kwargs):
        self._font = font
        self._text_inset = text_inset
        self._fill = bg
        self._hover_color = hover
        self._text_color = fg
        self._parent_bg = parent_bg or parent.cget('bg')
        self._label = text
        self._command = command
        self._hovered = False
        self._selected = False
        self._state = 'normal'
        font_width = tkfont.Font(font=font).measure(text)
        height = height or max(34, int(tkfont.Font(font=font).metrics('linespace') + 2*pady))
        width = width or int(font_width+2*padx+6)
        super().__init__(parent, width=width, height=height, bg=self._parent_bg,
                         bd=0, highlightthickness=0, takefocus=1,
                         cursor='hand2', **kwargs)
        self.radius = radius
        self.bind('<Configure>', self._render, add='+')
        self.bind('<Enter>', self._enter, add='+')
        self.bind('<Leave>', self._leave, add='+')
        self.bind('<ButtonRelease-1>', self._activate, add='+')
        self.bind('<Key-Return>', self._activate, add='+')
        self.bind('<Key-space>', self._activate, add='+')
        self.bind('<FocusIn>', self._render, add='+')
        self.bind('<FocusOut>', self._render, add='+')
        self._render()

    def _enter(self, _event=None):
        self._hovered = True
        self._render()

    def _leave(self, _event=None):
        self._hovered = False
        self._render()

    def _activate(self, event=None):
        if self._state == 'normal' and callable(self._command):
            self.focus_set()
            self._command()

    def _render(self, _event=None):
        self.delete('all')
        w = self.winfo_width() if self.winfo_width()>1 else int(self.cget('width'))
        h = self.winfo_height() if self.winfo_height()>1 else int(self.cget('height'))
        if self._state == 'disabled':
            bg, fg = RAISED, SUBTLE
        else:
            bg = self._hover_color if self._hovered else self._fill
            fg = self._text_color
        _rounded_shape(self, w, h, self.radius, bg,
                       ACCENT if self.focus_get() == self else bg)
        self.create_text(w/2, h/2, text=self._label, fill=fg,
                         font=self._font, anchor='center', justify='center',
                         width=max(10, w-self._text_inset),tags='label')

    def configure(self, cnf=None, **kwargs):
        if isinstance(cnf, dict):
            kwargs = {**cnf, **kwargs}
        if not kwargs and cnf is None:
            return super().configure()
        if 'state' in kwargs:
            state = kwargs.pop('state')
            if state not in ('normal', 'disabled'):
                raise ValueError('Estado de botão inválido.')
            self._state = state
        if 'bg' in kwargs:
            self._fill = kwargs.pop('bg')
        if 'fg' in kwargs:
            self._text_color = kwargs.pop('fg')
        if 'font' in kwargs:
            self._font = kwargs.pop('font')
        if 'text_inset' in kwargs:
            self._text_inset = kwargs.pop('text_inset')
        if 'text' in kwargs:
            self._label = kwargs.pop('text')
        if kwargs:
            super().configure(**kwargs)
        self._render()

    config = configure


class RoundedNavButton(RoundedButton):
    """Centered sidebar menu, with rounded selected and hover backgrounds."""
    def __init__(self, parent, text, command, *, width=198, icon=None, **kwargs):
        self._nav_icon=icon
        super().__init__(parent, text, command, width=width, height=41,
                         font=('Segoe UI', 9), radius=7,
                         bg=SIDEBAR, hover=RAISED, fg=MUTED,
                         parent_bg=SIDEBAR, **kwargs)

    def set_hover(self, hovered):
        self._hovered = bool(hovered)
        self._render()

    def set_selected(self, selected):
        self._selected = bool(selected)
        self._fill = ACCENT_SOFT if selected else SIDEBAR
        self._hover_color = BORDER if selected else RAISED
        self._text_color = TEXT if selected else MUTED
        self._font = ('Segoe UI', 9, 'bold' if selected else 'normal')
        self._render()

    def _render(self,_event=None):
        super()._render()
        if self._nav_icon:
            from .studio_controls import draw_icon
            w=self.winfo_width() if self.winfo_width()>1 else int(self.cget('width'))
            h=self.winfo_height() if self.winfo_height()>1 else int(self.cget('height'))
            self.itemconfigure('label',anchor='w',justify='left',width=max(10,w-52))
            self.coords('label',40,h/2)
            draw_icon(self,self._nav_icon,20,h/2,17,self._text_color)


class RoundedEntry(tk.Canvas):
    """Single-line centered editable field with a rounded border."""
    def __init__(self, parent, *, textvariable=None, width=160,
                 bg=RAISED, parent_bg=None, **kwargs):
        self._fill = bg
        self._focus = False
        super().__init__(parent, width=width, height=40, bg=parent_bg or parent.cget('bg'),
                         highlightthickness=0, bd=0, **kwargs)
        self.entry = tk.Entry(self, textvariable=textvariable,
                              bg=bg, fg=TEXT, insertbackground=TEXT,
                              selectbackground=ACCENT, selectforeground='white',
                              font=('Segoe UI',10), justify='center',
                              relief='flat', bd=0, highlightthickness=0)
        self.entry.place(x=12, y=9, relwidth=1, width=-24, height=22)
        self.bind('<Configure>', self._render, add='+')
        self.bind('<Button-1>', lambda _e:self.entry.focus_set(), add='+')
        self.entry.bind('<FocusIn>', self._focus_in, add='+')
        self.entry.bind('<FocusOut>', self._focus_out, add='+')
        self._render()

    def _focus_in(self, _event=None):
        self._focus=True
        self._render()

    def _focus_out(self, _event=None):
        self._focus=False
        self._render()

    def _render(self, _event=None):
        self.delete('background')
        w,h=max(self.winfo_width(),int(self.cget('width'))),max(self.winfo_height(),40)
        if w>=3:
            self.create_polygon(*rounded_points(w-1,h-1,10),fill=self._fill,
                                outline=ACCENT if self._focus else BORDER,
                                width=2 if self._focus else 1,
                                smooth=True,splinesteps=18,tags='background')
            self.tag_lower('background')


class RoundedSelect(tk.Canvas):
    """Keyboard-accessible centered select menu with a tracked Tk variable."""
    def __init__(self, parent, *, textvariable, values, width=140,
                 bg=RAISED, parent_bg=None, **kwargs):
        self._variable = textvariable
        self._values = tuple(str(v) for v in values)
        self._fill = bg
        self._hovered = False
        super().__init__(parent,width=width,height=40,bg=parent_bg or parent.cget('bg'),
                         bd=0,highlightthickness=0,cursor='hand2',takefocus=1,**kwargs)
        self._trace = self._variable.trace_add('write',lambda *_:self._render())
        self.bind('<Configure>', self._render, add='+')
        self.bind('<Enter>', lambda _e:self._set_hover(True), add='+')
        self.bind('<Leave>', lambda _e:self._set_hover(False), add='+')
        self.bind('<Button-1>', self._open, add='+')
        self.bind('<Key-Return>', self._open, add='+')
        self.bind('<Key-space>', self._open, add='+')
        self.bind('<Key-Down>', self._open, add='+')
        self._render()

    def _set_hover(self, state):
        self._hovered=state
        self._render()

    def _open(self, _event=None):
        self.focus_set()
        menu=tk.Menu(self,tearoff=0,bg=RAISED,fg=TEXT,
                     activebackground=ACCENT,activeforeground='white',
                     font=('Segoe UI',10),bd=0,relief='flat')
        for item in self._values:
            menu.add_command(label=item,command=lambda v=item:self._choose(v))
        try:
            menu.tk_popup(self.winfo_rootx(),self.winfo_rooty()+self.winfo_height())
        finally:
            menu.grab_release()

    def _choose(self, value):
        self._variable.set(value)
        self.event_generate('<<ComboboxSelected>>',when='tail')

    def _render(self, _event=None):
        self.delete('all')
        w,h=max(self.winfo_width(),int(self.cget('width'))),max(self.winfo_height(),40)
        bg=BORDER if self._hovered else self._fill
        _rounded_shape(self,w,h,10,bg,ACCENT if self.focus_get()==self else BORDER)
        self.create_text((w-21)/2,h/2,text=self._variable.get(),
                         fill=TEXT,font=('Segoe UI',10),anchor='center')
        self.create_text(w-18,h/2,text='▾',fill=MUTED,
                         font=('Segoe UI',12,'bold'),anchor='center')

    def destroy(self):
        try:
            self._variable.trace_remove('write',self._trace)
        except tk.TclError:
            pass
        super().destroy()
