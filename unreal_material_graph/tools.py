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


def _normalize_graph_asset_path(value: str) -> str:
    normalized = (value or "").strip()
    if not normalized:
        return normalized
    if normalized.startswith("/"):
        return normalized
    return f"/Game/Materials/{normalized}"


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


def create_material_graph_recipe(
    material_name: str,
    nodes: List[Dict[str, Any]],
    connections: Optional[List[Dict[str, Any]]] = None,
    properties: Optional[Dict[str, Any]] = None,
    compile: bool = True,
) -> Dict[str, Any]:
    """Build a material graph from a recipe payload."""
    operation_id = _new_operation_id("create_material_graph_recipe")
    result = build_material_graph(
        material_name=material_name,
        nodes=nodes,
        connections=connections,
        properties=properties,
        compile=compile,
    )
    if result.get("status") == "error":
        return {
            "success": False,
            "operation_id": operation_id,
            "domain": "material_graph",
            "targets": [material_name],
            "applied_changes": [],
            "failed_changes": [
                {
                    "target": material_name,
                    "field": "graph",
                    "error": result.get("error", "graph build failed"),
                }
            ],
            "post_state": {},
            "verification": {"verified": False, "checks": []},
            "error": result.get("error", "graph build failed"),
        }
    graph_summary = analyze_material_graph(material_name)
    requested_asset_path = _normalize_graph_asset_path(material_name)
    checks = [
        _graph_check(
            material_name, "node_count", len(nodes), graph_summary.get("node_count")
        ),
        _graph_check(
            material_name,
            "asset_path",
            requested_asset_path,
            _normalize_graph_asset_path(graph_summary.get("asset_path", "")),
        ),
    ]
    if connections:
        checks.append(
            _graph_check(
                material_name,
                "requested_connections",
                len(connections),
                result.get("result", {}).get("connection_count"),
            )
        )
    verified = all(item["ok"] for item in checks) and bool(graph_summary.get("success"))
    return {
        "success": verified,
        "operation_id": operation_id,
        "domain": "material_graph",
        "targets": [material_name],
        "applied_changes": [
            {
                "target": material_name,
                "field": "node",
                "value": node.get("type"),
                "node_id": node.get("id"),
            }
            for node in nodes
        ],
        "failed_changes": [],
        "post_state": {material_name: graph_summary},
        "verification": {"verified": verified, "checks": checks},
        "summary": graph_summary,
        "result": result.get("result"),
    }


def connect_material_nodes(
    material_name: str,
    connections: List[Dict[str, Any]],
    nodes: Optional[List[Dict[str, Any]]] = None,
    compile: bool = True,
) -> Dict[str, Any]:
    """Apply a connection recipe, optionally creating nodes in the same transaction."""
    result = create_material_graph_recipe(
        material_name=material_name,
        nodes=nodes or [],
        connections=connections,
        compile=compile,
    )
    result["operation_id"] = _new_operation_id("connect_material_nodes")
    return result


def analyze_material_graph(asset_path: str) -> Dict[str, Any]:
    """Read and summarize a material graph for diagnostics and planning."""
    operation_id = _new_operation_id("analyze_material_graph")
    graph = _load_full_graph(asset_path)
    if graph.get("status") == "error":
        return {
            "success": False,
            "operation_id": operation_id,
            "domain": "material_graph",
            "targets": [asset_path],
            "applied_changes": [],
            "failed_changes": [
                {
                    "target": asset_path,
                    "field": "graph",
                    "error": graph.get("error", "graph analysis failed"),
                }
            ],
            "post_state": {},
            "verification": {"verified": False, "checks": []},
            "error": graph.get("error", "graph analysis failed"),
        }

    result = graph.get("result") or {}
    nodes = result.get("nodes") or []
    connections = result.get("connections") or []
    property_connections = result.get("property_connections") or {}
    asset_path_resolved = result.get("path") or asset_path
    requested_asset_path = _normalize_graph_asset_path(asset_path)
    resolved_asset_path = _normalize_graph_asset_path(asset_path_resolved)
    node_types = Counter(
        node.get("type", "Unknown") for node in nodes if isinstance(node, dict)
    )
    checks = [
        _graph_check(
            asset_path,
            "nodes_loaded",
            True,
            isinstance(nodes, list),
        ),
        _graph_check(
            asset_path,
            "connections_loaded",
            True,
            isinstance(connections, list),
        ),
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
                len(property_connections) if isinstance(property_connections, dict) else 0,
            )
        )
    verified = all(item["ok"] for item in checks)
    return {
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
                "node_type_counts": dict(sorted(node_types.items())),
                "property_connections": sorted(property_connections.keys())
                if isinstance(property_connections, dict)
                else [],
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
        "node_type_counts": dict(sorted(node_types.items())),
        "property_connections": sorted(property_connections.keys())
        if isinstance(property_connections, dict)
        else [],
    }
