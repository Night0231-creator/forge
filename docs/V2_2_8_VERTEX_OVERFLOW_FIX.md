# Mini Forge V2.2.8 — TaleWeaverCmd: limite real de 60 mil vértices

O TaleWeaverCmd pode recusar personagens com: "Creature has 82763 vertices which exceeds the max allowed count of 60000".
Avisos simultâneos sobre shaders Sprites/Default e Sprites/Mask podem ser secundários, pois a exceção de contagem de vértices identifica diretamente a falha.

Blender conta vértices por posição na malha, mas o Unity pode criar vértices extras nas costuras UV, normais ou materiais. Por isso o limite anterior de 55 mil no Blender não foi suficiente.

## Mudanças

1. Após preparar texturas e UV, o Blender exporta OBJ e conta combinações posição/UV/normal/material.
2. Se ultrapassar 48 mil, reduz triângulos automaticamente e exporta novamente, até um número limitado de tentativas.
3. O FBX final usa a mesma malha pós-otimização.
4. O relatório inclui taleweavercmd_obj_split_vertices, taleweavercmd_obj_positions e taleweavercmd_vertex_reductions.
5. Projetos antigos que ultrapassam 60 mil combinações no OBJ recebem aviso antes de iniciar o TaleWeaverCmd.
6. Erros do Unity por excesso de vértices têm prioridade sobre avisos secundários de shader.

O número de vértices OBJ é uma estimativa, não garantia do contador interno Unity. Não removemos o teto oficial de 60.000. A redução geométrica pode sacrificar detalhes finos, mas preserva as texturas originais.
A CI valida código e pacote, não a conversão real com TaleWeaverCmd+TaleSpire.

Referência oficial: https://talespire.com/taleweaverlite-guide
