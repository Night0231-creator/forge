# Astronyx Mini Forge Studio 💜

**Conversor gratuito de personagens 3D do Meshy para miniaturas do TaleSpire.**

## ⬇️ Baixar para Windows 10 (22H2 x64) e Windows 11 x64

### [BAIXAR VERSÃO PORTÁTIL (ZIP) — recomendada quando o instalador mostra erro 4551](https://github.com/Night0231-creator/forge/releases/latest)

1. Baixe o arquivo `AstronyxMiniForgeStudio-Portable-v2.2.3-Win10-Win11-x64.zip`.
2. Clique com o botão direito e selecione **Extrair tudo**; não execute dentro do ZIP.
3. Abra a pasta `AstronyxMiniForgeStudio` extraída.
4. Execute `AstronyxMiniForgeStudio.exe` e mantenha a pasta `_internal` junto dele.

A versão portátil não executa o instalador Inno Setup nem extrai um bootloader PyInstaller dentro de TEMP; isso evita o caminho que provocou o **erro 4551** em alguns Windows 11. **Ainda pode ser bloqueada por políticas de segurança**, pois não tem assinatura digital certificada. Não desligue o Defender, Smart App Control ou políticas da empresa.

### [Baixar instalador tradicional (Setup.exe)](https://github.com/Night0231-creator/forge/releases/latest)

Baixe `AstronyxMiniForgeStudio-Setup-v2.2.3.exe`. O instalador continua disponível para Windows 10 e Windows 11 nos computadores que permitem a execução.

**Dependências para converter:** [Blender](https://www.blender.org/download/) e [TaleSpire na Steam](https://store.steampowered.com/app/720620/TaleSpire/) com TaleWeaverCmd. Python não é necessário no computador dos amigos.

**Atualizações:** no instalador tradicional, o programa oferece o novo Setup. No modo portátil, mostra a página das Releases para baixar um ZIP novo manualmente.

**Compatibilidade:** Windows 10 22H2 x64 (versão final do Windows 10) e Windows 11 x64. Os testes automáticos do GitHub Actions usam runners Windows Server 2022 e 2025, que não substituem testes reais em Windows 10/11 de clientes.

**Sobre o bloqueio 4551:** [guia detalhado](docs/WINDOWS10_WINDOWS11_ERRO4551.md).

> Ferramenta independente do Meshy e TaleSpire. Use arquivos que você tenha direito de baixar e converter.

## Para quem desenvolve o projeto

O **único executável de instalação destinado aos amigos** fica na página de **Releases**. O código, testes e automação ficam preservados neste repositório para permitir gerar próximas versões sem quebrar as atualizações.

[Documentação para desenvolvedores](docs/DESENVOLVIMENTO.md)


## Novidades V2.2.3

- HUD híbrido Blender + Astronyx, dashboard e galeria de personagens com pesquisa.
- Prévia geométrica, aramada e albedo/UV com controles de câmera.
- Preservados os arquivos do motor de conversão da V2.1.0.
- Executável e instalador com metadados de versão e identificação de editora.
- **Limite atual:** sem certificado de assinatura, o Windows 11 ainda pode bloquear o instalador por reputação desconhecida.

### O que resolve realmente o SmartScreen
Assinar o programa e o instalador com um certificado confiável, mantendo o mesmo editor nas próximas versões, e permitir que a reputação seja estabelecida; alternativamente, distribuir pela Microsoft Store. Não é possível prometer ausência de aviso apenas alterando o código.


## V2.2.3 — Escala e qualidade
A correção limita a escala automática pela altura e pela base visual (largura/profundidade), preserva mais detalhes com os presets Alta e Ultra e melhora as normais da malha. Ultra é opcional: 4096 px consome bastante memória. Consulte [notas da V2.2.3](docs/V2_2_2_SCALE_QUALITY.md). A opção portátil para Windows 10/11 continua disponível.


## Astronyx V2.2.3 — HUD refinado

A interface recebeu um dashboard renovado, navegação com destaques e feedback ao passar o mouse, cabeçalho de contexto, cores e tipografia mais consistentes. A biblioteca agora se adapta à largura da janela, permite pesquisa sem revarrer o disco e mostra miniaturas com redimensionamento de alta qualidade. O motor de conversão e os arquivos dos seus personagens continuam inalterados.

[Notas de interface e testes](docs/V2_2_3_HUD.md).
