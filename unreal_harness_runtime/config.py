"""Shared runtime configuration for Unreal harness components."""

from __future__ import annotations

import os
from pathlib import Path


_REPO_ROOT = Path(__file__).resolve().parents[1]

_DEFAULT_EDITOR_EXE_CANDIDATES = [
    Path(r"D:\UnrealEngines\UnrealEngine5_6\Engine\Binaries\Win64\UnrealEditor.exe"),
    Path(r"D:\UE5\UE5New\UnrealEngine\Engine\Binaries\Win64\UnrealEditor.exe"),
    Path(r"F:\GFFEngines\Main\Engine\Binaries\Win64\UnrealEditor.exe"),
]

_DEFAULT_PROJECT_PATH_CANDIDATES = [
    _REPO_ROOT / "RenderingMCP" / "RenderingMCP.uproject",
]


def _first_existing_path(candidates: list[Path]) -> Path:
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


def _env_path(name: str) -> Path | None:
    value = os.environ.get(name, "").strip()
    return Path(value) if value else None


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


def get_project_path() -> Path:
    configured = _env_path("UE_PROJECT_PATH")
    if configured is not None:
        return configured
    return _first_existing_path(_DEFAULT_PROJECT_PATH_CANDIDATES)


def get_commandlet_script_path() -> Path:
    return _REPO_ROOT / "commandlets" / "asset_import_commandlet.py"


def get_runtime_paths() -> dict[str, str]:
    return {
        "host": get_unreal_host(),
        "port": str(get_unreal_port()),
        "editor_exe": str(get_editor_exe_path()),
        "editor_cmd": str(get_editor_cmd_path()),
        "project_path": str(get_project_path()),
        "commandlet_script": str(get_commandlet_script_path()),
    }
