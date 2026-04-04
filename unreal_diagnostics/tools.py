"""Diagnostics helpers for the new harness architecture."""

from __future__ import annotations

import json
import socket
import subprocess
import time
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict

from unreal_editor_mcp.common import send_command
from unreal_editor_mcp.tools import get_current_level
from unreal_harness_runtime.config import (
    get_editor_cmd_path,
    get_editor_exe_path,
    get_project_path,
    get_unreal_host,
    get_unreal_port,
    get_runtime_paths,
)
from unreal_harness_runtime.python_exec import run_editor_python, wrap_editor_python

from unreal_orchestrator.catalog import list_domains


TOKEN_USAGE_LOG = Path(__file__).resolve().parents[1] / "logs" / "token_usage.jsonl"


def _new_diag_operation_id(action: str) -> str:
    return f"diagnostics:{action}:{int(time.time() * 1000)}"


def _diag_check(target: str, field: str, expected: Any, actual: Any) -> Dict[str, Any]:
    return {
        "target": target,
        "field": field,
        "expected": expected,
        "actual": actual,
        "ok": expected == actual,
    }


def _diag_wrap(
    action: str,
    *,
    targets: list[str],
    post_state: Dict[str, Any],
    checks: list[Dict[str, Any]],
    success: bool,
    failed_changes: list[Dict[str, Any]] | None = None,
    extras: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    payload = {
        "success": success,
        "operation_id": _new_diag_operation_id(action),
        "domain": "diagnostics",
        "targets": targets,
        "applied_changes": [],
        "failed_changes": failed_changes or [],
        "post_state": post_state,
        "verification": {
            "verified": all(check.get("ok", False) for check in checks)
            if checks
            else success,
            "checks": checks,
        },
    }
    if extras:
        payload.update(extras)
    return payload


def _ready_level_summary(level_info: Dict[str, Any]) -> Dict[str, Any] | None:
    if not isinstance(level_info, dict):
        return None
    if level_info.get("status") == "success":
        result = level_info.get("result") or {}
        return {
            "success": bool(result.get("success", False)),
            "level_name": result.get("level_name"),
            "level_path": result.get("level_path"),
        }
    return {
        "success": bool(level_info.get("success", False)),
        "level_name": level_info.get("level_name"),
        "level_path": level_info.get("level_path"),
    }


def _build_ready_state(
    *,
    success: bool = True,
    ready: bool,
    transport_ok: bool,
    python_ready: bool,
    recommended_action: str,
    current_level: Dict[str, Any],
    debug: bool,
    mode: str = "usage",
    auto_launch_allowed: bool = False,
    transport_probe: Dict[str, Any] | None = None,
    python_probe: Dict[str, Any] | None = None,
    attempts: int | None = None,
    error: str | None = None,
) -> Dict[str, Any]:
    state = {
        "success": success,
        "ready": ready,
        "mode": mode,
        "auto_launch_allowed": auto_launch_allowed,
        "transport_ok": transport_ok,
        "python_ready": python_ready,
        "current_level_summary": _ready_level_summary(current_level),
        "recommended_action": recommended_action,
    }
    if debug:
        state["current_level"] = current_level
        state["transport_probe"] = transport_probe
        state["python_probe"] = python_probe
        if attempts is not None:
            state["attempts"] = attempts
        if error is not None:
            state["error"] = error
    return state


def get_harness_health() -> Dict[str, Any]:
    """Return a compact health snapshot for the new harness skeleton."""
    current_level = get_current_level()
    success = current_level.get("status") == "success" or bool(
        current_level.get("success")
    )
    return _diag_wrap(
        "get_harness_health",
        targets=["harness"],
        post_state={
            "harness": {"domains": list_domains(), "current_level": current_level}
        },
        checks=[
            _diag_check("harness", "domains_present", True, len(list_domains()) > 0)
        ],
        success=success,
        extras={"domains": list_domains(), "current_level": current_level},
    )


def get_transport_port_status(timeout_seconds: float = 1.0) -> Dict[str, Any]:
    """Check whether the Unreal MCP TCP port is accepting connections."""
    host = get_unreal_host()
    port = get_unreal_port()
    started_at = time.perf_counter()
    try:
        with socket.create_connection((host, port), timeout=timeout_seconds):
            latency_ms = round((time.perf_counter() - started_at) * 1000, 2)
            return _diag_wrap(
                "get_transport_port_status",
                targets=[f"{host}:{port}"],
                post_state={
                    f"{host}:{port}": {"reachable": True, "latency_ms": latency_ms}
                },
                checks=[_diag_check(f"{host}:{port}", "reachable", True, True)],
                success=True,
                extras={
                    "host": host,
                    "port": port,
                    "reachable": True,
                    "latency_ms": latency_ms,
                },
            )
    except OSError as exc:
        latency_ms = round((time.perf_counter() - started_at) * 1000, 2)
        return _diag_wrap(
            "get_transport_port_status",
            targets=[f"{host}:{port}"],
            post_state={
                f"{host}:{port}": {"reachable": False, "latency_ms": latency_ms}
            },
            checks=[_diag_check(f"{host}:{port}", "reachable", True, False)],
            success=False,
            failed_changes=[
                {"target": f"{host}:{port}", "field": "reachable", "error": str(exc)}
            ],
            extras={
                "host": host,
                "port": port,
                "reachable": False,
                "latency_ms": latency_ms,
                "error": str(exc),
            },
        )


def get_unreal_python_status() -> Dict[str, Any]:
    """Check whether Unreal Python can execute in the current editor session."""
    result = run_editor_python(
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
    success = bool(result.get("success") and result.get("python_ready"))
    return _diag_wrap(
        "get_unreal_python_status",
        targets=[result.get("editor_world") or "editor_python"],
        post_state={"editor_python": result},
        checks=[
            _diag_check(
                "editor_python", "python_ready", True, result.get("python_ready", False)
            )
        ],
        success=success,
        failed_changes=[]
        if success
        else [
            {
                "target": "editor_python",
                "field": "python_ready",
                "error": result.get("error", "python not ready"),
            }
        ],
        extras=result,
    )


def get_editor_process_status() -> Dict[str, Any]:
    """Return a compact snapshot of running UnrealEditor processes."""
    command = (
        "Get-Process UnrealEditor -ErrorAction SilentlyContinue | "
        "Select-Object Id,ProcessName,MainWindowTitle,Responding | ConvertTo-Json -Compress"
    )
    completed = subprocess.run(
        ["powershell", "-NoProfile", "-Command", command],
        capture_output=True,
        text=True,
        timeout=30,
    )
    stdout = (completed.stdout or "").strip()
    if not stdout:
        return _diag_wrap(
            "get_editor_process_status",
            targets=[],
            post_state={"editor_processes": {"running": False, "processes": []}},
            checks=[_diag_check("editor_processes", "running", False, False)],
            success=True,
            extras={"running": False, "processes": []},
        )
    try:
        parsed = json.loads(stdout)
    except json.JSONDecodeError:
        return _diag_wrap(
            "get_editor_process_status",
            targets=[],
            post_state={"editor_processes": {"running": False}},
            checks=[_diag_check("editor_processes", "parse", True, False)],
            success=False,
            failed_changes=[
                {
                    "target": "editor_processes",
                    "field": "parse",
                    "error": "Failed to parse process list",
                }
            ],
            extras={
                "running": False,
                "error": "Failed to parse process list",
                "stdout": stdout,
            },
        )
    processes = parsed if isinstance(parsed, list) else [parsed]
    running = len(processes) > 0
    return _diag_wrap(
        "get_editor_process_status",
        targets=[
            item.get("MainWindowTitle") or item.get("ProcessName") or "UnrealEditor"
            for item in processes
        ],
        post_state={"editor_processes": {"running": running, "processes": processes}},
        checks=[_diag_check("editor_processes", "running", True, running)],
        success=running,
        failed_changes=[]
        if running
        else [
            {
                "target": "editor_processes",
                "field": "running",
                "error": "No UnrealEditor process found",
            }
        ],
        extras={"running": running, "processes": processes},
    )


def get_commandlet_runtime_status() -> Dict[str, Any]:
    """Check whether commandlet prerequisites are present on disk."""
    runtime_paths = get_runtime_paths()
    checks = {
        "editor_cmd_exists": get_editor_cmd_path().exists(),
        "project_exists": get_project_path().exists(),
        "commandlet_script_exists": Path(runtime_paths["commandlet_script"]).exists(),
    }
    verification_checks = [
        _diag_check("commandlet_runtime", field, True, value)
        for field, value in checks.items()
    ]
    success = all(checks.values())
    return _diag_wrap(
        "get_commandlet_runtime_status",
        targets=[runtime_paths["project_path"]],
        post_state={
            "commandlet_runtime": {"runtime_paths": runtime_paths, "checks": checks}
        },
        checks=verification_checks,
        success=success,
        failed_changes=[]
        if success
        else [
            {
                "target": "commandlet_runtime",
                "field": field,
                "error": "missing prerequisite",
            }
            for field, value in checks.items()
            if not value
        ],
        extras={"runtime_paths": runtime_paths, "checks": checks},
    )


def get_token_usage_summary(top_n: int = 10) -> Dict[str, Any]:
    """Summarize recorded token usage by component and operation."""
    if not TOKEN_USAGE_LOG.exists():
        return _diag_wrap(
            "get_token_usage_summary",
            targets=["token_usage_log"],
            post_state={"token_usage_log": {"log_exists": False, "entries": 0}},
            checks=[_diag_check("token_usage_log", "log_exists", False, False)],
            success=True,
            extras={"log_exists": False, "entries": 0, "top_operations": []},
        )

    groups: Dict[tuple[str, str], Dict[str, float]] = defaultdict(
        lambda: {
            "count": 0,
            "request_bytes": 0,
            "response_bytes": 0,
            "estimated_request_tokens": 0,
            "estimated_response_tokens": 0,
            "latency_ms_total": 0.0,
        }
    )
    entries = 0
    sessions = set()
    cold_start_entries = []
    hot_entries = []
    with TOKEN_USAGE_LOG.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            entries += 1
            session_id = record.get("session_id")
            if session_id:
                sessions.add(session_id)
            if record.get("session_entry_index") == 1:
                cold_start_entries.append(record)
            elif record.get("session_entry_index"):
                hot_entries.append(record)
            key = (
                record.get("component", "unknown"),
                record.get("operation", "unknown"),
            )
            bucket = groups[key]
            bucket["count"] += 1
            bucket["request_bytes"] += record.get("request_bytes", 0)
            bucket["response_bytes"] += record.get("response_bytes", 0)
            bucket["estimated_request_tokens"] += record.get(
                "estimated_request_tokens", 0
            )
            bucket["estimated_response_tokens"] += record.get(
                "estimated_response_tokens", 0
            )
            bucket["latency_ms_total"] += record.get("latency_ms", 0.0)

    ranked = sorted(
        groups.items(),
        key=lambda item: (
            item[1]["estimated_response_tokens"],
            item[1]["response_bytes"],
            item[1]["count"],
        ),
        reverse=True,
    )

    top_operations = []
    for (component, operation), stats in ranked[:top_n]:
        count = max(1, int(stats["count"]))
        top_operations.append(
            {
                "component": component,
                "operation": operation,
                "count": int(stats["count"]),
                "avg_request_bytes": round(stats["request_bytes"] / count, 2),
                "avg_response_bytes": round(stats["response_bytes"] / count, 2),
                "avg_request_tokens": round(
                    stats["estimated_request_tokens"] / count, 2
                ),
                "avg_response_tokens": round(
                    stats["estimated_response_tokens"] / count, 2
                ),
                "avg_latency_ms": round(stats["latency_ms_total"] / count, 2),
                "total_response_tokens": int(stats["estimated_response_tokens"]),
            }
        )

    payload = {
        "log_exists": True,
        "log_path": str(TOKEN_USAGE_LOG),
        "entries": entries,
        "session_count": len(sessions),
        "cold_start_summary": {
            "entries": len(cold_start_entries),
            "avg_response_tokens": round(
                sum(
                    item.get("estimated_response_tokens", 0)
                    for item in cold_start_entries
                )
                / max(1, len(cold_start_entries)),
                2,
            ),
            "avg_latency_ms": round(
                sum(item.get("latency_ms", 0.0) for item in cold_start_entries)
                / max(1, len(cold_start_entries)),
                2,
            ),
        },
        "hot_session_summary": {
            "entries": len(hot_entries),
            "avg_response_tokens": round(
                sum(item.get("estimated_response_tokens", 0) for item in hot_entries)
                / max(1, len(hot_entries)),
                2,
            ),
            "avg_latency_ms": round(
                sum(item.get("latency_ms", 0.0) for item in hot_entries)
                / max(1, len(hot_entries)),
                2,
            ),
        },
        "operation_count": len(groups),
        "top_operations": top_operations,
    }
    return _diag_wrap(
        "get_token_usage_summary",
        targets=[str(TOKEN_USAGE_LOG)],
        post_state={"token_usage_log": payload},
        checks=[_diag_check("token_usage_log", "log_exists", True, True)],
        success=True,
        extras=payload,
    )


def get_runtime_policy() -> Dict[str, Any]:
    """Describe the runtime policy boundary between normal usage and MCP development."""
    payload = {
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
        "runtime_paths": get_runtime_paths(),
    }
    return _diag_wrap(
        "get_runtime_policy",
        targets=["runtime_policy"],
        post_state={"runtime_policy": payload},
        checks=[
            _diag_check(
                "runtime_policy", "default_mode", "usage", payload["default_mode"]
            )
        ],
        success=True,
        extras=payload,
    )


def get_editor_ready_state(debug: bool = False) -> Dict[str, Any]:
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
    payload = _build_ready_state(
        success=True,
        ready=ready,
        transport_ok=transport_ok,
        python_ready=python_ready,
        current_level=level_info,
        transport_probe=tcp_probe,
        python_probe=python_probe,
        recommended_action="safe_to_continue" if ready else "wait_and_retry",
        debug=debug,
    )
    return _diag_wrap(
        "get_editor_ready_state",
        targets=[
            payload.get("current_level_summary", {}).get("level_path") or "editor"
        ],
        post_state={"editor_ready": payload},
        checks=[
            _diag_check(
                "editor_ready", "transport_ok", True, payload.get("transport_ok")
            ),
            _diag_check(
                "editor_ready", "python_ready", True, payload.get("python_ready")
            ),
        ],
        success=ready,
        failed_changes=[]
        if ready
        else [
            {
                "target": "editor_ready",
                "field": "ready",
                "error": payload.get("recommended_action"),
            }
        ],
        extras=payload,
    )


def wait_for_editor_ready(
    timeout_seconds: int = 120,
    poll_seconds: int = 5,
    usage_mode: str = "usage",
    debug: bool = False,
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
        last_state = get_editor_ready_state(debug=debug)
        if debug:
            last_state["attempts"] = attempts
        if last_state.get("ready"):
            return _diag_wrap(
                "wait_for_editor_ready",
                targets=[
                    last_state.get("current_level_summary", {}).get("level_path")
                    or "editor"
                ],
                post_state={"editor_ready": last_state},
                checks=[
                    _diag_check(
                        "editor_ready",
                        "transport_ok",
                        True,
                        last_state.get("transport_ok"),
                    ),
                    _diag_check(
                        "editor_ready",
                        "python_ready",
                        True,
                        last_state.get("python_ready"),
                    ),
                ],
                success=True,
                extras=last_state,
            )
        time.sleep(max(1, poll_seconds))

    payload = _build_ready_state(
        success=False,
        ready=False,
        transport_ok=bool(last_state.get("transport_ok", False)),
        python_ready=bool(last_state.get("python_ready", False)),
        current_level=(
            last_state.get("current_level", {})
            if debug
            else {"result": last_state.get("current_level_summary") or {}}
        ),
        transport_probe=last_state.get("transport_probe") if debug else None,
        python_probe=last_state.get("python_probe") if debug else None,
        recommended_action=(
            "may_use_dev_launch_workflow"
            if usage_mode == "dev"
            else "open_editor_manually"
        ),
        debug=debug,
        mode=usage_mode,
        auto_launch_allowed=usage_mode == "dev",
        attempts=attempts,
        error=f"Timed out waiting for editor readiness after {attempts} attempts",
    )
    return _diag_wrap(
        "wait_for_editor_ready",
        targets=[
            payload.get("current_level_summary", {}).get("level_path") or "editor"
        ],
        post_state={"editor_ready": payload},
        checks=[
            _diag_check(
                "editor_ready", "transport_ok", True, payload.get("transport_ok")
            ),
            _diag_check(
                "editor_ready", "python_ready", True, payload.get("python_ready")
            ),
        ],
        success=False,
        failed_changes=[
            {"target": "editor_ready", "field": "ready", "error": payload.get("error")}
        ],
        extras=payload,
    )


def dev_launch_editor_and_wait_ready(
    timeout_seconds: int = 420,
    poll_seconds: int = 5,
    editor_exe: str | None = None,
    project_path: str | None = None,
) -> Dict[str, Any]:
    """Development-only helper that launches the editor and waits for readiness.

    This is intentionally separate from normal usage flow. Regular user-facing
    failures should not auto-launch the editor.
    """
    pre_state = get_editor_ready_state()
    if pre_state.get("ready"):
        return _diag_wrap(
            "dev_launch_editor_and_wait_ready",
            targets=[str(get_project_path())],
            post_state={"editor_launch": pre_state},
            checks=[_diag_check("editor_launch", "ready", True, True)],
            success=True,
            extras={
                "launched": False,
                "mode": "dev",
                "message": "Editor already ready",
                "state": pre_state,
            },
        )

    resolved_editor_exe = editor_exe or str(get_editor_exe_path())
    resolved_project_path = project_path or str(get_project_path())
    command = [
        resolved_editor_exe,
        resolved_project_path,
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
        debug=True,
    )
    return _diag_wrap(
        "dev_launch_editor_and_wait_ready",
        targets=[resolved_project_path],
        post_state={"editor_launch": final_state},
        checks=[_diag_check("editor_launch", "ready", True, final_state.get("ready"))],
        success=bool(final_state.get("ready")),
        failed_changes=[]
        if final_state.get("ready")
        else [
            {
                "target": resolved_project_path,
                "field": "ready",
                "error": final_state.get(
                    "error", "editor launch did not reach ready state"
                ),
            }
        ],
        extras={
            "launched": True,
            "mode": "dev",
            "command": command,
            "state": final_state,
        },
    )
