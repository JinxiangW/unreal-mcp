"""Lightweight usage telemetry for Unreal MCP tool calls."""

from __future__ import annotations

import json
import math
import os
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Dict


_LOCK = threading.Lock()
_LOG_PATH = Path(__file__).resolve().parents[1] / "logs" / "token_usage.jsonl"
_SESSION_ID = os.environ.get("UE_MCP_SESSION_ID", f"sess_{uuid.uuid4().hex}")
_ENTRY_INDEX = 0


def estimate_text_tokens(text: str) -> int:
    if not text:
        return 0
    return max(1, math.ceil(len(text) / 4))


def estimate_payload_tokens(payload: Any) -> int:
    return estimate_text_tokens(_serialize_payload(payload))


def payload_size_bytes(payload: Any) -> int:
    return len(_serialize_payload(payload).encode("utf-8"))


def _serialize_payload(payload: Any) -> str:
    try:
        return json.dumps(
            payload, ensure_ascii=False, default=str, separators=(",", ":")
        )
    except Exception:
        return repr(payload)


def record_tool_usage(
    component: str,
    operation: str,
    *,
    request_payload: Any = None,
    response_payload: Any = None,
    metadata: Dict[str, Any] | None = None,
    started_at: float | None = None,
) -> None:
    global _ENTRY_INDEX
    entry = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "session_id": _SESSION_ID,
        "component": component,
        "operation": operation,
        "request_bytes": payload_size_bytes(request_payload),
        "response_bytes": payload_size_bytes(response_payload),
        "estimated_request_tokens": estimate_payload_tokens(request_payload),
        "estimated_response_tokens": estimate_payload_tokens(response_payload),
        "metadata": metadata or {},
    }
    if started_at is not None:
        entry["latency_ms"] = round((time.perf_counter() - started_at) * 1000, 2)

    try:
        with _LOCK:
            _ENTRY_INDEX += 1
            entry["session_entry_index"] = _ENTRY_INDEX
            _LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
            with _LOG_PATH.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:
        # Telemetry must never break tool execution.
        return
