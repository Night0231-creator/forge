"""Capture the real desktop UI with a prepared local project, without updating it.

Run on Windows or an available X display. Used for visual QA of the native
application, rather than an HTML mockup. Model files and settings are preserved.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import sys
import tempfile
import time
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PIL import ImageGrab
from core.footprint_calibrator import find_project_obj
from studio import Studio
import app as legacy


def capture(project, output, width=1440, height=880):
    project=Path(project).resolve()
    obj=find_project_obj(project)
    with tempfile.TemporaryDirectory(prefix='Astronyx-Visual-QA-') as tmp:
        config=Path(tmp)/'settings.json'
        with patch.object(Studio,'_begin_updates',return_value=None), \
             patch.object(legacy,'user_config_file',return_value=config):
            window=Studio()
        try:
            window.geometry(f'{width}x{height}+0+0')
            if window._startup_library_job is not None:
                window.after_cancel(window._startup_library_job)
                window._startup_library_job=None
            window.workspace.refresh([SimpleNamespace(
                name=project.name,folder=project,obj=obj,tsmod=None)])
            editor=window.workspace.workspace_editor
            if editor is None:
                raise RuntimeError('Painting editor did not open.')
            deadline=time.monotonic()+12
            while time.monotonic()<deadline:
                window.update()
                if editor.viewer._texture_image is not None:
                    break
                time.sleep(.02)
            if editor.viewer._texture_image is None:
                raise RuntimeError('Textured preview did not finish rendering.')
            window.update_idletasks()
            x,y=window.winfo_rootx(),window.winfo_rooty()
            box=(x,y,x+window.winfo_width(),y+window.winfo_height())
            image=ImageGrab.grab(bbox=box)
            output=Path(output).resolve()
            output.parent.mkdir(parents=True,exist_ok=True)
            image.save(output)
            print(f'Native UI: {image.width}x{image.height}; '
                  f'viewport: {editor.viewer.winfo_width()}x{editor.viewer.winfo_height()}; '
                  f'tools: {editor.tools_dock.winfo_width()} px')
            print(output)
        finally:
            window.destroy()


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project',required=True)
    parser.add_argument('--output',required=True)
    parser.add_argument('--width',type=int,default=1440)
    parser.add_argument('--height',type=int,default=880)
    args=parser.parse_args()
    capture(args.project,args.output,args.width,args.height)
