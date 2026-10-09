# Astronyx Mini Forge Studio V2.0.1 — gerar instalador Windows

Este pacote preserva o **motor V1.7** que você testou com o TaleSpire. O Studio utiliza a interface V2.0 com biblioteca, navegação lateral e recursos novos. O objetivo deste pacote é gerar o executável portável e o instalador para que seus amigos **não precisem de Python**.

## Caminho A — compilar pelo seu Windows

1. Extraia `Astronyx_Mini_Forge_Studio_v2_0_1.zip` por completo.
2. Instale Python 3.12 ou superior e [Inno Setup 6](https://jrsoftware.org/isdl.php) **no PC que vai COMPILAR**.
3. Abra o PowerShell **na pasta extraída** e execute:

   ```powershell
   powershell -ExecutionPolicy Bypass -File .\tools\build_windows.ps1
   ```

4. Após os testes automáticos, confira:
   - `dist\AstronyxMiniForgeStudio.exe` — programa portátil.
   - `dist\installer\AstronyxMiniForgeStudio-Setup-v2.0.1.exe` — instalador para os amigos.
   - `dist\validation-portable.json` — autoteste dos arquivos e do runtime Tcl.
5. Rode o Setup.exe **no seu próprio Windows** e abra o Studio. Escolha um modelo Meshy e converta para confirmar o resultado visual no TaleSpire.
6. Distribua o instalador aos amigos. No PC deles ainda precisam estar instalados **Blender** e **TaleSpire**, que fornece o TaleWeaverCmd.

## Caminho B — GitHub Actions (compilar na nuvem)

1. Entre no GitHub e crie um repositório privado para o código.
2. Publique **todo o conteúdo da pasta extraída**, incluindo a pasta oculta `.github/workflows/`. Uma opção prática é usar o GitHub Desktop (File → Add local repository, Create a repository here, Publish repository). Ao publicar, selecione **Keep this code private** se desejar.
3. Acesse a aba **Actions** do repositório e procure **Astronyx Mini Forge Studio 2.0.1 Windows**.
4. Clique em **Run workflow** se precisar executar manualmente. Um `push` na branch main também inicia o fluxo.
5. Ao terminar com marca verde, abra a execução e baixe na seção **Artifacts**:
   - `AstronyxMiniForgeStudio-Windows-Portable` (contém o EXE portátil).
   - `AstronyxMiniForgeStudio-Windows-Setup` (contém o instalador).
   - `AstronyxMiniForgeStudio-Validacao` (relatórios do autoteste e SHA256 dos arquivos).
6. Instale no seu Windows e faça pelo menos uma conversão real. Somente depois compartilhe com os amigos.

## O que os testes garantem e o que NÃO garantem

A suíte testa funções de preparação, estrutura de arquivos, instalação local de `.tsMod` e erros. O `--self-test` do EXE testa se os recursos e o Tcl foram incluídos; a ação Windows também instala silenciosamente o Setup e executa o autoteste do EXE instalado.

**O teste automático não abre TaleSpire nem confirma a conversão de um arquivo Meshy real.** Essa verificação final precisa ser feita em um computador com Blender e TaleSpire. O compilador Windows não está disponível no ambiente onde este ZIP foi criado, por isso o pacote **não contém executáveis Windows já compilados**.

## Atualizações seguras

Mantenha o backup do Studio/V1.7. O instalador não deve remover as miniaturas salvas pelo usuário. Não distribua tokens, senhas, arquivos `settings.json` pessoais ou modelos privados sem autorização.
