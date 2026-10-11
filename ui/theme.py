"""Shared Astronyx desktop styles.

Only presentation; neither geometry nor the TaleWeaverCmd pipeline imports this.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from .rounded import RoundedButton
from .palette import (BG, SIDEBAR, PANEL, RAISED, BORDER, TEXT, MUTED, SUBTLE,
                      ACCENT, ACCENT_HOVER, ACCENT_SOFT, ACCENT_INK, GREEN, YELLOW)


def gallery_columns(width: int) -> int:
    """Keep thumbnails readable rather than squeezing three into small windows."""
    return 4 if width >= 1160 else 3 if width >= 820 else 2 if width >= 530 else 1


def hover_button(parent, text, command, primary=False, compact=False):
    return RoundedButton(
        parent, text, command,
        bg=ACCENT if primary else RAISED,
        hover=ACCENT_HOVER if primary else BORDER,
        fg=ACCENT_INK if primary else TEXT, parent_bg=parent.cget('bg'), radius=7,
        font=('Segoe UI',9 if compact else 10,'bold' if primary else 'normal'),
        padx=12 if compact else 16, pady=6 if compact else 9)


def apply_studio_style(root):
    style = ttk.Style(root)
    # Clam honours dark field colours on Windows as well as X11.
    if style.theme_use() != 'clam':
        style.theme_use('clam')
    root.option_add('*TCombobox*Listbox.background', RAISED)
    root.option_add('*TCombobox*Listbox.foreground', TEXT)
    root.option_add('*TCombobox*Listbox.selectBackground', ACCENT_SOFT)
    root.option_add('*TCombobox*Listbox.selectForeground', TEXT)
    style.configure('TNotebook', background=BG, borderwidth=0)
    style.configure('TNotebook.Tab', background=PANEL, foreground=MUTED,
                    padding=(12, 8), font=('Segoe UI', 9))
    style.map('TNotebook.Tab', background=[('selected', RAISED)],
              foreground=[('selected', TEXT)])
    style.configure('TCheckbutton', background=PANEL, foreground=TEXT,
                    font=('Segoe UI', 9))
    style.map('TCheckbutton', background=[('active', PANEL)])
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
                    lightcolor=RAISED,darkcolor=RAISED,
                    selectbackground=ACCENT_SOFT, selectforeground=TEXT,
                    padding=(9, 6), font=('Segoe UI', 10))
    style.map('Astronyx.TCombobox',
              fieldbackground=[('readonly', RAISED)], foreground=[('readonly', TEXT)])
    style.configure('Astronyx.Horizontal.TProgressbar', background=ACCENT,
                    troughcolor=RAISED, thickness=9, borderwidth=0)
    style.configure('Astronyx.Vertical.TScrollbar', background=RAISED,
                    troughcolor=BG, bordercolor=BG, lightcolor=RAISED,
                    darkcolor=RAISED, arrowcolor=MUTED, arrowsize=10)
    return style
