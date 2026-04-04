"""In-memory result handle store for large MCP payloads."""

from __future__ import annotations

import threading
import time
import uuid
from typing import Any, Dict, Optional


_LOCK = threading.Lock()
_STORE: Dict[str, Dict[str, Any]] = {}


def store_result(
    payload: Any, metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    handle = f"rh_{uuid.uuid4().hex}"
    entry = {
        "handle": handle,
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "payload": payload,
        "metadata": metadata or {},
    }
    with _LOCK:
        _STORE[handle] = entry
    return {
        "result_handle": handle,
        "metadata": entry["metadata"],
        "created_at": entry["created_at"],
    }


def read_result(
    handle: str,
    *,
    fields: Optional[list[str]] = None,
    offset: int = 0,
    limit: Optional[int] = None,
) -> Dict[str, Any]:
    with _LOCK:
        entry = _STORE.get(handle)
    if not entry:
        return {"success": False, "error": f"Unknown result handle: {handle}"}

    payload = entry["payload"]
    result_payload = payload
    if fields and isinstance(payload, dict):
        result_payload = {field: payload.get(field) for field in fields}
    elif isinstance(payload, list):
        sliced = (
            payload[offset : offset + limit] if limit is not None else payload[offset:]
        )
        result_payload = sliced

    return {
        "success": True,
        "result_handle": handle,
        "metadata": entry["metadata"],
        "created_at": entry["created_at"],
        "result": result_payload,
    }


def release_result(handle: str) -> Dict[str, Any]:
    with _LOCK:
        removed = _STORE.pop(handle, None)
    return {
        "success": removed is not None,
        "result_handle": handle,
        "released": removed is not None,
    }
