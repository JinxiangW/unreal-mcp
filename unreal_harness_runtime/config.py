"""Shared runtime configuration for Unreal harness components."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Iterable

try:
    import winreg
except ImportError:  # pragma: no cover - non-Windows fallback
    winreg = None  # type: ignore[assignment]


_REPO_ROOT = Path(__file__).resolve().parents[1]

_DEFAULT_EDITOR_EXE_CANDIDATES = [
    Path(r"D:\UnrealEngines\UnrealEngine5_6\Engine\Binaries\Win64\UnrealEditor.exe"),
    Path(r"D:\UE5\UE5New\UnrealEngine\Engine\Binaries\Win64\UnrealEditor.exe"),
    Path(r"F:\GFFEngines\Main\Engine\Binaries\Win64\UnrealEditor.exe"),
]

_DEFAULT_ENGINE_ROOT_CANDIDATES = [
    Path(r"D:\UnrealEngines\UnrealEngine5_6\Engine"),
    Path(r"D:\UE5\UE5New\UnrealEngine\Engine"),
    Path(r"F:\GFFEngines\Main\Engine"),
]

def _first_existing_path(candidates: list[Path]) -> Path:
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


def _env_path(name: str) -> Path | None:
    value = os.environ.get(name, "").strip()
    return Path(value) if value else None


def _normalize_engine_root(path: Path) -> Path:
    if path.name.lower() == "engine":
        return path
    if (path / "Engine").exists() or path.suffix.lower() != ".exe":
        return path / "Engine"
    for parent in path.parents:
        if parent.name.lower() == "engine":
            return parent
    return path


def _engine_root_has_source(path: Path) -> bool:
    return (path / "Source").is_dir() and (path / "Binaries").is_dir()


def _first_engine_root(candidates: Iterable[Path]) -> Path | None:
    normalized = [_normalize_engine_root(candidate) for candidate in candidates]
    for candidate in normalized:
        if _engine_root_has_source(candidate):
            return candidate
    for candidate in normalized:
        if candidate.exists():
            return candidate
    return normalized[0] if normalized else None


def _read_project_engine_association(project_path: Path | None) -> str | None:
    if project_path is None or not project_path.exists():
        return None
    try:
        data = json.loads(project_path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return None
    association = data.get("EngineAssociation")
    return association.strip() if isinstance(association, str) and association.strip() else None


def _lookup_registered_engine_root(association: str) -> Path | None:
    if winreg is None:
        return None
    registry_roots = [
        (winreg.HKEY_CURRENT_USER, rf"Software\Epic Games\Unreal Engine\Builds", association),
        (winreg.HKEY_LOCAL_MACHINE, rf"SOFTWARE\EpicGames\Unreal Engine\{association}", "InstalledDirectory"),
        (winreg.HKEY_LOCAL_MACHINE, rf"SOFTWARE\WOW6432Node\EpicGames\Unreal Engine\{association}", "InstalledDirectory"),
    ]
    for hive, key_path, value_name in registry_roots:
        try:
            with winreg.OpenKey(hive, key_path) as key:
                value, _ = winreg.QueryValueEx(key, value_name)
        except OSError:
            continue
        if isinstance(value, str) and value.strip():
            return _normalize_engine_root(Path(value.strip()))
    return None


def _engine_association_candidate(project_path: Path | None) -> Path | None:
    association = _read_project_engine_association(project_path)
    if not association:
        return None

    association_path = Path(association)
    if association_path.is_absolute():
        return _normalize_engine_root(association_path)

    registered = _lookup_registered_engine_root(association)
    if registered is not None:
        return registered
    return None


def get_unreal_host() -> str:
    return os.environ.get("UE_HOST", "127.0.0.1")


def get_unreal_port() -> int:
    return int(os.environ.get("UE_PORT", "55557"))


def get_editor_exe_path() -> Path:
    configured = _env_path("UE_EDITOR_EXE")
    if configured is not None:
        return configured
    return _first_existing_path(_DEFAULT_EDITOR_EXE_CANDIDATES)


def get_editor_cmd_path() -> Path:
    configured = _env_path("UE_EDITOR_CMD")
    if configured is not None:
        return configured

    editor_exe = get_editor_exe_path()
    if editor_exe.name.lower() == "unrealeditor.exe":
        return editor_exe.with_name("UnrealEditor-Cmd.exe")
    return editor_exe.parent / "UnrealEditor-Cmd.exe"


def get_engine_root_path_optional() -> Path | None:
    candidates: list[Path] = []

    configured_engine_root = _env_path("UE_ENGINE_ROOT")
    if configured_engine_root is not None:
        candidates.append(configured_engine_root)

    for editor_env in ("UE_EDITOR_EXE", "UE_EDITOR_CMD"):
        editor_path = _env_path(editor_env)
        if editor_path is not None:
            candidates.append(editor_path)

    association_candidate = _engine_association_candidate(get_project_path_optional())
    if association_candidate is not None:
        candidates.append(association_candidate)

    candidates.extend(_DEFAULT_EDITOR_EXE_CANDIDATES)
    candidates.extend(_DEFAULT_ENGINE_ROOT_CANDIDATES)
    return _first_engine_root(candidates)


def get_engine_root_path() -> Path:
    resolved = get_engine_root_path_optional()
    if resolved is None:
        raise RuntimeError(
            "Unreal Engine root is not configured. Set UE_ENGINE_ROOT or UE_EDITOR_EXE."
        )
    return resolved


def get_project_path_optional() -> Path | None:
    configured = _env_path("UE_PROJECT_PATH")
    return configured


def get_project_path() -> Path:
    configured = get_project_path_optional()
    if configured is not None:
        return configured
    raise RuntimeError(
        "UE_PROJECT_PATH is not configured. Set UE_PROJECT_PATH to the target .uproject path."
    )


def get_commandlet_script_path() -> Path:
    return _REPO_ROOT / "commandlets" / "asset_import_commandlet.py"


def get_runtime_paths() -> dict[str, str]:
    project_path = get_project_path_optional()
    engine_root = get_engine_root_path_optional()
    return {
        "host": get_unreal_host(),
        "port": str(get_unreal_port()),
        "editor_exe": str(get_editor_exe_path()),
        "editor_cmd": str(get_editor_cmd_path()),
        "engine_root": str(engine_root) if engine_root is not None else "",
        "engine_source": str(engine_root / "Source") if engine_root is not None else "",
        "engine_root_source_available": "true"
        if engine_root is not None and _engine_root_has_source(engine_root)
        else "false",
        "project_path": str(project_path) if project_path is not None else "",
        "project_path_configured": "true" if project_path is not None else "false",
        "commandlet_script": str(get_commandlet_script_path()),
    }
