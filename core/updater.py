"""Opt-in updates from verified public GitHub Releases. No silent installs."""
from __future__ import annotations
import hashlib
import json
import os
import re
import subprocess
import sys
import urllib.request
from pathlib import Path
from urllib.parse import urlsplit
from dataclasses import dataclass
from .version import APP_VERSION, REPO

API = f'https://api.github.com/repos/{REPO}/releases/latest'
PAGE = f'https://github.com/{REPO}/releases/latest'
MAX_SIZE = 200 * 1024 * 1024

class UpdateError(Exception):
    pass

def version_tuple(v):
    m = re.fullmatch(r'v?(\d+)\.(\d+)\.(\d+)', str(v).strip())
    if not m: raise ValueError('Versão inválida')
    return tuple(map(int, m.groups()))

def allowed(url, release=False):
    x = urlsplit(url)
    if x.scheme != 'https' or x.username or x.password: return False
    if release: return x.hostname == 'github.com' and x.path.startswith(f'/{REPO}/releases/download/')
    return x.hostname == 'api.github.com' and x.path == f'/repos/{REPO}/releases/latest'

def read_url(url, limit):
    request = urllib.request.Request(url, headers={'User-Agent':'AstronyxMiniForgeStudio','Accept':'application/vnd.github+json'})
    with urllib.request.urlopen(request, timeout=18) as resp: result = resp.read(limit+1)
    if len(result)>limit: raise UpdateError('Arquivo maior que o limite permitido')
    return result

@dataclass(frozen=True)
class Release:
    version: str
    notes: str
    page: str
    filename: str
    installer_url: str
    sha_url: str
    size: int
    digest: str|None=None

def find_update(current=APP_VERSION):
    try:
        obj=json.loads(read_url(API,262144))
        if obj.get('draft') or obj.get('prerelease'): return None
        version=obj['tag_name'].removeprefix('v')
        if version_tuple(version)<=version_tuple(current):return None
        filename=f'AstronyxMiniForgeStudio-Setup-v{version}.exe'
        assets={a['name']:a for a in obj.get('assets',[]) if isinstance(a,dict) and 'name' in a}
        setup,checksum=assets.get(filename),assets.get('SHA256SUMS.txt')
        if not setup or not checksum:raise UpdateError('A Release precisa do instalador e do SHA256SUMS.txt')
        url,sha_url=setup['browser_download_url'],checksum['browser_download_url']
        if not allowed(url,True) or not allowed(sha_url,True):raise UpdateError('URL fora do repositório')
        size=int(setup.get('size') or 0)
        if not 0<size<=MAX_SIZE:raise UpdateError('Tamanho informado inválido')
        digest=str(setup.get('digest') or '')
        if digest and not re.fullmatch(r'sha256:[0-9a-fA-F]{64}',digest):raise UpdateError('Digest inválido')
        page=obj.get('html_url') or PAGE
        if urlsplit(page).hostname!='github.com' or not page.startswith(f'https://github.com/{REPO}/releases/'):page=PAGE
        return Release(version,str(obj.get('body') or '')[:2000],page,filename,url,sha_url,size,digest[7:].lower() if digest else None)
    except UpdateError:raise
    except (OSError,ValueError,KeyError,TypeError) as exc:raise UpdateError('Não foi possível consultar Releases públicas do projeto.') from exc

def manifest_sha(data,name):
    for line in data.splitlines():
        m=re.fullmatch(r'([0-9a-fA-F]{64})\s+\*?(.+)',line.strip())
        if m and m.group(2).replace('\\','/').split('/')[-1]==name:return m.group(1).lower()
    raise UpdateError('Checksum do instalador ausente no manifesto')

def file_sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as file:
        for chunk in iter(lambda:file.read(1048576),b''):h.update(chunk)
    return h.hexdigest()

def download_installer(release,progress=None,destination=None):
    if (not re.fullmatch(r'\d+\.\d+\.\d+',release.version) or
        release.filename!=f'AstronyxMiniForgeStudio-Setup-v{release.version}.exe' or
        not allowed(release.installer_url,True) or not allowed(release.sha_url,True)):
        raise UpdateError('Endereço ou arquivo de atualização inválido')
    try:expected=manifest_sha(read_url(release.sha_url,65536).decode('utf-8-sig'),release.filename)
    except (OSError,UnicodeError) as exc:raise UpdateError('Falha ao obter SHA-256') from exc
    if release.digest and expected!=release.digest:raise UpdateError('Hash do GitHub não corresponde ao manifesto')
    base=Path(destination) if destination else Path(os.environ.get('LOCALAPPDATA',str(Path.home())))/'AstronyxMiniForge'/'updates'
    dest=base/release.version/release.filename
    dest.parent.mkdir(parents=True,exist_ok=True)
    if dest.is_file() and dest.stat().st_size==release.size and file_sha(dest)==expected:return dest
    temp=dest.with_suffix('.download')
    try:
        if temp.exists():temp.unlink()
        req=urllib.request.Request(release.installer_url,headers={'User-Agent':'AstronyxMiniForgeStudio'})
        hasher=hashlib.sha256()
        got=0
        with urllib.request.urlopen(req,timeout=45) as remote,temp.open('wb') as local:
            while True:
                chunk=remote.read(262144)
                if not chunk:break
                got+=len(chunk)
                if got>MAX_SIZE or got>release.size:raise UpdateError('Arquivo maior que o previsto')
                hasher.update(chunk)
                local.write(chunk)
                if progress:progress(got,release.size)
        if got!=release.size or hasher.hexdigest()!=expected:raise UpdateError('Download não passou na verificação SHA-256')
        temp.replace(dest)
        return dest
    except UpdateError:raise
    except OSError as exc:raise UpdateError('Falha de rede no download') from exc
    finally:
        if temp.exists():temp.unlink()

def is_portable() -> bool:
    """Recognize portable ZIP separately from a formal Inno Setup installation.

    Both distributions can have _internal. Installed builds have unins000.exe.
    """
    if sys.platform != 'win32' or not getattr(sys, 'frozen', False):
        return False
    return not (Path(sys.executable).resolve().parent / 'unins000.exe').is_file()


def run_installer(path):
    if is_portable():
        raise UpdateError('No modo portátil, baixe o ZIP da Release oficial e substitua a pasta, preservando seus projetos.')
    if sys.platform!='win32' or not getattr(sys,'frozen',False):
        raise UpdateError('Atualização interna exige o .exe Windows')
    p=Path(path)
    if not p.is_file() or not p.name.startswith('AstronyxMiniForgeStudio-Setup-v'):raise UpdateError('Instalador inválido')
    subprocess.Popen([str(p)],cwd=str(p.parent))
