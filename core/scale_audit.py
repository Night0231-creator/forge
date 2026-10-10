"""Auditoria visual de escala 1x1 para OBJ Y-up do TaleWeaverCmd.

Não altera a malha e não tenta inferir o collider/tamanho de gameplay.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass

from .geometry import ObjStats, suggest_factor, suggest_safe_factor


@dataclass(frozen=True)
class ScaleAudit:
    target_height: float
    footprint_limit: float | None
    original_height: float
    original_width: float
    original_depth: float
    requested_factor: float
    applied_factor: float
    effective_height: float
    effective_width: float
    effective_depth: float
    height_retained_pct: float
    footprint_limited: bool
    status: str

    def to_dict(self) -> dict:
        return asdict(self)

    def explanation(self) -> str:
        if self.footprint_limited:
            return (
                'Acessórios, armas, asas ou a própria largura do modelo podem estar '
                'reduzindo a altura. Para preservar a proporção de um humanoide 1×1, '
                'ajuste as dimensões da malha original no Blender e converta novamente. '
                'Aumentar apenas o multiplicador pode ultrapassar a base visual.'
            )
        return (
            'A altura-alvo foi preservada, mesmo se o modelo tiver armas, asas '
            'ou acessórios largos. A largura não reduz mais o personagem. '
            'Compare com uma miniatura 1×1 dentro do TaleSpire: estas medidas '
            'não alteram o collider nem o tamanho de gameplay.'
        )

    def summary(self) -> str:
        return (
            f'Altura original: {self.original_height:.3f} un.\n'
            f'Largura / profundidade: {self.original_width:.3f} / '
            f'{self.original_depth:.3f} un.\n'
            f'Altura alvo: {self.target_height:.3f} un.\n'
            f'Escala calculada: {self.applied_factor:.3f}x '
            f'(pela altura seria {self.requested_factor:.3f}x)\n'
            f'Altura estimada final: {self.effective_height:.3f} un. '
            f'({self.height_retained_pct:.1f}% do alvo)\n'
            f'Base visual estimada: {self.effective_width:.3f} × '
            f'{self.effective_depth:.3f} un.\n\n'
            + self.explanation()
        )


def audit_scale(stats: ObjStats, target_height: float = 1.75,
                footprint_limit: float | None = None) -> ScaleAudit:
    """Same auto-scale math used by conversion, with a human-readable diagnosis."""
    requested = suggest_factor(stats.height, target_height)
    applied = suggest_safe_factor(stats, target_height, footprint_limit)
    limited = applied < requested * (1 - 1e-7)
    retained = 100.0 * (stats.height * applied) / target_height
    status = 'base_limitada' if limited else 'altura_alvo'
    return ScaleAudit(
        target_height=float(target_height),
        footprint_limit=float(footprint_limit),
        original_height=stats.height,
        original_width=stats.width,
        original_depth=stats.depth,
        requested_factor=requested,
        applied_factor=applied,
        effective_height=stats.height * applied,
        effective_width=stats.width * applied,
        effective_depth=stats.depth * applied,
        height_retained_pct=retained,
        footprint_limited=limited,
        status=status,
    )
