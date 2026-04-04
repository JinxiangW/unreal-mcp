"""
Common helpers for Unreal Editor MCP.
"""

import json
import logging
import time
from datetime import datetime
from functools import wraps
from pathlib import Path
from typing import Any, Dict, Optional

from unreal_observability.token_usage import record_tool_usage

from .connection import get_unreal_connection


logger = logging.getLogger("UnrealEditorMCP")


def save_json_to_file(
    data: Dict[str, Any],
    save_to: str,
    tool_name: str,
    asset_name: Optional[str] = None,
) -> Dict[str, Any]:
    if not save_to:
        return {}

    try:
        save_path = Path(save_to)
        if save_to.endswith("/") or save_to.endswith("\\") or save_path.is_dir():
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_asset_name = (
                (asset_name or "data").replace("/", "_").replace("\\", "_")
            )
            save_path = save_path / f"{tool_name}_{safe_asset_name}_{timestamp}.json"

        save_path.parent.mkdir(parents=True, exist_ok=True)
        with open(save_path, "w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2, ensure_ascii=False)

        return {"saved_to": str(save_path.absolute()), "save_success": True}
    except Exception as exc:
        logger.error("Failed to save JSON: %s", exc)
        return {"save_success": False, "save_error": str(exc)}


def with_unreal_connection(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as exc:
            logger.error("%s error: %s", func.__name__, exc)
            return {"success": False, "message": str(exc)}

    return wrapper


def send_command(
    command: str, params: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    started_at = time.perf_counter()
    unreal = get_unreal_connection()
    response = unreal.send_command(command, params)
    payload = response or {"success": False, "message": "No response from Unreal"}
    record_tool_usage(
        "unreal_editor_mcp.transport",
        command,
        request_payload=params or {},
        response_payload=payload,
        metadata={"transport": "tcp"},
        started_at=started_at,
    )
    return payload
