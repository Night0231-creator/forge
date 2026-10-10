"""Local, read-only scale diagnostics for Meshy -> TaleWeaverCmd -> TaleSpire.

Does not decode .tsMod internals, pretend the Basecoat reference describes scale,
or upload files. The ZIP includes model geometry only when the user explicitly
requests it from the UI, and the original BLEND is never included.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from .geometry import inspect_obj
from .obj_vertex_budget import inspect_obj_vertex_budget


def _optional_json(path: Path) -> dict:
    if not path.is_file():
        return {}
    try:
        value = json.loads(path.read_text(encoding='utf-8-sig'))
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError, UnicodeError):
        return {}


def _model_size(path: Path) -> dict | None:
    if not path.is_file():
        return None
    stats = inspect_obj(path)
    vertices = inspect_obj_vertex_budget(path)
    return {
        'height': round(stats.height, 6),
        'width': round(stats.width, 6),
        'depth': round(stats.depth, 6),
        'positions': stats.vertices,
        'faces': stats.faces,
        'split_vertices_estimate': vertices.split_vertices,
    }


def build_scale_report(folder: str | Path) -> dict:
    """Report the two real OBJ stages, metadata and possible size loss."""
    root = Path(folder).expanduser().resolve()
    source = root / 'TaleWeaverCmd_Source'
    stage = root / 'Entrada_TaleWeaverCmd'
    if not root.is_dir() or not source.is_dir():
        raise FileNotFoundError('Escolha a pasta do projeto com TaleWeaverCmd_Source.')
    obj = source / (root.name + '.obj')
    if not obj.is_file():
        candidates = list(source.glob('*.obj'))
        if len(candidates) != 1:
            raise FileNotFoundError('Não foi possível identificar um único OBJ fonte.')
        obj = candidates[0]
    original = _model_size(obj)
    prepared = _model_size(stage / 'model.obj')
    blender = _optional_json(root / 'blender_stats.json')
    scale = _optional_json(root / 'TaleWeaverCmd_escala.json')
    params = _optional_json(stage / 'params.json')
    expected = scale.get('scale_factor')
    issues = []
    if not prepared:
        issues.append('Não existe Entrada_TaleWeaverCmd/model.obj: exportação final ausente.')
    elif original and original['height'] > 1e-6:
        measured = prepared['height'] / original['height']
        if isinstance(expected, (int, float)) and math.isfinite(expected):
            if not math.isclose(measured, expected, rel_tol=.025, abs_tol=.005):
                issues.append(
                    'O OBJ final não corresponde ao multiplicador registrado '
                    f'({measured:.4f}x medido; {expected:.4f}x esperado).')
        if measured < .5:
            issues.append(
                'O OBJ final ficou com menos de metade da altura original. '
                'Verifique a escala automática e o multiplicador registrado.')
    if original and blender.get('height') is not None:
        try:
            if not math.isclose(float(blender['height']), original['height'],
                                rel_tol=.03, abs_tol=.03):
                issues.append('Altura do OBJ fonte difere da altura do relatório Blender.')
        except (TypeError, ValueError):
            issues.append('Altura registrada pelo Blender é inválida.')
    if prepared and prepared['height'] >= .5:
        issues.append(
            'A escala visual no tabuleiro NÃO pode ser confirmada pelos arquivos OBJ. '
            'Compare este relatório com o .tsMod produzido nesta mesma tentativa.')
    return {
        'schema_version': 1,
        'note': (
            'Medidas de arquivo em unidades de malha. Não há dados confiáveis '
            'de Default Scale do TaleSpire nem escala interna do .tsMod Basecoat. '
            'Nenhum conteúdo é enviado à rede automaticamente.'
        ),
        'project_name': root.name,
        'blender_report_height': blender.get('height'),
        'blender_requested_height': blender.get('requested_height'),
        'blender_width': blender.get('width'),
        'blender_vertex_count': blender.get('vertices'),
        'vertex_reductions': blender.get('taleweavercmd_vertex_reductions'),
        'obj_source': original,
        'obj_sent_to_taleweavercmd': prepared,
        'recorded_scale_factor': expected,
        'recorded_effective_height': scale.get('effective_height'),
        'params_points': list(params.get('PointsOfInterest', {}).keys())
        if isinstance(params.get('PointsOfInterest'), dict) else [],
        'tsmod_exists': (root / (obj.stem + '.tsMod')).is_file(),
        'observations': issues,
    }


def save_scale_diagnostics(folder: str | Path, *, create_zip: bool = True) -> tuple[Path, Path | None]:
    """Generate a local report and optional user-shareable ZIP.

    ZIP includes only known generated outputs: geometry, logs and metadata.
    Never includes original .blend or linked external images and never uploads.
    """
    root = Path(folder).expanduser().resolve()
    report = build_scale_report(root)
    output = root / 'diagnostico_escala.json'
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    if not create_zip:
        return output, None

    archive = root / 'Diagnostico_Escala_Astronyx.zip'
    source = root / 'TaleWeaverCmd_Source'
    stage = root / 'Entrada_TaleWeaverCmd'
    filenames = [
        output, root / 'blender_stats.json', root / 'TaleWeaverCmd_escala.json',
        source / (root.name + '.obj'), stage / 'model.obj',
        stage / 'params.json', stage / 'taleweavercmd.log',
        root / (root.name + '.tsMod'),
    ]
    # Support renamed project folders when the actual OBJ is unique.
    filenames.extend(source.glob('*.obj'))
    filenames.extend(root.glob('*.tsMod'))
    included = set()
    with ZipFile(archive, 'w', compression=ZIP_DEFLATED, compresslevel=5) as zipfile:
        for file in filenames:
            if not file.is_file() or file in included:
                continue
            if file.stat().st_size > 150 * 1024 * 1024:
                continue
            included.add(file)
            zipfile.write(file, arcname=file.relative_to(root).as_posix())
    return output, archive
