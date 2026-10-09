# Astronyx V2.2.2 — Scale & Quality Fix

- Normalização centraliza a malha e apoia os pés no zero do modelo exportado.
- A base visual é limitada, por padrão, a **1,30 unidade no plano horizontal**; não é um padrão oficial do TaleSpire e não altera diretamente o tamanho/collider de gameplay.
- A escala automática do TaleWeaverCmd calcula tanto altura quanto largura e profundidade do OBJ; pontos Head/Spell/Hit/Torch são associados à altura **efetivamente exportada**.
- Detalhes de escala em `blender_stats.json` e `TaleWeaverCmd_escala.json`. O modelo de origem não é sobrescrito.
- As normais são recalculadas no Blender e bordas acima de 55° permanecem marcadas como quinas.
- Qualidade: **Leve** 18k/1024, **Equilibrado** 45k/2048, **Alta** 100k/2048 (padrão), **Ultra** até 120k triângulos/4096px. O limite seguro de 60 mil vértices permanece ativo; o Blender pode reduzir os triângulos adicionais se necessário.
- **Ultra** pode ser lento e consumir bastante memória; vários materiais/UVs ainda podem exigir atlas com perda de detalhe.
- Criaturas com asas, armas ou capas muito largas podem ficar menores ao ajustar a base. Para tais modelos, revise o tamanho manualmente e compare no TaleSpire.
- O programa ainda exporta miniaturas estáticas. Animações, tremor ao soltar e tamanho de gameplay dependem também do TaleSpire, não só da malha.
- Os testes automatizados não substituem conversão real com Blender/TaleWeaverCmd e verificação visual dentro do jogo.

**Teste sugerido:** reconverta o original `.glb` ou `.blend`, use Alta e alvo de 1,75, instale o novo `.tsMod` e compare com uma miniatura 1×1. Preserve os arquivos anteriores para comparação.
