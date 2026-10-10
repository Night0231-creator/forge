"""Notas de fidelidade explicáveis para o relatório de conversão Meshy."""
from __future__ import annotations

import math


def quality_notes(stats: dict) -> list[str]:
    """As notas não afirmam qualidade no jogo sem teste visual real."""
    notes: list[str] = []
    if stats.get('albedo_method') == 'png_original':
        notes.append('Cores originais do PNG preservadas sem novo bake do albedo.')
    else:
        notes.append('Albedo reconstruído pelo Blender: texturas e UVs complexas podem sofrer perda de nitidez.')
    if stats.get('uv_mode') == 'repacked':
        notes.append('Atlas UV reorganizado por haver vários materiais/UVs; confira rosto, cabelo e armadura.')
    else:
        notes.append('UV original mantido quando compatível com o modelo convertido.')
    try:
        ratio = float(stats.get('triangle_retention_percent', 100))
        if math.isfinite(ratio) and ratio < 65:
            notes.append(f'Apenas {ratio:.1f}% dos triângulos foram mantidos; detalhes pequenos podem se perder.')
    except (ValueError, TypeError):
        pass
    try:
        target = int(stats.get('texture_bake_size', 2048))
        if target > 2048:
            notes.append('Pré-processamento acima de 2048 px; as cópias para TaleWeaverCmd serão reduzidas a 2048 px.')
    except (ValueError, TypeError):
        pass
    notes.append('Valide no TaleSpire: a prévia não representa iluminação, materiais e escala física do jogo.')
    return notes
