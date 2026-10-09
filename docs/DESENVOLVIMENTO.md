# Astronyx Mini Forge Studio V2.1.0

**Novo estúdio visual e distribuição Windows, preservando o motor de conversão funcional da V1.7.** Projeto gratuito e independente do TaleSpire / Meshy.

## Novidades

- Navegação lateral roxa e escura; páginas Início Rápido, Minhas miniaturas, Prévia 3D, Ajustes avançados, Gerar .tsMod, Instalar no TaleSpire, Ajuda.
- **Biblioteca de projetos:** detecta `.tsMod`, miniatura PNG e OBJ nas pastas geradas, com ações para abrir a pasta, conferir a prévia ou escolher o `.tsMod` para instalação. Não altera arquivos nem apaga projetos.
- Painel de estado sempre visível para Blender e TaleWeaverCmd.
- `tools/build_windows.ps1`: prepara `AstronyxMiniForgeStudio.exe` independente de Python.
- `installer/AstronyxMiniForgeStudio.iss`: projeto de instalador Windows que cria atalhos e desinstalador com Inno Setup 6.
- `.github/workflows/build-windows.yml`: gera **dois artefatos** no GitHub Actions: `.exe` portável e instalador `Setup.exe`.
- `iniciar.bat` abre preferencialmente o executável quando disponível; versão de código-fonte também pode ser iniciada usando Python 3.10+.

## Status da versão

**Verificação adicional na V2.1.0:** `--self-test` checa Tcl e recursos empacotados, e o GitHub Actions executa o instalador silenciosamente em Windows para testar o EXE instalado. **Testado neste ambiente:** suíte de testes Python e interface em ambiente gráfico Linux virtual (Tkinter). **Não testado aqui:** compilação nativa do executável ou do instalador no Windows. A exportação .tsMod usa o mesmo motor da V1.7 que você confirmou funcionar no seu computador, sem mudanças nas funções de conversão.

## Instalar na máquina de desenvolvimento

1. Extraia o ZIP completamente.
2. Instale Python 3.10+ na máquina **de desenvolvimento**; execute `instalar.bat` e `iniciar.bat`.
3. Mantenha Blender e TaleSpire instalados. O TaleWeaverCmd vem dentro de `TaleSpire\Tools\TaleWeaverCmd\Windows\`.
4. Use **Início rápido** para escolher seu Meshy (`.blend`, `.glb`, `.fbx`, `.obj`, `.zip`), nome, destino e iniciar a conversão.

## Gerar EXE e instalador no Windows

No computador Windows que vai compilar, instale Python 3.10+ (recomendado 3.12). Para gerar também o **instalador Setup.exe**, instale [Inno Setup 6](https://jrsoftware.org/isdl.php) e execute no PowerShell dentro da pasta do projeto:

```powershell
powershell -ExecutionPolicy Bypass -File .\tools\build_windows.ps1
```

Depois, use `dist\AstronyxMiniForgeStudio.exe` (versão portável) ou `dist\installer\AstronyxMiniForgeStudio-Setup-v2.1.0.exe` (instalador com atalhos).

**Alternativa sem compilar localmente:** envie o código ao seu GitHub, abra Actions → "Astronyx Mini Forge Studio 2.0 Windows" → Run workflow → baixe os dois arquivos publicados na execução. Não há necessidade de compartilhar senhas ou tokens.

Os amigos **não precisam instalar Python** para usar o `.exe` gerado. Eles precisam do Blender e TaleSpire com TaleWeaverCmd para converter, pois não distribuímos esses programas de terceiros.

### Observações importantes

- O `.zip` distribuído aqui contém **código-fonte + projeto de compilação**, não um `.exe` de Windows já compilado.
- O .exe de distribuição pode disparar um alerta SmartScreen por não ter assinatura digital. Baixe somente de um repositório ou pessoa de confiança e verifique o arquivo antes de executar. Não recomendamos ignorar avisos de segurança desconhecidos.
- O instalador não apaga a pasta de miniaturas nem as configurações (`%LOCALAPPDATA%\AstronyxMiniForge`).
- Mantenha backup da V1.7 estável. O V2.0 usa o mesmo arquivo de preferências e não altera a estrutura dos projetos anteriores.
- `.tsMod` só será considerado pronto quando o TaleWeaverCmd realmente produzir o arquivo esperado. O projeto não gera animação ou rigging.

## Testes

```bash
python -m unittest discover -s tests -v
```

## Validação Windows V2.1.0

A ação do GitHub agora impede publicar artefatos quando falhar o autoteste do executável portátil ou do instalador. Faz checagem de recursos, runtime Tcl e execução do instalador em ambiente Windows. Não simula nem atesta conversão 3D real.

Com o executável compilado, rode `AstronyxMiniForgeStudio.exe --self-test relatorio.json` para diagnosticar a distribuição sem abrir a interface. A pasta `dist` também terá `validation-portable.json`, `validation-installer.json` e `SHA256SUMS.txt` na execução da ação.

**Sem acesso ao compilador Windows nesta sessão:** este ZIP traz os arquivos de compilação e testes, mas **não inclui nenhum `.exe` pré-compilado**. Para gerar os executáveis, use a ação GitHub no seu repositório ou execute o script `tools\build_windows.ps1` em um Windows com Python e Inno Setup.

## V2.0.2 – beta de escala/qualidade

O valor inicial 14 foi reduzido para 1,75 (aumento 8x fazia o jogo tratar o modelo como gigante). Migração dos presets antigos; textura padrão 2048; perfil detalhado até 100 mil triângulos, sempre respeitando até 60 mil vértices; UV original mantido nos modelos com apenas um material. 

Para recuperar polígonos e detalhes de textura, é preciso converter **novamente o arquivo original do Meshy**. Repetir apenas .tsMod reaproveita a malha antiga. O programa não exporta esqueleto/animação de caminhada; o movimento da miniatura depende do TaleSpire.

Esta atualização é **experimental**, não validada visualmente com Blender/TaleWeaverCmd reais. Consulte NOTAS_CORRECAO_QUALIDADE.md.


## Atualizações automáticas V2.1.0

O Studio verifica Releases públicas em segundo plano ao abrir e pelo botão Atualizações. Havendo versão nova, mostra notas e oferece Mais tarde, Ver Release ou Baixar e instalar. Instalação é interativa (não silenciosa), com verificação SHA-256 antes de executar. Miniaturas e configurações não são alteradas. A primeira instalação de V2.1.0 deve ser manual para habilitar esse mecanismo nas próximas versões.

Para publicar Release no GitHub Actions use Run workflow e marque publish_release. Alternativamente envie uma tag vX.Y.Z que coincida com core/version.py. O repo precisa ser público para a checagem sem login dos amigos.
