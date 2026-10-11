"""Optional accelerated PBR-ish preview using ModernGL 3.3.

Dedicated worker-thread contexts; no OpenGL calls on the Tk thread. This GPU
preview is not the TaleWeaver export renderer. Missing/old GPU -> CPU fallback.
"""
from __future__ import annotations

import math
import threading
import numpy as np
from PIL import Image
from .texture_renderer import draw, draw_fast, MAX_TRIANGLES
from .studio_scene import studio_background

VS = """#version 330
in vec3 in_position;
in vec2 in_uv;
in vec3 in_normal;
out vec2 v_uv;
out vec3 v_normal;
out vec3 v_eye;
uniform float u_yaw;
uniform float u_pitch;
uniform float u_unit;
uniform float u_depth_span;
uniform vec2 u_pan;
uniform vec2 u_resolution;
uniform vec3 u_center;
void main() {
    vec3 p = in_position - u_center;
    float c=cos(u_yaw), s=sin(u_yaw);
    float cp=cos(u_pitch), sp=sin(u_pitch);
    vec3 rotated=vec3(c*p.x-s*p.z, p.y, s*p.x+c*p.z);
    vec3 view=vec3(rotated.x,cp*rotated.y-sp*rotated.z,
                   sp*rotated.y+cp*rotated.z);
    vec3 n=vec3(c*in_normal.x-s*in_normal.z, in_normal.y,
                s*in_normal.x+c*in_normal.z);
    v_normal=normalize(vec3(n.x,cp*n.y-sp*n.z,sp*n.y+cp*n.z));
    v_eye=view;
    v_uv=in_uv;
    float ndc_x=2.0*(view.x*u_unit+u_pan.x)/u_resolution.x;
    float ndc_y=2.0*(view.y*u_unit-u_resolution.y*.05-u_pan.y)/u_resolution.y;
    gl_Position=vec4(ndc_x, ndc_y,-view.z/u_depth_span,1.0);
}
""";

FS = """#version 330
uniform sampler2D u_albedo;
uniform sampler2D u_maes;
uniform sampler2D u_normalmap;
uniform int u_use_normal;
uniform float u_light;
uniform float u_emission;
uniform float u_ambient;
uniform vec3 u_sky_tint;
uniform vec3 u_ground_tint;
uniform vec3 u_light_dir;
in vec2 v_uv;
in vec3 v_normal;
in vec3 v_eye;
out vec4 fragColor;
const float PI=3.14159265359;
void main() {
    vec3 N=normalize(v_normal);
    if (N.z<0.0) N=-N;
    if (u_use_normal!=0) {
        vec3 dx=dFdx(v_eye),dy=dFdy(v_eye);
        vec2 duv1=dFdx(v_uv),duv2=dFdy(v_uv);
        vec3 T=dx*duv2.y-dy*duv1.y;
        T=normalize(T - N*dot(T,N));
        vec3 B=normalize(cross(N,T))*sign(duv1.x*duv2.y-duv1.y*duv2.x);
        if (length(T)>0.5 && length(B)>0.5) {
            vec3 normalData=texture(u_normalmap,v_uv).rgb*2.0-1.0;
            N=normalize(mat3(T,B,N)*normalData);
        }
    }
    vec3 color=pow(texture(u_albedo,v_uv).rgb,vec3(2.2));
    vec4 maes=texture(u_maes,v_uv);
    float metallic=clamp(maes.r,0.0,1.0);
    float ao=clamp(maes.g,0.0,1.0);
    float roughness=clamp(1.0-maes.a,.075,.96);
    vec3 L=normalize(u_light_dir);
    vec3 V=vec3(0.0,0.0,1.0);
    vec3 H=normalize(L+V);
    float NdotL=max(dot(N,L),0.0);
    float NdotV=max(dot(N,V),.001);
    float NdotH=max(dot(N,H),0.0);
    float VdotH=max(dot(V,H),0.0);
    float alpha=roughness*roughness;
    float a2=alpha*alpha;
    float denom=max(PI*pow(NdotH*NdotH*(a2-1.0)+1.0,2.0),.001);
    float D=a2/denom;
    float k=pow(roughness+1.0,2.0)/8.0;
    float Gv=NdotV/(NdotV*(1.0-k)+k);
    float Gl=NdotL/(NdotL*(1.0-k)+k);
    vec3 F0=mix(vec3(.04),color,metallic);
    vec3 F=F0+(1.0-F0)*pow(1.0-VdotH,5.0);
    vec3 spec=(D*Gv*Gl*F)/max(4.0*NdotL*NdotV,.001);
    vec3 diffuse=(1.0-metallic)*color/PI;
    // Lightweight hemispheric ambient lighting, not a real HDRI/IBL map.
    float up=clamp(N.y*.5+.5,0.0,1.0);
    vec3 hemisphere=mix(u_ground_tint,u_sky_tint,up);
    vec3 env_diffuse=color*(1.0-metallic)*hemisphere;
    vec3 env_reflect=F0*hemisphere*(1.0-roughness*.65);
    vec3 ambient=(env_diffuse+env_reflect*.7)*u_ambient*max(.12,ao);
    // Broad fill keeps backlit miniatures legible without a second shadow map.
    float fill=max(dot(N,normalize(vec3(-.65,.25,-.34))),0.0);
    vec3 lit=ambient+(diffuse+spec)*NdotL*u_light*2.1
             +diffuse*hemisphere*fill*u_light*.22;
    // TaleSpire can condition emission on its own paint-wash settings.
    vec3 emitted=color*maes.b*u_emission;
    vec3 mapped=(lit+emitted)/(lit+emitted+vec3(1.0));
    fragColor=vec4(pow(clamp(mapped,0.0,1.0),vec3(1.0/2.2)),1.0);
}
""";


def _mesh_buffer(mesh) -> np.ndarray:
    """Interleaved triangle vertices: position 3 + UV 2 + flat normal 3."""
    points=np.asarray(mesh.points,dtype=np.float32)
    indices=np.asarray(mesh.triangles,dtype=np.int32)
    if not len(indices) or len(indices)>MAX_TRIANGLES:
        raise ValueError('Malha fora do limite da prévia.')
    tris=points[indices]
    normals=np.cross(tris[:,1]-tris[:,0],tris[:,2]-tris[:,0])
    magnitude=np.maximum(np.linalg.norm(normals,axis=1,keepdims=True),1e-8)
    normals/=magnitude
    joined=np.concatenate((tris,np.asarray(mesh.texcoords,dtype=np.float32),
                           np.broadcast_to(normals[:,None,:],tris.shape)),axis=2)
    return np.ascontiguousarray(joined.reshape(-1,8),dtype=np.float32)


ENV_PRESETS = {
    'Estúdio': ((.77,.83,1.00),(.27,.24,.32)),
    'Pôr do sol': ((1.00,.71,.46),(.39,.23,.34)),
    'Luar': ((.40,.58,.96),(.12,.16,.32)),
}

def _validate_settings(light: float, emission: float, ambient: float = 1.0,
                       environment: str = 'Estúdio'):
    if not all(math.isfinite(v) for v in (light,emission,ambient)):
        raise ValueError('Iluminação inválida.')
    if environment not in ENV_PRESETS:
        raise ValueError('Ambiente de iluminação desconhecido.')
    if not 0.0 <= ambient <= 3.0:
        raise ValueError('Luz ambiente fora do intervalo permitido.')
    if not 0.0 <= light <= 4.0 or not 0.0 <= emission <= 5.0:
        raise ValueError('Iluminação fora do intervalo permitido.')


class GPUPreview:
    """Private to one worker thread; reuse GL context, geometry and textures."""
    def __init__(self, ctx=None, fragment_shader=None):
        import moderngl
        self.owner=threading.get_ident()
        self.gl=moderngl
        self.ctx=ctx if ctx is not None else moderngl.create_context(standalone=True,require=330)
        self.program=self.ctx.program(vertex_shader=VS,fragment_shader=fragment_shader or FS)
        self.ctx.enable(moderngl.DEPTH_TEST)
        self.mesh_id=None
        self.geometry=None
        self.vao=None
        self.tex_cache={}
        self._neutral_maes=np.array([[[0,255,0,128]]],dtype=np.uint8)
        self._neutral_normal=np.array([[[128,128,255]]],dtype=np.uint8)
        self.framebuffer=None
        self.frame_size=None
        self.render_calls=0

    def _thread_check(self):
        if threading.get_ident()!=self.owner:
            raise RuntimeError('Contexto GPU utilizado em thread diferente.')

    def _set_mesh(self,mesh):
        key=id(mesh)
        if key==self.mesh_id and self.vao is not None:
            return
        if self.vao is not None: self.vao.release()
        if self.geometry is not None: self.geometry.release()
        self.geometry=self.ctx.buffer(_mesh_buffer(mesh).tobytes())
        self.vao=self.ctx.vertex_array(
            self.program,[(self.geometry,'3f 2f 3f','in_position','in_uv','in_normal')])
        self.mesh_id=key
        lo,hi=mesh.points.min(axis=0),mesh.points.max(axis=0)
        self.center=tuple(float(v) for v in (lo+hi)*.5)
        self.extent=max(float((hi-lo).max()),1e-5)
        # Texture cache is independent of the geometry; keep GPU textures.

    def _texture(self,name,data,components):
        arr=np.asarray(data,dtype=np.uint8)
        if arr.ndim!=3 or arr.shape[2]!=components:
            raise ValueError('Dados de textura inválidos.')
        entry=self.tex_cache.get(name)
        # Keep an identity reference to prevent Python recycling an old id.
        if entry is not None and entry[0] is data and entry[2]==arr.shape:
            return entry[1]
        if entry is not None:
            entry[1].release()
        height,width=arr.shape[:2]
        if height*width>4096*4096:
            raise ValueError('Textura acima do limite da GPU.')
        image=self.ctx.texture((width,height),components,
                               np.ascontiguousarray(np.flipud(arr)).tobytes(),alignment=1)
        image.filter=(self.gl.LINEAR,self.gl.LINEAR)
        image.repeat_x=False
        image.repeat_y=False
        self.tex_cache[name]=(data,image,arr.shape)
        return image

    def _fbo(self,width,height):
        if self.frame_size!=(width,height):
            if self.framebuffer is not None:
                self.framebuffer.release()
            self.framebuffer=self.ctx.simple_framebuffer((width,height),components=4)
            self.frame_size=(width,height)
        return self.framebuffer

    def render_to(self,target,mesh,albedo,maes,normal_map,yaw,pitch,zoom,width,height,
               pan_x=0.,pan_y=0.,light=1.0,emission=1.0,
               ambient=1.0,environment='Estúdio',clear=True):
        self._thread_check()
        _validate_settings(light,emission,ambient,environment)
        width,height=max(1,int(width)),max(1,int(height))
        self._set_mesh(mesh)
        extent=self.extent
        unit=min(width*.62,height*.74)/extent*zoom
        target.use()
        self.ctx.enable(self.gl.DEPTH_TEST)
        if clear:
            target.clear(0.,0.,0.,0.,depth=1.0)
        props={
            'u_yaw':float(yaw),'u_pitch':float(pitch),
            'u_unit':float(unit),'u_depth_span':float(extent)*2.0,
            'u_pan':(float(pan_x),float(pan_y)),
            'u_resolution':(float(width),float(height)),
            'u_center':self.center,
            'u_light':float(light),'u_emission':float(emission),
            'u_ambient':float(ambient),
            'u_sky_tint':ENV_PRESETS[environment][0],
            'u_ground_tint':ENV_PRESETS[environment][1],
            'u_light_dir':(.35,.77,.53),
            'u_use_normal':int(normal_map is not None),
            'u_albedo':0,'u_maes':1,'u_normalmap':2,
        }
        for name,value in props.items():
            self.program[name].value=value
        self._texture('albedo',albedo,3).use(location=0)
        if maes is None:
            maes=self._neutral_maes
        self._texture('maes',maes,4).use(location=1)
        if normal_map is None:
            normal_map=self._neutral_normal
        self._texture('normal',normal_map,3).use(location=2)
        self.vao.render(mode=self.gl.TRIANGLES)
        self.render_calls+=1

    def render(self,mesh,albedo,maes,normal_map,yaw,pitch,zoom,width,height,
               pan_x=0.,pan_y=0.,light=1.0,emission=1.0,
               ambient=1.0,environment='Estúdio',canvas_size=None):
        width=int(max(100,min(width,900)))
        height=int(max(100,min(height,900)))
        fbo=self._fbo(width,height)
        self.ctx.viewport=(0,0,width,height)
        self.render_to(fbo,mesh,albedo,maes,normal_map,yaw,pitch,zoom,width,height,
                       pan_x,pan_y,light,emission,ambient,environment)
        pixels=fbo.read(components=4,alignment=1)
        model=Image.frombytes('RGBA',(width,height),pixels).transpose(Image.Transpose.FLIP_TOP_BOTTOM)
        return Image.alpha_composite(studio_background(width,height,canvas_size).convert('RGBA'),model).convert('RGB')

    def release(self):
        for entry in self.tex_cache.values():
            entry[1].release()
        self.tex_cache.clear()
        for name in ('vao','geometry','framebuffer','program'):
            item=getattr(self,name,None)
            if item is not None:
                item.release()
                setattr(self,name,None)


_THREAD=threading.local()


def render_preview(mesh,albedo,maes,normal_map,yaw,pitch,zoom,width,height,
                   pan_x=0.,pan_y=0.,show_reference=False,light=1.0,
                   emission=1.0,force_cpu=False,ambient=1.0,
                   environment='Estúdio',canvas_size=None):
    """Render on worker only; automatically fallback on unsupported hardware."""
    _validate_settings(float(light),float(emission),float(ambient),environment)
    if not show_reference and not force_cpu:
        try:
            gpu=getattr(_THREAD,'gpu',None)
            if gpu is None and not getattr(_THREAD,'no_gpu',False):
                gpu=GPUPreview()
                _THREAD.gpu=gpu
            if gpu is not None:
                img=gpu.render(mesh,albedo,maes,normal_map,yaw,pitch,zoom,width,
                               height,pan_x,pan_y,light,emission,ambient,environment,canvas_size)
                return img,'GPU OpenGL 3.3 · PBR (prévia)'
        except Exception as exc:
            # Expose a short diagnostic instead of hiding a driver/shader issue.
            _THREAD.no_gpu=True
            _THREAD.gpu=None
            _THREAD.gpu_error=f'{type(exc).__name__}: {str(exc)[:95]}'
    if len(mesh.triangles)>4500:
        img=draw_fast(mesh,albedo,yaw,pitch,zoom,width,height,pan_x,pan_y,
                      show_reference,1.75,canvas_size)
        backend='CPU · Albedo rápido colorido'
    else:
        img=draw(mesh,albedo,yaw,pitch,zoom,width,height,pan_x,pan_y,
                 False,show_reference,1.75,canvas_size)
        backend='CPU · Albedo texturizado'
    reason=getattr(_THREAD,'gpu_error',None)
    if reason and not force_cpu:
        backend+=' · OpenGL indisponível: '+reason[:63]
    return img,backend


def gpu_available() -> bool:
    try:
        import moderngl
        return True
    except ImportError:
        return False
