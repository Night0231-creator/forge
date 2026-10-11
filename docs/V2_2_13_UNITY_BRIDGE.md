# Astronyx Mini Forge V2.2.13 — Unity Bridge (experimental)

## Objetivo

Depois de instalar Unity 2021.3.45f2 e TaleWeaverLite, a preparação de modelos para Unity pode ser automática.

- Importe GLB/ZIP do Meshy na tela Início e converta normalmente.
- Em Mais opções > Exportação / Unity, escolha uma única vez a raiz do projeto TaleWeaverLite visto no Unity Hub.
- Ative "Importar no Unity automaticamente após cada conversão".
- A próxima conversão copiará OBJ ancorado nos pés e Albedo/Normal/MAES para Assets/AstronyxImports/<personagem>_NNN, preservando versões anteriores.
- Um script próprio em Assets/Editor/AstronyxMiniForgeBridgeV2213.cs gera material e prefab de prévia automaticamente ao importar o arquivo. Alternativa: Tools > Astronyx > Preparar modelos importados.
- O botão Importar último modelo no Unity evita reconverter tudo se você já tiver um projeto pronto.

## O que é automático

Detecção do Unity 2021.3.45f2 instalado no Hub, validação do projeto, cópia local de geometria e texturas, preparação de material/prefab, ancoragem geométrica e integração opcional ao final da conversão. Pode abrir o projeto no Unity após confirmação.

## O que continua manual

A exportação final do TaleWeaverLite utiliza DLLs pré-compiladas, sem API pública estável confirmada. Portanto abra o projeto Unity, escolha o mesh Model_PivoPes.obj e as três texturas no Creature Mod, ajuste Transform visual e Default Scale = 1, posicione Head/Spell/Hit/Torch e salve o .tsMod no próprio TaleWeaverLite. Teste base, tamanho e movimentação no TaleSpire.

A prévia começa em 1x, sem multiplicar por 8 automaticamente. O teste antigo do Eclipse Warlord com 8x resultou em problemas de movimentação; a issue #6 permanece aberta.

## Segurança

Somente são criados arquivos na pasta Assets/AstronyxImports e um script de propriedade do Mini Forge em Assets/Editor. Não altera projetos anteriores, arquivo .tsMod, arquivos Meshy, Packages ou ProjectSettings, nem executa links. Se o script existente for diferente, interrompe a integração em vez de sobrescrevê-lo.

O código de integração Python foi testado com arquivos de geometria sintéticos. O teste real no Unity e no TaleSpire ainda é necessário.

Documentação oficial:
https://talespire.com/taleweaverlite-guide
https://talespire.com/taleweaverlite-install-guide
