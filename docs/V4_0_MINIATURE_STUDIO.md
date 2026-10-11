# Astronyx Mini Forge V4.0 — Miniature Studio

## O que mudou
Na imagem da V3.2 a miniatura aparecia como um conjunto de pequenos triângulos escuros porque o visualizador de geometria do Tk era mostrado enquanto a renderização texturizada ainda estava pendente, falhava ou ficava lenta. Agora a V4 usa o **modelo texturizado** como destino principal e, se OpenGL falhar, desenha uma prévia colorida rápida por CPU usando todas as faces disponíveis (até os limites de segurança). Não garante um modelo PBR no fallback CPU, mas é melhor do que mostrar apenas a malha escura.

A bancada foi redesenhada como um único espaço de pintura: lista de projetos Meshy à esquerda; pincéis, camadas, materiais e viewport no centro; barra compacta com Importar GLB/ZIP, Exportar .tsMod e Instalar no TaleSpire. O modelo selecionado abre diretamente no Painting Studio. As telas avançadas de preparação, Blender e TaleWeaverCmd continuam acessíveis pelo menu do aplicativo. Não mexemos no motor de conversão, nas escalas nem nas texturas exportadas sem confirmação.

## Usando a bancada
1. Abra o Mini Forge V4 e selecione uma miniatura existente na barra esquerda. Ou clique em **Importar GLB / ZIP**.
2. A pintura 3D aparece automaticamente. Esquerdo pinta, botão direito gira, roda aproxima.
3. Na aba Pincéis escolha pincel, preenchimento, seleção de cor ou carimbo. Carimbos de Estrela, Selo e Runa vêm no aplicativo. **Carregar PNG…** usa um arquivo local com transparência; o arquivo não é enviado para servidor.
4. Camadas: adicione, reordene, desfaça, ajuste opacidade; Materiais: edite regiões MAES.
5. **Salvar projeto** grava seus rascunhos; **Exportar texturas** aplica os PNGs na preparação com backup.
6. Para gerar a miniatura jogável, escolha **Exportar .tsMod**, rode o TaleWeaverCmd e valide no TaleSpire.

## Diagnóstico GPU
- **GPU OpenGL 3.3 / PBR** no rodapé: renderizador ModernGL ativo.
- **CPU · Albedo rápido colorido**: o renderizador usou a prévia CPU mais rápida, com cor por face. O 3D permanece girável e o editor pinta nas UVs, mas a prévia não reproduz materiais PBR.
- Quando há erro no driver, o texto do backend inclui uma mensagem curta para investigação. Atualizar o driver OpenGL 3.3+ é recomendável.
- A visualização CPU 2D por face utiliza cores do Albedo nos centros UV e uma iluminação simples; a precisão é menor que a prévia GPU ou a renderização no TaleSpire.

## Recursos do Basecoat que ainda precisam de implementação
Esta versão não copia código, marca ou ativos do Basecoat e **não alcança paridade completa**: não há remesh otimizado automático com bake de normais, ambient occlusion de superfície com projeção real, region blocking por geometria/IA, carimbos projetados atravessando costuras UV, tablet com pressão, HDRI real, exportação Unity AssetBundle completa nem instalação automática de todos os modos de TaleSpire.

## Testes
O CI Windows compila o aplicativo, executa testes do motor, testa Setup e ZIP extraído. O shader GPU deve também ser testado num Windows 10/11 com driver real; a escala 1×1 e a movimentação são confirmadas apenas dentro do TaleSpire.

Referência de recursos: https://store.steampowered.com/app/4468700/Basecoat_Mini_Painting_Studio/
