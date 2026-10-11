"""Small native vector controls for the desktop studio. No image assets needed."""
from __future__ import annotations

import tkinter as tk

from .palette import (BG, PANEL, RAISED, BORDER, TEXT, MUTED, ACCENT,
                      ACCENT_SOFT)
from .rounded import rounded_points


def draw_icon(canvas, name, x, y, size=22, color=MUTED):
    """Draw a consistent 24-unit outline icon, centred at x/y."""
    before=set(canvas.find_all())
    def line(*coords, **kw):
        canvas.create_line(*coords, fill=color, width=1.7, capstyle='round',
                           joinstyle='round', **kw)
    def rect(*coords, **kw):
        canvas.create_rectangle(*coords, outline=color, width=1.6, **kw)
    def oval(*coords, **kw):
        canvas.create_oval(*coords, outline=color, width=1.6, **kw)
    if name=='pincel':
        line(9,16,18,4,21,7,12,18,9,16)
        canvas.create_polygon(9,17,12,19,9,22,4,22,6,18,fill=color,outline='')
    elif name=='balde':
        line(4,10,12,3,20,11,12,19,4,10,18,10)
        line(5,5,13,13)
        canvas.create_polygon(20,14,17,20,22,20,fill=color,outline='')
    elif name=='carimbo':
        line(9,13,9,6,10,3,14,3,15,6,15,13)
        rect(4,13,20,18)
        line(3,22,21,22)
    elif name=='regiao':
        rect(3,3,21,21,dash=(3,2))
        line(8,12,16,12)
        line(12,8,12,16)
    elif name=='conta-gotas':
        line(4,20,6,16,17,5,20,8,9,19,4,20)
        line(14,3,22,11)
    elif name=='borracha':
        line(3,16,14,4,22,12,14,21,8,21,3,16)
        line(8,11,17,18)
        line(14,21,22,21)
    elif name in ('undo','redo'):
        line(5,6,5,12,11,12)
        canvas.create_arc(5,7,22,23,start=0,extent=170,style='arc',outline=color,width=1.7)
        if name=='redo':
            for item in set(canvas.find_all())-before:
                canvas.scale(item,12,12,-1,1)
    elif name=='frame':
        for coords in ((3,9,3,3,9,3),(15,3,21,3,21,9),
                       (21,15,21,21,15,21),(9,21,3,21,3,15)):
            line(*coords)
        oval(9,9,15,15)
    elif name in ('cube','logo'):
        line(12,2,22,7,22,17,12,22,2,17,2,7,12,2,12,12,12,22)
        line(2,7,12,12,22,7)
    elif name=='import':
        line(12,2,12,15,7,10)
        line(12,15,17,10)
        line(3,14,3,21,21,21,21,14)
    elif name=='folder':
        line(2,7,2,21,22,21,22,7,12,7,9,3,2,3,2,7)
    elif name=='layers':
        line(2,7,12,2,22,7,12,12,2,7)
        line(2,12,12,17,22,12)
        line(2,17,12,22,22,17)
    elif name=='search':
        oval(3,3,16,16)
        line(15,15,21,21)
    elif name=='save':
        line(3,3,18,3,21,6,21,21,3,21,3,3)
        rect(7,3,16,9)
        rect(7,14,17,21)
    elif name=='library':
        for a,b in ((3,3),(14,3),(3,14),(14,14)):
            rect(a,b,a+7,b+7)
    else:
        line(5,5,19,19)
        line(19,5,5,19)
    scale=size/24
    for item in set(canvas.find_all())-before:
        canvas.scale(item,0,0,scale,scale)
        canvas.move(item,x-size/2,y-size/2)


class Tooltip:
    """Delayed hints with no polling; timers disappear with their widget."""
    def __init__(self,widget,text):
        self.widget,self.text=widget,text
        self.job=None
        self.window=None
        widget.bind('<Enter>',self.schedule,add='+')
        widget.bind('<Leave>',self.hide,add='+')
        widget.bind('<ButtonPress>',self.hide,add='+')
        widget.bind('<Destroy>',self.hide,add='+')

    def schedule(self,_event=None):
        self.hide()
        self.job=self.widget.after(450,self.show)

    def show(self):
        self.job=None
        if not self.widget.winfo_exists() or not self.widget.winfo_viewable():
            return
        tip=tk.Toplevel(self.widget)
        self.window=tip
        tip.overrideredirect(True)
        tip.configure(bg=BORDER)
        tk.Label(tip,text=self.text,bg=RAISED,fg=TEXT,padx=10,pady=7,
                 font=('Segoe UI',9),wraplength=260,justify='left').pack(padx=1,pady=1)
        tip.update_idletasks()
        x=min(self.widget.winfo_rootx()+self.widget.winfo_width()+8,
              tip.winfo_screenwidth()-tip.winfo_reqwidth()-8)
        y=min(self.widget.winfo_rooty()+5,tip.winfo_screenheight()-tip.winfo_reqheight()-8)
        tip.geometry(f'+{max(0,x)}+{max(0,y)}')

    def hide(self,_event=None):
        if self.job is not None:
            try: self.widget.after_cancel(self.job)
            except tk.TclError: pass
            self.job=None
        if self.window is not None:
            self.window.destroy()
            self.window=None


class IconButton(tk.Canvas):
    def __init__(self,parent,icon,title,command,*,size=38):
        super().__init__(parent,width=size,height=size,bg=parent.cget('bg'),
                         highlightthickness=0,bd=0,takefocus=True,cursor='hand2')
        self.tool,self.title,self.command=icon,title,command
        self.selected=self.hovered=False
        self.tooltip=Tooltip(self,title)
        self.bind('<Configure>',lambda _e:self._draw())
        self.bind('<ButtonRelease-1>',self._activate)
        self.bind('<Return>',self._activate)
        self.bind('<space>',self._activate)
        self.bind('<Enter>',lambda _e:self._hover(True),add='+')
        self.bind('<Leave>',lambda _e:self._hover(False),add='+')
        self.bind('<FocusIn>',lambda _e:self._draw())
        self.bind('<FocusOut>',lambda _e:self._draw())
        self._draw()

    def _activate(self,_event=None):
        self.focus_set()
        self.command()
        return 'break'

    def _hover(self,value):
        self.hovered=value
        self._draw()

    def set_selected(self,value):
        self.selected=bool(value)
        self._draw()

    def _draw(self):
        self.delete('all')
        w=self.winfo_width() if self.winfo_width()>1 else int(self.cget('width'))
        h=self.winfo_height() if self.winfo_height()>1 else int(self.cget('height'))
        fill=ACCENT_SOFT if self.selected else RAISED if self.hovered else self.cget('bg')
        self.create_polygon(*rounded_points(w-1,h-1,7),smooth=True,splinesteps=16,
                            fill=fill,outline=ACCENT if self.focus_get()==self else fill)
        draw_icon(self,self.tool,w/2,h/2,22,ACCENT if self.selected else TEXT if self.hovered else MUTED)


class SwatchButton(tk.Canvas):
    def __init__(self,parent,name,colour,command):
        super().__init__(parent,width=34,height=32,bg=parent.cget('bg'),
                         highlightthickness=0,takefocus=True,cursor='hand2')
        self.colour,self.selected=colour,False
        self.command=command
        self.tooltip=Tooltip(self,f'{name}  ·  {colour}')
        self.bind('<Configure>',lambda _e:self._draw())
        self.bind('<ButtonRelease-1>',self._activate)
        self.bind('<Return>',self._activate)
        self.bind('<space>',self._activate)
        self.bind('<FocusIn>',lambda _e:self._draw())
        self.bind('<FocusOut>',lambda _e:self._draw())
        self._draw()

    def _activate(self,_event=None):
        self.focus_set()
        self.command()
        return 'break'

    def set_selected(self,value):
        self.selected=value
        self._draw()

    def _draw(self):
        self.delete('all')
        w=max(1,self.winfo_width()) if self.winfo_width()>1 else 34
        h=32
        outline=TEXT if self.selected else ACCENT if self.focus_get()==self else self.cget('bg')
        self.create_polygon(*rounded_points(w-1,h-1,6),smooth=True,splinesteps=16,
                            fill=self.cget('bg'),outline=outline,width=2)
        item=self.create_polygon(*rounded_points(w-9,h-9,4),smooth=True,splinesteps=16,
                                 fill=self.colour,outline=self.colour)
        self.move(item,4,4)


class SearchField(tk.Frame):
    """A real Entry with a visual placeholder that never enters the query."""
    def __init__(self,parent,variable,placeholder,*,width=240):
        super().__init__(parent,bg=RAISED,highlightthickness=1,
                         highlightbackground=BORDER,width=width,height=36)
        self.pack_propagate(False)
        icon=tk.Canvas(self,bg=RAISED,width=32,height=34,highlightthickness=0)
        icon.pack(side='left')
        draw_icon(icon,'search',17,17,16,MUTED)
        self.entry=tk.Entry(self,textvariable=variable,bg=RAISED,fg=TEXT,
                            insertbackground=TEXT,selectbackground=ACCENT_SOFT,
                            selectforeground=TEXT,bd=0,relief='flat',font=('Segoe UI',9))
        self.entry.pack(side='left',fill='both',expand=True,padx=(0,8),pady=7)
        self.placeholder=tk.Label(self,text=placeholder,bg=RAISED,fg=MUTED,
                                  font=('Segoe UI',9),anchor='w',cursor='xterm')
        self.placeholder.bind('<Button-1>',lambda _e:self.entry.focus_set())
        self.variable=variable
        self.trace=variable.trace_add('write',self._refresh)
        self.entry.bind('<FocusIn>',self._refresh,add='+')
        self.entry.bind('<FocusOut>',self._refresh,add='+')
        self.bind('<Destroy>',self._cleanup,add='+')
        self._refresh()

    def _refresh(self,*_args):
        focused=self.focus_get()==self.entry
        self.configure(highlightbackground=ACCENT if focused else BORDER)
        if not self.variable.get() and not focused:
            self.placeholder.place(x=33,y=6,relwidth=1,width=-40,height=22)
        else:
            self.placeholder.place_forget()

    def _cleanup(self,event):
        if event.widget==self:
            self.variable.trace_remove('write',self.trace)
