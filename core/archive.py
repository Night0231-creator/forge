"""Safely open Meshy ZIP downloads locally, without cloud calls."""
from __future__ import annotations

import shutil
from pathlib import Path, PurePosixPath
from zipfile import ZipFile, BadZipFile

MODEL_EXTENSIONS = ('.glb', '.blend', '.fbx', '.obj', '.gltf', '.stl')
MAX_UNCOMPRESSED = 900 * 1024 * 1024
MAX_FILES = 1500


def extract_meshy_zip(archive: Path, destination: Path) -> Path:
    """Extract and return a model file, leaving source ZIP untouched.

    Reject ZIP traversal, symlinks, giant compressed archives and encrypted files.
    Preserve adjacent OBJ/GLTF textures and reference files.
    """
    destination = Path(destination).resolve()
    destination.mkdir(parents=True, exist_ok=True)
    try:
        with ZipFile(archive) as zipfile:
            infos = zipfile.infolist()
            if len(infos) > MAX_FILES:
                raise ValueError('ZIP com arquivos demais; extraia manualmente e escolha o modelo.')
            total = sum(info.file_size for info in infos)
            if total > MAX_UNCOMPRESSED:
                raise ValueError('ZIP grande demais (limite 900 MB descompactados).')
            files = []
            for info in infos:
                rel = PurePosixPath(info.filename.replace('\\', '/'))
                if not rel.parts or rel.is_absolute() or '..' in rel.parts or ':' in rel.parts[0]:
                    raise ValueError('ZIP contém caminho inseguro: ' + info.filename)
                if info.flag_bits & 1:
                    raise ValueError('ZIP protegido por senha não é suportado.')
                # Unix symlinks inside ZIP are unsafe for extracted 3D resources.
                if ((info.external_attr >> 16) & 0o170000) == 0o120000:
                    raise ValueError('ZIP contém link simbólico; exporte um ZIP normal do Meshy.')
                target = destination.joinpath(*rel.parts)
                if not target.resolve().is_relative_to(destination):
                    raise ValueError('ZIP contém caminho fora da pasta de extração.')
                if info.is_dir():
                    target.mkdir(parents=True, exist_ok=True)
                else:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    with zipfile.open(info) as src, target.open('wb') as dst:
                        shutil.copyfileobj(src, dst)
                    if target.suffix.casefold() in MODEL_EXTENSIONS:
                        files.append(target)
            if not files:
                raise ValueError('ZIP não contém modelo .glb, .blend, .fbx, .obj, .gltf ou .stl.')
            # Prefer self-contained GLB; otherwise prefer the original .blend.
            rank = {ext: idx for idx, ext in enumerate(MODEL_EXTENSIONS)}
            files.sort(key=lambda p: (rank[p.suffix.casefold()], -p.stat().st_size, str(p)))
            return files[0]
    except BadZipFile as ex:
        raise ValueError('Arquivo ZIP inválido ou danificado.') from ex
