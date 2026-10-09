# Astronyx Mini Forge — HUD V2.2 Preview

Branch de desenvolvimento `v2.2-ui`. A Release pública da V2.1.0 não é alterada.

## Entregue neste preview
- Dashboard com início rápido, status dos projetos e progresso real
- Navegação reorganizada: Dashboard, Studio 3D, Biblioteca, Converter, Ferramentas e Instalar
- Inspetor de altura, rotação e triângulos ligado às variáveis existentes do conversor
- Biblioteca em galeria com thumbnails, pesquisa sem diferenciar maiúsculas, filtros e ações
- Testes puros do filtro e pipeline Windows em branch separada

## Limitações
- O visor 3D existente continua geométrico, sem shader PBR em tempo real.
- Não implementa animação, rigging nem remeshing novo.
- A versão distribuída via Releases continua V2.1.0 até revisão do instalador e teste de um arquivo Meshy real no TaleSpire.

## Arquivos protegidos
`core/blender_pipeline.py`, `core/taleweavercmd.py`, `core/geometry.py`, `core/tsmod.py` não foram modificados.

## Como validar
Execute `python -m unittest discover -s tests -v`. Para abrir a interface a partir do código: `python studio.py`. A compilação na branch de teste deve completar o teste Windows sem publicar nova Release.
