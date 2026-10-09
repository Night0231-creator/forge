# Diagnóstico de escala 1×1 (prévia V2.2.6)

A aba **GERAR .TSMOD** oferece **Diagnosticar escala 1×1** para abrir a pasta de um
personagem preparado. A análise lê apenas o OBJ Y-up em TaleWeaverCmd_Source;
não executa Blender, não altera a malha nem faz upload do personagem.

O relatório compara a altura desejada (referência inicial humanoide de 1,75
unidades) com a largura/profundidade máxima de 1,30 unidade visual. Se
armas, capas, asas ou braços abertos ultrapassarem essa base, o fator pode
reduzir também a altura. O relatório explica a redução e apresenta as
dimensões estimadas. Os mesmos valores ficam em TaleWeaverCmd_escala.json
em "scale_check" ao converter em modo automático.

**Importante:** esses valores são limites VISUAIS escolhidos para o Mini Forge,
não dimensões oficiais do grid, base física/collider ou classificação de
criatura do TaleSpire. Nenhum algoritmo consegue simultaneamente manter
a proporção de asas largas, a altura de um humanoide e toda a malha dentro
de uma base estreita. Ajuste o GLB original no Blender e reconverta se
necessário. Uma conversão real dentro do TaleSpire continua indispensável.

Também foi corrigido o reaproveitamento do log de execução anterior do
TaleWeaverCmd: o log da tentativa é reiniciado antes de cada processo para
evitar que uma falha antiga apareça como diagnóstico atual.
