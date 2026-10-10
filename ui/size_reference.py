"""Silhueta humanoide de escala visual para a prévia local.

O comparador é um desenho esquemático sobre a imagem 2D. A altura usa
a mesma escala de projeção do OBJ Y-up, mas NÃO representa collider/base
de gameplay, criatura 3D real nem dimensões oficiais do TaleSpire.
"""
from __future__ import annotations

import math

from PIL import Image, ImageDraw


def project_reference_y(fraction: float, *, base_y: float, center_y: float,
                        pixels_per_unit: float, pitch: float,
                        frame_height: int, pan_y: float = 0.0,
                        reference_height: float = 1.75) -> float:
    """Projeção ortográfica da mesma unidade vertical usada na malha."""
    return (frame_height * .55
            - math.cos(pitch) * (base_y + fraction * reference_height - center_y)
            * pixels_per_unit + pan_y)


def paint_reference(image: Image.Image, *, base_y: float, center_y: float,
                    model_height: float, pixels_per_unit: float,
                    pitch: float, pan_x: float = 0.0, pan_y: float = 0.0,
                    reference_height: float = 1.75) -> Image.Image:
    """Desenha boneco e régua 1x1; não altera a malha nem texturas exportadas."""
    if (not all(math.isfinite(v) for v in
                (base_y, center_y, model_height, pixels_per_unit, pitch,
                 pan_x, pan_y, reference_height))
            or reference_height <= 0 or pixels_per_unit <= 0):
        raise ValueError('Parametros de referencia de tamanho invalidos.')

    draw = ImageDraw.Draw(image)
    x = image.width * .81 + pan_x
    def y(frac: float) -> float:
        return project_reference_y(
            frac, base_y=base_y, center_y=center_y,
            pixels_per_unit=pixels_per_unit, pitch=pitch,
            frame_height=image.height, pan_y=pan_y,
            reference_height=reference_height)

    top, bottom = y(1.0), y(0.0)
    stroke = max(2, min(5, round(image.width / 135)))
    white, violet, muted = (235, 225, 252), (183, 139, 251), (135, 150, 185)
    gauge = x - image.width * .105
    draw.line([(gauge, top), (gauge, bottom)], fill=muted, width=1)
    for yy in (top, bottom):
        draw.line([(gauge-5, yy), (gauge+5, yy)], fill=muted, width=1)

    # Cabeça/corpo/braços/pernas usam a MESMA escala vertical do OBJ.
    # A silhueta continua frontal em vistas giradas: é uma régua, não um mesh 3D.
    head_center = y(.895)
    radius = max(2.0, abs(y(.995)-y(.795)) * .48)
    draw.ellipse((x-radius,head_center-radius,x+radius,head_center+radius),
                 outline=violet, width=stroke)
    draw.line([(x,y(.78)),(x,y(.44))],fill=white,width=stroke+1)
    arm = reference_height * pixels_per_unit * .14
    draw.line([(x,y(.73)),(x-arm,y(.52))],fill=violet,width=stroke)
    draw.line([(x,y(.73)),(x+arm,y(.52))],fill=violet,width=stroke)
    leg = reference_height * pixels_per_unit * .11
    draw.line([(x,y(.44)),(x-leg,y(.02))],fill=violet,width=stroke)
    draw.line([(x,y(.44)),(x+leg,y(.02))],fill=violet,width=stroke)

    # Legenda fica dentro do quadro, inclusive com referências muito altas.
    label_x = max(4, min(image.width-112, x-45))
    label_y = max(5, min(image.height-38, min(top,bottom)-29))
    draw.text((label_x,label_y), f'REF 1x1  {reference_height:.2f}u',fill=violet)
    draw.text((label_x,max(5, image.height-26)),
              f'MODELO  {model_height:.2f}u',fill=white)
    return image
