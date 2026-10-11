# V2.2.12 — Interface essencial Meshy → TaleSpire

## Como importar um personagem

1. No Meshy AI, baixe o modelo em formato **GLB** (recomendado) ou um ZIP com os arquivos 3D.
2. Abra o Astronyx Mini Forge, página **Início**.
3. Arraste o GLB ou ZIP para a área **SOLTE SEU MODELO AQUI** ou clique em **Escolher GLB ou ZIP**.
4. Confira o nome do arquivo exibido e clique em **GERAR .TSMOD**.
5. Aguarde a barra de progresso. Clique em **Abrir resultado** para acessar a pasta e instalar o .tsMod.

O botão principal usa o pipeline existente Blender + TaleWeaverCmd. A primeira
execução precisa encontrar ambos. Caso algum deles não seja detectado,
o aplicativo solicita configuração; nada é publicado nem convertido pela nuvem.

## Menos menus

A navegação principal mostra apenas **Início**, **Meus modelos** e
**Instalar no TaleSpire**. Em **Mais opções** ficam Conversão detalhada,
Prévia 3D, Ajustes avançados, Exportação / Unity e Ajuda.
Nenhum projeto ou função anterior foi apagado.

## Arrastar e soltar

No Windows, o executável distribui o suporte TkDND via tkinterdnd2. O sistema
aceita um arquivo existente por vez e somente extensões .blend/.glb/.gltf/
.fbx/.obj/.stl/.zip. Rejeita executáveis, links e arrastos múltiplos. Nunca
executa diretamente o arquivo arrastado; ele só é selecionado para o
pipeline de conversão.

Se uma política do Windows bloquear o recurso, use **Escolher GLB ou ZIP**.

## Sobre o Unity e TaleWeaverLite

O Unity e TaleWeaverLite já podem estar instalados, mas o fluxo totalmente
automatizado Unity→.tsMod ainda **não** está implementado. A opção
Exportação / Unity continua criando um pacote preparado para importar no
projeto Unity, que deve ser finalizado manualmente. A geração automática
de .tsMod pela tela inicial usa o TaleWeaverCmd.

**Limite atual:** A escala/movimentação 1×1 do Eclipse Warlord não foi
validada com o novo fluxo no TaleSpire; não é garantido que a interface
nova corrija isso. Issue: https://github.com/Night0231-creator/forge/issues/6
