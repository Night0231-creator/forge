"""Astronyx V2.2.3 visual tokens & non-invasive Tk style helpers.

Only presentation; neither geometry nor the TaleWeaverCmd pipeline imports this.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from .rounded import RoundedButton

BG = '#0C0F1A'
SIDEBAR = '#101321'
PANEL = '#191D2E'
RAISED = '#252A40'
BORDER = '#343953'
TEXT = '#F3F4FC'
MUTED = '#A8AEC4'
SUBTLE = '#7E88A6'
ACCENT = '#8859EA'
ACCENT_HOVER = '#A077FF'
ACCENT_SOFT = '#302449'
GREEN = '#71DBB3'
YELLOW = '#F3CB84'


def gallery_columns(width: int) -> int:
    """Keep thumbnails readable rather than squeezing three into small windows."""
    return 4 if width >= 1160 else 3 if width >= 820 else 2 if width >= 530 else 1


def hover_button(parent, text, command, primary=False, compact=False):
    return RoundedButton(
        parent, text, command,
        bg=ACCENT if primary else RAISED,
        hover=ACCENT_HOVER if primary else BORDER,
        fg=TEXT, parent_bg=parent.cget('bg'), radius=10,
        font=('Segoe UI',9 if compact else 10,'bold'),
        padx=12 if compact else 16, pady=7 if compact else 10)


def apply_studio_style(root):
    style = ttk.Style(root)
    style.configure('Sidebar.TCheckbutton', background=SIDEBAR,
                    foreground=TEXT, font=('Segoe UI',9),padding=3)
    style.map('Sidebar.TCheckbutton', background=[('active',SIDEBAR)],
              foreground=[('active',TEXT)])
    style.configure('Astronyx.TEntry', foreground=TEXT, fieldbackground=RAISED,
                    background=RAISED, bordercolor=BORDER, insertcolor=TEXT,
                    lightcolor=BORDER, darkcolor=BORDER,
                    padding=(10, 8), font=('Segoe UI', 10))
    style.configure('Astronyx.TCombobox', foreground=TEXT, fieldbackground=RAISED,
                    background=RAISED, bordercolor=BORDER, arrowcolor=TEXT,
                    selectbackground=ACCENT_SOFT, selectforeground=TEXT,
                    padding=7, font=('Segoe UI', 10))
    style.map('Astronyx.TCombobox',
              fieldbackground=[('readonly', RAISED)], foreground=[('readonly', TEXT)])
    style.configure('Astronyx.Horizontal.TProgressbar', background=ACCENT,
                    troughcolor=RAISED, thickness=9, borderwidth=0)
    return style
