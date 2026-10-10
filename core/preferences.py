"""Persist UI preferences and show exported files in the system file manager."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


def load_preferences(path: Path) -> dict:
    """Read existing v1.0/v1.1 settings; invalid or missing files use defaults."""
    try:
        settings = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError, TypeError):
        settings = {}
    if not isinstance(settings, dict):
        settings = {}
    return {
        'output_root': settings.get('output_root', ''),
        'blender': settings.get('blender', ''),
        # New setting enabled by default; remember explicit false on next run.
        'open_after_conversion': settings.get('open_after_conversion', True) is True,
        'auto_update_check': settings.get('auto_update_check', True) is True,
        'cmd_enabled': settings.get('cmd_enabled', False) is True,
        'cmd_executable': settings.get('cmd_executable', ''),
        'cmd_arguments': settings.get('cmd_arguments', ''),
        'cmd_json_template': settings.get('cmd_json_template', ''),
        # Migrate the unsafe 14-unit / 8x legacy baseline once.
        'scale_factor': ('1' if settings.get('settings_schema', 1) < 2
                         and str(settings.get('scale_factor', '8')) == '8'
                         else str(settings.get('scale_factor', '1'))),
        'auto_scale': settings.get('auto_scale', True) is True,
        'target_height': ('1.75' if settings.get('settings_schema', 1) < 2
                          and str(settings.get('target_height', '14')).strip() in ('14', '14.0')
                          else str(settings.get('target_height', '1.75'))),
        'install_after_conversion': settings.get('install_after_conversion', False) is True,
        'tsmod_folder': settings.get('tsmod_folder', ''),
        'reference_tsmod': settings.get('reference_tsmod', ''),
        'auto_import_preset': settings.get('auto_import_preset', True) is True,
    }


def save_preferences(path: Path, *, output_root: str, blender: str,
                     open_after_conversion: bool, cmd_enabled: bool = False,
                     cmd_executable: str = "", cmd_arguments: str = "",
                     cmd_json_template: str = "", scale_factor: str = "1",
                     auto_scale: bool = True, target_height: str = "1.75",
                     install_after_conversion: bool = False, tsmod_folder: str = "",
                     auto_update_check: bool = True,
                     reference_tsmod: str = '', auto_import_preset: bool = True) -> None:
    """Save app preferences atomically without touching projects or models."""
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        'settings_schema': 2,
        'output_root': output_root,
        'blender': blender,
        'open_after_conversion': bool(open_after_conversion),
        'auto_update_check': bool(auto_update_check),
        'cmd_enabled': bool(cmd_enabled),
        'cmd_executable': cmd_executable,
        'cmd_arguments': cmd_arguments,
        'cmd_json_template': cmd_json_template,
        'scale_factor': str(scale_factor),
        'auto_scale': bool(auto_scale), 'target_height': str(target_height),
        'install_after_conversion': bool(install_after_conversion),
        'tsmod_folder': tsmod_folder,
        'reference_tsmod': str(reference_tsmod),
        'auto_import_preset': bool(auto_import_preset),
    }
    temporary = path.with_name(path.name + '.tmp')
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    temporary.replace(path)


def open_output_folder(folder: Path) -> None:
    """Open an already-created folder, without interpreting its name as a command."""
    folder = Path(folder).expanduser()
    if not folder.is_dir():
        raise FileNotFoundError(f'A pasta ainda não existe: {folder}')
    if os.name == 'nt':
        os.startfile(str(folder))
    elif sys.platform == 'darwin':
        subprocess.Popen(['open', str(folder)])
    else:
        subprocess.Popen(['xdg-open', str(folder)])
