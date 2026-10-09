# Correção experimental do Astronyx Mini Forge V2.0.2

- O preset 14 unidades do V2.0.1 ampliava humanoides normalizados a 1,75 por 8 vezes. O novo valor inicial é 1,75, sem padrão oficial imposto.
- Preferências antigas no preset padrão 14/8 são migradas uma vez para 1,75/1.
- UVs originais do Meshy são preservadas quando existe somente um material e UV válida. Caso contrário, precisa recalcular o atlas.
- Textura 2048 por padrão (limite documentado do TaleSpire), redução de geometria menos agressiva e teto de 60 mil vértices.
- Perfis: Leve 18 mil triângulos e 1024px; Equilibrado 45 mil e 2048px; Detalhado 100 mil e 2048px.
- Alertas para redução severa e modelos excessivamente largos.
- Para avaliar **qualidade**, converta novamente o BLEND/GLB original. Regerar somente o tsMod não recupera triângulos/texturas já processados.
- TaleWeaverCmd gera miniatura estática; não exporta armature/rig nem cria animação. Movimento durante arrasto é do TaleSpire.
- Atualização beta: testes Python não substituem o teste da malha, texturas, normais e escala dentro do jogo. Mantenha a versão anterior disponível e compare.
