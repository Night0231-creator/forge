"""A quiet, decorative studio floor; never exported into model textures."""
from functools import lru_cache

import numpy as np
from PIL import Image, ImageDraw

PREVIEW_LIMIT = 900


@lru_cache(maxsize=3)
def _background(width, height):
    rows = np.linspace(0, 1, height, dtype=np.float32)[:, None, None]
    top = np.array([14, 14, 18], dtype=np.float32)
    bottom = np.array([23, 23, 29], dtype=np.float32)
    pixels = np.broadcast_to(top + (bottom-top)*rows, (height, width, 3))
    image = Image.fromarray(pixels.astype(np.uint8))
    draw = ImageDraw.Draw(image)
    horizon = height * .43
    for i in range(1, 19):
        y = horizon + (height-horizon) * (i/18)**2
        strength = int(26 + 14 * (i/18)**2)
        draw.line((0, y, width, y), fill=(strength, strength, strength+6))
    for i in range(-18, 19):
        x = width/2 + i * width/12
        draw.line((width/2 + i*2, horizon, x, height), fill=(34, 34, 42))
    return image


def studio_background(width, height, canvas_size=None):
    # A copy keeps renderer writes and reference overlays out of the cache.
    size=canvas_size or (width,height)
    image=_background(int(size[0]),int(size[1])).copy()
    if image.size != (width,height):
        x=(image.width-width)//2
        y=(image.height-height)//2
        return image.crop((x,y,x+width,y+height))
    return image
