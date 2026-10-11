"""Resize MAES channels as data; smoothness is never visual transparency."""
from PIL import Image


def fit_maes(image, maximum=2048, resample=Image.Resampling.LANCZOS):
    ratio=min(1,maximum/max(image.size))
    size=tuple(max(1,round(v*ratio)) for v in image.size)
    rgba=image.convert('RGBA')
    if size==rgba.size:
        return rgba
    return Image.merge('RGBA',[channel.resize(size,resample) for channel in rgba.split()])
