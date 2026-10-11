# Astronyx Mini Forge V3.0 — Novo estúdio unificado

## Objetivo
Uma única área de trabalho para preparar, pintar e exportar miniaturas digitais. Referência de usabilidade: Basecoat (TitanCraft); identidade visual, código, botões e composição são próprios da Astronyx, sem copiar interface ou ativos protegidos.

## Interface principal do EXE
O aplicativo abre em **Estúdio de Pintura** e mostra uma biblioteca compacta de miniaturas convertidas, um grande visualizador 3D central e um inspetor lateral com ações. Ações rápidas:

1. **+ Novo modelo Meshy** ou menu **Importar Miniatura** → escolhe GLB/ZIP no fluxo de conversão e usa Blender + TaleWeaverCmd.
2. **Pintar miniatura** → abre o editor dentro da própria janela do estúdio.
3. **Preparar .tsMod** → abre a etapa do conversor oficial.
4. **Instalar no jogo** → abre o instalador local de miniaturas TaleSpire quando o .tsMod já existe.

## Bancada de pintura
O editor embutido tem um único canvas 3D grande. À esquerda, as abas Pincéis, Camadas, Materiais; o mapa UV pode ser mostrado ou ocultado, permitindo trabalhar com prioridade na miniatura. Esquerdo: pintar; direito: girar; roda: zoom. Conta-gotas, borracha, seleção por cor, camadas e materiais funcionam como na V2.4.

- **Salvar projeto** escreve rascunhos e metadados na pasta Pintura.
- **Exportar texturas** aplica Albedo/MAES com backups e requer gerar novamente o .tsMod para a pintura entrar no jogo.
- **← Projetos** volta à galeria, avisando que edições não salvas serão descartadas.

## Compatibilidade e limitações
O novo layout mantém as mesmas ferramentas de conversão e os projetos antigos. O renderer 3D atual ainda usa CPU/NumPy, não GPU; o Metal/AO/Emissão não são visualizados fisicamente no renderizador, apenas nos canais MAES exportados; STL sem UV deve passar pela preparação existente antes da pintura. A escala 1x1 e a interação/movimentação devem ser verificadas no TaleSpire com miniaturas reais.

Telas técnicas existentes ficam em **Mais opções**. Não foi reimplementado do zero o código de conversão; a V3.0 refaz o shell/fluxo do EXE preservando as funções existentes.
