# Astronyx Mini Forge — Erro 4551 (Windows 11) e Windows 10

A captura enviada pelo usuário mostra: "Incapaz de executar o arquivo no diretório temporário. Instalação abortada. Erro 4551: Uma política de Controle de Aplicativo bloqueou este arquivo."

## Diagnóstico

É um bloqueio de política do Windows, provável **Smart App Control ou Windows Defender Application Control**, durante a execução temporária do mecanismo do Inno Setup. Não indica incompatibilidade com a versão do Windows e não deve ser resolvido desativando o antivírus.

## Distribuição alternativa

A partir da 2.2.1, a Release tem:
- **Instalador tradicional**: `AstronyxMiniForgeStudio-Setup-v2.2.1.exe`, para máquinas sem essa restrição.
- **Versão portátil one-dir**: `AstronyxMiniForgeStudio-Portable-v2.2.1-Win10-Win11-x64.zip`; extraia e execute `AstronyxMiniForgeStudio.exe` na pasta extraída, mantendo a pasta `_internal`.

Esse ZIP não executa o instalador Inno Setup. O PyInstaller em modo one-dir também não precisa descompactar seu runtime numa pasta TEMP em cada execução. Isso **reduz a probabilidade desse erro específico**, mas a política do Windows ainda pode bloquear binários não assinados.

## Confirmação técnica em Windows 11

Em `Visualizador de Eventos > Logs de Aplicativos e Serviços > Microsoft > Windows > CodeIntegrity > Operational`, o evento 3077 registra arquivos bloqueados por políticas de integridade. Informe o nome do arquivo bloqueado sem apagar logs. Não desative Smart App Control, políticas da empresa ou o Defender.

## Compatibilidade

- Windows 10 **22H2 64-bit** é a versão final geral; o suporte padrão acabou em outubro de 2025 (há ESU e edições LTSC específicas).
- Windows 11 64-bit com atualizações recentes.
- A automação compila no Windows Server 2025 e testa o código em Windows Server 2022; não são substitutos de ensaios físicos nas versões de cliente.

## Solução de longo prazo

Assinar todos os executáveis e instaladores com certificado confiável de assinatura de código, preferencialmente por serviço de assinatura de artefatos, incluindo timestamp. Smart App Control não tem exceção segura por aplicativo. A Release atual **não é assinada digitalmente**.

Referências Microsoft:
- https://learn.microsoft.com/windows/apps/develop/smart-app-control/overview
- https://support.microsoft.com/en-us/windows/security/threat-malware-protection/smart-app-control-frequently-asked-questions
- https://learn.microsoft.com/en-us/windows/apps/develop/smart-app-control/code-signing-for-smart-app-control
