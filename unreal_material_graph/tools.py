"""Material graph harness tools built on top of the raw material graph backend."""

from __future__ import annotations

from collections import Counter
import time
from typing import Any, Dict, List, Optional

from unreal_backend_tcp.tools import (
    build_material_graph,
    get_material_graph as raw_get_material_graph,
    read_result_handle,
    release_result_handle,
)


def _new_operation_id(action: str) -> str:
    return f"material_graph:{action}:{int(time.time() * 1000)}"


def _graph_check(target: str, field: str, expected: Any, actual: Any) -> Dict[str, Any]:
    return {
        "target": target,
        "field": field,
        "expected": expected,
        "actual": actual,
        "ok": expected == actual,
    }


def _structured_graph_failure(
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
        "domain": "material_graph",
        "targets": [target] if target else [],
        "applied_changes": [],
        "failed_changes": failed_changes
        or [{"target": target, "field": "graph", "error": error}],
        "post_state": post_state or {},
        "verification": {"verified": False, "checks": []},
        "error": error,
    }


def _normalize_graph_asset_path(value: str) -> str:
    normalized = (value or "").strip()
    if not normalized:
        return normalized
    if normalized.startswith("/"):
        return normalized
    return f"/Game/Materials/{normalized}"


def _output_name_from_index(output_index: Any) -> str:
    try:
        return f"Output_{int(output_index)}"
    except (TypeError, ValueError):
        return "Output_0"


def _normalize_connection_schema(
    connection: Dict[str, Any],
    *,
    include_legacy_keys: bool = True,
) -> Dict[str, Any]:
    normalized = dict(connection)
    source = normalized.get("source", normalized.get("from"))
    target = normalized.get("target", normalized.get("to"))
    source_output = normalized.get(
        "source_output",
        normalized.get("from_output", _output_name_from_index(normalized.get("output_index", 0))),
    )
    target_input = normalized.get("target_input", normalized.get("to_input"))

    normalized["source"] = source
    normalized["target"] = target
    normalized["source_output"] = source_output
    normalized["target_input"] = target_input
    if include_legacy_keys:
        normalized["from"] = source
        normalized["to"] = target
        normalized["from_output"] = source_output
        normalized["to_input"] = target_input
    return normalized


def _normalize_property_connection_schema(
    property_name: str,
    payload: Dict[str, Any],
    *,
    include_legacy_keys: bool = True,
) -> Dict[str, Any]:
    normalized = dict(payload)
    source = normalized.get("source", normalized.get("node_id"))
    source_output = normalized.get(
        "source_output",
        normalized.get("from_output", _output_name_from_index(normalized.get("output_index", 0))),
    )
    normalized["source"] = source
    normalized["target"] = "Material"
    normalized["source_output"] = source_output
    normalized["target_input"] = property_name
    normalized["node_id"] = source
    try:
        normalized["output_index"] = int(
            normalized.get("output_index", source_output.rsplit("_", 1)[-1])
        )
    except (TypeError, ValueError):
        normalized["output_index"] = 0
    if include_legacy_keys:
        normalized["from"] = source
        normalized["to"] = "Material"
        normalized["from_output"] = source_output
        normalized["to_input"] = property_name
    return normalized


def _canonical_property_connection_payload(
    property_connections: Optional[Dict[str, Any]]
) -> Dict[str, Dict[str, Any]]:
    canonical: Dict[str, Dict[str, Any]] = {}
    for property_name, payload in (property_connections or {}).items():
        if payload is None:
            continue
        normalized = _normalize_property_connection_schema(
            property_name,
            payload if isinstance(payload, dict) else {"source": payload},
            include_legacy_keys=False,
        )
        canonical[property_name] = {
            "source": normalized.get("source"),
            "source_output": normalized.get("source_output"),
        }
    return canonical


def _normalize_graph_payload(
    result: Dict[str, Any],
    *,
    include_legacy_connection_keys: bool,
) -> Dict[str, Any]:
    nodes = list(result.get("nodes") or [])
    connections = [
        _normalize_connection_schema(
            connection,
            include_legacy_keys=include_legacy_connection_keys,
        )
        for connection in (result.get("connections") or [])
        if isinstance(connection, dict)
    ]
    property_connections_raw = result.get("property_connections") or {}
    property_connections = {
        property_name: _normalize_property_connection_schema(
            property_name,
            payload if isinstance(payload, dict) else {},
            include_legacy_keys=include_legacy_connection_keys,
        )
        for property_name, payload in property_connections_raw.items()
        if isinstance(property_name, str) and isinstance(payload, dict)
    }
    return {
        "nodes": nodes,
        "connections": connections,
        "property_connections": property_connections,
    }


def get_material_graph_harness_info() -> Dict[str, Any]:
    """Describe the current material graph harness boundary."""
    payload = {
        "domain": "material_graph",
        "backend": "internal_tcp_backend",
        "target_backend": "cpp_primary",
        "status": "available_via_internal_backend",
        "supports": [
            "graph_read",
            "graph_analysis",
            "material_node_creation",
            "graph_connections",
            "graph_patch",
            "property_connection_patch",
            "recipe_builds",
        ],
    }
    return {
        "success": True,
        "operation_id": _new_operation_id("get_material_graph_harness_info"),
        "domain": "material_graph",
        "targets": ["material_graph_harness"],
        "applied_changes": [],
        "failed_changes": [],
        "post_state": {"material_graph_harness": payload},
        "verification": {"verified": True, "checks": []},
        **payload,
    }


def _load_full_graph(asset_path: str) -> Dict[str, Any]:
    response = raw_get_material_graph(
        asset_path=asset_path,
        summary_only=False,
        result_handle=True,
    )
    handle = response.get("result_handle")
    if handle:
        fetched = read_result_handle(handle)
        release_result_handle(handle)
        if fetched.get("success") and isinstance(fetched.get("result"), dict):
            return fetched["result"]
    return response


def analyze_material_graph(
    asset_path: str,
    include_full_graph: bool = False,
    include_legacy_connection_keys: bool = True,
) -> Dict[str, Any]:
    """Read and summarize a material graph for diagnostics and planning."""
    operation_id = _new_operation_id("analyze_material_graph")
    graph = _load_full_graph(asset_path)
    if graph.get("status") == "error":
        return _structured_graph_failure(
            operation_id,
            asset_path,
            graph.get("error", "graph analysis failed"),
        )

    result = graph.get("result") or {}
    normalized_graph = _normalize_graph_payload(
        result,
        include_legacy_connection_keys=include_legacy_connection_keys,
    )
    nodes = normalized_graph["nodes"]
    connections = normalized_graph["connections"]
    property_connections = normalized_graph["property_connections"]
    asset_path_resolved = result.get("path") or asset_path
    requested_asset_path = _normalize_graph_asset_path(asset_path)
    resolved_asset_path = _normalize_graph_asset_path(asset_path_resolved)
    node_types = Counter(
        node.get("type", "Unknown") for node in nodes if isinstance(node, dict)
    )
    checks = [
        _graph_check(asset_path, "nodes_loaded", True, isinstance(nodes, list)),
        _graph_check(asset_path, "connections_loaded", True, isinstance(connections, list)),
        _graph_check(asset_path, "asset_path", requested_asset_path, resolved_asset_path),
    ]
    verification_mode = "structural"
    if "node_count" in result:
        verification_mode = "backend_summary"
        checks.append(
            _graph_check(asset_path, "node_count", result.get("node_count"), len(nodes))
        )
    if "connection_count" in result:
        verification_mode = "backend_summary"
        checks.append(
            _graph_check(
                asset_path,
                "connection_count",
                result.get("connection_count"),
                len(connections),
            )
        )
    if "property_connection_count" in result:
        verification_mode = "backend_summary"
        checks.append(
            _graph_check(
                asset_path,
                "property_connection_count",
                result.get("property_connection_count"),
                len(property_connections),
            )
        )
    verified = all(item["ok"] for item in checks)

    payload: Dict[str, Any] = {
        "success": bool(result.get("success", False)),
        "operation_id": operation_id,
        "domain": "material_graph",
        "targets": [asset_path],
        "applied_changes": [],
        "failed_changes": [],
        "post_state": {
            asset_path: {
                "asset_type": result.get("asset_type"),
                "node_count": len(nodes),
                "connection_count": len(connections),
                "property_connection_count": len(property_connections),
                "node_type_counts": dict(sorted(node_types.items())),
                "property_connections": sorted(property_connections.keys()),
            }
        },
        "verification": {
            "verified": verified,
            "checks": checks,
            "mode": verification_mode,
        },
        "asset_path": asset_path_resolved,
        "asset_type": result.get("asset_type"),
        "node_count": len(nodes),
        "connection_count": len(connections),
        "property_connection_count": len(property_connections),
        "node_type_counts": dict(sorted(node_types.items())),
        "property_connections": property_connections if include_full_graph else sorted(property_connections.keys()),
    }
    if include_full_graph:
        payload["nodes"] = nodes
        payload["connections"] = connections
        payload["graph"] = {
            "nodes": nodes,
            "connections": connections,
            "property_connections": property_connections,
        }
    return payload


def _count_graph_property_connections(property_connections: Dict[str, Any]) -> int:
    return len(property_connections)


def _count_non_material_connections(connections: List[Dict[str, Any]]) -> int:
    return sum(1 for item in connections if item.get("target") != "Material")


def _count_property_connection_updates(property_connections: Dict[str, Any]) -> int:
    return len([item for item in property_connections.values() if item.get("source")])


def _run_graph_patch(
    *,
    operation_name: str,
    material_name: str,
    add_nodes: Optional[List[Dict[str, Any]]] = None,
    add_connections: Optional[List[Dict[str, Any]]] = None,
    properties: Optional[Dict[str, Any]] = None,
    property_connections: Optional[Dict[str, Any]] = None,
    delete_nodes: Optional[List[str]] = None,
    disconnect_connections: Optional[List[Dict[str, Any]]] = None,
    disconnect_properties: Optional[List[str]] = None,
    compile: bool = True,
    include_full_graph: bool = False,
    include_legacy_connection_keys: bool = True,
) -> Dict[str, Any]:
    operation_id = _new_operation_id(operation_name)
    requested_asset_path = _normalize_graph_asset_path(material_name)

    pre_graph = analyze_material_graph(
        material_name,
        include_full_graph=False,
        include_legacy_connection_keys=include_legacy_connection_keys,
    )
    pre_node_count = pre_graph.get("node_count") if pre_graph.get("success") else None
    pre_connection_count = (
        pre_graph.get("connection_count") if pre_graph.get("success") else None
    )
    pre_property_connections = (
        pre_graph.get("property_connections")
        if pre_graph.get("success") and isinstance(pre_graph.get("property_connections"), list) is False
        else {}
    )
    if not isinstance(pre_property_connections, dict):
        pre_property_connections = {}

    normalized_connections = [
        _normalize_connection_schema(item, include_legacy_keys=False)
        for item in (add_connections or [])
    ]
    normalized_disconnect_connections = [
        _normalize_connection_schema(item, include_legacy_keys=False)
        for item in (disconnect_connections or [])
    ]
    normalized_property_connections = _canonical_property_connection_payload(
        property_connections
    )
    result = build_material_graph(
        material_name=material_name,
        nodes=add_nodes or [],
        connections=normalized_connections or None,
        properties=properties,
        property_connections=normalized_property_connections or None,
        delete_nodes=delete_nodes or None,
        disconnect_connections=normalized_disconnect_connections or None,
        disconnect_properties=disconnect_properties or None,
        compile=compile,
    )
    if result.get("status") == "error":
        return _structured_graph_failure(
            operation_id,
            material_name,
            result.get("error", "graph patch failed"),
        )

    post_graph = analyze_material_graph(
        material_name,
        include_full_graph=include_full_graph,
        include_legacy_connection_keys=include_legacy_connection_keys,
    )
    if not post_graph.get("success"):
        post_graph["operation_id"] = operation_id
        return post_graph

    builder_result = result.get("result") or {}
    created_node_count = builder_result.get("node_count", len(add_nodes or []))
    created_connection_count = builder_result.get(
        "connection_count",
        len(normalized_connections) + len(normalized_property_connections),
    )
    requested_node_count = len(add_nodes or [])
    requested_connection_count = len(normalized_connections)
    requested_property_connection_count = len(normalized_property_connections)

    checks = [
        _graph_check(material_name, "asset_path", requested_asset_path, _normalize_graph_asset_path(post_graph.get("asset_path", ""))),
        _graph_check(material_name, "created_nodes", requested_node_count, created_node_count),
        _graph_check(
            material_name,
            "created_connections",
            requested_connection_count + requested_property_connection_count,
            created_connection_count,
        ),
    ]

    if pre_node_count is not None:
        expected_post_nodes = (
            pre_node_count - len(delete_nodes or []) + requested_node_count
        )
        checks.append(
            _graph_check(
                material_name,
                "post_node_count",
                expected_post_nodes,
                post_graph.get("node_count"),
            )
        )
    if pre_connection_count is not None:
        expected_post_connections = (
            pre_connection_count
            - _count_non_material_connections(normalized_disconnect_connections)
            + _count_non_material_connections(normalized_connections)
        )
        checks.append(
            _graph_check(
                material_name,
                "post_connection_count",
                expected_post_connections,
                post_graph.get("connection_count"),
            )
        )
    post_property_connections = post_graph.get("property_connections", {})
    if isinstance(post_property_connections, list):
        post_property_connections = {}
    if pre_property_connections:
        expected_post_property_count = len(pre_property_connections)
        for property_name in disconnect_properties or []:
            if property_name in pre_property_connections:
                expected_post_property_count -= 1
        for property_name in normalized_property_connections:
            if property_name not in pre_property_connections:
                expected_post_property_count += 1
        checks.append(
            _graph_check(
                material_name,
                "post_property_connection_count",
                expected_post_property_count,
                _count_graph_property_connections(post_property_connections),
            )
        )

    applied_changes = [
        {
            "target": material_name,
            "field": "node",
            "value": node.get("type"),
            "node_id": node.get("id"),
        }
        for node in (add_nodes or [])
    ]
    applied_changes.extend(
        {
            "target": material_name,
            "field": "connection",
            "value": {
                "source": connection.get("source"),
                "target": connection.get("target"),
                "source_output": connection.get("source_output"),
                "target_input": connection.get("target_input"),
            },
        }
        for connection in normalized_connections
    )
    applied_changes.extend(
        {
            "target": material_name,
            "field": f"property_connection.{property_name}",
            "value": payload,
        }
        for property_name, payload in normalized_property_connections.items()
    )
    applied_changes.extend(
        {
            "target": material_name,
            "field": "delete_node",
            "value": node_id,
        }
        for node_id in (delete_nodes or [])
    )
    applied_changes.extend(
        {
            "target": material_name,
            "field": "disconnect_connection",
            "value": connection,
        }
        for connection in normalized_disconnect_connections
    )
    applied_changes.extend(
        {
            "target": material_name,
            "field": "disconnect_property",
            "value": property_name,
        }
        for property_name in (disconnect_properties or [])
    )

    verified = all(item["ok"] for item in checks)
    return {
        "success": verified,
        "operation_id": operation_id,
        "domain": "material_graph",
        "targets": [material_name],
        "applied_changes": applied_changes,
        "failed_changes": [],
        "post_state": {material_name: post_graph},
        "verification": {"verified": verified, "checks": checks},
        "summary": post_graph,
        "result": builder_result,
        "graph": post_graph.get("graph") if include_full_graph else None,
    }


def create_material_graph_recipe(
    material_name: str,
    nodes: List[Dict[str, Any]],
    connections: Optional[List[Dict[str, Any]]] = None,
    properties: Optional[Dict[str, Any]] = None,
    property_connections: Optional[Dict[str, Any]] = None,
    delete_nodes: Optional[List[str]] = None,
    disconnect_connections: Optional[List[Dict[str, Any]]] = None,
    disconnect_properties: Optional[List[str]] = None,
    compile: bool = True,
    include_full_graph: bool = False,
    include_legacy_connection_keys: bool = True,
) -> Dict[str, Any]:
    """Build or patch a material graph from one recipe payload."""
    return _run_graph_patch(
        operation_name="create_material_graph_recipe",
        material_name=material_name,
        add_nodes=nodes,
        add_connections=connections,
        properties=properties,
        property_connections=property_connections,
        delete_nodes=delete_nodes,
        disconnect_connections=disconnect_connections,
        disconnect_properties=disconnect_properties,
        compile=compile,
        include_full_graph=include_full_graph,
        include_legacy_connection_keys=include_legacy_connection_keys,
    )


def connect_material_nodes(
    material_name: str,
    connections: List[Dict[str, Any]],
    nodes: Optional[List[Dict[str, Any]]] = None,
    property_connections: Optional[Dict[str, Any]] = None,
    compile: bool = True,
    include_full_graph: bool = False,
    include_legacy_connection_keys: bool = True,
) -> Dict[str, Any]:
    """Apply node and property connections, optionally creating nodes in the same transaction."""
    result = _run_graph_patch(
        operation_name="connect_material_nodes",
        material_name=material_name,
        add_nodes=nodes or [],
        add_connections=connections,
        property_connections=property_connections,
        compile=compile,
        include_full_graph=include_full_graph,
        include_legacy_connection_keys=include_legacy_connection_keys,
    )
    result["operation_id"] = _new_operation_id("connect_material_nodes")
    return result


def set_material_graph_property_connections(
    material_name: str,
    property_connections: Dict[str, Dict[str, Any]],
    disconnect_properties: Optional[List[str]] = None,
    compile: bool = True,
    include_full_graph: bool = False,
    include_legacy_connection_keys: bool = True,
) -> Dict[str, Any]:
    """Patch only material property connections without rebuilding the whole graph."""
    return _run_graph_patch(
        operation_name="set_material_graph_property_connections",
        material_name=material_name,
        property_connections=property_connections,
        disconnect_properties=disconnect_properties,
        compile=compile,
        include_full_graph=include_full_graph,
        include_legacy_connection_keys=include_legacy_connection_keys,
    )


def patch_material_graph(
    material_name: str,
    add_nodes: Optional[List[Dict[str, Any]]] = None,
    add_connections: Optional[List[Dict[str, Any]]] = None,
    delete_nodes: Optional[List[str]] = None,
    disconnect_connections: Optional[List[Dict[str, Any]]] = None,
    property_connections: Optional[Dict[str, Dict[str, Any]]] = None,
    disconnect_properties: Optional[List[str]] = None,
    properties: Optional[Dict[str, Any]] = None,
    compile: bool = True,
    include_full_graph: bool = False,
    include_legacy_connection_keys: bool = True,
) -> Dict[str, Any]:
    """Patch a material graph with add/delete/disconnect operations."""
    return _run_graph_patch(
        operation_name="patch_material_graph",
        material_name=material_name,
        add_nodes=add_nodes,
        add_connections=add_connections,
        delete_nodes=delete_nodes,
        disconnect_connections=disconnect_connections,
        property_connections=property_connections,
        disconnect_properties=disconnect_properties,
        properties=properties,
        compile=compile,
        include_full_graph=include_full_graph,
        include_legacy_connection_keys=include_legacy_connection_keys,
    )
