"""Measured Y-up OBJ footprint preview, not a TaleSpire collider prediction.

The TaleWeaverCmd converter knows the mesh geometry but does not expose a
documented API for physical tile occupancy, drag handles or in-game scaling.
The square drawn by the UI is therefore a 1x1 *unit reference only*.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
import math
from pathlib import Path
import random
import statistics

from .geometry import inspect_obj, ObjStats

HUMANOID_REFERENCE_HEIGHT = 1.75
UNIT_TILE_EDGE = 1.0
MAX_SAMPLE = 2400
MAX_FEET = 2500


@dataclass(frozen=True)
class CalibrationReport:
    source_obj: str
    height: float
    width: float
    depth: float
    min_y: float
    max_y: float
    vertices: int
    faces: int
    ground_center_x: float
    ground_center_z: float
    offset_from_center: float
    core_width: float | None
    core_depth: float | None
    footprint_reference: float
    humanoid_height_reference: float
    observations: tuple[str, ...]
    caveat: str

    def to_dict(self) -> dict:
        return {
            'schema': 'astronyx-1x1-visual-calibration-v1',
            'source_obj': self.source_obj,
            'bounds': {
                'width': self.width, 'height': self.height, 'depth': self.depth,
                'min_y': self.min_y, 'max_y': self.max_y,
                'vertices': self.vertices, 'faces': self.faces,
            },
            'foot_anchor_estimate': {
                'x': self.ground_center_x,
                'z': self.ground_center_z,
                'distance_from_mesh_center': self.offset_from_center,
            },
            'middle_body_projection': {
                'width': self.core_width, 'depth': self.core_depth,
                'method': '5th-95th percentile of vertices in middle 20%-75% height; heuristic',
            },
            'visual_references': {
                'unit_square_edge': self.footprint_reference,
                'humanoid_height': self.humanoid_height_reference,
                'physical_collision_verified': False,
                'default_scale_verified': False,
            },
            'observations': list(self.observations),
            'caveat': self.caveat,
        }


@dataclass(frozen=True)
class CalibrationPreview:
    report: CalibrationReport
    points: tuple[tuple[float, float, float], ...]


def _sample_add(bucket, value, n, maximum, rng):
    if len(bucket) < maximum:
        bucket.append(value)
    else:
        choose = rng.randrange(n)
        if choose < maximum:
            bucket[choose] = value


def _pct(values: list[float], fraction: float) -> float:
    values = sorted(values)
    if len(values) == 1:
        return values[0]
    index = (len(values)-1)*fraction
    low = int(index)
    high = min(low+1,len(values)-1)
    return values[low]*(1-(index-low)) + values[high]*(index-low)


def analyze_footprint(path: str | Path, *, reference_height: float = HUMANOID_REFERENCE_HEIGHT
                      ) -> CalibrationPreview:
    """Inspect actual OBJ vertex coordinates in two streaming passes.

    The preview samples points reproducibly; measurements include *all*
    positions in the model through the ObjStats first pass. Any material,
    attachment or faraway vertex can enlarge the full-width bounds.
    """
    if not math.isfinite(reference_height) or not 0.5 <= reference_height <= 5:
        raise ValueError('Altura de referência deve estar entre 0,5 e 5.')
    path = Path(path)
    bounds: ObjStats = inspect_obj(path)
    if bounds.height < 1e-6:
        raise ValueError('Modelo OBJ tem altura insuficiente para calibrar.')
    rng = random.Random(2214)
    points: list[tuple[float,float,float]] = []
    feet: list[tuple[float,float]] = []
    core: list[tuple[float,float]] = []
    n_feet=n_core=0
    y_min=bounds.min_xyz[1]
    foot_ceiling=y_min + .06*bounds.height
    mid_floor=y_min + .20*bounds.height
    mid_ceil=y_min + .75*bounds.height
    count=0
    with path.open('r',encoding='utf-8-sig',errors='replace') as stream:
        for line in stream:
            if not line.startswith('v '):
                continue
            values=line.split()
            if len(values) < 4:
                raise ValueError('OBJ contém um vértice incompleto.')
            xyz=tuple(float(x) for x in values[1:4])
            if not all(math.isfinite(x) for x in xyz):
                raise ValueError('OBJ contém coordenadas inválidas.')
            count+=1
            _sample_add(points,xyz,count,MAX_SAMPLE,rng)
            x,y,z=xyz
            if y<=foot_ceiling:
                n_feet+=1
                _sample_add(feet,(x,z),n_feet,MAX_FEET,rng)
            if mid_floor<=y<=mid_ceil:
                n_core+=1
                _sample_add(core,(x,z),n_core,MAX_FEET,rng)

    foot_x=statistics.median(x for x,_ in feet) if feet else (bounds.min_xyz[0]+bounds.max_xyz[0])/2
    foot_z=statistics.median(z for _,z in feet) if feet else (bounds.min_xyz[2]+bounds.max_xyz[2])/2
    cx=(bounds.min_xyz[0]+bounds.max_xyz[0])/2
    cz=(bounds.min_xyz[2]+bounds.max_xyz[2])/2
    offset=math.hypot(foot_x-cx,foot_z-cz)
    core_width=(_pct([x for x,_ in core],.95)-_pct([x for x,_ in core],.05)) if len(core)>20 else None
    core_depth=(_pct([z for _,z in core],.95)-_pct([z for _,z in core],.05)) if len(core)>20 else None

    concerns=[]
    if max(bounds.width,bounds.depth) > 2*UNIT_TILE_EDGE:
        concerns.append('A projeção horizontal total supera 2 unidades: verifique acessórios e base visual antes de exportar.')
    elif max(bounds.width,bounds.depth) > 1.25*UNIT_TILE_EDGE:
        concerns.append('A projeção horizontal ultrapassa a referência de 1 unidade; confira a posição dos pés e da base.')
    if bounds.height > 3.0:
        concerns.append('A altura da malha supera 3 unidades: ampliação excessiva pode prejudicar a manipulação no jogo.')
    elif bounds.height < .6:
        concerns.append('A altura da malha é baixa para a referência humanoide; confira o tamanho dentro do TaleSpire.')
    if offset > max(.20, .15*max(bounds.width,bounds.depth)):
        concerns.append('O centro estimado do apoio está deslocado: avalie a origem e a ancoragem nos pés.')
    if core_width is not None and core_depth is not None:
        if max(core_width,core_depth)<max(bounds.width,bounds.depth)*.50:
            concerns.append('A geometria lateral pode incluir acessórios largos; largura total não equivale a tamanho da base.')
    if not concerns:
        concerns.append('Dimensões medidas sem alertas fortes; isso NÃO confirma colisão ou movimentação 1×1.')
    caveat=('Referências de malha: quadrado de 1 unidade e humanoide de '
            f'{reference_height:.2f} unidades. Não representam a colisão, '
            'o tamanho físico real da base ou o Default Scale do TaleSpire; '
            'somente um teste no jogo pode confirmar esses dados.')
    report=CalibrationReport(
        source_obj=path.name,height=round(bounds.height,6),
        width=round(bounds.width,6),depth=round(bounds.depth,6),
        min_y=round(bounds.min_xyz[1],6),max_y=round(bounds.max_xyz[1],6),
        vertices=bounds.vertices,faces=bounds.faces,
        ground_center_x=round(foot_x,6),ground_center_z=round(foot_z,6),
        offset_from_center=round(offset,6),
        core_width=round(core_width,6) if core_width is not None else None,
        core_depth=round(core_depth,6) if core_depth is not None else None,
        footprint_reference=UNIT_TILE_EDGE,
        humanoid_height_reference=reference_height,
        observations=tuple(concerns),caveat=caveat,
    )
    return CalibrationPreview(report,tuple(points))


def find_project_obj(root: str | Path) -> Path:
    """Prefer what TaleWeaverCmd received, then the generated OBJ from Blender."""
    folder=Path(root).expanduser()
    final=folder/'Entrada_TaleWeaverCmd'/'model.obj'
    if final.is_file():
        return final
    source=folder/'TaleWeaverCmd_Source'/(folder.name+'.obj')
    if source.is_file():
        return source
    options=sorted((folder/'TaleWeaverCmd_Source').glob('*.obj')) if (folder/'TaleWeaverCmd_Source').is_dir() else []
    if len(options)==1:
        return options[0]
    raise FileNotFoundError('OBJ não encontrado. Converta o GLB antes de calibrar.')


def write_calibration_report(root: str | Path, obj: str | Path | None = None) -> Path:
    """Write sidecar JSON in the selected project folder; never change OBJ/.tsMod."""
    folder=Path(root).expanduser().resolve()
    if not folder.is_dir():
        raise FileNotFoundError('Pasta da miniatura inexistente.')
    source=Path(obj) if obj is not None else find_project_obj(folder)
    source=source.resolve()
    if not source.is_relative_to(folder):
        raise ValueError('O relatório automático só usa modelos da pasta do projeto.')
    preview=analyze_footprint(source)
    output=folder/'calibracao_visual_1x1.json'
    output.write_text(json.dumps(preview.report.to_dict(),
                      ensure_ascii=False,indent=2),encoding='utf-8')
    return output
