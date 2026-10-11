"""Optional TkDND integration: gracefully falls back to file picker.

Drag-and-drop depends on the external, optional tkinterdnd2 Tcl extension.
The user can always click to browse when the platform/extension is unavailable.
"""
from __future__ import annotations


def register_file_drop(root, widgets, callback) -> bool:
    try:
        from tkinterdnd2 import DND_FILES, TkinterDnD
        TkinterDnD._require(root)
        for widget in widgets:
            TkinterDnD.DnDWrapper.drop_target_register(widget, DND_FILES)
            TkinterDnD.DnDWrapper.dnd_bind(widget, '<<Drop>>', callback)
        return True
    except (ImportError, OSError, RuntimeError, Exception):
        # Never block the entire Mini Forge UI for an optional Tcl plugin.
        return False
