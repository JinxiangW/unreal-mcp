"""Helpers for executing Unreal Python through the editor MCP."""

from __future__ import annotations

import json
from typing import Any, Dict

from unreal_editor_mcp.common import send_command, with_unreal_connection


PYTHON_RESULT_MARKER = "__UNREAL_MCP_JSON__:"


def json_literal(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)


def python_literal(value: Any) -> str:
    return repr(value)


def wrap_editor_python(body: str) -> str:
    marker = json_literal(PYTHON_RESULT_MARKER)
    indented_body = "\n".join(
        f"    {line}" if line else "" for line in body.splitlines()
    )
    return f"""
import json
import traceback
import unreal

def _mcp_emit(payload):
    print({marker} + json.dumps(payload, ensure_ascii=False))

try:
{indented_body}
except Exception as exc:
    _mcp_emit({{"success": False, "error": str(exc), "traceback": traceback.format_exc()}})
""".strip()


@with_unreal_connection
def run_editor_python(code: str, execution_mode: str = "ExecuteFile") -> Dict[str, Any]:
    response = send_command(
        "run_python",
        {
            "code": code,
            "execution_mode": execution_mode,
        },
    )

    if response.get("status") == "error":
        return {
            "success": False,
            "error": response.get("error", "Unknown run_python error"),
        }

    result = response.get("result") or {}
    parsed = result.get("parsed_result")
    if isinstance(parsed, dict):
        return parsed

    if result.get("success"):
        return {"success": True, "run_python": result}

    return {
        "success": False,
        "error": result.get("command_result", "Python execution failed"),
        "run_python": result,
    }
