# Compatibilidade e avisos do Windows 11

O instalador é criado com Inno Setup e o aplicativo com PyInstaller. A edição V2.2 inclui metadados de versão do Windows, informações da editora e compilação com `--noupx` (sem compactação UPX), além de testes automáticos e arquivo de checksums SHA-256 nas Releases.

## Limitação do SmartScreen e Smart App Control

Sem assinatura digital confiável, um programa novo pode aparecer como editor desconhecido e ter sua execução bloqueada pelo Windows 11. Isso não indica automaticamente malware, mas também não é uma confirmação de segurança. **Não há um parâmetro de compilação que desative legitimamente a proteção no computador dos usuários.**

A solução duradoura é a assinatura de código confiável, tanto de `AstronyxMiniForgeStudio.exe` quanto do instalador `Setup.exe`, com identidade verificada, ou a publicação pela Microsoft Store. Mesmo programas assinados podem mostrar avisos até ganharem reputação.

Para um alerta de antivírus que classifique o programa erroneamente como ameaça, envie o arquivo ao serviço oficial de análise da Microsoft: https://www.microsoft.com/wdsi/filesubmission.

Sempre distribua a partir de https://github.com/Night0231-creator/forge/releases/latest; evite desativar o Defender e não recomende adicionar exceções genéricas de antivírus.

## Assinar uma Release futuramente

Depois de obter um certificado de assinatura confiável, assine o executável **antes** de compilar o instalador e assine o próprio instalador depois. Use assinatura SHA-256 e carimbo do tempo. Não inclua certificados privados ou senhas neste repositório. Integre o provedor de assinatura ao pipeline do GitHub Actions usando as credenciais gerenciadas pelo serviço escolhido.
