# Astronyx Mini Forge V2.3.0 — Pintura direta em 3D

Na janela Painting Studio, pinte diretamente na miniatura usando o botão esquerdo. O botão direito orbita a câmera; a roda do mouse aproxima. Se desmarcar **Pintar diretamente no modelo 3D**, o botão esquerdo volta a girar o personagem.

A pintura localiza a face visível sob o cursor através de projeção geométrica ortográfica em CPU (NumPy); calcula as coordenadas UV por interpolação baricêntrica e envia pincel, conta-gotas, borracha ou balde ao mesmo atlas do editor 2D. A prévia 3D é atualizada periodicamente e depois de desfazer/refazer.

**Fluxo:** Meshy AI → converter → PINTAR MINIATURA → salvar rascunho → aplicar na exportação → gerar novamente .tsMod. Salvar rascunho não modifica os arquivos finais. Aplicar cria backups de todos os Albedos antes de modificá-los. O .tsMod anterior fica intacto até reexportação.

**Limitações:** a seleção atua somente sobre as faces incluídas na prévia OBJ (máximo de 150 mil triângulos), sem pintar através de superfícies ocultas. O pincel mede pixels da textura, não unidades de mundo. Saltos grandes entre ilhas UV interrompem o traço. Não há aceleração GPU, materiais PBR, camadas ou pincel 3D volumétrico. O tamanho 1×1 e o movimento permanecem pendentes de testes reais no TaleSpire.

O projeto é uma implementação própria inspirada na categoria de ferramentas como Basecoat, sem copiar ativos/código comercial.
