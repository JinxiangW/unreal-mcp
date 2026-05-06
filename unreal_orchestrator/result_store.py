"""In-memory result handle store for large MCP payloads."""

from __future__ import annotations

import threading
import time
import uuid
from typing import Any, Dict, Optional


_LOCK = threading.Lock()
_STORE: Dict[str, Dict[str, Any]] = {}


def _resolve_path(payload: Any, path: Optional[str]) -> tuple[bool, Any, str | None]:
    if not path:
        return True, payload, None

    current = payload
    for part in path.split("."):
        key = part.strip()
        if not key:
            return False, None, f"Invalid result path: {path}"
        if isinstance(current, dict) and key in current:
            current = current[key]
            continue
        return False, None, f"Result path not found: {path}"
    return True, current, None


def _project_fields(item: Any, fields: Optional[list[str]]) -> Any:
    if fields and isinstance(item, dict):
        return {field: item.get(field) for field in fields}
    return item


def _slice_payload(
    payload: Any,
    *,
    fields: Optional[list[str]],
    offset: int,
    limit: Optional[int],
) -> tuple[Any, Dict[str, Any]]:
    if isinstance(payload, list):
        normalized_offset = max(0, offset)
        sliced = (
            payload[normalized_offset : normalized_offset + limit]
            if limit is not None
            else payload[normalized_offset:]
        )
        projected = [_project_fields(item, fields) for item in sliced]
        page = {
            "total_count": len(payload),
            "returned_count": len(projected),
            "offset": normalized_offset,
        }
        if limit is not None:
            page["limit"] = limit
        return projected, page

    if fields and isinstance(payload, dict):
        return {field: payload.get(field) for field in fields}, {}
    return payload, {}


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
    path: Optional[str] = None,
) -> Dict[str, Any]:
    with _LOCK:
        entry = _STORE.get(handle)
    if not entry:
        return {"success": False, "error": f"Unknown result handle: {handle}"}

    resolved, payload, error = _resolve_path(entry["payload"], path)
    if not resolved:
        return {
            "success": False,
            "result_handle": handle,
            "error": error,
        }

    result_payload, page = _slice_payload(
        payload,
        fields=fields,
        offset=offset,
        limit=limit,
    )

    response = {
        "success": True,
        "result_handle": handle,
        "metadata": entry["metadata"],
        "created_at": entry["created_at"],
        "result": result_payload,
    }
    if path:
        response["path"] = path
    if page:
        response["page"] = page
        response.update(page)
    return response


def release_result(handle: str) -> Dict[str, Any]:
    with _LOCK:
        removed = _STORE.pop(handle, None)
    return {
        "success": removed is not None,
        "result_handle": handle,
        "released": removed is not None,
    }
