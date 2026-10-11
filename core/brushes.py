"""Texture and surface brush falloff shared by both painting views."""
from __future__ import annotations

import math
import numpy as np
from PIL import Image, ImageDraw


def coverage(distance, radius: float, hardness: float = 1.0):
    if not (math.isfinite(radius) and radius > 0
            and math.isfinite(hardness) and 0 <= hardness <= 1):
        raise ValueError('Raio ou dureza do pincel inválido.')
    normalized = np.asarray(distance) / radius
    if hardness == 1:
        return (normalized <= 1).astype(np.float32)
    t = np.clip((normalized - hardness) / (1 - hardness), 0, 1)
    return 1 - t * t * (3 - 2 * t)


def segment_distance(x, y, start, end):
    ax, ay = start
    bx, by = end
    dx, dy = bx - ax, by - ay
    square = dx * dx + dy * dy
    if square < 1e-12:
        return np.hypot(x - ax, y - ay)
    t = np.clip(((x - ax) * dx + (y - ay) * dy) / square, 0, 1)
    return np.hypot(x - (ax + t * dx), y - (ay + t * dy))


def stamp_mask(diameter: int, shape: str = 'Estrela', custom=None):
    if not isinstance(diameter,int) or not 4 <= diameter <= 512:
        raise ValueError('Carimbo deve ter tamanho entre 4 e 512.')
    if custom is not None:
        if custom.width*custom.height > 1024*1024:
            raise ValueError('Imagem de carimbo muito grande.')
        return custom.convert('RGBA').getchannel('A').resize(
            (diameter,diameter),Image.Resampling.LANCZOS)
    mask=Image.new('L',(diameter,diameter),0)
    draw=ImageDraw.Draw(mask)
    m=diameter/2
    if shape=='Estrela':
        points=[]
        for i in range(10):
            angle=-math.pi/2+i*math.pi/5
            radius=.46*diameter if i%2==0 else .21*diameter
            points.append((m+math.cos(angle)*radius,m+math.sin(angle)*radius))
        draw.polygon(points,fill=255)
    elif shape=='Selo':
        draw.ellipse((2,2,diameter-3,diameter-3),outline=255,width=max(2,diameter//12))
        draw.ellipse((diameter*.28,diameter*.28,diameter*.72,diameter*.72),fill=255)
    elif shape=='Runa':
        w=max(2,diameter//12)
        draw.line((m,diameter*.08,m,diameter*.92),fill=255,width=w)
        draw.line((diameter*.25,diameter*.22,m,diameter*.48,
                   diameter*.75,diameter*.22),fill=255,width=w)
        draw.line((diameter*.25,diameter*.75,m,diameter*.48,
                   diameter*.75,diameter*.75),fill=255,width=w)
    else:
        raise ValueError('Forma de carimbo desconhecida.')
    return mask
