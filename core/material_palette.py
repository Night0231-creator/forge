"""Colour and surface finish choices for painting, independent of the UI."""
from dataclasses import dataclass


@dataclass(frozen=True)
class MaterialChoice:
    name: str
    colour: str
    category: str
    metallic: int
    emission: int
    smoothness: int

    @property
    def finish(self):
        # AO belongs to the model's baked detail and is preserved by the brush.
        return self.metallic, self.emission, self.smoothness


MATERIALS = (
    MaterialChoice('Aço', '#AAB9C7', 'Metais', 230, 0, 180),
    MaterialChoice('Ouro', '#E4B54C', 'Metais', 240, 0, 220),
    MaterialChoice('Bronze', '#A57C4A', 'Metais', 215, 0, 155),
    MaterialChoice('Ferro', '#555B68', 'Metais', 210, 0, 110),
    MaterialChoice('Couro', '#70452F', 'Natural', 0, 0, 70),
    MaterialChoice('Tecido', '#613E94', 'Natural', 0, 0, 35),
    MaterialChoice('Pele', '#DEAB85', 'Natural', 0, 0, 63),
    MaterialChoice('Pedra', '#858898', 'Natural', 0, 0, 30),
    MaterialChoice('Cristal', '#8A64FF', 'Magia', 40, 180, 215),
    MaterialChoice('Chama', '#FFAC35', 'Magia', 0, 235, 60),
    MaterialChoice('Gelo', '#70DCEC', 'Magia', 30, 110, 210),
    MaterialChoice('Esmalte', '#366AC5', 'Cores', 0, 0, 215),
)
