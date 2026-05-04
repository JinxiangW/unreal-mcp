"""Shared editor-readiness guard for MCP domain tools.

Extracted from unreal_orchestrator/server.py so every domain server can wrap
its live-editor tools without duplicating the guard logic.
"""

from __future__ import annotations

import inspect
import time
from functools import wraps
from typing import Any, Dict

from unreal_diagnostics.tools import get_editor_ready_state, wait_for_editor_ready


def _new_operation_id(action: str) -> str:
    return f"guard:{action}:{int(time.time() * 1000)}"


def _compact_preflight(preflight: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "ready": bool(preflight.get("ready", False)),
        "transport_ok": bool(preflight.get("transport_ok", False)),
        "python_ready": bool(preflight.get("python_ready", False)),
        "current_level_summary": preflight.get("current_level_summary"),
        "recommended_action": preflight.get("recommended_action"),
    }


def _result_success(result: Any) -> bool:
    if not isinstance(result, dict):
        return True
    if "success" in result:
        return bool(result.get("success"))
    if result.get("status") == "error":
        return False
    if isinstance(result.get("result"), dict):
        return bool(result["result"].get("success", result.get("status") == "success"))
    return bool(result.get("status") == "success")


def _summarize_result(result: Any) -> Any:
    if not isinstance(result, dict):
        return result
    preferred_keys = (
        "operation_id",
        "domain",
        "targets",
        "summary",
        "items",
        "applied_changes",
        "failed_changes",
        "post_state",
        "verification",
    )
    if "status" in result and isinstance(result.get("result"), dict):
        inner = result["result"]
        summary: Dict[str, Any] = {
            "success": bool(inner.get("success", result.get("status") == "success"))
        }
        for key in preferred_keys:
            if key in inner:
                summary[key] = inner[key]
        for key in (
            "count",
            "returned_count",
            "total_count",
            "offset",
            "limit",
            "path",
            "asset_path",
            "level_path",
        ):
            if key in inner:
                summary[key] = inner[key]
        for list_key in ("assets", "actors", "lights"):
            if list_key in inner:
                summary[list_key] = inner[list_key]
        return summary
    summary: Dict[str, Any] = {"success": bool(result.get("success", False))}
    for key in (
        "domain",
        "asset_path",
        "asset_name",
        "asset_class",
        "parameter_name",
        "changed",
        "operation_id",
        "targets",
        "summary",
        "items",
        "applied_changes",
        "failed_changes",
        "post_state",
        "verification",
        "failed_properties",
        "modified_properties",
        "error",
        "message",
    ):
        if key in result:
            summary[key] = result[key]
    if len(summary) == 1:
        return result
    return summary


def _input_error_result(operation: str, error: str) -> Dict[str, Any]:
    domain = operation.split(".", 1)[0] if "." in operation else operation
    return {
        "success": False,
        "operation_id": _new_operation_id(operation.replace(".", "_")),
        "domain": domain,
        "targets": [],
        "applied_changes": [],
        "failed_changes": [{"field": "input", "error": error}],
        "post_state": {},
        "verification": {"verified": False, "checks": []},
        "error": error,
    }


def _guard_live_editor_call(
    operation: str,
    func,
    *args,
    wait_for_ready: bool = True,
    ready_timeout_seconds: int = 120,
    ready_poll_seconds: int = 5,
    _guard_debug: bool = False,
    **kwargs,
) -> Dict[str, Any]:
    preflight = (
        wait_for_editor_ready(
            timeout_seconds=ready_timeout_seconds,
            poll_seconds=ready_poll_seconds,
            debug=_guard_debug,
        )
        if wait_for_ready
        else get_editor_ready_state(debug=_guard_debug)
    )

    if not preflight.get("ready"):
        payload = {
            "success": False,
            "operation": operation,
            "ready": False,
            "recommended_action": preflight.get("recommended_action"),
            "error": "Editor is not ready for this live-editor operation",
        }
        if _guard_debug:
            payload["preflight"] = preflight
        else:
            payload["preflight_summary"] = _compact_preflight(preflight)
        return payload

    try:
        result = func(*args, **kwargs)
    except ValueError as exc:
        result = _input_error_result(operation, str(exc))
    payload = {
        "success": _result_success(result),
        "operation": operation,
        "ready": True,
        "recommended_action": preflight.get("recommended_action"),
    }
    if _guard_debug:
        payload["preflight"] = preflight
        payload["result"] = result
    else:
        payload["preflight_summary"] = _compact_preflight(preflight)
        payload["result_summary"] = _summarize_result(result)
    return payload


def make_guarded_tool(operation_name: str, raw_func):
    """Wrap *raw_func* so it runs editor-readiness preflight before execution.

    The returned function has the same parameters as *raw_func* plus three
    keyword-only guard parameters: ``wait_for_ready``, ``ready_timeout_seconds``,
    ``ready_poll_seconds``.  FastMCP sees the full signature via ``__signature__``.
    """
    sig = inspect.signature(raw_func)
    new_params = list(sig.parameters.values())
    new_params.extend([
        inspect.Parameter(
            "wait_for_ready", inspect.Parameter.KEYWORD_ONLY, default=True
        ),
        inspect.Parameter(
            "ready_timeout_seconds", inspect.Parameter.KEYWORD_ONLY, default=120
        ),
        inspect.Parameter(
            "ready_poll_seconds", inspect.Parameter.KEYWORD_ONLY, default=5
        ),
    ])
    new_sig = sig.replace(parameters=new_params)

    @wraps(raw_func)
    def guarded(*args, **kwargs):
        wait_for_ready = kwargs.pop("wait_for_ready", True)
        ready_timeout_seconds = kwargs.pop("ready_timeout_seconds", 120)
        ready_poll_seconds = kwargs.pop("ready_poll_seconds", 5)
        return _guard_live_editor_call(
            operation_name,
            raw_func,
            *args,
            wait_for_ready=wait_for_ready,
            ready_timeout_seconds=ready_timeout_seconds,
            ready_poll_seconds=ready_poll_seconds,
            **kwargs,
        )

    guarded.__signature__ = new_sig
    return guarded
