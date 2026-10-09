# Astronyx Mini Forge Studio V2.2.3 — HUD Polish

Atualização **visual e de usabilidade**, mantendo os conversores Meshy → Blender → TaleWeaverCmd → TaleSpire inalterados.

## Melhorias
- Paleta escura consistente com roxo Astronyx e maior contraste de textos.
- Navegação lateral dividida em Workspace e Ferramentas, indicador ativo e hover.
- Cabeçalho contextual com nome e descrição da página atual.
- Dashboard com foco em **Nova conversão**, visão de projetos e progresso real do processamento.
- Cartões da biblioteca com bordas, hierarquia tipográfica, status e miniaturas redimensionadas com Pillow/LANCZOS.
- Layout adaptativo: a galeria usa 1 a 4 colunas conforme a largura disponível.
- Pesquisa e filtros sem reexaminar arquivos em disco a cada tecla digitada.
- Estados vazios diferentes para biblioteca sem projetos e resultados filtrados vazios.
- Botões com navegação por teclado e foco visível.

## Compatibilidade / limites
- Sem mudanças no pipeline de Blender, TaleWeaverCmd, UVs, normalização ou escala.
- Windows 10/11 continuam com instalador Setup.exe e ZIP portátil sem instalação.
- A interface continua Tkinter; não há novo editor 3D ou renderizador PBR.
- É necessário validar visualmente a interface no Windows após a compilação e reavaliar o app em DPI 125/150%.

## Testes
`python -m unittest discover -s tests -v` + smoke test Windows + zip extraído.
