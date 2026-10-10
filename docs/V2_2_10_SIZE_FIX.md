# V2.2.10 — Perfil Basecoat 1×1 visual e correção da miniatura minúscula

## Defeito corrigido

A V2.2.9 forçava a malha inteira a ter largura/profundidade no máximo 1,30 unidade **depois** de ajustar a altura para 1,75. Personagens com asas, espadas, capas e acessórios podiam ser reduzidos drasticamente. No segundo estágio, TaleWeaverCmd podia reduzir a malha novamente pela mesma regra.

Agora o Blender ajusta pela altura escolhida, mantendo a largura natural do personagem. A etapa automática do TaleWeaverCmd usa altura vertical sem impor largura máxima por padrão. A auditoria de escala indica o tamanho final estimado e continua sem modificar o collider do jogo.

## Novo preset aplicado ao abrir modelos Meshy

Ao selecionar um arquivo válido .GLB, .GLTF, .FBX, .OBJ, .BLEND, .STL ou .ZIP:
- Altura vertical: 1,75 unidade (referência inicial editável).
- Rotação Z: 0 graus.
- Geometria: perfil Alta, até 100.000 triângulos de entrada; a otimização do TaleWeaverCmd continua limitada a vértices seguros.
- Textura: 2048 pixels.
- Escala automática e TaleWeaverCmd: ativados.
- Multiplicador manual: 1 (não utilizado enquanto escala automática estiver ativada).
- Exportação CustomMiniPlugin: desativada (opcional para uso com mod).

A opção de autoaplicar o preset pode ser desativada. Para retornar ao perfil use o botão **Reaplicar perfil Basecoat 1×1**. Para aumentar em etapas controladas, use **Aumentar altura visual em 25%** na tela Gerar .tsMod; isso altera o perfil local, não o arquivo de referência.

## O que o Basecoat realmente fornece

O .tsMod enviado (eclipse_warlord) é um pacote binário. Seu cabeçalho revela formato e metadados do Basecoat, mas não fornece uma altura 3D ou tamanho de gameplay confiável. Portanto o nome *Basecoat 1×1 visual* descreve uma aproximação para comparação, nunca uma extração de proporções internas ou garantia de escala idêntica.

A documentação oficial informa que TaleWeaverLite tem ajustes separados de visual e Default Scale (tamanho inicial no tabuleiro). O TaleWeaverCmd não expõe necessariamente o mesmo ajuste no JSON documentado. O resultado só pode ser validado observando o personagem dentro do TaleSpire.

- https://talespire.com/taleweaverlite-guide
- https://talespire.com/faq

## Teste real

1. Abra V2.2.10.
2. Selecione o **GLB ORIGINAL** do Meshy. O preset deve ser aplicado automaticamente.
3. Converta de novo por inteiro (não use somente Gerar .tsMod de arquivos antigos reduzidos).
4. No TaleSpire, compare com uma miniatura humanoide 1×1 nativa e com o arquivo Basecoat pronto, à mesma aproximação da câmera.
5. Caso ainda esteja pequeno, calibre a altura visual (por exemplo usando +25%) e gere de novo; não aumente diretamente a base física no arquivo binário.

Os testes de CI não abrem o jogo, nem garantem escala de gameplay exata.
