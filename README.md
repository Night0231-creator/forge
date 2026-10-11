# Astronyx Mini Forge Studio 💜

**Conversor gratuito de personagens 3D do Meshy para miniaturas do TaleSpire.**

## ⬇️ Baixar para Windows 10 (22H2 x64) e Windows 11 x64

### [BAIXAR VERSÃO PORTÁTIL (ZIP) — recomendada quando o instalador mostra erro 4551](https://github.com/Night0231-creator/forge/releases/latest)

1. Baixe o arquivo `AstronyxMiniForgeStudio-Portable-v4.2.0-Win10-Win11-x64.zip`.
2. Clique com o botão direito e selecione **Extrair tudo**; não execute dentro do ZIP.
3. Abra a pasta `AstronyxMiniForgeStudio` extraída.
4. Execute `AstronyxMiniForgeStudio.exe` e mantenha a pasta `_internal` junto dele.

A versão portátil não executa o instalador Inno Setup nem extrai um bootloader PyInstaller dentro de TEMP; isso evita o caminho que provocou o **erro 4551** em alguns Windows 11. **Ainda pode ser bloqueada por políticas de segurança**, pois não tem assinatura digital certificada. Não desligue o Defender, Smart App Control ou políticas da empresa.

### [Baixar instalador tradicional (Setup.exe)](https://github.com/Night0231-creator/forge/releases/latest)

Baixe `AstronyxMiniForgeStudio-Setup-v4.2.0.exe`. O instalador continua disponível para Windows 10 e Windows 11 nos computadores que permitem a execução.

**Dependências para converter:** [Blender](https://www.blender.org/download/) e [TaleSpire na Steam](https://store.steampowered.com/app/720620/TaleSpire/) com TaleWeaverCmd. Python não é necessário no computador dos amigos.

**Atualizações:** no instalador tradicional, o programa oferece o novo Setup. No modo portátil, mostra a página das Releases para baixar um ZIP novo manualmente.

**Compatibilidade:** Windows 10 22H2 x64 (versão final do Windows 10) e Windows 11 x64. Os testes automáticos do GitHub Actions usam runners Windows Server 2022 e 2025, que não substituem testes reais em Windows 10/11 de clientes.

**Sobre o bloqueio 4551:** [guia detalhado](docs/WINDOWS10_WINDOWS11_ERRO4551.md).

> Ferramenta independente do Meshy e TaleSpire. Use arquivos que você tenha direito de baixar e converter.

## Para quem desenvolve o projeto

O **único executável de instalação destinado aos amigos** fica na página de **Releases**. O código, testes e automação ficam preservados neste repositório para permitir gerar próximas versões sem quebrar as atualizações.

[Documentação para desenvolvedores](docs/DESENVOLVIMENTO.md)


## Histórico: melhorias introduzidas na V2.2.0

- HUD híbrido Blender + Astronyx, dashboard e galeria de personagens com pesquisa.
- Prévia geométrica, aramada e albedo/UV com controles de câmera.
- Preservados os arquivos do motor de conversão da V2.1.0.
- Executável e instalador com metadados de versão e identificação de editora.
- **Limite atual:** sem certificado de assinatura, o Windows 11 ainda pode bloquear o instalador por reputação desconhecida.

### O que resolve realmente o SmartScreen
Assinar o programa e o instalador com um certificado confiável, mantendo o mesmo editor nas próximas versões, e permitir que a reputação seja estabelecida; alternativamente, distribuir pela Microsoft Store. Não é possível prometer ausência de aviso apenas alterando o código.


## Histórico: V2.2.2 — Escala e qualidade
A correção limita a escala automática pela altura e pela base visual (largura/profundidade), preserva mais detalhes com os presets Alta e Ultra e melhora as normais da malha. Ultra é opcional: 4096 px consome bastante memória. Consulte [notas da V2.2.2](docs/V2_2_2_SCALE_QUALITY.md). A opção portátil para Windows 10/11 continua disponível.


## Astronyx V2.2.3 — HUD refinado

A interface recebeu um dashboard renovado, navegação com destaques e feedback ao passar o mouse, cabeçalho de contexto, cores e tipografia mais consistentes. A biblioteca agora se adapta à largura da janela, permite pesquisa sem revarrer o disco e mostra miniaturas com redimensionamento de alta qualidade. O motor de conversão e os arquivos dos seus personagens continuam inalterados.

[Notas de interface e testes](docs/V2_2_3_HUD.md).


## V2.2.5 — Instalador e atualização interna

O Setup distribui o runtime em uma pasta `_internal` ao lado do executável. Isso evita a extração de bibliotecas Python em `_MEI` em cada abertura do app instalado. O instalador utiliza fechamento controlado de aplicativos pelo Inno Setup antes de substituir arquivos, e o atualizador reconhece instalações pela presença do desinstalador `unins000.exe`. A versão ZIP portátil continua disponível separadamente.

Se a atualização da V2.2.3 falhar, baixe o novo Setup manualmente na página Releases e execute com o programa fechado. O instalador preserva os arquivos de projetos, Blender e TaleSpire. O aplicativo não tem assinatura digital certificada; ainda podem existir avisos do SmartScreen.


## V2.2.5 — Diagnostico do TaleWeaverCmd

- Verifica `UnityPlayer.dll` e `TaleWeaverCmd_Data` ao chamar o binario oficial do Windows; recomende verificar arquivos do TaleSpire na Steam se faltarem.
- Texturas PNG com mais de 2048 px sao reduzidas apenas na copia de `Entrada_TaleWeaverCmd`; arquivos originais preservados.
- Para saida com codigo 1, exibe as mensagens relevantes de `taleweavercmd.log` em vez de somente `memorysetup`.
- A causa especifica de um erro codigo 1 so pode ser confirmada ao analisar o log da falha real.


## V2.2.6 — Prévia 1×1 e fidelidade Meshy

- Prévia texturizada com régua humanoide 1×1 visual, sem alterar o arquivo ou o collider do TaleSpire.
- Amostragem bilinear na prévia e novo diagnóstico de escala por largura, profundidade e altura.
- Para materiais simples com PNG e UV compatíveis, preserva o albedo original sem recompressão; para materiais complexos, continua usando o Blender.
- Baking com margens de UV refinadas, quatro amostras, enquadramento da thumbnail pela altura efetiva e notas de qualidade no log.
- Consulte [notas técnicas](docs/V2_2_6_MESHY_QUALITY_PREVIEW.md) e [auditoria 1×1](docs/V2_2_6_SCALE_DIAGNOSTICS.md). A conversão real precisa ser conferida no TaleSpire.


## V2.2.7 — Atualizações automáticas e HUD arredondado

- Opção **Avisar sobre novas versões** na barra lateral, ativada por padrão e persistida nas preferências.
- Consulta a Release oficial ao abrir o Studio e a cada cinco minutos enquanto estiver aberto. Mostra uma notificação por versão; o botão Atualizações permite consultar manualmente.
- Nenhuma instalação silenciosa: apenas o usuário autoriza o download e a execução do instalador com hash SHA-256 verificado. O modo portátil continua com download manual do ZIP.
- Menus de navegação, ações e campos com cantos arredondados; valores e rótulos de ajustes de modelagem centralizados.
- O atualizador não mantém processos em segundo plano quando o aplicativo está fechado e não promete notificação instantânea: até cinco minutos entre verificações, mais latência de rede.


## V2.2.8 — Correção do erro de mais de 60.000 vértices

- Otimiza automaticamente a malha do Meshy pela contagem de combinações UV/normais/material do OBJ preparado.
- Mantém alvo conservador de 48 mil vértices estimados antes do TaleWeaverCmd (teto oficial: 60 mil).
- FBX e OBJ usam a mesma malha pós-otimização; o GLB original não é alterado.
- Mensagem prioriza erro real de vértices sobre alertas de shader. A simplificação pode reduzir detalhes geométricos finos.
- [Notas técnicas](docs/V2_2_8_VERTEX_OVERFLOW_FIX.md).


## V2.2.9 — Comparação com .tsMod pronto do Basecoat

- Selecione um .tsMod pronto na aba Instalar no TaleSpire como **referência**.
- Compare o cabeçalho, a versão interna e os metadados com um .tsMod produzido no Mini Forge.
- Ao gerar um .tsMod, salva um relatório JSON na pasta do projeto quando houver referência selecionada.
- A comparação também funciona no comando de repetir apenas a exportação .tsMod.
- Não altera, extrai, substitui ou redistribui o binário de referência. Cabeçalho semelhante NÃO comprova que o modelo 3D funciona no TaleSpire ou satisfaz limite de vértices.


## V2.2.10 — Corrigir miniaturas muito pequenas (preset visual Basecoat)

- Remove a antiga redução automática da altura total do personagem para conter asas ou armas na largura de 1,30 unidade.
- Ao selecionar GLB/FBX/OBJ/BLEND/ZIP do Meshy, aplica o perfil visual Basecoat 1×1: altura 1,75, rotação 0, 100.000 triângulos, textura 2048, qualidade Alta e escala automática.
- Inclui opção para desativar o preset e botão para reaplicar os ajustes; botão +25% permite calibrar a altura conforme o resultado no TaleSpire.
- A referência .tsMod Basecoat não informa uma altura confiável no cabeçalho: os valores são aproximados, não uma reprodução exata.
- Para aplicar a correção, reimporte o **GLB original** do Meshy e faça a conversão completa; arquivos OBJ antigos já reduzidos não recuperam detalhes perdidos.

## V2.2.11 — Preparar miniaturas para TaleWeaverLite/Unity

- Novo botão para gerar um ZIP com malha OBJ de pivô nos pés, materiais, Albedo/Normal/MAES e FBX original alternativo.
- Usa **Transform** para ajuste VISUAL no TaleWeaverLite e **Default Scale = 1** para escala inicial 1×1, conforme documentação oficial.
- Inclui guia, estimativa de ancoragem e sugestão de visual 8× baseada apenas no teste do Eclipse Warlord (não é um padrão universal).
- **Requer Unity 2021.3.45f2 + TaleWeaverLite gratuitos para finalizar .tsMod.** Não altera a geração automática existente pelo TaleWeaverCmd.
- O modo é experimental, não altera a base física ou o colisor automaticamente e não promete eliminar o bug de movimentação.
- [Manual do fluxo TaleWeaverLite](docs/V2_2_11_UNITY_HANDOFF.md).


## V2.2.12 — Tela inicial essencial e importação direta Meshy

- Abra Início, arraste o GLB/ZIP do Meshy na área indicada ou clique em Escolher GLB ou ZIP, depois Gerar .tsMod.
- Menus principais: Início, Meus modelos, Instalar no TaleSpire. Ajustes, Unity e diagnóstico ficam dentro de Mais opções; continuam disponíveis.
- Suporte opcional a arrastar/soltar nativo Windows com TkDND integrado ao pacote. Se indisponível, use o seletor padrão.
- O fluxo de um clique usa Blender + TaleWeaverCmd local. Unity/TaleWeaverLite continua como preparação opcional com etapa final manual, até validar automação no editor.
- [Manual V2.2.12](docs/V2_2_12_SIMPLE_IMPORT.md).


## V2.2.13 — Unity Bridge

- Selecione uma vez o projeto TaleWeaverLite no Unity Hub e ative a importação automática após a conversão.
- Cria Assets/AstronyxImports com OBJ ancorado, Albedo/Normal/MAES e script C# que gera material e prefab de prévia.
- Importar último modelo no Unity reutiliza uma conversão anterior.
- O .tsMod ainda exige salvar manualmente no TaleWeaverLite; escala 1x1 e movimento precisam de validação no jogo.
- [Manual da V2.2.13](docs/V2_2_13_UNITY_BRIDGE.md).


## V2.2.14 — Calibrador visual 1×1

- Na tela Início, **Calibrar 1×1** mostra a projeção do OBJ real ao lado de um quadrado 1×1 de referência geométrica e uma silhueta humana de 1,75 unidade.
- Mede os limites reais do OBJ, mediana aproximada dos pés e largura do corpo sem tratar acessórios automaticamente como a base física.
- Cada conversão registra `calibracao_visual_1x1.json` com medições e alertas de tamanho, sem alterar a malha original nem o `.tsMod`.
- Referências não equivalem ao collider/Default Scale do TaleSpire: validação final no jogo continua necessária.
- Editor de pintura de materiais fica para uma próxima versão. [Manual](docs/V2_2_14_VISUAL_CALIBRATOR.md).


## V2.2.15 — Painting Studio UV

- **PINTAR MINIATURA** abre o editor de textura UV com pincel, borracha, balde, conta-gotas, paleta, opacidade, desfazer e refazer.
- O editor permite salvar rascunhos em `Pintura/Albedo_editado.png` e aplicar a pintura com backups às texturas usadas pelo TaleWeaverCmd.
- O `.tsMod` anterior não é alterado: use **Gerar .tsMod de uma pasta já preparada** para incluir a nova textura.
- A prévia 3D permanece somente visual; pintura diretamente na malha 3D será etapa posterior.
- [Guia do Painting Studio](docs/V2_2_15_PAINTING_STUDIO.md).


## V2.3.0 — Pintura direta na superfície 3D

- Painting Studio agora aceita pinceladas no **modelo 3D visível**: clique sobre uma face, encontre a coordenada UV pela interpolação baricêntrica e edite o Albedo da miniatura.
- Botão esquerdo: pintar, direito: girar, roda: zoom. A opção de desligar pintura 3D devolve o giro ao botão esquerdo.
- Pincel, balde, conta-gotas e restaurar original disponíveis sobre o modelo; prévia da textura é atualizada periodicamente durante a pintura.
- Desfazer/refazer, rascunho e backups continuam; o .tsMod precisa ser gerado novamente para refletir as alterações.
- A seleção é calculada por CPU e é limitada às faces renderizadas do OBJ. Não é aceleração por GPU nem pintura PBR.
- [Guia V2.3](docs/V2_3_3D_PAINT.md).

## V2.4.0 — Camadas, seleção inteligente e materiais TaleSpire

- No **Painting Studio**, novas abas Pincéis, Camadas e Materiais para manter a interface compacta.
- As camadas são transparentes e editáveis independentemente: adicionar/remover, ocultar, controlar opacidade, alterar ordem, desfazer/refazer. O limite dinâmico de camadas protege a memória em texturas grandes.
- **Selecionar região similar** encontra a área conectada de cor semelhante (tolerância ajustável) no atlas, clicando também sobre o 3D. Pincel, borracha e balde respeitam a seleção.
- Presets Aço, Ouro, Bronze, Couro, Tecido, Pele, Pedra e Cristal editam a textura **MAES** da região selecionada, usando os canais R=Metallic, G=AO, B=Emissive, A=Smoothness, com undo.
- Salvar gera Albedo_editado.png, camadas/camada_XX.png, camadas.json e, se houver edição de material, MAES_editado.png. Reabrir restaura as camadas somente se a imagem-base ainda corresponder ao projeto salvo.
- Aplicar gera backups dos Albedos e MAES existentes antes de modificar os arquivos que alimentam TaleWeaverCmd/Unity. A pasta de staging não excede 2048 em nenhuma dimensão.
- **A prévia ainda mostra Albedo; o metal/brilho/emissão devem ser verificados dentro do TaleSpire** após gerar novamente o .tsMod. O programa não altera a física/base 1×1.
- [Manual da V2.4](docs/V2_4_LAYERED_MATERIALS.md).


## V3.0.0 — Novo aplicativo unificado de pintura 3D

A interface principal do executável foi redesenhada para colocar **pintura, projetos e exportação** no centro da experiência. O fluxo tem inspiração funcional na categoria de programas como Basecoat, com design e código próprios.

- **Estúdio de Pintura** é a nova tela inicial: lista de projetos convertidos, miniatura texturizada grande ao centro e ações laterais de Pintar, Preparar .tsMod e Instalar no TaleSpire.
- Clique em **Pintar miniatura** para abrir o editor **na própria área de trabalho**, sem uma segunda janela. O botão **← Projetos** volta à biblioteca com confirmação de perda de alterações não salvas.
- **Editor V3.0:** viewport 3D grande com pintura no modelo, câmera com botão direito, ferramentas à esquerda (pincéis, camadas, materiais) e **Mapa UV opcional**. O UV inicia recolhido para liberar espaço para o personagem.
- **Importar Miniatura** abre o fluxo existente de conversão Meshy GLB/ZIP. Páginas técnicas e configuração de Blender/TaleWeaverCmd continuam acessíveis pelo menu **Mais opções**.
- **Atalhos** e atualizador existentes continuam, com versões renomeadas para 3.0.0. Nenhum .tsMod pré-existente é alterado ao abrir o estúdio.
- Esta versão muda a experiência visual, mas mantém o **renderizador CPU**, o motor de pintura V2.4, materiais MAES e os mesmos limites de seleção por UV. Não inclui todos os recursos do Basecoat.
- [Guia do novo estúdio V3.0](docs/V3_0_UNIFIED_WORKSPACE.md).


## V3.1.0 — GPU PBR Preview (Windows 10/11)

- **Aceleração opcional por GPU**: ModernGL (OpenGL 3.3+) renderiza a miniatura para um framebuffer fora da tela. Uma thread própria mantém o contexto vivo; a janela Tk mostra o frame pronto.
- **PBR aproximado na prévia**: shader usa Albedo, MAES (metálico R, AO G, emissão B, suavidade A), normais disponíveis, luz direcional, Fresnel/GGX e tone mapping. Não altera o arquivo final.
- Na janela Painting Studio há **GPU / PBR**, sliders **Luz** e **Emissão**. Ao pintar ou aplicar preset, a prévia atualiza o material na GPU.
- **Fallback automático**: drivers sem OpenGL 3.3 continuam com renderizador CPU de Albedo. O status no viewer informa qual modo foi usado.
- Prévia limitada a 150 mil triângulos e 900x900 pixels por frame; renderização GPU + cópia GPU→Tk não garantem 60 FPS.
- PyInstaller inclui ModernGL e glcontext; CI Windows testa código, aplicativo empacotado, instalador e ZIP portátil. [Guia V3.1](docs/V3_1_GPU_PBR_PREVIEW.md).


## V3.2.0 — Pintura fluida e iluminação ambiente

- Quando você pinta ou gira uma miniatura, o render mantém a última imagem enquanto a próxima é calculada, sem redesenhar até 1600 polígonos Tk em toda movimentação.
- Pincel e borracha recompõem somente o retângulo da textura alterado. As operações que modificam camadas inteiras continuam recompondo a textura completa quando necessário.
- O modo OpenGL 3.3 / ModernGL inclui três presets de iluminação ambiente hemisférica: Estúdio, Pôr do sol e Luar, com intensidade ajustável de 0–200%. Não é um HDRI real e não promete 60 FPS.
- Atualizações da cor Albedo deixam de copiar o mapa MAES a cada pincelada. Os dados MAES continuam modificados somente pelo material e sua exportação.
- O modo CPU de reserva, histórico/rascunhos/backups e exportação TaleWeaverLite permanecem disponíveis; nada modifica automaticamente .tsMod nem escala 1x1.
- [Guia V3.2](docs/V3_2_SMOOTH_PAINT_ENV_LIGHTING.md).


## V4.0.0 — Astronyx Miniature Studio (redesign e prévia corrigida)

- O aplicativo passa a abrir o editor de pintura ao selecionar um projeto Meshy preparado, sem a tela intermediária de geometria escura. Biblioteca e bancada permanecem na mesma janela.
- Cabeçalhos duplicados removidos do workspace para ampliar o modelo 3D. Importação, exportação TaleSpire e instalação permanecem no fluxo principal; telas técnicas continuam acessíveis.
- **Correção de miniaturas escuras:** quando OpenGL não está disponível ou falha no driver Windows, o fallback CPU desenha toda a silhueta em cores do Albedo, rasterizando os triângulos pela ordem de profundidade com Pillow, sem depender da prévia geométrica limitada a 1600 faces. Em modelos pequenos, mantém a rasterização texturizada mais precisa. A falha GPU é exibida no status em vez de ficar escondida.
- **Carimbos** Estrela, Selo, Runa e PNG de transparência importado; podem ser colocados diretamente na superfície 3D ou no mapa UV, respeitando camadas e seleções.
- O editor mantém backups dos Albedos/MAES antes de exportar e não altera arquivos .tsMod automaticamente; gere novamente o .tsMod pelo conversor após editar a pintura.
- Este é um produto independente inspirado na usabilidade do Basecoat, **não uma réplica do software**. Ainda faltam automação de remesh/unwrap com bake de normais, iluminação HDRI real, pincel UV com simetria avançada, regiões semânticas e outros recursos. A visualização GPU depende do driver OpenGL 3.3+.
- [Guia V4.0](docs/V4_0_MINIATURE_STUDIO.md).


## V4.1.0 — Pintura de superfície e regiões geométricas

- Pincel e carimbos projetados sobre a superfície, atravessando costuras UV.
- Dureza ajustável, proteção das faces ocultas e pintura através opcional.
- Regiões conectadas da geometria com ângulo ajustável e preenchimento para modelos sem cores.
- Materiais personalizados, seleção realçada no 3D e ferramentas com rolagem.
- Mantém preparação, backups e reexportação TaleSpire. [Guia e limites](docs/V4_1_SURFACE_PAINT.md).


## V4.2.0 — Novo visual do estúdio

- Painéis cinza-escuro, seleção azul e ferramentas vetoriais compactas.
- Menus Arquivo / Preparar / Exportar / Ajuda; projetos no seletor superior e painel recolhível.
- Paleta com busca por nome e categorias; cor personalizada por seletor ou código hexadecimal.
- Controles do pincel no painel lateral, materiais e camadas em abas; iluminação e mapa UV em Exibir.
- Grade discreta na prévia GPU/CPU, vistas de câmera e movimento com o botão do meio.
- O visual segue a organização das imagens públicas do Basecoat, com marca e implementação próprias.
- A grade é apenas visual: não muda a malha, a escala ou as texturas exportadas.
