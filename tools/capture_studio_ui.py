"""Capture the real desktop UI without touching existing projects or settings.

Use --project for a local project or --example for the bundled low-poly warrior.
The example is a QA fixture, not an export pipeline or a generated mockup.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import struct
import sys
import tempfile
import time
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
from PIL import Image, ImageDraw, ImageGrab
from core.footprint_calibrator import find_project_obj
from core.library import Miniature
from studio import Studio
import app as legacy


def prepare_example(destination):
    """Decode the repository's coloured GLB into a disposable textured fixture."""
    data=(Path(__file__).resolve().parents[1]/'assets/exemplo_guerreiro.glb').read_bytes()
    length=struct.unpack_from('<I',data,12)[0]
    document=json.loads(data[20:20+length])
    binary=data[28+length:]
    def accessor(index):
        spec=document['accessors'][index]
        view=document['bufferViews'][spec['bufferView']]
        dtype={5121:'u1',5123:'<u2',5125:'<u4',5126:'<f4'}[spec['componentType']]
        components={'SCALAR':1,'VEC3':3,'VEC4':4}[spec['type']]
        stride=view.get('byteStride',np.dtype(dtype).itemsize*components)
        return np.ndarray((spec['count'],components),dtype=dtype,buffer=binary,
                          offset=view.get('byteOffset',0)+spec.get('byteOffset',0),
                          strides=(stride,np.dtype(dtype).itemsize))
    project=Path(destination)/'Guerreiro de exemplo'
    source=project/'TaleWeaverCmd_Source'
    source.mkdir(parents=True)
    lite=project/'TaleWeaverLite'
    lite.mkdir()
    lines=['mtllib model.mtl','usemtl Miniature']
    atlas=Image.new('RGB',(1024,1024))
    draw=ImageDraw.Draw(atlas)
    vertex=uv=1
    for index,mesh in enumerate(document['meshes']):
        primitive=mesh['primitives'][0]
        points=accessor(primitive['attributes']['POSITION'])
        colours=accessor(primitive['attributes']['COLOR_0'])
        colour=tuple(int(v) for v in colours[0,:3])
        cellx,celly=index%4,index//4
        draw.rectangle((cellx*256,celly*256,(cellx+1)*256-1,(celly+1)*256-1),fill=colour)
        for x,y,z in points:
            lines.append(f'v {x} {z} {-y}')
        u0,u1=(cellx+.08)/4,(cellx+.92)/4
        v0,v1=1-(celly+.92)/4,1-(celly+.08)/4
        lines.extend((f'vt {u0} {v0}',f'vt {u1} {v0}',f'vt {u1} {v1}'))
        for a,b,c in accessor(primitive['indices']).reshape(-1,3):
            lines.append(f'f {vertex+int(a)}/{uv} {vertex+int(b)}/{uv+1} {vertex+int(c)}/{uv+2}')
        vertex+=len(points)
        uv+=3
    (source/'model.obj').write_text('\n'.join(lines),encoding='utf-8')
    (source/'model.mtl').write_text('newmtl Miniature\nmap_Kd Albedo.png\n',encoding='utf-8')
    for folder in (source,lite):
        atlas.save(folder/'Albedo.png')
        Image.new('RGBA',atlas.size,(0,255,0,60)).save(folder/'MAES.png')
    return project


def capture(project, output, width=1440, height=880, page='editor'):
    project=Path(project).resolve() if project else None
    entry=Miniature(folder=project,name=project.name,tsmod=None,thumbnail=None,
                    obj=find_project_obj(project),updated_at=project.stat().st_mtime) if project else None
    with tempfile.TemporaryDirectory(prefix='Astronyx-Visual-QA-') as tmp:
        config=Path(tmp)/'settings.json'
        with patch.object(Studio,'_begin_updates',return_value=None), \
             patch.object(legacy,'user_config_file',return_value=config):
            window=Studio()
        errors=[]
        window.report_callback_exception=lambda _type,value,_tb:errors.append(str(value))
        try:
            window.geometry(f'{width}x{height}+0+0')
            if window._startup_library_job is not None:
                window.after_cancel(window._startup_library_job)
                window._startup_library_job=None
            window.target.set(tmp)
            # Notebook events can arrive after navigation; keep the fixture list.
            window.refresh_library=lambda:None
            if entry and page!='welcome':
                window.library_entries=[entry]
                window._render_library_entries()
                from ui.hud22 import refresh_dashboard
                refresh_dashboard(window)
                window.workspace.refresh([entry])
            if page=='import':
                window._navigate('quick','tab_dashboard')
            elif page=='library':
                with patch.object(window,'refresh_library',return_value=None):
                    window._navigate('library','tab_library')
            editor=window.workspace.workspace_editor
            if page=='editor' and editor is None:
                raise RuntimeError('Painting editor did not open.')
            deadline=time.monotonic()+12
            ready=False
            while time.monotonic()<deadline:
                window.update()
                viewer=editor.viewer if editor and page=='editor' else None
                ready=viewer is None or viewer.frame_count>0 or (
                    viewer._using_fallback and viewer._fallback._texture_image is not None)
                if ready:
                    # Allow the final layout and fallback composition to settle.
                    until=time.monotonic()+.25
                    while time.monotonic()<until:
                        window.update()
                        time.sleep(.01)
                    break
                time.sleep(.02)
            if not ready: raise RuntimeError('Textured preview did not finish rendering.')
            if errors: raise RuntimeError('; '.join(errors))
            window.update_idletasks()
            x,y=window.winfo_rootx(),window.winfo_rooty()
            box=(x,y,x+window.winfo_width(),y+window.winfo_height())
            image=ImageGrab.grab(bbox=box,xdisplay=None if sys.platform=='win32' else window.winfo_screen())
            output=Path(output).resolve()
            output.parent.mkdir(parents=True,exist_ok=True)
            image.save(output)
            result={'page':page,'window':[image.width,image.height],'output':str(output)}
            if editor:
                viewer=editor.viewer
                result['viewport']=[viewer.winfo_width(),viewer.winfo_height()]
                result['native']=not viewer._using_fallback
                result['tools']=editor.tools_dock.winfo_width()
                if page=='editor' and viewer.winfo_width()<400:
                    raise RuntimeError('The viewport is too narrow at the supported window size.')
            print(json.dumps(result,ensure_ascii=False))
            return result
        finally:
            window.destroy()


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project')
    parser.add_argument('--example',action='store_true')
    parser.add_argument('--page',choices=('editor','welcome','import','library'),default='editor')
    parser.add_argument('--output',required=True)
    parser.add_argument('--width',type=int,default=1440)
    parser.add_argument('--height',type=int,default=880)
    args=parser.parse_args()
    if args.project and args.example: parser.error('Choose --project or --example.')
    if not args.project and not args.example and args.page=='editor':
        parser.error('An editor capture requires --project or --example.')
    if args.example:
        with tempfile.TemporaryDirectory(prefix='Astronyx-Example-QA-') as tmp:
            capture(prepare_example(tmp),args.output,args.width,args.height,args.page)
    else:
        capture(args.project,args.output,args.width,args.height,args.page)
