# V2.2.9 — .tsMod de referência (Basecoat)

Um arquivo .tsMod exportado por Basecoat foi inspecionado para verificar o formato dos seus metadados. Observou-se:
- Assinatura de arquivo: CE D1 CE D1.
- Versão interna de cabeçalho: 1.
- Auxiliar do cabeçalho: 5 (significado proprietário não inferido).
- Descrição em UTF-16LE iniciando no deslocamento 48, com indicação de exportação Basecoat.
- Não é um ZIP nem GLB legível; o conteúdo binário NÃO foi incluído no repositório.

## Como usar
1. Abra Mini Forge → Instalar no TaleSpire.
2. Escolha o .tsMod já pronto no campo ARQUIVO DE REFERÊNCIA BASECOAT.
3. No campo ARQUIVO .TSMOD, selecione o seu novo exportado e clique em Comparar.
4. Verifique assinatura, versão interna, exportador e tamanho no relatório visual.
5. Se deixar uma referência registrada, o Forge cria comparacao_tsmod_referencia.json na pasta do projeto após o TaleWeaverCmd gerar um novo .tsMod.
6. Se repetir somente a etapa .tsMod, a comparação também pode ser registrada.

O arquivo de referência NUNCA é alterado, reempacotado, injetado como template ou enviado ao GitHub. O caminho fica apenas no computador.

### Limites
* Assinatura semelhante não comprova compatibilidade: nenhum cabeçalho mede limites de vértices, shaders, UV, animações ou escala real.
* A exportação continua exigindo OBJ, texturas PNG e TaleWeaverCmd. Um .tsMod Basecoat pronto não converte novos GLBs automaticamente.
* O mod original pode ser instalado como está usando a função de instalação atual; o usuário deve possuir permissão para utilizar o conteúdo.
* Para alterar a geometria de um personagem, use o GLB/OBJ/BLEND fonte, preferencialmente exportado pelo programa original, em vez de alterar bytes do .tsMod.

## Testes
Comparações automatizadas usam apenas um cabeçalho SINTÉTICO, sem embutir qualquer modelo ou arquivo proprietário.
