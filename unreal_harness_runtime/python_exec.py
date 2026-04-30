"""Helpers for executing Unreal Python through the editor MCP."""

from __future__ import annotations

import json
import time
from typing import Any, Dict

from unreal_observability.token_usage import record_tool_usage
from unreal_backend_tcp.common import send_command, with_unreal_connection


PYTHON_RESULT_MARKER = "__UNREAL_MCP_JSON__:"


def json_literal(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)


def python_literal(value: Any) -> str:
    return repr(value)


def wrap_editor_python(body: str) -> str:
    marker = json_literal(PYTHON_RESULT_MARKER)
    indented_body = (
        "\n".join(f"    {line}" if line else "" for line in body.splitlines())
        if body.strip()
        else "    pass"
    )
    return f"""
import gc
import json
import sys
import traceback
import unreal

def _mcp_emit(payload):
    print({marker} + json.dumps(payload, ensure_ascii=False))

def _mcp_collect_unreal_garbage():
    try:
        gc.collect()
    except Exception:
        pass
    try:
        unreal.SystemLibrary.collect_garbage()
    except Exception:
        pass

def _mcp_run():
{indented_body}

try:
    _mcp_run()
except Exception:
    _mcp_exc_type, _mcp_exc_value, _mcp_exc_tb = sys.exc_info()
    try:
        _mcp_emit({{
            "success": False,
            "error": str(_mcp_exc_value),
            "traceback": "".join(traceback.format_exception(_mcp_exc_type, _mcp_exc_value, _mcp_exc_tb)),
        }})
    finally:
        try:
            traceback.clear_frames(_mcp_exc_tb)
        except Exception:
            pass
        del _mcp_exc_type
        del _mcp_exc_value
        del _mcp_exc_tb
finally:
    try:
        del _mcp_run
    except Exception:
        pass
    _mcp_collect_unreal_garbage()
""".strip()


@with_unreal_connection
def run_editor_python(code: str, execution_mode: str = "ExecuteFile") -> Dict[str, Any]:
    started_at = time.perf_counter()
    response = send_command(
        "run_python",
        {
            "code": code,
            "execution_mode": execution_mode,
        },
    )

    if response.get("status") == "error":
        payload = {
            "success": False,
            "error": response.get("error", "Unknown run_python error"),
        }
        record_tool_usage(
            "unreal_harness_runtime.python_exec",
            "run_editor_python",
            request_payload={"execution_mode": execution_mode, "code": code},
            response_payload=payload,
            metadata={"status": "transport_error"},
            started_at=started_at,
        )
        return payload

    result = response.get("result") or {}
    parsed = result.get("parsed_result")
    if isinstance(parsed, dict):
        record_tool_usage(
            "unreal_harness_runtime.python_exec",
            "run_editor_python",
            request_payload={"execution_mode": execution_mode, "code": code},
            response_payload=parsed,
            metadata={"status": "parsed_result"},
            started_at=started_at,
        )
        return parsed

    if result.get("success"):
        payload = {"success": True, "run_python": result}
        record_tool_usage(
            "unreal_harness_runtime.python_exec",
            "run_editor_python",
            request_payload={"execution_mode": execution_mode, "code": code},
            response_payload=payload,
            metadata={"status": "raw_success"},
            started_at=started_at,
        )
        return payload

    payload = {
        "success": False,
        "error": result.get("command_result", "Python execution failed"),
        "run_python": result,
    }
    record_tool_usage(
        "unreal_harness_runtime.python_exec",
        "run_editor_python",
        request_payload={"execution_mode": execution_mode, "code": code},
        response_payload=payload,
        metadata={"status": "raw_failure"},
        started_at=started_at,
    )
    return payload
