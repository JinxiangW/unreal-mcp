"""High-level blueprint inspection and graph-edit tools."""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from unreal_backend_tcp.tools import (
    add_blueprint_node as raw_add_blueprint_node,
    analyze_blueprint_graph as raw_analyze_blueprint_graph,
    connect_nodes as raw_connect_nodes,
    get_blueprint_function_details as raw_get_blueprint_function_details,
    get_blueprint_variable_details as raw_get_blueprint_variable_details,
    read_blueprint_content as raw_read_blueprint_content,
    set_node_property as raw_set_node_property,
)


def _new_operation_id(action: str) -> str:
    return f"blueprint:{action}:{int(time.time() * 1000)}"


def _structured_blueprint_failure(
    operation_id: str,
    target: str,
    error: str,
    *,
    failed_changes: Optional[list[Dict[str, Any]]] = None,
    post_state: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    return {
        "success": False,
        "operation_id": operation_id,
        "domain": "blueprint",
        "targets": [target] if target else [],
        "applied_changes": [],
        "failed_changes": failed_changes
        or [{"target": target, "field": "blueprint", "error": error}],
        "post_state": post_state or {},
        "verification": {"verified": False, "checks": []},
        "error": error,
    }


def _result_success(result: Dict[str, Any]) -> bool:
    if result.get("status") == "error":
        return False
    body = result.get("result") or result
    return bool(body.get("success", result.get("status") == "success"))


def _result_body(result: Dict[str, Any]) -> Dict[str, Any]:
    if result.get("status") == "success" and isinstance(result.get("result"), dict):
        return result["result"]
    return result


def _resolve_blueprint_identifier(
    *,
    blueprint_path: Optional[str] = None,
    blueprint_name: Optional[str] = None,
) -> tuple[str, str]:
    value = (blueprint_path or blueprint_name or "").strip()
    if not value:
        raise ValueError("blueprint_path or blueprint_name is required")
    if value.startswith("/"):
        return value, value
    resolved = f"/Game/Blueprints/{value}"
    if "." not in resolved:
        base_name = value.rsplit("/", 1)[-1]
        resolved = f"{resolved}.{base_name}"
    return value, resolved


def get_blueprint_harness_info() -> Dict[str, Any]:
    """Describe the current blueprint harness backend and scope."""
    payload = {
        "domain": "blueprint",
        "backend": "internal_tcp_blueprint_bridge",
        "target_backend": "cpp_primary",
        "supports": [
            "blueprint_asset_read",
            "graph_analysis",
            "graph_node_discovery",
            "graph_node_creation",
            "graph_connections",
            "pin_default_updates",
        ],
    }
    return {
        "success": True,
        "operation_id": _new_operation_id("get_blueprint_harness_info"),
        "domain": "blueprint",
        "targets": ["blueprint_harness"],
        "applied_changes": [],
        "failed_changes": [],
        "post_state": {"blueprint_harness": payload},
        "verification": {"verified": True, "checks": []},
        **payload,
    }


def read_blueprint_content(
    blueprint_path: str | None = None,
    blueprint_name: str | None = None,
    include_event_graph: bool = True,
    include_functions: bool = True,
    include_variables: bool = True,
    include_components: bool = True,
    include_interfaces: bool = True,
) -> Dict[str, Any]:
    """Read high-level blueprint content with a consistent input shape."""
    operation_id = _new_operation_id("read_blueprint_content")
    try:
        identifier, resolved_path = _resolve_blueprint_identifier(
            blueprint_path=blueprint_path,
            blueprint_name=blueprint_name,
        )
    except ValueError as exc:
        return _structured_blueprint_failure(operation_id, "", str(exc))

    result = raw_read_blueprint_content(
        blueprint_path=resolved_path,
        include_event_graph=include_event_graph,
        include_functions=include_functions,
        include_variables=include_variables,
        include_components=include_components,
        include_interfaces=include_interfaces,
    )
    if not _result_success(result):
        body = _result_body(result)
        return _structured_blueprint_failure(
            operation_id,
            identifier,
            body.get("error", "read_blueprint_content failed"),
        )

    body = _result_body(result)
    checks = [
        {
            "target": identifier,
            "field": "blueprint_loaded",
            "expected": True,
            "actual": True,
            "ok": True,
        }
    ]
    return {
        "success": True,
        "operation_id": operation_id,
        "domain": "blueprint",
        "targets": [identifier],
        "applied_changes": [],
        "failed_changes": [],
        "post_state": {identifier: body},
        "verification": {"verified": True, "checks": checks},
        **body,
    }


def analyze_blueprint_graph(
    blueprint_path: str | None = None,
    blueprint_name: str | None = None,
    graph_name: str = "EventGraph",
    include_node_details: bool = True,
    include_pin_connections: bool = True,
    trace_execution_flow: bool = True,
    include_full_graph: bool = False,
) -> Dict[str, Any]:
    """Read and summarize one blueprint graph."""
    operation_id = _new_operation_id("analyze_blueprint_graph")
    try:
        identifier, resolved_path = _resolve_blueprint_identifier(
            blueprint_path=blueprint_path,
            blueprint_name=blueprint_name,
        )
    except ValueError as exc:
        return _structured_blueprint_failure(operation_id, "", str(exc))

    result = raw_analyze_blueprint_graph(
        blueprint_path=resolved_path,
        graph_name=graph_name,
        include_node_details=include_node_details,
        include_pin_connections=include_pin_connections,
        trace_execution_flow=trace_execution_flow,
        summary_only=not include_full_graph,
        result_handle=include_full_graph,
    )
    if not _result_success(result):
        body = _result_body(result)
        return _structured_blueprint_failure(
            operation_id,
            identifier,
            body.get("error", "analyze_blueprint_graph failed"),
        )

    body = _result_body(result)
    graph_data = body.get("graph_data") or body.get("result") or {}
    nodes = graph_data.get("nodes") or []
    connections = graph_data.get("connections") or []
    summary = {
        "node_count": body.get("node_count", len(nodes)),
        "connection_count": body.get("connection_count", len(connections)),
        "graph_name": body.get("graph_name") or graph_data.get("graph_name", graph_name),
    }
    payload = {
        "success": True,
        "operation_id": operation_id,
        "domain": "blueprint",
        "targets": [identifier],
        "applied_changes": [],
        "failed_changes": [],
        "post_state": {identifier: summary},
        "verification": {"verified": True, "checks": []},
        "blueprint_path": body.get("blueprint_path", resolved_path),
        "graph_name": summary["graph_name"],
        "node_count": summary["node_count"],
        "connection_count": summary["connection_count"],
    }
    if include_full_graph:
        payload["graph_data"] = graph_data
    return payload


def find_blueprint_nodes(
    blueprint_path: str | None = None,
    blueprint_name: str | None = None,
    graph_name: str = "EventGraph",
    title_filter: str | None = None,
    class_filter: str | None = None,
    node_name_filter: str | None = None,
    pin_name_filter: str | None = None,
    pin_direction: str | None = None,
) -> Dict[str, Any]:
    """Find blueprint graph nodes by title, class, node name, or pin metadata."""
    operation_id = _new_operation_id("find_blueprint_nodes")
    graph_result = analyze_blueprint_graph(
        blueprint_path=blueprint_path,
        blueprint_name=blueprint_name,
        graph_name=graph_name,
        include_node_details=True,
        include_pin_connections=True,
        trace_execution_flow=False,
        include_full_graph=True,
    )
    if not graph_result.get("success"):
        graph_result["operation_id"] = operation_id
        return graph_result

    graph_data = graph_result.get("graph_data") or {}
    nodes = graph_data.get("nodes") or []
    normalized_direction = (pin_direction or "").strip().lower()
    matched_nodes = []
    for node in nodes:
        title = str(node.get("title") or "")
        node_class = str(node.get("class") or "")
        node_name = str(node.get("name") or "")
        pins = node.get("pins") or []

        if title_filter and title_filter.lower() not in title.lower():
            continue
        if class_filter and class_filter.lower() not in node_class.lower():
            continue
        if node_name_filter and node_name_filter.lower() not in node_name.lower():
            continue
        if pin_name_filter:
            filtered_pins = []
            for pin in pins:
                pin_name = str(pin.get("name") or "")
                pin_dir = str(pin.get("direction") or "").lower()
                if pin_name_filter.lower() not in pin_name.lower():
                    continue
                if normalized_direction and pin_dir != normalized_direction:
                    continue
                filtered_pins.append(pin)
            if not filtered_pins:
                continue
            node = dict(node)
            node["matched_pins"] = filtered_pins
        matched_nodes.append(node)

    target = graph_result.get("blueprint_path") or blueprint_path or blueprint_name or ""
    return {
        "success": True,
        "operation_id": operation_id,
        "domain": "blueprint",
        "targets": [target] if target else [],
        "applied_changes": [],
        "failed_changes": [],
        "post_state": {target: {"matched_nodes": matched_nodes}},
        "verification": {"verified": True, "checks": []},
        "blueprint_path": target,
        "graph_name": graph_result.get("graph_name", graph_name),
        "matched_count": len(matched_nodes),
        "nodes": matched_nodes,
    }


def add_blueprint_node(
    blueprint_path: str | None = None,
    blueprint_name: str | None = None,
    node_type: str = "",
    node_params: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Create one blueprint graph node."""
    operation_id = _new_operation_id("add_blueprint_node")
    try:
        identifier, resolved_name = _resolve_blueprint_identifier(
            blueprint_path=blueprint_path,
            blueprint_name=blueprint_name,
        )
    except ValueError as exc:
        return _structured_blueprint_failure(operation_id, "", str(exc))
    if not node_type.strip():
        return _structured_blueprint_failure(
            operation_id, identifier, "node_type must not be empty"
        )

    result = raw_add_blueprint_node(
        blueprint_name=resolved_name,
        node_type=node_type,
        node_params=node_params or {},
    )
    if not _result_success(result):
        body = _result_body(result)
        return _structured_blueprint_failure(
            operation_id,
            identifier,
            body.get("error", "add_blueprint_node failed"),
        )
    body = _result_body(result)
    return {
        "success": True,
        "operation_id": operation_id,
        "domain": "blueprint",
        "targets": [identifier],
        "applied_changes": [
            {
                "target": identifier,
                "field": "node",
                "value": body.get("node_type", node_type),
                "node_id": body.get("node_id"),
            }
        ],
        "failed_changes": [],
        "post_state": {identifier: body},
        "verification": {"verified": True, "checks": []},
        **body,
    }


def connect_blueprint_nodes(
    blueprint_path: str | None = None,
    blueprint_name: str | None = None,
    source_node_id: str = "",
    source_pin_name: str = "",
    target_node_id: str = "",
    target_pin_name: str = "",
    function_name: str | None = None,
) -> Dict[str, Any]:
    """Connect two blueprint graph nodes using the backend K2 schema."""
    operation_id = _new_operation_id("connect_blueprint_nodes")
    try:
        identifier, resolved_name = _resolve_blueprint_identifier(
            blueprint_path=blueprint_path,
            blueprint_name=blueprint_name,
        )
    except ValueError as exc:
        return _structured_blueprint_failure(operation_id, "", str(exc))

    result = raw_connect_nodes(
        blueprint_name=resolved_name,
        source_node_id=source_node_id,
        source_pin_name=source_pin_name,
        target_node_id=target_node_id,
        target_pin_name=target_pin_name,
        function_name=function_name,
    )
    if not _result_success(result):
        body = _result_body(result)
        return _structured_blueprint_failure(
            operation_id,
            identifier,
            body.get("error", "connect_blueprint_nodes failed"),
        )
    body = _result_body(result)
    return {
        "success": True,
        "operation_id": operation_id,
        "domain": "blueprint",
        "targets": [identifier],
        "applied_changes": [{"target": identifier, "field": "connection", "value": body.get("connection")}],
        "failed_changes": [],
        "post_state": {identifier: body},
        "verification": {"verified": True, "checks": []},
        **body,
    }


def set_blueprint_node_property(
    blueprint_path: str | None = None,
    blueprint_name: str | None = None,
    node_id: str = "",
    function_name: str | None = None,
    property_name: str | None = None,
    property_value: Any = None,
    action: str | None = None,
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Set a node property or execute one semantic node-edit action."""
    operation_id = _new_operation_id("set_blueprint_node_property")
    try:
        identifier, resolved_name = _resolve_blueprint_identifier(
            blueprint_path=blueprint_path,
            blueprint_name=blueprint_name,
        )
    except ValueError as exc:
        return _structured_blueprint_failure(operation_id, "", str(exc))

    result = raw_set_node_property(
        blueprint_name=resolved_name,
        node_id=node_id,
        function_name=function_name,
        property_name=property_name,
        property_value=property_value,
        action=action,
        extra=extra,
    )
    if not _result_success(result):
        body = _result_body(result)
        return _structured_blueprint_failure(
            operation_id,
            identifier,
            body.get("error", "set_blueprint_node_property failed"),
        )
    body = _result_body(result)
    return {
        "success": True,
        "operation_id": operation_id,
        "domain": "blueprint",
        "targets": [identifier],
        "applied_changes": [{"target": identifier, "field": property_name or action or "node", "value": property_value}],
        "failed_changes": [],
        "post_state": {identifier: body},
        "verification": {"verified": True, "checks": []},
        **body,
    }


def add_point_light_component_node(
    blueprint_path: str | None = None,
    blueprint_name: str | None = None,
    node_params: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Convenience wrapper around AddComponentByClass for PointLightComponent."""
    params = dict(node_params or {})
    params.setdefault("component_class", "/Script/Engine.PointLightComponent")
    return add_blueprint_node(
        blueprint_path=blueprint_path,
        blueprint_name=blueprint_name,
        node_type="AddComponentByClass",
        node_params=params,
    )


def get_blueprint_variable_details(
    blueprint_path: str | None = None,
    blueprint_name: str | None = None,
    variable_name: str | None = None,
) -> Dict[str, Any]:
    """Read blueprint variable metadata with a consistent input shape."""
    operation_id = _new_operation_id("get_blueprint_variable_details")
    try:
        identifier, resolved_path = _resolve_blueprint_identifier(
            blueprint_path=blueprint_path,
            blueprint_name=blueprint_name,
        )
    except ValueError as exc:
        return _structured_blueprint_failure(operation_id, "", str(exc))
    result = raw_get_blueprint_variable_details(
        blueprint_path=resolved_path,
        variable_name=variable_name,
    )
    if not _result_success(result):
        body = _result_body(result)
        return _structured_blueprint_failure(
            operation_id,
            identifier,
            body.get("error", "get_blueprint_variable_details failed"),
        )
    body = _result_body(result)
    return {
        "success": True,
        "operation_id": operation_id,
        "domain": "blueprint",
        "targets": [identifier],
        "applied_changes": [],
        "failed_changes": [],
        "post_state": {identifier: body},
        "verification": {"verified": True, "checks": []},
        **body,
    }


def get_blueprint_function_details(
    blueprint_path: str | None = None,
    blueprint_name: str | None = None,
    function_name: str | None = None,
    include_graph: bool = True,
) -> Dict[str, Any]:
    """Read blueprint function metadata with a consistent input shape."""
    operation_id = _new_operation_id("get_blueprint_function_details")
    try:
        identifier, resolved_path = _resolve_blueprint_identifier(
            blueprint_path=blueprint_path,
            blueprint_name=blueprint_name,
        )
    except ValueError as exc:
        return _structured_blueprint_failure(operation_id, "", str(exc))
    result = raw_get_blueprint_function_details(
        blueprint_path=resolved_path,
        function_name=function_name,
        include_graph=include_graph,
    )
    if not _result_success(result):
        body = _result_body(result)
        return _structured_blueprint_failure(
            operation_id,
            identifier,
            body.get("error", "get_blueprint_function_details failed"),
        )
    body = _result_body(result)
    return {
        "success": True,
        "operation_id": operation_id,
        "domain": "blueprint",
        "targets": [identifier],
        "applied_changes": [],
        "failed_changes": [],
        "post_state": {identifier: body},
        "verification": {"verified": True, "checks": []},
        **body,
    }
