# Astronyx Mini Forge Studio V4.1 — pintura de superfície

O pincel 3D passa a projetar sua área sobre as faces cobertas, em vez de editar apenas a coordenada UV do centro do clique. Traços e carimbos podem atravessar costuras entre ilhas UV sem desenhar uma linha sobre partes não relacionadas do atlas.

## Usar

1. Importe e prepare o modelo pelo fluxo existente, ou selecione um projeto preparado na biblioteca.
2. Na aba **Pintar**, pinte diretamente na miniatura; direito gira e roda aproxima. O tamanho do pincel no 3D é medido em pixels da tela; no mapa UV é medido em pixels da textura.
3. A aba **Opções** oferece dureza de borda e **Pintar através do modelo**. Desativado por padrão, o pincel usa um teste de profundidade local para proteger as faces ocultas. Ativá-lo inclui as superfícies atrás do pincel.
4. **Geometria** seleciona faces conectadas, separando bordas conforme o ângulo escolhido. Reconhece posições coincidentes nas costuras UV, funciona sem cores e não identifica automaticamente roupas/pele. **Cor similar** mantém a seleção por cor anterior. O balde cria uma região geométrica quando esse modo está ativo e ainda não há seleção; uma seleção existente é respeitada até ser limpa.
5. Uma seleção aparece com um tom azul na prévia 3D. O realce é somente visual e não entra nas texturas salvas.
6. Carimbos Estrela/Selo/Runa e PNG ficam em **Opções**. No 3D são projetados com o mesmo teste de profundidade e respeitam a seleção; o PNG fornece a transparência e recebe a cor escolhida.
7. Em **Material**, escolha um preset e ajuste metal, oclusão ambiente, emissão e suavidade. Aplique à região selecionada; desfazer/refazer atualiza também a prévia de material.
8. Salve o projeto, exporte as texturas e gere novamente o `.tsMod` pelo fluxo existente. A exportação continua criando backups.

As abas de ferramentas possuem rolagem para manter os controles acessíveis em telas menores.

## Limites concretos

- Projeção ortográfica em CPU para pintura, com prévia GPU opcional; não é um pincel volumétrico nem um sistema de pressão de tablet. Pintura através segue a direção da câmera.
- A visibilidade usa amostras de meio pixel na tela. Detalhes menores que isso e silhuetas muito finas podem apresentar imprecisão na borda; aproxime o modelo.
- UVs sobrepostas compartilham os mesmos pixels. UVs degeneradas não recebem pintura. A seleção geométrica não atravessa bordas não manifold; bordas suaves podem ligar regiões maiores que as pretendidas.
- Limites atuais do viewer: 150 mil triângulos e atlas de até 4096². Uma operação de pincel com área UV excessiva é recusada antes de aplicar a pintura e recomenda aproximar o modelo ou reduzir o pincel.
- Não inclui remesh de alta para baixa resolução com bake de detalhe do original, sombras/highlights automáticos gravados na textura, pressão de tablet ou exportação Unity AssetBundle completa.
- A escala 1×1 e o movimento continuam exigindo validação dentro do TaleSpire. Esta versão mantém o pipeline de conversão e dependências anteriores: Blender e TaleWeaverCmd.

## Validação

Testes de comportamento cobrem costuras UV, continuidade de traços, faces ocultas, pintura através, carimbos com transparência, dureza, opacidade única em bordas compartilhadas, seleção, borracha, undo/redo e materiais. Testes de janela real executam os callbacks de pintura, preenchimento e materiais em um desktop disponível. CI Windows verifica testes, recursos do EXE, instalação e ZIP portátil; não substitui um teste no TaleSpire com uma miniatura real.
