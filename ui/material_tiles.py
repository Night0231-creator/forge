"""Small procedural material swatches; no downloaded assets or live render loop."""
from functools import lru_cache
import tkinter as tk
import numpy as np
from PIL import Image, ImageColor, ImageTk

from .palette import PANEL, RAISED, BORDER, TEXT, ACCENT
from .studio_controls import Tooltip


@lru_cache(maxsize=24)
def material_swatch(choice, size=48):
    y,x=np.mgrid[-1:1:complex(size),-1:1:complex(size)]
    inside=x*x+y*y<=.86
    z=np.sqrt(np.maximum(0,1-(x*x+y*y)/.86))
    n=np.stack((x/np.sqrt(.86),-y/np.sqrt(.86),z),axis=-1)
    light=np.array([-.4,.65,.64]);light/=np.linalg.norm(light)
    half=light+np.array([0,0,1]);half/=np.linalg.norm(half)
    diffuse=np.maximum(0,n@light)
    smooth=choice.smoothness/255
    metal=choice.metallic/255
    spec=np.maximum(0,n@half)**(8+100*smooth*smooth)
    colour=np.array(ImageColor.getrgb(choice.colour))/255
    pigment=colour*(.23+.7*diffuse[...,None])*(1-.3*metal)
    reflected=(np.ones(3)*(1-metal)+colour*metal)*spec[...,None]*(.25+metal)
    lit=np.clip(pigment+reflected+colour*(choice.emission/255)*.42,0,1)
    rgba=np.zeros((size,size,4),dtype=np.uint8)
    rgba[:,:,:3]=np.rint(lit*255).astype(np.uint8)
    rgba[:,:,3]=inside.astype(np.uint8)*255
    return Image.fromarray(rgba)


class MaterialTile(tk.Canvas):
    def __init__(self,parent,choice,command):
        super().__init__(parent,width=82,height=80,bg=PANEL,
                         highlightthickness=0,takefocus=True,cursor='hand2')
        self.choice=choice
        self.command=command
        self.selected=False
        self.hover=False
        self.photo=ImageTk.PhotoImage(material_swatch(choice),master=self)
        self.tooltip=Tooltip(self,f'{choice.name}  ·  Cor e acabamento para pincel, balde e carimbo')
        self.bind('<Configure>',lambda _e:self._draw())
        self.bind('<Enter>',lambda _e:self._hover(True),add='+')
        self.bind('<Leave>',lambda _e:self._hover(False),add='+')
        self.bind('<FocusIn>',lambda _e:self._draw())
        self.bind('<FocusOut>',lambda _e:self._draw())
        self.bind('<Button-1>',lambda _e:self._invoke())
        self.bind('<Return>',lambda _e:self._invoke())
        self.bind('<space>',lambda _e:self._invoke())
        self._draw()

    def _invoke(self):
        self.focus_set()
        self.command()
        return 'break'

    def _hover(self,active):
        self.hover=active
        self._draw()

    def set_selected(self,active):
        self.selected=bool(active)
        self._draw()

    def _draw(self):
        self.delete('all')
        width=max(60,self.winfo_width())
        border=ACCENT if self.selected or self.focus_get()==self else BORDER
        self.create_rectangle(1,1,width-2,78,fill=RAISED if self.hover or self.selected else PANEL,
                              outline=border,width=1)
        self.create_image(width/2,29,image=self.photo)
        self.create_text(width/2,65,text=self.choice.name,fill=TEXT,font=('Segoe UI',8))
