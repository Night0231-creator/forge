# V2.2.14 — Calibrador visual 1×1

Esta atualização prioriza o primeiro dos três módulos propostos:
**comparar a geometria e a posição dos pés antes de exportar**.
Pintura de materiais não foi incluída nesta versão.

## Como usar

1. Na tela Início, importe o arquivo GLB do Meshy e clique em Gerar .tsMod.
2. Após a conversão, clique em **Calibrar 1×1** na mesma tela
   (ou em Mais opções > Prévia 3D).
3. Compare o modelo com a silhueta de referência 1,75 unidade na
   vista frontal e com um quadrado teórico 1×1 unidade visto de cima.
4. Veja altura, largura, profundidade, deslocamento estimado dos pés
   e alertas sobre acessórios grandes ou altura de malha excessiva.
5. Clique em Salvar análise JSON, se quiser compartilhar medidas.

Toda nova conversão também cria um relatório
**calibracao_visual_1x1.json** dentro da pasta do personagem,
usando preferencialmente Entrada_TaleWeaverCmd/model.obj:
é a malha que o TaleWeaverCmd recebeu, e não o arquivo bruto Meshy.

### Definições e limitações

- As dimensões vêm de TODOS os vértices OBJ, eixo vertical Y.
- Para prever o centro dos pés, usa a mediana dos vértices nos 6%
  inferiores da altura. A projeção do corpo usa percentis 5%-95%
  de vértices entre 20%-75% da altura. São heurísticas: armas,
  capas e acessórios podem distorcer medidas.
- O quadrado desenhado é de **1 unidade por lado** e o humanoide
  mede **1,75 unidade**. São referências de desenho, NÃO uma
  extração de collider, tamanho físico da base ou default scale.
- Nenhuma função da CLI TaleWeaverCmd documenta o collider ou
  o Default Scale efetivos do jogo. O programa NÃO pode garantir
  que altura 1,75 e quadrado 1x1 equivalham à movimentação correta.
- O calibrador NÃO reescreve OBJ, .tsMod, parâmetros de TaleWeaverCmd,
  escala do TaleSpire nem scripts Unity. Apenas mede e registra avisos.

### Por que o Eclipse Warlord 8x apresentou problemas?

Com altura de malha de quase 12 unidades e enorme projeção
horizontal, o modelo passou a se aproximar visualmente da altura
desejada, mas a pega/arraste e a base se tornaram problemáticas.
A V2.2.14 irá sinalizar esse padrão como risco geométrico
antes de enviar outra miniatura ao jogo, sem repetir um
multiplicador 8x automático.

### Próximas etapas

O editor de materiais (cores e brilho) e a ampliação da validação
de shader/normal maps ficam para versões posteriores, após
confirmarmos a calibração com o usuário no TaleSpire.

A issue https://github.com/Night0231-creator/forge/issues/6
permanece aberta, aguardando validação de um mod no próprio jogo.
