"""Diagnostics helpers for the new harness architecture."""

from __future__ import annotations

import subprocess
import time
from pathlib import Path
from typing import Any, Dict

from unreal_editor_mcp.common import send_command
from unreal_editor_mcp.tools import get_current_level
from unreal_harness_runtime.python_exec import run_editor_python, wrap_editor_python

from unreal_orchestrator.catalog import list_domains


DEFAULT_EDITOR_EXE = Path(r"F:\GFFEngines\Main\Engine\Binaries\Win64\UnrealEditor.exe")
DEFAULT_PROJECT_PATH = Path(r"F:\GFFEngines\Main_Client\Client.uproject")


def get_harness_health() -> Dict[str, Any]:
    """Return a compact health snapshot for the new harness skeleton."""
    return {
        "success": True,
        "domains": list_domains(),
        "current_level": get_current_level(),
    }


def get_runtime_policy() -> Dict[str, Any]:
    """Describe the runtime policy boundary between normal usage and MCP development."""
    return {
        "success": True,
        "default_mode": "usage",
        "auto_launch_default": False,
        "auto_launch_scope": "mcp_development_only",
        "normal_failure_behavior": [
            "return_failure",
            "include_ready_state",
            "include_recommended_action",
            "do_not_launch_editor",
        ],
        "dev_only_tools": [
            "dev_launch_editor_and_wait_ready",
        ],
    }


def get_editor_ready_state() -> Dict[str, Any]:
    """Check whether the current Unreal Editor session is ready for heavier commands."""
    tcp_probe = send_command("get_current_level", {})
    transport_ok = tcp_probe.get("status") == "success" and (
        tcp_probe.get("result") or {}
    ).get("success")

    python_probe = run_editor_python(
        wrap_editor_python(
            """
_mcp_emit({
    "success": True,
    "python_ready": True,
    "editor_world": unreal.EditorLevelLibrary.get_editor_world().get_name() if unreal.EditorLevelLibrary.get_editor_world() else None,
})
"""
        )
    )
    python_ready = bool(
        python_probe.get("success") and python_probe.get("python_ready")
    )

    level_info = get_current_level() if transport_ok else tcp_probe

    ready = bool(transport_ok and python_ready)
    return {
        "success": True,
        "ready": ready,
        "mode": "usage",
        "auto_launch_allowed": False,
        "transport_ok": transport_ok,
        "python_ready": python_ready,
        "current_level": level_info,
        "transport_probe": tcp_probe,
        "python_probe": python_probe,
        "recommended_action": "safe_to_continue" if ready else "wait_and_retry",
    }


def wait_for_editor_ready(
    timeout_seconds: int = 120,
    poll_seconds: int = 5,
    usage_mode: str = "usage",
) -> Dict[str, Any]:
    """Poll the editor until both transport and Unreal Python are ready."""
    deadline = time.time() + timeout_seconds
    attempts = 0
    last_state: Dict[str, Any] = {
        "success": False,
        "ready": False,
        "recommended_action": "wait_and_retry",
    }

    while time.time() < deadline:
        attempts += 1
        last_state = get_editor_ready_state()
        last_state["attempts"] = attempts
        if last_state.get("ready"):
            return last_state
        time.sleep(max(1, poll_seconds))

    last_state["success"] = False
    last_state["mode"] = usage_mode
    last_state["error"] = (
        f"Timed out waiting for editor readiness after {attempts} attempts"
    )
    last_state["auto_launch_allowed"] = usage_mode == "dev"
    last_state["recommended_action"] = (
        "may_use_dev_launch_workflow" if usage_mode == "dev" else "open_editor_manually"
    )
    last_state["attempts"] = attempts
    return last_state


def dev_launch_editor_and_wait_ready(
    timeout_seconds: int = 420,
    poll_seconds: int = 5,
    editor_exe: str = str(DEFAULT_EDITOR_EXE),
    project_path: str = str(DEFAULT_PROJECT_PATH),
) -> Dict[str, Any]:
    """Development-only helper that launches the editor and waits for readiness.

    This is intentionally separate from normal usage flow. Regular user-facing
    failures should not auto-launch the editor.
    """
    pre_state = get_editor_ready_state()
    if pre_state.get("ready"):
        return {
            "success": True,
            "launched": False,
            "mode": "dev",
            "message": "Editor already ready",
            "state": pre_state,
        }

    command = [
        editor_exe,
        project_path,
        "-NoSplash",
        "-NoSound",
        "-NoRHIValidation",
        "-SkipCompile",
    ]
    subprocess.Popen(command, shell=False)

    final_state = wait_for_editor_ready(
        timeout_seconds=timeout_seconds,
        poll_seconds=poll_seconds,
        usage_mode="dev",
    )
    return {
        "success": bool(final_state.get("ready")),
        "launched": True,
        "mode": "dev",
        "command": command,
        "state": final_state,
    }
