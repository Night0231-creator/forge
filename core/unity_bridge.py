"""Safe local Unity / TaleWeaverLite bridge for Astronyx-prepared models.

Only writes within Assets/AstronyxImports and one owned Assets/Editor script.
Never changes Packages, ProjectSettings, a user's existing models, or .tsMod.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import unicodedata
from pathlib import Path

from .geometry import inspect_obj
from .taleweaverlite_handoff import _find_source, _foot_pivot, _copy_anchored_obj, _texture
from .unity_editor_template import UNITY_EDITOR_CS

EDITOR_FILE = "AstronyxMiniForgeBridgeV2213.cs"
VALID_EDITOR_VERSION = "2021.3.45f2"


def find_unity_editor() -> Path | None:
    """Bounded Windows Hub search. No full disk scan or registry writes."""
    override = os.getenv("ASTRONYX_UNITY_EDITOR", "").strip('" ')
    candidates = [Path(override)] if override else []
    for variable in ("PROGRAMFILES", "PROGRAMFILES(X86)"):
        root = os.getenv(variable)
        if root:
            candidates.append(Path(root) / "Unity" / "Hub" / "Editor" /
                              VALID_EDITOR_VERSION / "Editor" / "Unity.exe")
    for p in candidates:
        if p.is_file():
            return p.resolve()
    return None


def validate_unity_project(path: str | Path) -> Path:
    """Require a Unity project with a TaleWeaverLite hint, not an arbitrary folder."""
    root = Path(path).expanduser().resolve()
    assets = root / "Assets"
    version = root / "ProjectSettings" / "ProjectVersion.txt"
    if not assets.is_dir() or not version.is_file() or assets.is_symlink():
        raise ValueError("Escolha a raiz do projeto TaleWeaverLite no Unity Hub (Assets e ProjectSettings).")
    try:
        contents = version.read_text(encoding="utf-8-sig", errors="replace")
    except OSError as error:
        raise ValueError("Não foi possível validar a versão do projeto Unity.") from error
    if "m_EditorVersion:" not in contents:
        raise ValueError("ProjectVersion.txt não parece pertencer a um projeto Unity.")
    package = root / "Packages" / "manifest.json"
    package_text = ""
    if package.is_file():
        try:
            package_text = package.read_text(encoding="utf-8", errors="replace")
        except OSError:
            pass
    if "taleweaver" not in root.name.casefold() and "bouncyrock.taleweaver" not in package_text.casefold():
        raise ValueError(
            "Esta pasta não parece ser o TaleWeaverLite. Selecione o projeto extraído "
            "que você adicionou ao Unity Hub.")
    return root


def find_taleweaverlite_project() -> Path | None:
    """Search immediate children in common user folders; no unbounded recursion."""
    override = os.getenv("ASTRONYX_TALEWEAVER_PROJECT", "").strip('" ')
    if override:
        try:
            return validate_unity_project(override)
        except (ValueError, OSError):
            pass
    home = Path.home()
    candidates = [home / "Documents", home / "Downloads", home / "Desktop"]
    for base in candidates:
        for path in [base / "TaleWeaverLite", base / "TaleWeaverLite-0-0-70"]:
            try:
                return validate_unity_project(path)
            except (ValueError, OSError):
                pass
        if not base.is_dir():
            continue
        for path in sorted(base.iterdir()):
            if "taleweaver" not in path.name.casefold() or not path.is_dir():
                continue
            try:
                return validate_unity_project(path)
            except (ValueError, OSError):
                pass
    return None


def _safe_asset_name(value: str) -> str:
    clean = unicodedata.normalize("NFKD", value).encode("ascii", errors="ignore").decode()
    clean = re.sub(r"[^A-Za-z0-9_-]+", "_", clean).strip("_-.")[:45]
    return clean or "Personagem"


def _unique_folder(parent: Path, name: str) -> Path:
    for index in range(1, 1001):
        candidate = parent / f"{name}_{index:03d}"
        if not candidate.exists() and not candidate.is_symlink():
            return candidate
    raise ValueError("Limite de importações atingido na pasta Unity.")


def _write_owned_editor_script(assets: Path) -> Path:
    """Never overwrite a user-modified script with the same filename."""
    folder = assets / "Editor"
    if folder.is_symlink():
        raise ValueError("Pasta Unity Assets/Editor usa um link simbólico.")
    folder.mkdir(parents=True, exist_ok=True)
    dest = folder / EDITOR_FILE
    if dest.exists():
        if dest.is_symlink() or dest.read_text(encoding="utf-8") != UNITY_EDITOR_CS:
            raise ValueError(
                "O script Astronyx do Unity foi alterado. Mantenha uma cópia "
                "ou renomeie-o antes de ativar a integração.")
        return dest
    dest.write_text(UNITY_EDITOR_CS, encoding="utf-8")
    return dest


def import_into_unity_project(
    source_project: str | Path, unity_project: str | Path
) -> dict:
    """Stage real geometry/materials; Unity auto-imports and creates a preview.

    One folder is created for each run, so prior user adjustments are preserved.
    Local previews remain 1x: no game default scale or 8x transforms are injected.
    """
    unity = validate_unity_project(unity_project)
    source_root = Path(source_project).expanduser().resolve()
    source_obj = _find_source(source_root)
    stats = inspect_obj(source_obj)
    if stats.height <= 0.001:
        raise ValueError("O OBJ convertido tem altura inválida.")
    textures = {name: _texture(source_root, name)
                for name in ("Albedo.png", "Normal.png", "MAES.png")}
    assets = unity / "Assets"
    import_root = assets / "AstronyxImports"
    if import_root.is_symlink():
        raise ValueError("Pasta AstronyxImports é um link simbólico.")
    import_root.mkdir(exist_ok=True)
    destination = _unique_folder(import_root, _safe_asset_name(source_root.name))
    destination.mkdir()
    try:
        foot_x, foot_z = _foot_pivot(source_obj, stats.min_xyz[1], stats.height)
        _copy_anchored_obj(source_obj, destination / "Model_PivoPes.obj",
                           foot_x, foot_z, stats.min_xyz[1])
        (destination / "Astronyx_Unity.mtl").write_text(
            "newmtl AstronyxMini\nKd 1 1 1\nKs 0 0 0\n"
            "d 1\nillum 2\nmap_Kd Albedo.png\n",
            encoding="utf-8")
        for name, path in textures.items():
            shutil.copyfile(path, destination / name)
        report = {
            "schema": "astronyx-unity-bridge-1",
            "source_name": source_root.name,
            "source_height": round(stats.height, 5),
            "source_width": round(stats.width, 5),
            "source_depth": round(stats.depth, 5),
            "estimated_foot_anchor_xz": [round(foot_x,5), round(foot_z,5)],
            "visual_preview_scale": 1.0,
            "talespire_default_scale_requested": 1,
            "unity_project": unity.name,
            "status": "Unity assets staged; TaleWeaverLite export still manual",
            "movement_validated_in_game": False
        }
        (destination / "AstronyxImport.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        (destination / "LEIA_PRIMEIRO.txt").write_text(
            "Arquivos importados pelo Astronyx Mini Forge.\n\n"
            "Abra o projeto TaleWeaverLite no Unity 2021.3.45f2.\n"
            "O menu Tools > Astronyx > Preparar modelos importados cria "
            "um prefab de prévia, se ainda não aparecer automaticamente.\n"
            "No Creature Mod oficial selecione o Mesh do Model_PivoPes.obj "
            "e as texturas Albedo/Normal/MAES.\n"
            "Comece com Transform 1; ajuste olhando criaturas padrão, "
            "e configure Default Scale 1 para colocação inicial 1x1.\n"
            "Antes de salvar ajuste alvos Head/Spell/Hit/Torch e "
            "teste ancoragem e movimento no TaleSpire.\n"
            "O prefab é somente prévia, não é um arquivo .tsMod.\n",
            encoding="utf-8")
        script = _write_owned_editor_script(assets)
    except Exception:
        shutil.rmtree(destination, ignore_errors=True)
        raise
    return {
        "import_path": str(destination),
        "unity_project": str(unity),
        "editor_script": str(script),
        "source_height": report["source_height"],
        "preview_scale": 1.0,
        "default_scale": 1,
        "tsmod_created": False,
        "note": report["status"],
    }


def open_unity_project(project: str | Path, executable: str | Path | None = None):
    root = validate_unity_project(project)
    editor = Path(executable) if executable else find_unity_editor()
    if editor is None or not editor.is_file():
        raise FileNotFoundError(
            "Unity 2021.3.45f2 não detectado. Abra o projeto pelo Unity Hub.")
    return subprocess.Popen(
        [str(editor.resolve()), "-projectPath", str(root)],
        stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL)
