# V2.2.11 — Preparar TaleWeaverLite (Unity) para testar 1×1

O teste do Eclipse Warlord com modelo 8× deixou a figura visível, mas a base ficou grande e o movimento apresentou problemas. **Não** há um campo Default Scale documentado no params.json do TaleWeaverCmd. O editor TaleWeaverLite oficial permite escolher o Transform visual e o Default Scale de forma separada.

Fonte: https://talespire.com/taleweaverlite-guide

## Novo botão no Mini Forge

Na aba Gerar .tsMod, clique em **Preparar TaleWeaverLite (Transform visual + Default Scale 1×1)**. Escolha um projeto já convertido e forneça o multiplicador visual de referência. Para Eclipse Warlord, 8× ficou próximo do desejado no jogo, mas não garante deslocamento/colisão corretos.

O app gera Astronyx_TaleWeaverLite_1x1.zip com:
- Modelo/Model_PivoPes.obj: OBJ Y-up com centro dos pés estimado pela mediana horizontal dos vértices até 5% da altura;
- Texturas Albedo.png, Normal.png e MAES.png;
- Modelo/Astronyx_Unity.mtl apontando para albedo;
- FBX de TaleWeaverLite se presente, como alternativa;
- CALIBRACAO.json e LEIA_PRIMEIRO.txt.

Nenhum arquivo fonte é sobrescrito, nenhuma instalação do Unity é automática, nenhum .tsMod é alterado e nenhum upload externo é feito.

## Instalação gratuita e teste

https://talespire.com/taleweaverlite-install-guide

1. Instale Unity Hub e editor Unity 2021.3.45f2 (versão gratuita pessoal), abra o projeto TaleWeaverLite.
2. Confira TaleSpire > Model Import Settings; desative os redimensionamentos/recentralizações automáticos se estiverem alterando o pivô.
3. Importe o OBJ ancorado, suas três texturas e configure o Creature Mod (ou FBX alternativo).
4. Configure o tamanho visual do modelo no Transform, começando por 6×–8× só no Eclipse Warlord.
5. Configure Default Scale = 1 para escala inicial de tabuleiro 1×1.
6. Ajuste manualmente Head, Hit, Spell e Torch de acordo com o personagem visual.
7. Exporte um .tsMod no TaleWeaverLite e teste base, seleção, arraste e colocação no TaleSpire.

**Limitações:** O Default Scale=1 não garante que o colisor, a base visual e a movimentação estejam corretos. O centro dos pés é uma estimativa geométrica que pode falhar em modelos com capa/efeitos/pedestal. O modo é experimental, não uma correção validada no jogo. O Unity é necessário para o .tsMod final.
