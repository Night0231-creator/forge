"""Export read-only TaleWeaverLite Unity handoff from an Astronyx project.

Creature visual Transform and gameplay Default Scale are separate in Unity's
TaleWeaverLite UI. TaleWeaverCmd does not expose a documented equivalent in
its params.json; do not inject speculative keys into that schema.
"""
from __future__ import annotations

import json
import math
import statistics
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from .geometry import inspect_obj

UNITY_INSTALL = "https://talespire.com/taleweaverlite-install-guide"
UNITY_GUIDE = "https://talespire.com/taleweaverlite-guide"
MAX_ZIP_ITEM = 150 * 1024 * 1024
PNG_SIGNATURE = b'\x89PNG\r\n\x1a\n'


def _find_source(root: Path) -> Path:
    directory = root / 'TaleWeaverCmd_Source'
    if not directory.is_dir():
        raise FileNotFoundError('Projeto sem TaleWeaverCmd_Source: converta o modelo antes.')
    expected = directory / f'{root.name}.obj'
    if expected.is_file():
        return expected
    matches = list(directory.glob('*.obj'))
    if len(matches) != 1:
        raise FileNotFoundError('Não há um OBJ único no TaleWeaverCmd_Source.')
    return matches[0]


def _foot_pivot(source: Path, bottom: float, height: float) -> tuple[float, float]:
    """Median X/Z from low-lying vertices; heuristics, not rigged foot bones."""
    coords_x, coords_z = [], []
    threshold = bottom + max(height * 0.05, 0.0001)
    with source.open('r', encoding='utf-8-sig', errors='replace') as fh:
        for line in fh:
            if line.startswith('v '):
                p = line.split()
                if len(p) < 4:
                    raise ValueError('OBJ contém vértice incompleto.')
                x, y, z = [float(v) for v in p[1:4]]
                if not all(math.isfinite(v) for v in (x,y,z)):
                    raise ValueError('OBJ contém coordenadas inválidas.')
                if y <= threshold:
                    coords_x.append(x)
                    coords_z.append(z)
    if not coords_x:
        return 0., 0.
    return float(statistics.median(coords_x)), float(statistics.median(coords_z))


def _copy_anchored_obj(source: Path, destination: Path,
                       foot_x: float, foot_z: float, floor_y: float) -> None:
    """Translate positions only; leave UVs, normals and topology untouched."""
    with source.open('r', encoding='utf-8-sig', errors='replace') as incoming, \
         destination.open('w', encoding='utf-8', newline='\n') as outgoing:
        outgoing.write('# Astronyx TaleWeaverLite optional foot-pivot preview\n')
        for line in incoming:
            if line.startswith('mtllib '):
                outgoing.write('mtllib Astronyx_Unity.mtl\n')
            elif line.startswith('usemtl '):
                outgoing.write('usemtl AstronyxMini\n')
            elif line.startswith('v '):
                parts=line.split()
                x,y,z = [float(v) for v in parts[1:4]]
                parts[1:4]=[format(x-foot_x, '.9g'),
                             format(y-floor_y, '.9g'),
                             format(z-foot_z, '.9g')]
                outgoing.write(' '.join(parts)+'\n')
            else:
                outgoing.write(line)


def _texture(root: Path, name: str) -> Path:
    for folder in (root / 'TaleWeaverLite', root / 'TaleWeaverCmd_Source'):
        p=folder/name
        if p.is_file():
            with p.open('rb') as fh:
                if fh.read(8) != PNG_SIGNATURE:
                    raise ValueError(f'{p.name} não é PNG válido.')
            return p
    raise FileNotFoundError(f'Textura {name} não encontrada na conversão.')


def _add_file(zipper: ZipFile, source: Path, entry: str) -> None:
    if not source.is_file() or source.stat().st_size > MAX_ZIP_ITEM:
        raise ValueError(f'Arquivo ausente/grande demais no pacote: {source}')
    zipper.write(source, entry)


def prepare_taleweaverlite_handoff(
    project_folder: str | Path, *, visual_multiplier: float = 8.0,
    default_scale: int = 1
) -> tuple[Path, dict]:
    """Package existing mesh/texture + Unity instructions, no .tsMod rewriting.

    This does NOT run Unity or guarantee collision/drag behavior in the game.
    The 8x setting is a *suggestion* from the user's Eclipse test screenshot.
    """
    if not math.isfinite(visual_multiplier) or not 0.5 <= visual_multiplier <= 12:
        raise ValueError('Multiplicador visual deve ficar entre 0,5 e 12.')
    if default_scale != 1:
        raise ValueError('Este fluxo experimental é exclusivamente para miniaturas 1×1.')
    root=Path(project_folder).expanduser().resolve()
    if not root.is_dir():
        raise FileNotFoundError('Pasta do projeto não encontrada.')
    obj = _find_source(root)
    stats=inspect_obj(obj)
    if stats.height <= 1e-6:
        raise ValueError('Modelo sem altura suficiente para calibrar.')
    foot_x, foot_z = _foot_pivot(obj, stats.min_xyz[1], stats.height)
    source_dir = root / 'TaleWeaverLite'
    fbx=next(iter(sorted(source_dir.glob('*.fbx'))), None) if source_dir.is_dir() else None
    textures={key:_texture(root, key) for key in ('Albedo.png','Normal.png','MAES.png')}

    report={
        'mode': 'TaleWeaverLite manual handoff',
        'not_an_automatic_scale_fix': True,
        'source_project': root.name,
        'source_obj_height': round(stats.height,5),
        'source_obj_width': round(stats.width,5),
        'source_obj_depth': round(stats.depth,5),
        'estimated_foot_anchor_xyz': [
            round(foot_x,5),round(stats.min_xyz[1],5),round(foot_z,5)
        ],
        'suggested_unity_mesh_transform_scale': visual_multiplier,
        'requested_talespire_default_scale': default_scale,
        'estimated_preview_mesh_height': round(stats.height*visual_multiplier,5),
        'anchor_is_heuristic': True,
        'unity_requires_manual_install': True,
        'movement_and_base_not_yet_validated': True,
    }
    instructions=(
        'ASTRONYX MINI FORGE — TALEWEAVERLITE (UNITY) — TESTE 1x1\n'
        '========================================================\n\n'
        'Este pacote NAO e um .tsMod final. A exportacao deve ser concluida\n'
        'dentro do TaleWeaverLite (projeto Unity oficial).\n\n'
        f'1) Instale Unity Hub + Unity 2021.3.45f2 e TaleWeaverLite:\n{UNITY_INSTALL}\n'
        '2) Abra o projeto TaleWeaverLite no Unity. Importe os arquivos da\n'
        '   pasta Modelo (OBJ com ancora ou FBX) e as tres texturas PNG.\n'
        '3) Use Model_PivoPes.obj para TESTAR a origem reposicionada nos pes.\n'
        '   O arquivo FBX original tambem foi incluido como alternativa.\n'
        '4) No painel Creature Mod atribua Mesh, Albedo, Normal e MAES.\n'
        '5) Ajuste a escala visual no TRANSFORM do modelo; comece com\n'
        f'   {visual_multiplier:.2f}x (experimento baseado no Eclipse Warlord 8x).\n'
        '   NAO amplie o OBJ novamente no Mini Forge; ajuste somente uma etapa.\n'
        '6) Configure Default Scale = 1 no Creature Mod, que determina a\n'
        '   escala inicial da criatura no tabuleiro (separada do Transform).\n'
        '7) Ajuste Head/Hit/Spell/Torch de acordo com o corpo VISIVEL e\n'
        '   verifique se os pes tocam o chao antes de salvar .tsMod.\n'
        '8) Exporte e teste no TaleSpire com tamanho 1x1 selecionado, depois\n'
        '   arraste, solte e caminhe. Se a base ou o arraste continuarem\n'
        '   errados, diminua a escala visual no Unity e ajuste as ancoras.\n\n'
        'AVISOS: O transform nao garante base 1x1 nem movimentacao correta.\n'
        'O deslocamento automatico dos pes e aproximado para malhas sem rig.\n'
        'Nao misture um prefab FBX e um OBJ simultaneamente na mesma criatura.\n'
        f'Documentacao oficial: {UNITY_GUIDE}\n'
    )
    archive=root / 'Astronyx_TaleWeaverLite_1x1.zip'
    # Temp lives on local disk and is deleted regardless of packaging result.
    import tempfile
    with tempfile.TemporaryDirectory(prefix='amf_twl_') as temp:
        anchored=Path(temp)/'Model_PivoPes.obj'
        _copy_anchored_obj(obj,anchored,foot_x,foot_z,stats.min_xyz[1])
        with ZipFile(archive,'w',compression=ZIP_DEFLATED,compresslevel=6) as z:
            _add_file(z,anchored,'Modelo/Model_PivoPes.obj')
            z.writestr('Modelo/Astronyx_Unity.mtl',
                       'newmtl AstronyxMini\nKd 1 1 1\nKs 0 0 0\n'
                       'd 1\nillum 2\nmap_Kd Albedo.png\n')
            for name,path in textures.items():
                _add_file(z,path,'Modelo/'+name)
            if fbx is not None:
                _add_file(z,fbx,'Modelo/FBX_Original/'+fbx.name)
            z.writestr('CALIBRACAO.json',json.dumps(report,indent=2,ensure_ascii=False))
            z.writestr('LEIA_PRIMEIRO.txt',instructions)
    return archive,report
