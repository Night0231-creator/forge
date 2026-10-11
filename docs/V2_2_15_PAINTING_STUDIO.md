# Astronyx Mini Forge V2.2.15 — Painting Studio UV

Este é o primeiro módulo independente de pintura de miniaturas inspirado na categoria de produtos como Basecoat, sem reutilizar seu código ou arte.

## Como usar

1. Converta um modelo Meshy (GLB/ZIP) no Mini Forge.
2. Clique em **PINTAR MINIATURA** na tela inicial ou **Pintar textura UV** na prévia.
3. Pinte o atlas Albedo com pincel, balde ou borracha; selecione cores com a paleta ou conta-gotas.
4. **Salvar rascunho** grava `Pintura/Albedo_editado.png` sem modificar as texturas usadas para exportar.
5. **Aplicar na exportação** pede confirmação, cria backups `.bak` de todos os PNGs alterados e atualiza os albedos para a próxima conversão.
6. Use **Gerar .tsMod de uma pasta já preparada** para exportar a pintura; o .tsMod anterior não é alterado pelo editor.

## Limites

A pintura é feita no atlas UV 2D, não diretamente sobre o objeto 3D; a prévia só atualiza depois de aplicar. Ainda não há camadas, máscara, materiais PBR, raycast 3D nem pintura de sombra automática. A ferramenta não controla a escala nem a movimentação 1×1 no jogo, que ainda exigem validação real.

Dependência local: Pillow. Nenhuma conta externa ou conexão de rede é necessária para pintar.
