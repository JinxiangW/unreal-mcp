"""Minimal internal wrappers for the Unreal TCP backend."""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from .common import save_json_to_file, send_command, with_unreal_connection
from unreal_observability.token_usage import payload_size_bytes
from unreal_orchestrator.result_store import read_result, release_result, store_result


INLINE_RESULT_MAX_BYTES = int(os.environ.get("UE_MCP_INLINE_RESULT_MAX_BYTES", "32768"))


def _project_fields(
    item: Dict[str, Any], fields: Optional[List[str]]
) -> Dict[str, Any]:
    if not fields:
        return item
    return {field: item.get(field) for field in fields}


def _compact_list_result(
    result: Dict[str, Any],
    key: str,
    *,
    fields: Optional[List[str]],
    limit: Optional[int],
    offset: int,
) -> Dict[str, Any]:
    payload = dict(result)
    inner = dict(payload.get("result") or {})
    items = inner.get(key) or []
    total_count = len(items)
    sliced = items[offset : offset + limit] if limit is not None else items[offset:]
    inner[key] = [_project_fields(item, fields) for item in sliced]
    inner["total_count"] = total_count
    inner["returned_count"] = len(inner[key])
    inner["offset"] = offset
    if limit is not None:
        inner["limit"] = limit
    payload["result"] = inner
    return payload


def _response_body(response: Dict[str, Any]) -> Dict[str, Any]:
    return dict(response.get("result") or {})


def _response_success(response: Dict[str, Any]) -> bool:
    if response.get("status") == "error":
        return False
    body = _response_body(response)
    return bool(body.get("success", response.get("status") == "success"))


def _with_result_body(response: Dict[str, Any], body: Dict[str, Any]) -> Dict[str, Any]:
    payload = dict(response)
    payload["result"] = body
    return payload


def _asset_name_from_response(response: Dict[str, Any], fallback: str) -> str:
    body = _response_body(response)
    return (
        body.get("name")
        or body.get("blueprint_name")
        or body.get("asset_name")
        or fallback
    )


def _save_raw_response(
    response: Dict[str, Any], save_to: Optional[str], tool_name: str, fallback_name: str
) -> Dict[str, Any]:
    if not save_to or not _response_success(response):
        return {}
    return save_json_to_file(
        response,
        save_to,
        tool_name,
        _asset_name_from_response(response, fallback_name),
    )


def _attach_result_handle(
    payload: Dict[str, Any],
    raw_response: Dict[str, Any],
    *,
    enabled: bool,
    operation: str,
    auto_offloaded: bool = False,
) -> Dict[str, Any]:
    if not enabled or not _response_success(raw_response):
        return payload
    final_payload = dict(payload)
    final_payload.update(
        store_result(
            raw_response,
            metadata={
                "operation": operation,
                "response_bytes": payload_size_bytes(raw_response),
            },
        )
    )
    if auto_offloaded:
        final_payload["offloaded"] = True
        final_payload["offload_reason"] = "response_too_large"
        final_payload["inline_result_max_bytes"] = INLINE_RESULT_MAX_BYTES
    return final_payload


def _should_auto_offload(
    raw_response: Dict[str, Any], *, requested_inline: bool
) -> bool:
    if not requested_inline or not _response_success(raw_response):
        return False
    return payload_size_bytes(raw_response) > INLINE_RESULT_MAX_BYTES


def _finalize_large_result(
    *,
    raw_response: Dict[str, Any],
    summary_payload: Dict[str, Any],
    full_payload: Dict[str, Any],
    save_meta: Dict[str, Any],
    operation: str,
    summary_only: bool,
    result_handle: bool,
) -> Dict[str, Any]:
    auto_offloaded = _should_auto_offload(
        raw_response, requested_inline=not summary_only and not result_handle
    )
    payload = summary_payload if summary_only or auto_offloaded else full_payload
    payload = dict(payload)
    payload.update(save_meta)
    return _attach_result_handle(
        payload,
        raw_response,
        enabled=result_handle or auto_offloaded,
        operation=operation,
        auto_offloaded=auto_offloaded,
    )


def _summarize_property_connections(connections: Any) -> Dict[str, Any]:
    if not isinstance(connections, dict):
        return {"count": 0, "properties": []}
    return {"count": len(connections), "properties": sorted(connections.keys())}


def _summarize_material_graph_response(response: Dict[str, Any]) -> Dict[str, Any]:
    body = _response_body(response)
    summary = {
        "success": body.get("success", _response_success(response)),
        "asset_type": body.get("asset_type"),
        "name": body.get("name"),
        "path": body.get("path"),
        "node_count": body.get("node_count", len(body.get("nodes") or [])),
        "connection_count": body.get(
            "connection_count", len(body.get("connections") or []))
        ,
        "property_connection_summary": _summarize_property_connections(
            body.get("property_connections")
        ),
    }
    return _with_result_body(response, summary)


def read_result_handle(
    result_handle: str,
    fields: Optional[List[str]] = None,
    offset: int = 0,
    limit: Optional[int] = None,
) -> Dict[str, Any]:
    """Read a stored large-result handle."""
    return read_result(result_handle, fields=fields, offset=offset, limit=limit)


def release_result_handle(result_handle: str) -> Dict[str, Any]:
    """Release a stored large-result handle."""
    return release_result(result_handle)


@with_unreal_connection
def get_assets(
    path: str = "/Game/",
    asset_class: Optional[str] = None,
    name_filter: Optional[str] = None,
    summary_only: bool = True,
    fields: Optional[List[str]] = None,
    limit: Optional[int] = 20,
    offset: int = 0,
) -> Dict[str, Any]:
    """List assets in the project with optional class and name filters."""
    params: Dict[str, Any] = {"path": path}
    if asset_class:
        params["asset_class"] = asset_class
    if name_filter:
        params["name_filter"] = name_filter
    projected_fields = fields
    if summary_only and not projected_fields:
        projected_fields = ["name", "path", "class", "package"]
    return _compact_list_result(
        send_command("get_assets", params),
        "assets",
        fields=projected_fields,
        limit=limit,
        offset=offset,
    )


@with_unreal_connection
def get_current_level() -> Dict[str, Any]:
    """Get the current editor level."""
    return send_command("get_current_level", {})


@with_unreal_connection
def build_material_graph(
    material_name: str,
    nodes: List[Dict[str, Any]],
    connections: Optional[List[Dict[str, Any]]] = None,
    properties: Optional[Dict[str, Any]] = None,
    compile: bool = True,
) -> Dict[str, Any]:
    """Build an entire material graph in one request."""
    params: Dict[str, Any] = {
        "material_name": material_name,
        "nodes": nodes,
        "compile": compile,
    }
    if connections:
        params["connections"] = connections
    if properties:
        params["properties"] = properties
    return send_command("build_material_graph", params)


@with_unreal_connection
def get_material_graph(
    asset_path: str,
    save_to: Optional[str] = None,
    summary_only: bool = True,
    result_handle: bool = False,
) -> Dict[str, Any]:
    """Inspect a material or material function graph."""
    result = send_command("get_material_graph", {"asset_path": asset_path})
    save_meta = _save_raw_response(
        result, save_to, "material_graph", asset_path.split("/")[-1]
    )
    return _finalize_large_result(
        raw_response=result,
        summary_payload=_summarize_material_graph_response(result),
        full_payload=result,
        save_meta=save_meta,
        operation="get_material_graph",
        summary_only=summary_only,
        result_handle=result_handle,
    )
