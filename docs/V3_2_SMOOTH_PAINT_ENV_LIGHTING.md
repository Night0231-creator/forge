# Astronyx Mini Forge V3.2 — Fluidez da pintura e ambiente

## Mudanças implementadas
- Quando o usuário gira/pinta o modelo, a tela mantém a prévia texturizada anterior até a próxima imagem ficar pronta. O código antigo redesenhava a geometria Tk inteira por movimento (até aproximadamente 1600 polígonos), provocando atrasos e flashes.
- O motor de pintura em camadas recompõe **apenas os pixels do retângulo alterado** pelo pincel. Adicionar/reordenar/ocultar camadas continua recompondo a imagem completa, pois a alteração afeta a composição inteira.
- O refresh da textura do Albedo não refaz uma cópia do mapa MAES a cada pincelada. Quando o material MAES realmente muda, ele é atualizado no viewer.
- A prévia GPU ganhou luz de ambiente hemisférica com cores distintas de céu e solo e reflexo indireto aproximado. Presets **Estúdio, Pôr do sol, Luar**, mais intensidade do ambiente de 0 a 200% no painel 3D.
- Mantém controles independentes de luz direcional e emissão, desfazer/refazer e backups.

## Como experimentar
1. Abra o EXE V3.2 e carregue seu projeto Meshy já preparado.
2. Na bancada 3D, acione **GPU / PBR**. Experimente os três ambientes.
3. Use pincel em uma região e observe que a imagem não fica em branco durante os cálculos da próxima prévia.
4. Para testar materiais, selecione uma região, aplique Ouro polido ou Cristal mágico e ajuste a intensidade da iluminação.
5. Salve e aplique a pintura para atualizar os PNGs de preparação com backups. Exporte o .tsMod novamente, se desejar.

## Limites de desempenho e fidelidade
- O tempo real depende do driver e do hardware. O aplicativo ainda usa Tk para mostrar a imagem lida do framebuffer OpenGL; a pintura UV e a seleção de triângulos permanecem em CPU.
- Esta versão oferece iluminação ambiente **aproximada**, não um HDRI real nem image-based lighting com cubemaps, sombras dinâmicas ou ray tracing.
- O modo CPU continua como alternativa para drivers sem OpenGL 3.3; não reproduz os materiais PBR.
- A geometria, a escala 1×1 e o arquivo .tsMod permanecem inalterados pela visualização.
- Testes automatizados não substituem avaliação visual e de fluidez num PC Windows real nem garantem 30/60 FPS.

Referências:
- https://moderngl.readthedocs.io/en/latest/
- https://talespire.com/taleweaverlite-guide
