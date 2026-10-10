"""Conservative .tsMod header inspector and safe local-install helpers.

A positive header match is *not* a full-file TaleSpire compatibility test.
The known marker was observed in a real Basecoat-created .tsMod sample.
"""
from __future__ import annotations

import hashlib
import os
import shutil
import struct
from pathlib import Path

KNOWN_MAGIC = bytes.fromhex('ced1ced1')


def inspect_tsmod(filepath: str | Path) -> dict:
    path = Path(filepath)
    if path.suffix.lower() != '.tsmod':
        raise ValueError('Selecione um arquivo com extensão .tsMod.')
    if not path.is_file():
        raise FileNotFoundError(f'Arquivo não encontrado: {path}')
    size = path.stat().st_size
    if size < 16:
        raise ValueError('Arquivo .tsMod pequeno demais para conter um cabeçalho.')
    with path.open('rb') as stream:
        header = stream.read(8192)
    magic, version, text_bytes, aux = header[:4], *struct.unpack_from('<III', header, 4)
    recognized = magic == KNOWN_MAGIC
    metadata = ''
    if recognized and 0 < text_bytes <= 4096 and text_bytes % 2 == 0 and 48 + text_bytes <= len(header):
        metadata = header[48:48 + text_bytes].decode('utf-16le', errors='replace').rstrip('\0')
    producer = 'Basecoat' if 'exported using Basecoat.' in metadata else 'Não identificado'
    return {
        'filename': path.name,
        'size_bytes': size,
        'size_mb': round(size / (1024 * 1024), 2),
        'recognized_header': recognized,
        'header_magic': magic.hex(),
        'format_version': version if recognized else None,
        'header_aux': aux if recognized else None,
        'description': metadata,
        'producer': producer,
        'warning': ('Cabeçalho corresponde ao exemplo recebido, mas isso não garante que o jogo consiga abrir o arquivo.'
                    if recognized else
                    'Cabeçalho diferente do exemplo conhecido. Pode ser uma versão diferente ou arquivo inválido.'),
    }



def compare_tsmod_reference(reference: str | Path, candidate: str | Path) -> dict:
    """Compare a known-good .tsMod and a generated .tsMod safely.

    This comparison does NOT unzip/decompile files, extract meshes, copy
    protected bytes, or claim a functioning asset solely from matching headers.
    Producer, auxiliary field and size are descriptive, not compatibility gates.
    """
    original = inspect_tsmod(reference)
    generated = inspect_tsmod(candidate)
    if not original['recognized_header']:
        raise ValueError('A referência precisa ter um cabeçalho .tsMod reconhecido.')
    if not generated['recognized_header']:
        status = 'cabecalho_diferente'
    elif original['format_version'] != generated['format_version']:
        status = 'versao_diferente'
    else:
        status = 'cabecalho_compatível'
    ref = Path(reference).resolve()
    new = Path(candidate).resolve()
    same = ref == new or (original['size_bytes'] == generated['size_bytes']
                          and _same_file(ref, new))
    return {
        'status': 'arquivo_identico' if same else status,
        'same_file': same,
        'same_magic': original['header_magic'] == generated['header_magic'],
        'same_format_version': (
            original['recognized_header'] and generated['recognized_header']
            and original['format_version'] == generated['format_version']),
        'reference': {key: original[key] for key in (
            'filename', 'size_bytes', 'header_magic', 'format_version',
            'header_aux', 'description', 'producer')},
        'candidate': {key: generated[key] for key in (
            'filename', 'size_bytes', 'header_magic', 'format_version',
            'header_aux', 'description', 'producer')},
        'warning': (
            'A comparação verifica cabeçalho e metadados; NÃO confirma a malha, '
            'texturas, escala, limite de vértices ou funcionamento no TaleSpire. '
            'Não transforma nem usa dados binários da referência como template.'
        ),
    }


def format_tsmod_reference_report(report: dict) -> str:
    """Small, readable UI summary for Basecoat or TaleWeaverCmd comparisons."""
    base, result = report['reference'], report['candidate']
    if report['same_file']:
        headline = 'Você selecionou o mesmo arquivo (ou uma cópia idêntica).'
    elif report['same_magic'] and report['same_format_version']:
        headline = 'Cabeçalho e versão interna correspondem à referência.'
    elif not report['same_magic']:
        headline = 'O cabeçalho é diferente da referência.'
    else:
        headline = 'Versões internas diferentes; requer revisão manual.'
    return (
        headline + '\n'
        + f"Referência: {base['filename']}  •  {base['producer']}  "
          f"•  versão {base['format_version']}  •  {base['size_bytes']:,} bytes\n"
        + f"Gerado: {result['filename']}  •  {result['producer']}  "
          f"•  versão {result['format_version']}  •  {result['size_bytes']:,} bytes\n\n"
        + report['warning']
    )


def guess_talespire_content_folder() -> Path | None:
    # TaleSpire docs recommend Settings -> Open Settings Directory for accuracy.
    home = Path.home()
    root = home / 'AppData' / 'LocalLow'
    for studio in ('BouncyRock Entertainment', 'Bouncyrock Entertainment'):
        candidate = root / studio / 'TaleSpire' / 'LocalContentPacks'
        if candidate.is_dir():
            return candidate
    return None


def install_tsmod(filepath: str | Path, content_folder: str | Path, *, replace: bool = False) -> Path:
    src = Path(filepath).resolve()
    inspect_tsmod(src)
    dest_folder = Path(content_folder).resolve()
    if not dest_folder.is_dir() or dest_folder.name.casefold() != 'localcontentpacks':
        raise ValueError('Selecione a pasta LocalContentPacks existente do TaleSpire.')
    dest = dest_folder / src.name
    if src == dest:
        return dest
    if dest.exists():
        if _same_file(src, dest):
            return dest
        if not replace:
            raise FileExistsError(f'Já existe {dest.name} na pasta do jogo.')
        # Retain a backup; never delete/overwrite the user's only copy.
        import datetime
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        backup = dest.with_name(dest.name + '.' + timestamp + '.bak')
        count = 1
        while backup.exists():
            backup = dest.with_name(dest.name + '.' + timestamp + f'_{count}.bak')
            count += 1
        shutil.copy2(dest, backup)
    # Write to temporary file before replacing for crash-resistant copying.
    tmp = dest.with_name(dest.name + '.astronyx_tmp')
    try:
        shutil.copy2(src, tmp)
        os.replace(tmp, dest)
    finally:
        tmp.unlink(missing_ok=True)
    return dest


def _same_file(a: Path, b: Path) -> bool:
    if a.stat().st_size != b.stat().st_size:
        return False
    digests = []
    for p in (a, b):
        h = hashlib.sha256()
        with p.open('rb') as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b''):
                h.update(chunk)
        digests.append(h.digest())
    return digests[0] == digests[1]
