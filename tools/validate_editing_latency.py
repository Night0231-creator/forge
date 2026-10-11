"""Real Tk heartbeat while editing a 145,800-face mesh and 4K atlas.

This measures UI latency, not FPS or performance on a specific user's GPU.
Run with a desktop/Xvfb. Native and compatible previews share the same edits.
"""
import argparse
import json
import sys
import tempfile
import time
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import tkinter as tk
import numpy as np
from PIL import Image,ImageColor
from ui.painting_studio import PaintingStudio
from ui.texture_renderer import TextureMesh


def dense_plane(n=270):
    x,y=np.meshgrid(np.linspace(-1,1,n+1),np.linspace(-1,1,n+1))
    points=np.column_stack((x.ravel(),y.ravel(),np.zeros(x.size))).astype('f4')
    yy,xx=np.meshgrid(np.arange(n),np.arange(n),indexing='ij')
    a=(yy*(n+1)+xx).ravel();b=a+1;c=a+n+2;d=a+n+1
    faces=np.stack((np.column_stack((a,b,c)),np.column_stack((a,c,d))),axis=1).reshape(-1,3).astype('i4')
    return TextureMesh(points,faces,((points[:,:2]+1)*.5)[faces],Path('Albedo.png'))


def validate(require_native=False):
    root=tk.Tk();root.geometry('1280x820');errors=[]
    root.report_callback_exception=lambda _type,value,_tb:errors.append(str(value))
    report={'faces':145800,'atlas':[4096,4096],'phases':[]}
    def until(condition,timeout=30):
        deadline=time.perf_counter()+timeout
        while not condition():
            if time.perf_counter()>deadline:raise AssertionError('Editing validation timed out')
            root.update();time.sleep(.002)
    def settle(panel):
        until(lambda:not panel._edits.busy)
        # Let presentation callbacks settle before checking pixels.
        deadline=time.perf_counter()+.15
        until(lambda:time.perf_counter()>=deadline)
    try:
        with tempfile.TemporaryDirectory() as tmp:
            project=Path(tmp);folder=project/'TaleWeaverLite';folder.mkdir()
            source=project/'TaleWeaverCmd_Source';source.mkdir()
            obj=source/'test.obj'
            obj.write_text('v -1 -1 0\nv 1 -1 0\nv 1 1 0\nv -1 1 0\n'
                'vt 0 0\nvt 1 0\nvt 1 1\nvt 0 1\nf 1/1 2/2 3/3\nf 1/1 3/3 4/4\n')
            albedo=folder/'Albedo.png';Image.new('RGBA',(4096,4096),'#999999').save(albedo)
            Image.new('RGBA',(4096,4096),(0,255,0,30)).save(folder/'MAES.png')
            original=(obj.read_bytes(),albedo.read_bytes())
            panel=PaintingStudio(root,project);panel.pack(fill='both',expand=True)
            root.update();settle(panel)
            panel.viewer._mesh=dense_plane()
            panel.viewer.yaw=panel.viewer.pitch=0
            panel.viewer.compare_reference=False
            panel.viewer.render();settle(panel)
            native=not panel.viewer._using_fallback
            report['native']=native
            if require_native and not native:raise AssertionError('Native viewport unavailable')
            def run_phase(backend):
                panel.mode.set('pincel');panel.size.set(80)
                panel.paint_material.set(True)
                finish=(220,80,190) if not report['phases'] else (0,0,70)
                for index,value in zip((0,2,3),finish):
                    panel._material_channels[index].set(value)
                panel.color.set('#FF0000' if not report['phases'] else '#0000FF')
                if backend=='compatible':
                    panel.viewer.set_lighting(gpu=False)
                    panel.viewer._fallback._mesh=panel.viewer._mesh
                    panel.viewer.render()
                    until(lambda:panel.viewer._fallback._texture_image is not None
                                  and not panel.viewer._fallback._worker_busy)
                settle(panel)
                intervals=[];callbacks=[];clock=[time.perf_counter()];running=[True];stage=['paint'];peaks=[]
                observed={}
                def observe(name,method):
                    def timed(*args,**kwargs):
                        begin=time.perf_counter()
                        try:return method(*args,**kwargs)
                        finally:observed[name]=max(observed.get(name,0),(time.perf_counter()-begin)*1000)
                    return timed
                for owner,name in ((panel,'_poll_edits'),(panel,'_publish_edit'),(panel,'_render_texture'),
                                   (panel,'_refresh_live_preview'),(panel.viewer,'_draw')):
                    setattr(owner,name,observe(name,getattr(owner,name)))
                def heartbeat():
                    now=time.perf_counter();gap=(now-clock[0])*1000;intervals.append(gap);clock[0]=now
                    if gap>100:peaks.append((stage[0],round(gap,2)))
                    if running[0]:root.after(10,heartbeat)
                if backend=='compatible':
                    fallback=panel.viewer._fallback
                    fallback._start_texture=observe('compatible_start',fallback._start_texture)
                    fallback.render=observe('compatible_render',fallback.render)
                    fallback.after_cancel(fallback._poll_job)
                    fallback._poll=observe('compatible_poll',fallback._poll)
                    fallback._poll_job=fallback.after(33,fallback._poll)
                heartbeat()
                started=time.perf_counter()
                def invoke(method,event):
                    begin=time.perf_counter();method(event);callbacks.append((time.perf_counter()-begin)*1000)
                stage[0]='shading';panel.auto_shading.set(True)
                invoke(panel._configure_shading,None);settle(panel)
                assert panel.session.automatic_shading.enabled
                shade_maps=panel.session.automatic_shading.maps
                stage[0]='paint'
                x=panel.viewer.winfo_width()*.5;y=panel.viewer.winfo_height()*.55
                before=panel.session.image.getpixel((2048,2048))
                before_material=panel.session.maes_image.getpixel((2048,2048))
                invoke(panel._paint3d_start,SimpleNamespace(x=x,y=y))
                delivered=[False]
                def drag(index=1):
                    invoke(panel._paint3d_drag,SimpleNamespace(x=x+index*4,y=y+(index % 9)))
                    if index<30:root.after(8,lambda:drag(index+1))
                    else:
                        panel._paint3d_end(None);delivered[0]=True
                root.after(8,drag)
                until(lambda:delivered[0]);settle(panel)
                painted=panel.session.image.tobytes()
                assert panel.session.pick(2048,2048)==panel.color.get()
                assert panel.session.image.getpixel((2048,2048))[:3]!=ImageColor.getrgb(panel.color.get())
                assert panel.session.automatic_shading.maps is shade_maps
                painted_material=panel.session.maes_image.getpixel((2048,2048))
                assert painted_material==(finish[0],255,finish[1],finish[2])
                clock[0]=time.perf_counter()  # exclude this validator's full-4K byte comparisons
                stage[0]='undo';panel._undo();settle(panel)
                assert panel.session.image.getpixel((2048,2048))==before
                assert panel.session.maes_image.getpixel((2048,2048))==before_material
                stage[0]='redo/save';panel._redo();panel._save();settle(panel)
                assert panel.session.image.tobytes()==painted
                with Image.open(panel.saved) as saved:assert saved.convert('RGBA').tobytes()==painted
                with Image.open(panel.session.material_draft) as saved:
                    assert saved.convert('RGBA').getpixel((2048,2048))==painted_material
                clock[0]=time.perf_counter()
                stage[0]='geometry';panel.mode.set('regiao');panel.region_mode.set('Geometria')
                invoke(panel._paint3d_start,SimpleNamespace(x=x,y=y));settle(panel)
                assert panel.session.selection.getbbox() is not None
                clock[0]=time.perf_counter()
                panel._clear_region();settle(panel)
                stage[0]='color';panel.region_mode.set('Cor similar')
                invoke(panel._paint3d_start,SimpleNamespace(x=x,y=y));settle(panel)
                assert panel.session.selection.getbbox() is not None
                clock[0]=time.perf_counter()
                panel._clear_region();settle(panel)
                running[0]=False
                phase={'backend':backend,'max_callback_ms':round(max(callbacks),2),
                    'heartbeat_p95_ms':round(float(np.percentile(intervals[1:],95)),2),
                    'heartbeat_max_ms':round(max(intervals[1:]),2),
                    'seconds':round(time.perf_counter()-started,2),
                    'paint_undo_redo_save_selection':True,'material_brush_ao_undo_save':True,
                    'automatic_shading_prepare_paint_undo_save':True,
                    'slow_heartbeat':list(peaks),
                    'main_callbacks_ms':{name:round(value,2) for name,value in observed.items()}}
                report['phases'].append(phase)
                if phase['max_callback_ms']>100 or phase['heartbeat_max_ms']>350:
                    raise AssertionError('Editing blocks the UI beyond its latency budget')
            for backend in (('native','compatible') if native else ('compatible',)):
                run_phase(backend)
            assert (obj.read_bytes(),albedo.read_bytes())==original
            panel.destroy();root.update()
            assert not errors,errors
            report['sources_unchanged']=True;report['ok']=True
    except Exception as error:
        report['ok']=False;report['error']=f'{type(error).__name__}: {error}'
    finally:root.destroy()
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--report');parser.add_argument('--require-native',action='store_true')
    args=parser.parse_args();result=validate(args.require_native)
    text=json.dumps(result,ensure_ascii=False,indent=2)
    if args.report:
        path=Path(args.report);path.parent.mkdir(parents=True,exist_ok=True);path.write_text(text,encoding='utf-8')
    print(text);sys.exit(0 if result['ok'] else 1)
