"""
Workflow-oriented tools for Unreal Editor MCP.

This module keeps the tool surface aligned with the TCP plugin backend,
while grouping commands around editor workflows instead of legacy wrappers.
"""

import os

from typing import Any, Dict, List, Optional

from .common import (
    save_json_to_file,
    send_command,
    with_unreal_connection,
)
from unreal_orchestrator.result_store import read_result, release_result, store_result
from unreal_observability.token_usage import payload_size_bytes


INLINE_RESULT_MAX_BYTES = int(os.environ.get("UE_MCP_INLINE_RESULT_MAX_BYTES", "32768"))


SUPPORTED_BLUEPRINT_GRAPH_COMMANDS = {
    "add_blueprint_node",
    "connect_nodes",
    "create_variable",
    "set_blueprint_variable_properties",
    "add_event_node",
    "delete_node",
    "set_node_property",
    "create_function",
    "add_function_input",
    "add_function_output",
    "delete_function",
    "rename_function",
}


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
    if not requested_inline:
        return False
    if not _response_success(raw_response):
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
            "connection_count", len(body.get("connections") or [])
        ),
        "property_connection_summary": _summarize_property_connections(
            body.get("property_connections")
        ),
    }
    return _with_result_body(response, summary)


def _summarize_niagara_graph_response(response: Dict[str, Any]) -> Dict[str, Any]:
    body = _response_body(response)
    summary = {
        "success": body.get("success", _response_success(response)),
        "asset_path": body.get("asset_path"),
        "script_path": body.get("script_path"),
        "emitter": body.get("emitter"),
        "script": body.get("script"),
        "module": body.get("module"),
        "node_count": body.get("node_count", len(body.get("nodes") or [])),
        "connection_count": body.get(
            "connection_count", len(body.get("connections") or body.get("edges") or [])
        ),
        "input_count": len(body.get("inputs") or []),
        "output_count": len(body.get("outputs") or []),
        "parameter_count": len(body.get("parameters") or []),
    }
    return _with_result_body(response, summary)


def _summarize_niagara_emitter_response(response: Dict[str, Any]) -> Dict[str, Any]:
    body = _response_body(response)
    emitters = body.get("emitters") or []
    summary = {
        "success": body.get("success", _response_success(response)),
        "asset_path": body.get("asset_path") or body.get("system_path"),
        "detail_level": body.get("detail_level"),
        "emitter_count": len(emitters),
        "emitters": [
            {
                "name": emitter.get("name"),
                "enabled": emitter.get("enabled"),
                "renderer_count": len(emitter.get("renderers") or []),
                "script_count": len(emitter.get("scripts") or []),
                "parameter_count": len(emitter.get("parameters") or []),
            }
            for emitter in emitters
            if isinstance(emitter, dict)
        ],
    }
    return _with_result_body(response, summary)


def _summarize_blueprint_info_response(response: Dict[str, Any]) -> Dict[str, Any]:
    body = _response_body(response)
    widget_tree = body.get("widget_tree") or {}
    summary = {
        "success": body.get("success", _response_success(response)),
        "blueprint_path": body.get("blueprint_path"),
        "blueprint_name": body.get("blueprint_name"),
        "blueprint_class": body.get("blueprint_class"),
        "parent_class": body.get("parent_class"),
        "variable_count": len(body.get("variables") or []),
        "function_count": len(body.get("functions") or []),
        "widget_graph_count": len(widget_tree.get("widget_graphs") or []),
    }
    return _with_result_body(response, summary)


def _summarize_blueprint_content_response(response: Dict[str, Any]) -> Dict[str, Any]:
    body = _response_body(response)
    event_graph = body.get("event_graph") or {}
    summary = {
        "success": body.get("success", _response_success(response)),
        "blueprint_path": body.get("blueprint_path"),
        "blueprint_name": body.get("blueprint_name"),
        "parent_class": body.get("parent_class"),
        "variable_count": len(body.get("variables") or []),
        "function_count": len(body.get("functions") or []),
        "component_count": len(body.get("components") or []),
        "interface_count": len(body.get("interfaces") or []),
        "event_graph_summary": {
            "name": event_graph.get("name"),
            "node_count": event_graph.get(
                "node_count", len(event_graph.get("nodes") or [])
            ),
        }
        if event_graph
        else None,
    }
    return _with_result_body(response, summary)


def _summarize_compiled_code_response(response: Dict[str, Any]) -> Dict[str, Any]:
    body = _response_body(response)
    summary = {
        "success": body.get("success", _response_success(response)),
        "asset_path": body.get("asset_path"),
        "emitter": body.get("emitter"),
        "script": body.get("script"),
        "hlsl_cpu_length": body.get("hlsl_cpu_length", len(body.get("hlsl_cpu") or "")),
        "hlsl_gpu_length": body.get("hlsl_gpu_length", len(body.get("hlsl_gpu") or "")),
        "error_count": body.get("error_count", len(body.get("compile_errors") or [])),
        "compile_errors": body.get("compile_errors") or [],
    }
    return _with_result_body(response, summary)


def _summarize_particle_attributes_response(response: Dict[str, Any]) -> Dict[str, Any]:
    body = _response_body(response)
    emitters = body.get("emitters") or []
    summary = {
        "success": body.get("success", _response_success(response)),
        "component_name": body.get("component_name"),
        "current_frame": body.get("current_frame"),
        "emitter_count": len(emitters),
        "emitters": [
            {
                "name": emitter.get("name"),
                "particle_count": emitter.get("particle_count"),
                "attribute_count": len(emitter.get("attributes") or []),
                "sample_particle_count": len(emitter.get("particles") or []),
            }
            for emitter in emitters
            if isinstance(emitter, dict)
        ],
    }
    return _with_result_body(response, summary)


def _summarize_batch_response(
    response: Dict[str, Any],
    *,
    success_items_key: Optional[str] = None,
    failure_items_key: Optional[str] = None,
    include_success_items: bool = False,
) -> Dict[str, Any]:
    body = _response_body(response)
    success_items = list(body.get(success_items_key) or []) if success_items_key else []
    failure_items = list(body.get(failure_items_key) or []) if failure_items_key else []
    success_count = body.get("success_count")
    if success_count is None:
        success_count = body.get("deleted_count")
    if success_count is None:
        success_count = len(
            [
                item
                for item in success_items
                if not isinstance(item, dict) or item.get("success", True)
            ]
        )
    failed_count = body.get("fail_count")
    if failed_count is None:
        failed_count = body.get("failed_count")
    if failed_count is None:
        failed_count = len(failure_items)
    total_count = body.get("total_count")
    if total_count is None:
        total_count = success_count + failed_count

    summary: Dict[str, Any] = {
        "success": body.get("success", _response_success(response)),
        "summary": {
            "requested": total_count,
            "succeeded": success_count,
            "failed": failed_count,
        },
        "failed_items": failure_items,
    }
    if include_success_items:
        summary["success_items"] = success_items
    return _with_result_body(response, summary)


def _filter_named_properties(
    properties: Dict[str, Any], requested: Optional[List[str]]
) -> Dict[str, Any]:
    if not requested:
        return {}
    return {name: properties.get(name) for name in requested if name in properties}


def _summarize_asset_properties_response(
    response: Dict[str, Any], requested_properties: Optional[List[str]]
) -> Dict[str, Any]:
    body = _response_body(response)
    properties = body.get("properties") or {}
    summary = {
        "success": body.get("success", _response_success(response)),
        "asset_path": body.get("asset_path"),
        "asset_class": body.get("asset_class"),
        "property_count": len(properties),
        "properties": _filter_named_properties(properties, requested_properties),
    }
    return _with_result_body(response, summary)


def _summarize_actor_properties_response(
    response: Dict[str, Any], requested_properties: Optional[List[str]]
) -> Dict[str, Any]:
    body = _response_body(response)
    properties = body.get("properties") or {}
    summary = {
        "success": body.get("success", _response_success(response)),
        "name": body.get("name"),
        "class": body.get("class"),
        "location": body.get("location"),
        "rotation": body.get("rotation"),
        "scale": body.get("scale"),
        "property_count": len(properties),
        "properties": _filter_named_properties(properties, requested_properties),
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
def get_asset_properties(
    asset_path: str,
    properties: Optional[List[str]] = None,
    summary_only: bool = True,
) -> Dict[str, Any]:
    """Read editable properties from an asset."""
    params: Dict[str, Any] = {"asset_path": asset_path}
    if properties:
        params["properties"] = properties
    result = send_command("get_asset_properties", params)
    return (
        _summarize_asset_properties_response(result, properties)
        if summary_only
        else result
    )


@with_unreal_connection
def create_asset(
    asset_type: str,
    name: str,
    path: str = "/Game/",
    properties: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Create a new asset using the generic asset backend."""
    params: Dict[str, Any] = {
        "asset_type": asset_type,
        "name": name,
        "path": path,
    }
    if properties:
        params["properties"] = properties
    return send_command("create_asset", params)


@with_unreal_connection
def set_asset_properties(asset_path: str, properties: Dict[str, Any]) -> Dict[str, Any]:
    """Set editable properties on an asset."""
    return send_command(
        "set_asset_properties",
        {
            "asset_path": asset_path,
            "properties": properties,
        },
    )


@with_unreal_connection
def delete_asset(asset_path: str) -> Dict[str, Any]:
    """Delete an asset by path."""
    return send_command("delete_asset", {"asset_path": asset_path})


@with_unreal_connection
def batch_create_assets(
    items: List[Dict[str, Any]], include_success_items: bool = False
) -> Dict[str, Any]:
    """Create multiple assets in one request."""
    return _summarize_batch_response(
        send_command("batch_create_assets", {"items": items}),
        success_items_key="results",
        failure_items_key="failed",
        include_success_items=include_success_items,
    )


@with_unreal_connection
def batch_set_assets_properties(
    items: List[Dict[str, Any]], include_success_items: bool = False
) -> Dict[str, Any]:
    """Update multiple assets in one request."""
    return _summarize_batch_response(
        send_command("batch_set_assets_properties", {"items": items}),
        success_items_key="results",
        failure_items_key="failed",
        include_success_items=include_success_items,
    )


@with_unreal_connection
def get_current_level() -> Dict[str, Any]:
    """Get the current editor level."""
    return send_command("get_current_level", {})


@with_unreal_connection
def create_level(level_path: str) -> Dict[str, Any]:
    """Create a level asset."""
    return send_command("create_level", {"level_path": level_path})


@with_unreal_connection
def load_level(level_path: str) -> Dict[str, Any]:
    """Load a level into the editor."""
    return send_command("load_level", {"level_path": level_path})


@with_unreal_connection
def save_current_level() -> Dict[str, Any]:
    """Save the active level."""
    return send_command("save_current_level", {})


@with_unreal_connection
def get_viewport_camera() -> Dict[str, Any]:
    """Read the active editor viewport camera."""
    return send_command("get_viewport_camera", {})


@with_unreal_connection
def set_viewport_camera(
    location: Optional[Dict[str, float]] = None,
    rotation: Optional[Dict[str, float]] = None,
    fov: Optional[float] = None,
    ortho_width: Optional[float] = None,
    perspective: bool = True,
) -> Dict[str, Any]:
    """Set the active editor viewport camera."""
    params: Dict[str, Any] = {"perspective": perspective}
    if location is not None:
        params["location"] = location
    if rotation is not None:
        params["rotation"] = rotation
    if fov is not None:
        params["fov"] = fov
    if ortho_width is not None:
        params["ortho_width"] = ortho_width
    return send_command("set_viewport_camera", params)


@with_unreal_connection
def get_viewport_screenshot(
    output_path: str,
    format: str = "png",
    quality: int = 85,
    include_ui: bool = False,
    output_mode: str = "file",
    force_redraw: bool = True,
) -> Dict[str, Any]:
    """Capture the active editor or PIE viewport."""
    return send_command(
        "get_viewport_screenshot",
        {
            "output_path": output_path,
            "format": format,
            "quality": quality,
            "include_ui": include_ui,
            "output_mode": output_mode,
            "force_redraw": force_redraw,
        },
    )


@with_unreal_connection
def get_actors(
    actor_class: Optional[str] = None,
    detailed: bool = False,
    summary_only: bool = True,
    fields: Optional[List[str]] = None,
    limit: Optional[int] = 20,
    offset: int = 0,
    name_filter: Optional[str] = None,
) -> Dict[str, Any]:
    """List actors in the current level."""
    params: Dict[str, Any] = {"detailed": detailed}
    if actor_class:
        params["actor_class"] = actor_class
    projected_fields = fields
    if summary_only and not projected_fields:
        projected_fields = ["name", "class", "path", "location"]
    result = send_command("get_actors", params)
    payload = dict(result)
    inner = dict(payload.get("result") or {})
    actors = inner.get("actors") or []
    if name_filter:
        actors = [
            actor
            for actor in actors
            if name_filter.lower() in str(actor.get("name", "")).lower()
        ]
    inner["actors"] = actors
    payload["result"] = inner
    return _compact_list_result(
        payload,
        "actors",
        fields=projected_fields,
        limit=limit,
        offset=offset,
    )


@with_unreal_connection
def get_actor_properties(
    name: str,
    properties: Optional[List[str]] = None,
    summary_only: bool = True,
) -> Dict[str, Any]:
    """Read editable properties from an actor."""
    params: Dict[str, Any] = {"name": name}
    if properties:
        params["properties"] = properties
    result = send_command("get_actor_properties", params)
    return (
        _summarize_actor_properties_response(result, properties)
        if summary_only
        else result
    )


@with_unreal_connection
def spawn_actor(
    actor_class: str,
    name: Optional[str] = None,
    location: Optional[Dict[str, float]] = None,
    rotation: Optional[Dict[str, float]] = None,
    scale: Optional[Dict[str, float]] = None,
    properties: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Spawn an actor in the current level."""
    params: Dict[str, Any] = {"actor_class": actor_class}
    if name:
        params["name"] = name
    if location is not None:
        params["location"] = location
    if rotation is not None:
        params["rotation"] = rotation
    if scale is not None:
        params["scale"] = scale
    if properties:
        params["properties"] = properties
    return send_command("spawn_actor", params)


@with_unreal_connection
def set_actor_properties(name: str, properties: Dict[str, Any]) -> Dict[str, Any]:
    """Set editable properties on an actor."""
    return send_command(
        "set_actor_properties",
        {
            "name": name,
            "properties": properties,
        },
    )


@with_unreal_connection
def delete_actor(name: str) -> Dict[str, Any]:
    """Delete an actor by name."""
    return send_command("delete_actor", {"name": name})


@with_unreal_connection
def batch_spawn_actors(
    items: List[Dict[str, Any]], include_success_items: bool = False
) -> Dict[str, Any]:
    """Spawn multiple actors in one request."""
    return _summarize_batch_response(
        send_command("batch_spawn_actors", {"items": items}),
        success_items_key="results",
        failure_items_key="failed",
        include_success_items=include_success_items,
    )


@with_unreal_connection
def batch_delete_actors(
    names: List[str], include_success_items: bool = False
) -> Dict[str, Any]:
    """Delete multiple actors in one request."""
    return _summarize_batch_response(
        send_command("batch_delete_actors", {"names": names}),
        success_items_key="deleted",
        failure_items_key="failed",
        include_success_items=include_success_items,
    )


@with_unreal_connection
def batch_set_actors_properties(
    actors: List[Dict[str, Any]], include_success_items: bool = False
) -> Dict[str, Any]:
    """Update multiple actors in one request."""
    return _summarize_batch_response(
        send_command("batch_set_actors_properties", {"actors": actors}),
        success_items_key="results",
        failure_items_key="failed",
        include_success_items=include_success_items,
    )


@with_unreal_connection
def import_texture(
    source_path: str,
    name: str,
    destination_path: str = "/Game/Textures/",
    delete_source: bool = False,
    srgb: Optional[bool] = None,
    compression_settings: Optional[str] = None,
    filter: Optional[str] = None,
    address_x: Optional[str] = None,
    address_y: Optional[str] = None,
) -> Dict[str, Any]:
    """Import a texture into the project."""
    params: Dict[str, Any] = {
        "source_path": source_path,
        "name": name,
        "destination_path": destination_path,
        "delete_source": delete_source,
    }
    if srgb is not None:
        params["srgb"] = srgb
    if compression_settings is not None:
        params["compression_settings"] = compression_settings
    if filter is not None:
        params["filter"] = filter
    if address_x is not None:
        params["address_x"] = address_x
    if address_y is not None:
        params["address_y"] = address_y
    return send_command("import_texture", params)


@with_unreal_connection
def import_fbx(
    fbx_path: str,
    destination_path: str = "/Game/ImportedMeshes/",
    asset_name: Optional[str] = None,
    spawn_in_level: bool = True,
    location: Optional[List[float]] = None,
) -> Dict[str, Any]:
    """Import an FBX asset and optionally spawn it."""
    params: Dict[str, Any] = {
        "fbx_path": fbx_path,
        "destination_path": destination_path,
        "spawn_in_level": spawn_in_level,
    }
    if asset_name is not None:
        params["asset_name"] = asset_name
    if location is not None:
        params["location"] = location
    return send_command("import_fbx", params)


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


@with_unreal_connection
def get_niagara_graph(
    asset_path: Optional[str] = None,
    emitter: Optional[str] = None,
    script: str = "spawn",
    script_path: Optional[str] = None,
    module: str = "",
    save_to: Optional[str] = None,
    summary_only: bool = True,
    result_handle: bool = False,
) -> Dict[str, Any]:
    """Inspect a Niagara graph from a system emitter or standalone script."""
    params: Dict[str, Any] = {"script": script, "module": module}
    if script_path:
        params["script_path"] = script_path
    elif asset_path and emitter:
        params["asset_path"] = asset_path
        params["emitter"] = emitter
    else:
        return {
            "success": False,
            "error": "Must provide either (asset_path + emitter) or script_path",
        }

    result = send_command("get_niagara_graph", params)
    graph_name = script_path.split("/")[-1] if script_path else f"{emitter}_{script}"
    save_meta = _save_raw_response(result, save_to, "niagara_graph", graph_name)
    return _finalize_large_result(
        raw_response=result,
        summary_payload=_summarize_niagara_graph_response(result),
        full_payload=result,
        save_meta=save_meta,
        operation="get_niagara_graph",
        summary_only=summary_only,
        result_handle=result_handle,
    )


@with_unreal_connection
def update_niagara_graph(
    asset_path: Optional[str] = None,
    emitter: Optional[str] = None,
    script: str = "spawn",
    script_path: Optional[str] = None,
    operations: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Apply graph operations to a Niagara graph."""
    params: Dict[str, Any] = {"script": script, "operations": operations or []}
    if script_path:
        params["script_path"] = script_path
    elif asset_path and emitter:
        params["asset_path"] = asset_path
        params["emitter"] = emitter
    else:
        return {
            "success": False,
            "error": "Must provide either (asset_path + emitter) or script_path",
        }
    return send_command("update_niagara_graph", params)


@with_unreal_connection
def get_niagara_emitter(
    asset_path: str,
    detail_level: str = "overview",
    emitters: Optional[List[str]] = None,
    include: Optional[List[str]] = None,
    save_to: Optional[str] = None,
    summary_only: bool = True,
    result_handle: bool = False,
) -> Dict[str, Any]:
    """Inspect Niagara emitter structure and settings."""
    params: Dict[str, Any] = {"asset_path": asset_path, "detail_level": detail_level}
    if emitters is not None:
        params["emitters"] = emitters
    if include is not None:
        params["include"] = include
    result = send_command("get_niagara_emitter", params)
    save_meta = _save_raw_response(
        result, save_to, "niagara_emitter", asset_path.split("/")[-1]
    )
    return _finalize_large_result(
        raw_response=result,
        summary_payload=_summarize_niagara_emitter_response(result),
        full_payload=result,
        save_meta=save_meta,
        operation="get_niagara_emitter",
        summary_only=summary_only,
        result_handle=result_handle,
    )


@with_unreal_connection
def update_niagara_emitter(
    asset_path: str, operations: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """Apply emitter-level Niagara operations."""
    return send_command(
        "update_niagara_emitter",
        {
            "asset_path": asset_path,
            "operations": operations,
        },
    )


@with_unreal_connection
def get_niagara_compiled_code(
    asset_path: str,
    emitter: Optional[str] = None,
    script: str = "spawn",
    save_to: Optional[str] = None,
    include_code: bool = False,
    result_handle: bool = False,
) -> Dict[str, Any]:
    """Get compiled Niagara HLSL for debugging."""
    params: Dict[str, Any] = {"asset_path": asset_path, "script": script}
    if emitter:
        params["emitter"] = emitter
    result = send_command("get_niagara_compiled_code", params)
    save_meta = _save_raw_response(
        result,
        save_to,
        "niagara_compiled_code",
        emitter or asset_path.split("/")[-1],
    )
    return _finalize_large_result(
        raw_response=result,
        summary_payload=_summarize_compiled_code_response(result),
        full_payload=result,
        save_meta=save_meta,
        operation="get_niagara_compiled_code",
        summary_only=not include_code,
        result_handle=result_handle,
    )


@with_unreal_connection
def get_niagara_particle_attributes(
    component_name: str,
    emitter: Optional[str] = None,
    frame: int = 0,
    summary_only: bool = True,
    result_handle: bool = False,
) -> Dict[str, Any]:
    """Inspect runtime particle attributes from a Niagara component."""
    params: Dict[str, Any] = {"component_name": component_name, "frame": frame}
    if emitter:
        params["emitter"] = emitter
    result = send_command("get_niagara_particle_attributes", params)
    return _finalize_large_result(
        raw_response=result,
        summary_payload=_summarize_particle_attributes_response(result),
        full_payload=result,
        save_meta={},
        operation="get_niagara_particle_attributes",
        summary_only=summary_only,
        result_handle=result_handle,
    )


@with_unreal_connection
def get_blueprint_info(
    blueprint_path: str,
    include_variables: bool = True,
    include_functions: bool = True,
    include_widget_tree: bool = True,
    summary_only: bool = True,
    result_handle: bool = False,
) -> Dict[str, Any]:
    """Read high-level blueprint info.

    This uses the existing blueprint info command, which works best for
    Editor Utility Widgets but also returns useful metadata for regular blueprints.
    """
    result = send_command(
        "get_editor_widget_blueprint_info",
        {
            "blueprint_path": blueprint_path,
            "include_variables": include_variables,
            "include_functions": include_functions,
            "include_widget_tree": include_widget_tree,
        },
    )
    return _finalize_large_result(
        raw_response=result,
        summary_payload=_summarize_blueprint_info_response(result),
        full_payload=result,
        save_meta={},
        operation="get_blueprint_info",
        summary_only=summary_only,
        result_handle=result_handle,
    )


@with_unreal_connection
def update_blueprint(
    blueprint_path: str,
    properties: Optional[Dict[str, Any]] = None,
    compile_after: bool = False,
) -> Dict[str, Any]:
    """Save and optionally compile a blueprint update request."""
    params: Dict[str, Any] = {
        "blueprint_path": blueprint_path,
        "compile_after": compile_after,
    }
    if properties:
        params["properties"] = properties
    return send_command("update_editor_widget_blueprint", params)


@with_unreal_connection
def read_blueprint_content(
    blueprint_path: str,
    include_event_graph: bool = True,
    include_functions: bool = True,
    include_variables: bool = True,
    include_components: bool = True,
    include_interfaces: bool = True,
    save_to: Optional[str] = None,
    summary_only: bool = True,
    result_handle: bool = False,
) -> Dict[str, Any]:
    """Read a fuller blueprint content snapshot."""
    result = send_command(
        "read_blueprint_content",
        {
            "blueprint_path": blueprint_path,
            "include_event_graph": include_event_graph,
            "include_functions": include_functions,
            "include_variables": include_variables,
            "include_components": include_components,
            "include_interfaces": include_interfaces,
        },
    )
    save_meta = _save_raw_response(
        result, save_to, "blueprint_content", blueprint_path.split("/")[-1]
    )
    return _finalize_large_result(
        raw_response=result,
        summary_payload=_summarize_blueprint_content_response(result),
        full_payload=result,
        save_meta=save_meta,
        operation="read_blueprint_content",
        summary_only=summary_only,
        result_handle=result_handle,
    )


@with_unreal_connection
def analyze_blueprint_graph(blueprint_path: str) -> Dict[str, Any]:
    """Analyze blueprint graphs using the plugin backend."""
    return send_command("analyze_blueprint_graph", {"blueprint_path": blueprint_path})


@with_unreal_connection
def blueprint_graph_command(command: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """Run an advanced blueprint graph command.

    Supported commands:
    add_blueprint_node, connect_nodes, create_variable,
    set_blueprint_variable_properties, add_event_node, delete_node,
    set_node_property, create_function, add_function_input,
    add_function_output, delete_function, rename_function.
    """
    if command not in SUPPORTED_BLUEPRINT_GRAPH_COMMANDS:
        supported = ", ".join(sorted(SUPPORTED_BLUEPRINT_GRAPH_COMMANDS))
        return {
            "success": False,
            "error": f"Unsupported blueprint graph command: {command}. Supported: {supported}",
        }
    return send_command(command, params or {})


__all__ = [
    "get_assets",
    "get_asset_properties",
    "create_asset",
    "set_asset_properties",
    "delete_asset",
    "batch_create_assets",
    "batch_set_assets_properties",
    "get_current_level",
    "create_level",
    "load_level",
    "save_current_level",
    "get_viewport_camera",
    "set_viewport_camera",
    "get_viewport_screenshot",
    "get_actors",
    "get_actor_properties",
    "spawn_actor",
    "set_actor_properties",
    "delete_actor",
    "batch_spawn_actors",
    "batch_delete_actors",
    "batch_set_actors_properties",
    "import_texture",
    "import_fbx",
    "build_material_graph",
    "get_material_graph",
    "get_niagara_graph",
    "update_niagara_graph",
    "get_niagara_emitter",
    "update_niagara_emitter",
    "get_niagara_compiled_code",
    "get_niagara_particle_attributes",
    "get_blueprint_info",
    "update_blueprint",
    "read_blueprint_content",
    "analyze_blueprint_graph",
    "blueprint_graph_command",
    "read_result_handle",
    "release_result_handle",
]
