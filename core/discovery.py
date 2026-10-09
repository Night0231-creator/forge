"""Resolve installations of Blender and TaleWeaverCmd, including nondefault Steam libraries.

No executables or game resources are redistributed by Mini Forge.
"""
from __future__ import annotations

import os
import re
import shutil
from pathlib import Path


def _registry_steam_paths() -> list[Path]:
    if os.name != 'nt':
        return []
    try:
        import winreg
    except ImportError:
        return []
    paths = []
    for hive, key in ((winreg.HKEY_CURRENT_USER, r'Software\Valve\Steam'),
                      (winreg.HKEY_LOCAL_MACHINE, r'SOFTWARE\WOW6432Node\Valve\Steam'),
                      (winreg.HKEY_LOCAL_MACHINE, r'SOFTWARE\Valve\Steam')):
        try:
            with winreg.OpenKey(hive, key) as handle:
                for field in ('SteamPath', 'InstallPath'):
                    try:
                        value = winreg.QueryValueEx(handle, field)[0]
                        if value:
                            paths.append(Path(value))
                    except OSError:
                        pass
        except OSError:
            pass
    return paths


def steam_roots(extra_roots=()) -> list[Path]:
    """Locations containing steamapps (not assumed limited to C:)."""
    options = [Path(x) for x in extra_roots]
    options.extend(_registry_steam_paths())
    for env in ('STEAM_PATH', 'PROGRAMFILES(X86)', 'PROGRAMFILES'):
        value = os.environ.get(env)
        if value:
            base = Path(value)
            options.extend((base, base / 'Steam'))
    if os.name == 'nt':
        for drive in 'CDEFGHIJKLMNOP':
            options.extend((Path(f'{drive}:/Steam'), Path(f'{drive}:/SteamLibrary')))
    seen, valid = set(), []
    for opt in options:
        key = str(opt).casefold()
        if key not in seen:
            seen.add(key)
            valid.append(opt)
    return valid


def parse_steam_libraryfolders(contents: str) -> list[Path]:
    """Read only the 'path' strings of Steam libraryfolders.vdf, no VDF dependency."""
    result = []
    for raw in re.findall(r'^\s*"path"\s+"((?:\\.|[^"\\])*)"',
                          contents, re.MULTILINE | re.IGNORECASE):
        # Steam VDF escapes backslashes in paths. This also allows unescaped
        # forward-slash paths; only the path field is trusted.
        value = raw.replace('\\\\', '\\').replace('\\"', '"')
        if value:
            result.append(Path(value))
    return result


def steam_libraries(extra_roots=()) -> list[Path]:
    roots = steam_roots(extra_roots)
    seen, all_paths = set(), []
    for root in roots:
        configs = (root / 'steamapps' / 'libraryfolders.vdf', root / 'config' / 'libraryfolders.vdf')
        paths = [root]
        for config in configs:
            try:
                # Limit config read to avoid processing enormous unexpected files.
                if config.stat().st_size > 1024 * 1024:
                    continue
                paths.extend(parse_steam_libraryfolders(config.read_text(encoding='utf-8-sig', errors='replace')))
            except OSError:
                continue
        for path in paths:
            key = str(path).casefold()
            if key not in seen:
                seen.add(key)
                all_paths.append(path)
    return all_paths


def find_taleweavercmd(extra_roots=()) -> str | None:
    override = os.environ.get('ASTRONYX_TALEWEAVERCMD', '')
    if override and Path(override).is_file():
        return override
    for steam_root in steam_libraries(extra_roots):
        tool = steam_root / 'steamapps' / 'common' / 'TaleSpire' / 'Tools' / 'TaleWeaverCmd'
        for candidate in (tool / 'Windows' / 'TaleWeaverCmd.exe', tool / 'TaleWeaverCmd.exe'):
            if candidate.is_file():
                return str(candidate)
    return None


def find_blender() -> str | None:
    override = os.environ.get('ASTRONYX_BLENDER', '')
    if override and Path(override).is_file():
        return override
    installed = shutil.which('blender')
    if installed:
        return installed
    if os.name != 'nt':
        for candidate in ('/usr/bin/blender', '/usr/local/bin/blender', '/opt/blender/blender'):
            if Path(candidate).is_file():
                return candidate
        return None
    options = []
    for root in filter(None, (os.environ.get('PROGRAMFILES'),
                              os.environ.get('PROGRAMFILES(X86)'),
                              os.environ.get('LOCALAPPDATA'))):
        base = Path(root)
        for stem in (base / 'Blender Foundation', base / 'Programs' / 'Blender Foundation'):
            options.extend(stem.glob('Blender */blender.exe'))
            options.append(stem / 'Blender' / 'blender.exe')
    options = [p for p in options if p.is_file()]
    # Native 5.2 and 4.4 releases sorted by numeric version, not just alphabetic.
    def version_key(p):
        digits = re.findall(r'\d+', p.parent.name)
        return tuple(int(n) for n in digits) or (0,)
    return str(max(options, key=version_key)) if options else None


def tool_status(blender: str, taleweaver: str) -> tuple[bool, bool]:
    return Path(blender.strip().strip('"')).is_file(), Path(taleweaver.strip().strip('"')).is_file()
