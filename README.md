# Astronyx Mini Forge Studio 💜

**Conversor gratuito de personagens 3D do Meshy para miniaturas do TaleSpire.**

## ⬇️ Baixar para Windows 10 (22H2 x64) e Windows 11 x64

### [BAIXAR VERSÃO PORTÁTIL (ZIP) — recomendada quando o instalador mostra erro 4551](https://github.com/Night0231-creator/forge/releases/latest)

1. Baixe o arquivo `AstronyxMiniForgeStudio-Portable-v2.2.9-Win10-Win11-x64.zip`.
2. Clique com o botão direito e selecione **Extrair tudo**; não execute dentro do ZIP.
3. Abra a pasta `AstronyxMiniForgeStudio` extraída.
4. Execute `AstronyxMiniForgeStudio.exe` e mantenha a pasta `_internal` junto dele.

A versão portátil não executa o instalador Inno Setup nem extrai um bootloader PyInstaller dentro de TEMP; isso evita o caminho que provocou o **erro 4551** em alguns Windows 11. **Ainda pode ser bloqueada por políticas de segurança**, pois não tem assinatura digital certificada. Não desligue o Defender, Smart App Control ou políticas da empresa.

### [Baixar instalador tradicional (Setup.exe)](https://github.com/Night0231-creator/forge/releases/latest)

Baixe `AstronyxMiniForgeStudio-Setup-v2.2.9.exe`. O instalador continua disponível para Windows 10 e Windows 11 nos computadores que permitem a execução.

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
