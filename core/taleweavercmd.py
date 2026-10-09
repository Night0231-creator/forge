"""Official TaleWeaverCmd -srcDir pipeline.

Input contract validated against the README.txt provided with TaleSpire:
model.obj, albedo.png, metallic_ao_emis_smoothness.png, normals.png,
thumbnail.png, params.json; output converted.tsMod in source directory.
"""
from __future__ import annotations

import json
import math
import os
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Callable
from .geometry import inspect_obj, suggest_factor, suggest_safe_factor

REQUIRED_FILES = (
    'model.obj', 'albedo.png', 'metallic_ao_emis_smoothness.png',
    'normals.png', 'thumbnail.png', 'params.json',
)
IMAGE_MAP = {
    'albedo.png': 'Albedo.png',
    'metallic_ao_emis_smoothness.png': 'MAES.png',
    'normals.png': 'Normal.png',
    'thumbnail.png': 'thumbnail.png',
}


def find_taleweavercmd() -> str | None:
    from .discovery import find_taleweavercmd as detect_cmd
    return detect_cmd()


def nearby_readme(executable: str | Path) -> Path | None:
    p = Path(executable)
    for folder in (p.parent, p.parent.parent):
        for name in ('README.txt', 'readme.txt', 'README.md'):
            if (folder / name).is_file():
                return folder / name
    return None


def default_points(height: float) -> dict:
    """Approximate positions for upright, humanoid miniatures in Y-up TaleSpire.

    These are guesses derived from height, not inferred anatomically from model.
    """
    return {
        'Head': {'x': 0.0, 'y': round(height * .89, 4), 'z': 0.0},
        'Spell': {'x': round(-height * .22, 4), 'y': round(height * .7, 4), 'z': round(height * .12, 4)},
        'Hit': {'x': 0.0, 'y': round(height * .62, 4), 'z': 0.0},
        'Torch': {'x': round(height * .17, 4), 'y': round(height * .81, 4), 'z': round(height * .23, 4)},
    }


def build_params(name: str, height: float = 1.75) -> dict:
    """Schema and case are from TaleWeaverCmd's shipped README.txt."""
    if not (0.1 <= float(height) <= 40):
        raise ValueError('Altura inválida para gerar os pontos do personagem.')
    return {
        'Name': name.replace('_', ' '),
        'Description': 'Miniatura preparada com Astronyx Mini Forge a partir de um modelo 3D.',
        'UsePaint': True,
        'UseEmissive': False,
        'PointsOfInterest': default_points(float(height)),
        'TsTags': [],
        'CustomTags': [],
        'ThirdPartyToolId': 'Astronyx Mini Forge v1.7',
    }


def resize_obj_vertices(source: Path, destination: Path, scale: float) -> int:
    """Uniform scale of OBJ vertex coordinates; does not touch original OBJ/UV/textures.

    OBJ position lines start with 'v ' (vt/vn must remain unmodified).
    """
    if not math.isfinite(scale) or not 0.1 <= scale <= 100.0:
        raise ValueError('Multiplicador invalido: escolha de 0,1 ate 100.')
    if scale == 1:
        shutil.copy2(source, destination)
        return 0
    count = 0
    with source.open('r', encoding='utf-8', errors='replace') as inp, destination.open('w', encoding='utf-8', newline='\n') as out:
        for line in inp:
            if line.startswith('v '):
                fields = line.split()
                if len(fields) < 4:
                    raise ValueError('Linha de vertice OBJ invalida.')
                xyz = [float(v) for v in fields[1:4]]
                if not all(math.isfinite(v) for v in xyz):
                    raise ValueError('Vertice OBJ com coordenadas nao finitas.')
                new_xyz = [format(v * scale, '.9g') for v in xyz]
                out.write('v ' + ' '.join(new_xyz + fields[4:]) + '\n')
                count += 1
            else:
                out.write(line)
    if not count:
        raise ValueError('OBJ sem vertices nao pode ser redimensionado.')
    return count


def adjusted_points(data: dict, factor: float) -> dict:
    result = dict(data)
    points = result.get('PointsOfInterest')
    if not isinstance(points, dict):
        raise ValueError('O params.json nao possui PointsOfInterest validos.')
    result['PointsOfInterest'] = {
        name: {axis: round(float(coords[axis]) * factor, 6) for axis in ('x', 'y', 'z')}
        for name, coords in points.items()
    }
    return result


def prepare_cmd_input(folder: Path, name: str, height: float = 1.75, *, preserve_params: bool = False, scale_factor: float = 1.0,
                      target_height: float | None = None) -> Path:
    """Create exact official files, without affecting original 3D materials."""
    folder = Path(folder).resolve()
    # Manual mode stays backwards compatible with already-prepared OBJ files.
    # Detailed geometry inspection is mandatory only for automatic scaling.
    source_stats = (inspect_obj(folder / 'TaleWeaverCmd_Source' / f'{name}.obj')
                    if target_height is not None else None)
    scale_factor = (suggest_safe_factor(source_stats, float(target_height)) if source_stats is not None
                    else float(scale_factor))
    actual_height = (source_stats.height if source_stats is not None else height) * scale_factor
    if not math.isfinite(scale_factor) or not 0.1 <= scale_factor <= 100:
        raise ValueError('Multiplicador de escala deve ficar entre 0,1 e 100.')
    source = folder / 'TaleWeaverCmd_Source'
    obj_file = source / f'{name}.obj'
    missing = [p for p in (obj_file, *(source / f for f in IMAGE_MAP.values())) if not p.is_file()]
    if missing:
        raise FileNotFoundError('Arquivos faltando após processamento Blender: ' + ', '.join(p.name for p in missing))
    stage = folder / 'Entrada_TaleWeaverCmd'
    stage.mkdir(parents=True, exist_ok=True)
    resize_obj_vertices(obj_file, stage / 'model.obj', scale_factor)
    for dest, src in IMAGE_MAP.items():
        shutil.copy2(source / src, stage / dest)
    paramfile = stage / 'params.json'
    scale_metadata = folder / 'TaleWeaverCmd_escala.json'
    previous_factor = 1.0
    if scale_metadata.exists():
        try:
            previous_factor = float(json.loads(scale_metadata.read_text(encoding='utf-8'))['scale_factor'])
        except (ValueError, KeyError, TypeError, OSError):
            previous_factor = 1.0
    if not preserve_params or not paramfile.is_file():
        params = build_params(name, max(0.1, actual_height))
    else:
        params = json.loads(paramfile.read_text(encoding='utf-8'))
        if not math.isclose(scale_factor, previous_factor):
            params = adjusted_points(params, scale_factor / previous_factor)
    paramfile.write_text(json.dumps(params, ensure_ascii=False, indent=2), encoding='utf-8')
    ensure_cmd_files(stage)
    scale_metadata.write_text(json.dumps({'scale_factor': scale_factor, 'original_height': height,
                                           'source_height': (source_stats.height if source_stats else height),
                                           'effective_height': actual_height,
                                           'width': (source_stats.width * scale_factor if source_stats else None),
                                           'depth': (source_stats.depth * scale_factor if source_stats else None)}, indent=2), encoding='utf-8')
    return stage


def ensure_cmd_files(stage: Path) -> None:
    missing = [x for x in REQUIRED_FILES if not (stage / x).is_file()]
    if missing:
        raise FileNotFoundError('TaleWeaverCmd exige estes arquivos: ' + ', '.join(missing))
    for f in REQUIRED_FILES:
        if (stage / f).stat().st_size == 0:
            raise ValueError('Arquivo vazio: ' + f)
    params = json.loads((stage / 'params.json').read_text(encoding='utf-8'))
    expected = ('Name', 'Description', 'UsePaint', 'UseEmissive',
                'PointsOfInterest', 'TsTags', 'CustomTags')
    if not all(key in params for key in expected):
        raise ValueError('params.json incompleto para TaleWeaverCmd.')


def _backup_existing(path: Path) -> None:
    if path.is_file():
        stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup = path.with_name(f'{path.name}.{stamp}.bak')
        count = 1
        while backup.exists():
            backup = path.with_name(f'{path.name}.{stamp}_{count}.bak')
            count += 1
        shutil.copy2(path, backup)


def run_taleweavercmd(executable: Path, folder: Path, name: str,
                       height: float = 1.75,
                       preserve_params: bool = False,
                       scale_factor: float = 1.0,
                       target_height: float | None = None,
                       on_line: Callable[[str], None] | None = None,
                       on_process: Callable[[subprocess.Popen], None] | None = None) -> Path:
    """Run TaleWeaverCmd and copy its produced .tsMod to the user's folder.

    The real executable isn't bundled. Presence of an output file does NOT prove
    the asset renders in TaleSpire; verify in the game.
    """
    executable = Path(executable).resolve()
    if not executable.is_file():
        raise FileNotFoundError('Selecione TaleWeaverCmd.exe na pasta do TaleSpire.')
    folder = Path(folder).resolve()
    stage = prepare_cmd_input(folder, name, height, preserve_params=preserve_params,
                              scale_factor=scale_factor, target_height=target_height)
    try:
        measured = json.loads((folder / 'TaleWeaverCmd_escala.json').read_text(encoding='utf-8'))
        if on_line:
            on_line(f"Escala efetiva: {measured['scale_factor']:.3f}x | altura real: "
                    f"{float(measured.get('effective_height', measured['original_height'])):.2f} un.")
            if target_height is not None and float(measured.get('effective_height', 0)) < target_height*.9:
                on_line('Aviso: a base limitou a escala; confira armas e asas muito largas.')
    except (OSError, ValueError, KeyError, TypeError):
        pass
    output = stage / 'converted.tsMod'
    # Remove only the previous generated staging output to forbid false positives.
    # Preserve user's last finished mini in the parent folder.
    if output.exists():
        output.unlink()
    log_path = stage / 'taleweavercmd.log'
    args = [str(executable), '-srcDir', str(stage), '-logFile', str(log_path)]
    process = subprocess.Popen(args, cwd=str(executable.parent), stdin=subprocess.DEVNULL,
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                               encoding='utf-8', errors='replace', bufsize=1,
                               creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    if on_process:
        on_process(process)
    tail = []
    if process.stdout is not None:
        for line in process.stdout:
            clean = line.rstrip()
            tail.append(clean)
            if len(tail) > 35:
                tail.pop(0)
            if on_line:
                on_line(clean)
    code = process.wait()
    if process.stdout is not None:
        process.stdout.close()
    if code:
        raise RuntimeError(f'TaleWeaverCmd retornou código {code}. Consulte {log_path}.\n' + '\n'.join(tail[-12:]))
    if not output.is_file() or output.stat().st_size < 64:
        raise RuntimeError('TaleWeaverCmd terminou sem criar converted.tsMod válido. '
                           f'Veja o log em {log_path} e os arquivos em {stage}.\n' + '\n'.join(tail[-12:]))
    final = folder / f'{name}.tsMod'
    _backup_existing(final)
    shutil.copy2(output, final)
    if on_line:
        on_line('Arquivo .tsMod criado: ' + str(final) + ' (teste no TaleSpire recomendado)')
    return final
