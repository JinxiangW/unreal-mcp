"""Helpers for running Unreal commandlets as isolated subprocesses."""

from __future__ import annotations

import json
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List

from unreal_observability.token_usage import record_tool_usage
from .config import (
    get_commandlet_script_path,
    get_editor_cmd_path,
    get_project_path,
)
from .python_exec import PYTHON_RESULT_MARKER


def _normalize_arg(value: str) -> str:
    return value.replace("\\", "/")


def _extract_marker_payload(output: str) -> Dict[str, Any]:
    for line in output.splitlines():
        marker_index = line.find(PYTHON_RESULT_MARKER)
        if marker_index != -1:
            payload = line[marker_index + len(PYTHON_RESULT_MARKER) :]
            return json.loads(payload)
    return {
        "success": False,
        "error": "No JSON marker found in commandlet output",
        "python_commandlet_lines": [
            line
            for line in output.splitlines()
            if "PythonScriptCommandlet" in line or "Running Python script" in line
        ][-20:],
        "output_head": "\n".join(output.splitlines()[:40]),
        "output_tail": "\n".join(output.splitlines()[-40:]),
    }


def run_python_commandlet(
    args: List[str], timeout_seconds: int = 1800
) -> Dict[str, Any]:
    started_at = time.perf_counter()
    editor_cmd = get_editor_cmd_path()
    project_path = get_project_path()
    commandlet_script = get_commandlet_script_path()

    with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as handle:
        result_file = Path(handle.name)

    normalized_args = [_normalize_arg(arg) for arg in args]
    normalized_args.extend(["--result-file", _normalize_arg(str(result_file))])
    script_command = subprocess.list2cmdline(
        [commandlet_script.as_posix()] + normalized_args
    )
    command = [
        str(editor_cmd),
        str(project_path),
        "-run=PythonScript",
        f"-Script={script_command}",
        "-unattended",
        "-nop4",
        "-nosplash",
        "-nosound",
    ]
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            shell=False,
        )
        output = (completed.stdout or "") + "\n" + (completed.stderr or "")

        if result_file.exists() and result_file.stat().st_size > 0:
            result = json.loads(result_file.read_text(encoding="utf-8"))
        else:
            result = _extract_marker_payload(output)

        result["exit_code"] = completed.returncode
        if completed.returncode != 0 and result.get("success"):
            result["success"] = False
            result["error"] = f"Commandlet exited with code {completed.returncode}"
        record_tool_usage(
            "unreal_harness_runtime.commandlet_exec",
            "run_python_commandlet",
            request_payload={"args": args, "timeout_seconds": timeout_seconds},
            response_payload=result,
            metadata={
                "exit_code": completed.returncode,
                "stdout_bytes": len((completed.stdout or "").encode("utf-8")),
                "stderr_bytes": len((completed.stderr or "").encode("utf-8")),
            },
            started_at=started_at,
        )
        return result
    finally:
        if result_file.exists():
            result_file.unlink(missing_ok=True)
