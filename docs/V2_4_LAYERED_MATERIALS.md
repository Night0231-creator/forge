# Astronyx Mini Forge V2.4.0 — Pintura em camadas e materiais MAES

## Escopo
A V2.4 amplia a V2.3, preservando o pincel sobre o 3D/UV. Agora a pintura de cores é composta por camadas RGBA independentes, e os presets de materiais operam sobre os canais físicos da textura MAES. O editor continua local e independente, sem copiar código ou ativos do Basecoat.

## Pintura por camadas
Abra uma miniatura Meshy AI já convertida e clique em **PINTAR MINIATURA**. Na aba Camadas, use + para criar, − para remover, setas para mudar a ordem, e ajuste Visibilidade e Opacidade. A miniatura 3D e o atlas UV mostram a composição final da camada-base com as camadas visíveis.

As camadas são guardadas em Pintura/camadas/*.png com o arquivo Pintura/camadas.json. Desfazer/refazer inclui criação e reorganização de camadas e edição MAES, com histórico limitado por memória. Texturas grandes permitem menos camadas por segurança. O formato V2.3 continua aceito, sem alteração da geometria.

## Selecionar uma parte da miniatura
1. Na aba Pincéis, selecione **Selecionar região similar**.
2. Ajuste a tolerância (0–50) e clique numa cor da textura ou numa superfície visível da miniatura 3D.
3. A seleção conectada fica em destaque roxo no atlas. Pincel, balde e borracha passam a agir apenas dentro dessa região.
4. Remova a seleção em **Materiais → Limpar seleção**.

Este seletor é baseado em cor e conexão de pixels, não em semântica de personagem, nomes de peças, objetos ou IA. Partes com cores semelhantes podem ser selecionadas juntas se forem contíguas no atlas.

## Presets MAES para TaleSpire
Na aba **Materiais**, selecione um preset e aplique após ter selecionado uma região. A exportação altera os dados em:
- Vermelho: metálico (Metallic)
- Verde: oclusão ambiental (AO)
- Azul: intensidade de emissão (Emissive)
- Alfa: suavidade (Smoothness)

As cores de metal NÃO são simuladas no renderizador 3D atual; nele o usuário vê apenas Albedo. O efeito dos materiais aparece quando a mini é reexportada e aberta no TaleSpire/TaleWeaverLite que oferece suporte aos canais de MAES. A emissão pode depender da configuração **Use emissive info** e do efeito paint wash.

## Salvamento e segurança
**Salvar rascunho** não altera os arquivos existentes de TaleSpire. **Aplicar na exportação** faz backups timestamped .bak antes de atualizar Albedo e MAES em TaleWeaverLite, TaleWeaverCmd_Source e Entrada_TaleWeaverCmd (se existirem); o programa tenta restaurá-los se ocorrer uma falha. O .tsMod anterior não é alterado até executar uma nova exportação.

Se a textura-base mudar depois de uma conversão/exportação, o aplicativo não reaplica automaticamente as camadas salvas para evitar pintura duplicada. Os PNGs das camadas continuam no projeto. Para a mini entrar no TaleSpire, use o conversor oficial TaleWeaverCmd, depois valide visual e movimentação no jogo.

Referências oficiais:
- https://talespire.com/taleweaverlite-guide
- https://bouncyrock.com/news/articles/taleweaverlite-feature-release-emissive

Limites: sem renderer PBR/metal/emissão em tempo real, sem seleção semântica por objeto, sem aceleração GPU, sem correção automática de collider.
