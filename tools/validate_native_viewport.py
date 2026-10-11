"""Exercise the real painting window and save a machine-readable report.

Run on a graphical Windows session or Xvfb. --require-native is for an
OpenGL 3.3 capable test machine; basic CI graphics may use the fallback.
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
import time
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))

import tkinter as tk
from PIL import Image, ImageChops
from ui.painting_studio import PaintingStudio


def validate(require_native=False, screenshot=None):
    root=tk.Tk()
    errors=[]
    root.report_callback_exception=lambda _type,value,_tb:errors.append(str(value))
    root.geometry('1280x720')
    result={}
    def pump(seconds):
        end=time.perf_counter()+seconds
        while time.perf_counter()<end:
            root.update()
            time.sleep(.005)
    try:
        with tempfile.TemporaryDirectory() as tmp:
            project=Path(tmp)/'Guerreiro de teste'
            prepared=project/'TaleWeaverCmd_Source'
            prepared.mkdir(parents=True)
            (project/'TaleWeaverLite').mkdir()
            obj=prepared/'model.obj'
            obj.write_text('v -1 -1 0\nv 1 -1 0\nv 0 1 0\n'
                           'vt 0 0\nvt 1 0\nvt .5 1\nf 1/1 2/2 3/3\n')
            albedo=prepared/'Albedo.png'
            Image.new('RGBA',(512,512),(155,100,75,255)).save(albedo)
            Image.new('RGBA',(512,512),(0,255,0,128)).save(prepared/'MAES.png')
            original=obj.read_bytes(),albedo.read_bytes()
            panel=PaintingStudio(root,project)
            panel.pack(fill='both',expand=True)
            pump(.6)
            viewer=panel.viewer
            native=not viewer._using_fallback and viewer.frame_count>0
            result['native']=native
            result['renderer']=viewer.renderer_name
            if require_native and not native:
                raise AssertionError('O viewport nativo não iniciou.')
            viewer.set_camera('frente')
            pump(.2)
            x,y=viewer.winfo_width()*.5,viewer.winfo_height()*.55
            before=panel.session.image.copy()
            panel.color.set('#22FF44')
            event=SimpleNamespace(x=round(x),y=round(y))
            panel._paint3d_start(event)
            panel._paint3d_end(event)
            pump(.2)
            if ImageChops.difference(before.convert('RGB'),panel.session.image.convert('RGB')).getbbox() is None:
                raise AssertionError('O pincel não atingiu a textura.')
            result['surface_paint']=True
            panel._undo();pump(.15)
            if ImageChops.difference(before.convert('RGB'),panel.session.image.convert('RGB')).getbbox() is not None:
                raise AssertionError('Desfazer não restaurou a pintura.')
            result['undo']=True
            viewer.set_quality('Leve',60)
            root.geometry('1440x880')
            pump(.2)
            viewer.set_camera('frente');pump(.2)
            hit=panel._picker_for_camera().hit(viewer.winfo_width()*.5,viewer.winfo_height()*.55)
            if hit is None:raise AssertionError('Pincel desalinhado após redimensionar.')
            result['resize_pick']=True
            if native:
                # A screenshot here verifies presentation, not just projection math.
                from PIL import ImageGrab
                shot=ImageGrab.grab(xdisplay=None if sys.platform=='win32' else root.winfo_screen())
                x=viewer.winfo_rootx()+round(viewer.winfo_width()*.5)
                y=viewer.winfo_rooty()+round(viewer.winfo_height()*.55)
                pixel=shot.getpixel((x,y))[:3]
                result['center_rgb']=list(pixel)
                if max(pixel)<60:
                    raise AssertionError('Quadro reduzido não foi ampliado para a janela inteira.')
                result['scaled_frame_presented']=True
            if native:
                pump(.2)
                count=viewer.frame_count
                pump(.25)
                if viewer.frame_count!=count:raise AssertionError('A GPU continua renderizando quando ociosa.')
                result['idle_no_frames']=True
                result['draw_ms']=round(viewer.last_render_ms,2)
            if screenshot:
                from PIL import ImageGrab
                image_path=Path(screenshot)
                image_path.parent.mkdir(parents=True,exist_ok=True)
                ImageGrab.grab(xdisplay=None if sys.platform=='win32' else root.winfo_screen()).save(image_path)
            viewer.set_lighting(gpu=False);pump(.25)
            if not viewer._using_fallback:raise AssertionError('Modo compatível não ativou.')
            viewer.set_lighting(gpu=True);pump(.25)
            if native and viewer._using_fallback:raise AssertionError('Viewport nativo não retornou.')
            result['fallback_switch']=True
            if (obj.read_bytes(),albedo.read_bytes())!=original:
                raise AssertionError('A prévia alterou os arquivos originais.')
            result['sources_unchanged']=True
            panel.destroy();pump(.1)
            if errors:raise AssertionError('; '.join(errors))
            result['ok']=True
    except Exception as exc:
        result['ok']=False
        result['error']=f'{type(exc).__name__}: {exc}'
    finally:
        root.destroy()
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--report')
    parser.add_argument('--screenshot')
    parser.add_argument('--require-native',action='store_true')
    args=parser.parse_args()
    result=validate(args.require_native,args.screenshot)
    text=json.dumps(result,ensure_ascii=False,indent=2)
    if args.report:
        path=Path(args.report);path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(text,encoding='utf-8')
    print(text)
    sys.exit(0 if result['ok'] else 1)
