"""Helpers for Astronyx Mini Forge (no external Python dependencies)."""
from __future__ import annotations

import json
import re
from pathlib import Path

from .version import APP_VERSION

SUPPORTED = {".blend", ".glb", ".gltf", ".fbx", ".obj", ".stl", ".zip"}


def safe_slug(value: str) -> str:
    value = re.sub(r"[^\w\-]+", "_", value.strip(), flags=re.UNICODE)
    value = value.strip("_-.")
    value = re.sub(r"_+", "_", value)
    return (value or "Miniatura")[:65]


def find_blender() -> str | None:
    from .discovery import find_blender as detect_blender
    return detect_blender()



def validate_config(data: dict) -> dict:
    src = Path(str(data.get("source", ""))).expanduser()
    if not src.is_file() or src.suffix.lower() not in SUPPORTED:
        raise ValueError("Escolha um modelo existente .blend, .glb, .gltf, .fbx, .obj, .stl ou .zip.")
    dest = Path(str(data.get("output_root", ""))).expanduser()
    if not str(data.get("output_root", "")).strip():
        raise ValueError("Escolha a pasta para salvar os resultados.")
    if dest.exists() and not dest.is_dir():
        raise ValueError("O destino precisa ser uma pasta.")
    name = safe_slug(str(data.get("name", src.stem)))
    height = float(data.get("height", 1.75))
    angle = float(data.get("rotation", 0))
    tris = int(data.get("tris", 100000))
    tex = int(data.get("texture_size", 2048))
    if not (0.1 <= height <= 40):
        raise ValueError("A altura precisa estar entre 0,1 e 40 unidades.")
    if not (-360 <= angle <= 360):
        raise ValueError("A rotação deve ficar entre -360° e +360°.")
    if not (500 <= tris <= 120000):
        raise ValueError("O limite deve ficar entre 500 e 120.000 triângulos.")
    if tex not in (512, 1024, 2048, 4096):
        raise ValueError("Use texturas de 512, 1024, 2048 ou 4096 px.")
    src_abs = src.resolve()
    target = (dest / name).resolve()
    if target == src_abs.parent or src_abs.is_relative_to(target):
        raise ValueError("Escolha uma pasta de saída fora da pasta de origem do modelo.")
    return {
        "source": str(src_abs),
        "output_root": str(dest.resolve()),
        "name": name,
        "height": height,
        "rotation": angle,
        "tris": tris,
        "texture_size": tex,
        "create_plugin": bool(data.get("create_plugin", True)),
        "create_taleweavercmd": bool(data.get("create_taleweavercmd", False)),
    }


def create_instructions(destination: Path, name: str, stats: dict) -> None:
    guide = f"""ASTRONYX MINI FORGE V{APP_VERSION} — {name}
==============================================

RESULTADO OFICIAL DO TALESPIRE
- Se existir {name}.tsMod nesta pasta, ele foi gerado pelo TaleWeaverCmd
  oficial e deve ser testado no TaleSpire antes de ser compartilhado.
- Se NAO existir o .tsMod, veja a mensagem de erro no programa.
- A pasta Entrada_TaleWeaverCmd tem os seis arquivos exigidos:
    model.obj
    albedo.png
    normals.png
    metallic_ao_emis_smoothness.png
    thumbnail.png
    params.json

COMO INSTALAR
1. TaleSpire -> Settings -> Open Settings Directory.
2. Entre em LocalContentPacks.
3. Copie o arquivo {name}.tsMod para essa pasta.
4. Abra/reinicie TaleSpire e localize a miniatura.

COMO TENTAR NOVAMENTE (SEM ABRIR BLENDER)
1. Abra Astronyx Mini Forge -> GERAR .TSMOD.
2. Selecione TaleWeaverCmd.exe do TaleSpire.
3. Clique em 'Gerar .tsMod de uma pasta ja preparada'.
4. Escolha ESTA pasta do personagem ({name}).

DADOS DE CONVERSAO
- Altura: {stats.get('height', 'n/d')} unidades
- Triangulos: {stats.get('triangles', 'n/d')}
- Vertices: {stats.get('vertices', 'n/d')}
- Pontos de spell/hit/head/torch sao estimativas para personagem humanoide.
- Nao cria esqueleto ou animacoes.
- O modelo original nao e modificado.

ALTERNATIVAS
- TaleWeaverLite/{name}.fbx + texturas sao arquivos preparados para Unity.
- CustomMiniPlugin/{name} contem arquivos opcionais para mod, NAO e .tsMod.

LEMBRETE
O Mini Forge nao distribui Blender nem TaleWeaverCmd.
Execute o .exe oficial do TaleSpire; use apenas modelos permitidos.
"""
    (destination / "LEIA_PRIMEIRO.txt").write_text(guide, encoding="utf-8")


def write_manifest(destination: Path, cfg: dict, stats: dict):
    public_cfg = {key: value for key, value in cfg.items()
                  if key not in ("source", "output_root")}
    public_cfg["original_filename"] = Path(cfg["source"]).name
    (destination / "conversao.json").write_text(
        json.dumps({"app": "Astronyx Mini Forge", "version": APP_VERSION, "settings": public_cfg,
                    "stats": stats, "official_tsmod_created": False}, ensure_ascii=False, indent=2),
        encoding="utf-8")
