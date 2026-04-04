"""FastMCP entry point for the new harness orchestrator."""

from __future__ import annotations

import logging
import os
import time
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, Dict

from fastmcp import FastMCP

from .catalog import get_domain, list_domains, route_text
from unreal_asset.tools import (
    create_asset_with_properties as asset_create_asset_with_properties,
    duplicate_asset_with_overrides as asset_duplicate_asset_with_overrides,
    ensure_asset_with_properties as asset_ensure_asset_with_properties,
    ensure_folder as asset_ensure_folder,
    get_asset_harness_info,
    import_fbx_asset,
    import_texture_asset,
    move_asset_batch as asset_move_asset_batch,
    query_assets_summary as asset_query_assets_summary,
    update_asset_properties as asset_update_asset_properties,
)
from unreal_diagnostics.tools import (
    dev_launch_editor_and_wait_ready,
    get_commandlet_runtime_status,
    get_editor_ready_state,
    get_editor_process_status,
    get_harness_health,
    get_transport_port_status,
    get_runtime_policy,
    get_token_usage_summary,
    get_unreal_python_status,
    wait_for_editor_ready,
)
from unreal_material.tools import (
    create_material_asset as material_create_material_asset,
    create_material_instance_asset as material_create_material_instance_asset,
    get_material_harness_info,
    get_material_instance_parameter_names as material_get_material_instance_parameter_names,
    set_material_instance_scalar_parameter as material_set_material_instance_scalar_parameter,
    set_material_instance_texture_parameter as material_set_material_instance_texture_parameter,
    set_material_instance_vector_parameter as material_set_material_instance_vector_parameter,
    update_material_instance_parameters_and_verify as material_update_material_instance_parameters_and_verify,
    update_material_instance_properties as material_update_material_instance_properties,
)
from unreal_material_graph.tools import (
    analyze_material_graph as material_graph_analyze_material_graph,
    connect_material_nodes as material_graph_connect_material_nodes,
    create_material_graph_recipe as material_graph_create_material_graph_recipe,
    get_material_graph_harness_info,
)
from unreal_scene.tools import (
    apply_scene_actor_batch as scene_apply_scene_actor_batch,
    aim_actor_at as scene_aim_actor_at,
    create_spot_light_ring as scene_create_spot_light_ring,
    get_scene_backend_status,
    get_scene_harness_info,
    query_scene_actors as scene_query_scene_actors,
    query_scene_lights as scene_query_scene_lights,
    set_post_process_overrides as scene_set_post_process_overrides,
    set_scene_light_intensity as scene_set_scene_light_intensity,
    spawn_actor_with_defaults as scene_spawn_actor_with_defaults,
)


_CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s",
    handlers=[
        logging.FileHandler(os.path.join(_CURRENT_DIR, "unreal_orchestrator.log"))
    ],
)
logger = logging.getLogger("UnrealOrchestrator")


ENABLE_DEV_TOOLS = os.environ.get("UNREAL_MCP_ENABLE_DEV_TOOLS", "0") == "1"
ENABLE_EXTENDED_TOOLS = os.environ.get("UNREAL_MCP_ENABLE_EXTENDED_TOOLS", "0") == "1"


def _new_orchestrator_operation_id(action: str) -> str:
    return f"orchestrator:{action}:{int(time.time() * 1000)}"


def _compact_preflight(preflight: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "ready": bool(preflight.get("ready", False)),
        "transport_ok": bool(preflight.get("transport_ok", False)),
        "python_ready": bool(preflight.get("python_ready", False)),
        "current_level_summary": preflight.get("current_level_summary"),
        "recommended_action": preflight.get("recommended_action"),
    }


def _result_success(result: Any) -> bool:
    if not isinstance(result, dict):
        return True
    if "success" in result:
        return bool(result.get("success"))
    if result.get("status") == "error":
        return False
    if isinstance(result.get("result"), dict):
        return bool(result["result"].get("success", result.get("status") == "success"))
    return bool(result.get("status") == "success")


def _summarize_result(result: Any) -> Any:
    if not isinstance(result, dict):
        return result
    preferred_keys = (
        "operation_id",
        "domain",
        "targets",
        "summary",
        "items",
        "applied_changes",
        "failed_changes",
        "post_state",
        "verification",
    )
    if "status" in result and isinstance(result.get("result"), dict):
        inner = result["result"]
        summary: Dict[str, Any] = {
            "success": bool(inner.get("success", result.get("status") == "success"))
        }
        for key in preferred_keys:
            if key in inner:
                summary[key] = inner[key]
        for key in (
            "count",
            "returned_count",
            "total_count",
            "offset",
            "limit",
            "path",
            "asset_path",
            "level_path",
        ):
            if key in inner:
                summary[key] = inner[key]
        for list_key in ("assets", "actors", "lights"):
            if list_key in inner:
                summary[list_key] = inner[list_key]
        return summary
    summary: Dict[str, Any] = {"success": bool(result.get("success", False))}
    for key in (
        "domain",
        "asset_path",
        "asset_name",
        "asset_class",
        "parameter_name",
        "changed",
        "operation_id",
        "targets",
        "summary",
        "items",
        "applied_changes",
        "failed_changes",
        "post_state",
        "verification",
        "failed_properties",
        "modified_properties",
        "error",
        "message",
    ):
        if key in result:
            summary[key] = result[key]
    if len(summary) == 1:
        return result
    return summary


def _input_error_result(operation: str, error: str) -> Dict[str, Any]:
    domain = operation.split(".", 1)[0] if "." in operation else operation
    return {
        "success": False,
        "operation_id": _new_orchestrator_operation_id(operation.replace(".", "_")),
        "domain": domain,
        "targets": [],
        "applied_changes": [],
        "failed_changes": [{"field": "input", "error": error}],
        "post_state": {},
        "verification": {"verified": False, "checks": []},
        "error": error,
    }


def _guard_live_editor_call(
    operation: str,
    func,
    *args,
    wait_for_ready: bool = True,
    ready_timeout_seconds: int = 120,
    ready_poll_seconds: int = 5,
    debug: bool = False,
    **kwargs,
) -> Dict[str, Any]:
    preflight = (
        wait_for_editor_ready(
            timeout_seconds=ready_timeout_seconds,
            poll_seconds=ready_poll_seconds,
            debug=debug,
        )
        if wait_for_ready
        else get_editor_ready_state(debug=debug)
    )

    if not preflight.get("ready"):
        payload = {
            "success": False,
            "operation": operation,
            "ready": False,
            "recommended_action": preflight.get("recommended_action"),
            "error": "Editor is not ready for this live-editor operation",
        }
        if debug:
            payload["preflight"] = preflight
        else:
            payload["preflight_summary"] = _compact_preflight(preflight)
        return payload

    try:
        result = func(*args, **kwargs)
    except ValueError as exc:
        result = _input_error_result(operation, str(exc))
    payload = {
        "success": _result_success(result),
        "operation": operation,
        "ready": True,
        "recommended_action": preflight.get("recommended_action"),
    }
    if debug:
        payload["preflight"] = preflight
        payload["result"] = result
    else:
        payload["preflight_summary"] = _compact_preflight(preflight)
        payload["result_summary"] = _summarize_result(result)
    return payload


def set_scene_light_intensity(
    actor_name: str,
    intensity: float,
    unit: str = "Unitless",
    mobility: str | None = None,
    wait_for_ready: bool = True,
    ready_timeout_seconds: int = 120,
    ready_poll_seconds: int = 5,
) -> Dict[str, Any]:
    """Guarded scene light intensity update with automatic editor readiness preflight."""
    return _guard_live_editor_call(
        "scene.set_scene_light_intensity",
        scene_set_scene_light_intensity,
        actor_name,
        intensity,
        unit,
        mobility,
        wait_for_ready=wait_for_ready,
        ready_timeout_seconds=ready_timeout_seconds,
        ready_poll_seconds=ready_poll_seconds,
    )


def create_spot_light_ring(
    center: Dict[str, float],
    radius: float,
    z: float,
    count: int,
    target: Dict[str, float],
    intensity: float,
    intensity_unit: str = "Candelas",
    mobility: str = "Movable",
    name_prefix: str = "MCP_RingSpot",
    replace_existing: bool = True,
    wait_for_ready: bool = True,
    ready_timeout_seconds: int = 120,
    ready_poll_seconds: int = 5,
) -> Dict[str, Any]:
    """Guarded spotlight ring creation with automatic editor readiness preflight."""
    return _guard_live_editor_call(
        "scene.create_spot_light_ring",
        scene_create_spot_light_ring,
        center,
        radius,
        z,
        count,
        target,
        intensity,
        intensity_unit,
        mobility,
        name_prefix,
        replace_existing,
        wait_for_ready=wait_for_ready,
        ready_timeout_seconds=ready_timeout_seconds,
        ready_poll_seconds=ready_poll_seconds,
    )


def apply_scene_actor_batch(
    actor_specs: list[Dict[str, Any]],
    wait_for_ready: bool = True,
    ready_timeout_seconds: int = 120,
    ready_poll_seconds: int = 5,
) -> Dict[str, Any]:
    """Guarded batch actor recipe command for scene setup workflows."""
    return _guard_live_editor_call(
        "scene.apply_scene_actor_batch",
        scene_apply_scene_actor_batch,
        actor_specs,
        wait_for_ready=wait_for_ready,
        ready_timeout_seconds=ready_timeout_seconds,
        ready_poll_seconds=ready_poll_seconds,
    )


def query_scene_actors(
    actor_class: str | None = None,
    name_filter: str | None = None,
    limit: int = 20,
    wait_for_ready: bool = True,
    ready_timeout_seconds: int = 120,
    ready_poll_seconds: int = 5,
) -> Dict[str, Any]:
    """Guarded compact scene actor query."""
    return _guard_live_editor_call(
        "scene.query_scene_actors",
        scene_query_scene_actors,
        actor_class,
        name_filter,
        limit,
        wait_for_ready=wait_for_ready,
        ready_timeout_seconds=ready_timeout_seconds,
        ready_poll_seconds=ready_poll_seconds,
    )


def query_scene_lights(
    limit: int = 20,
    wait_for_ready: bool = True,
    ready_timeout_seconds: int = 120,
    ready_poll_seconds: int = 5,
) -> Dict[str, Any]:
    """Guarded compact scene light query."""
    return _guard_live_editor_call(
        "scene.query_scene_lights",
        scene_query_scene_lights,
        limit,
        wait_for_ready=wait_for_ready,
        ready_timeout_seconds=ready_timeout_seconds,
        ready_poll_seconds=ready_poll_seconds,
    )


def aim_actor_at(
    actor_name: str,
    target: Dict[str, float],
    preserve_roll: bool = True,
    roll: float | None = None,
    wait_for_ready: bool = True,
    ready_timeout_seconds: int = 120,
    ready_poll_seconds: int = 5,
) -> Dict[str, Any]:
    """Guarded actor aiming command with readback verification."""
    return _guard_live_editor_call(
        "scene.aim_actor_at",
        scene_aim_actor_at,
        actor_name,
        target,
        preserve_roll,
        roll,
        wait_for_ready=wait_for_ready,
        ready_timeout_seconds=ready_timeout_seconds,
        ready_poll_seconds=ready_poll_seconds,
    )


def set_post_process_overrides(
    actor_name: str,
    overrides: Dict[str, Any],
    wait_for_ready: bool = True,
    ready_timeout_seconds: int = 120,
    ready_poll_seconds: int = 5,
) -> Dict[str, Any]:
    """Guarded post-process override update with verification."""
    return _guard_live_editor_call(
        "scene.set_post_process_overrides",
        scene_set_post_process_overrides,
        actor_name,
        overrides,
        wait_for_ready=wait_for_ready,
        ready_timeout_seconds=ready_timeout_seconds,
        ready_poll_seconds=ready_poll_seconds,
    )


def spawn_actor_with_defaults(
    actor_class: str,
    name: str | None = None,
    location: Dict[str, float] | None = None,
    rotation: Dict[str, float] | None = None,
    scale: Dict[str, float] | None = None,
    actor_properties: Dict[str, Any] | None = None,
    root_component_properties: Dict[str, Any] | None = None,
    replace_existing: bool = False,
    wait_for_ready: bool = True,
    ready_timeout_seconds: int = 120,
    ready_poll_seconds: int = 5,
) -> Dict[str, Any]:
    """Guarded actor spawn recipe with default property application."""
    return _guard_live_editor_call(
        "scene.spawn_actor_with_defaults",
        scene_spawn_actor_with_defaults,
        actor_class,
        name,
        location,
        rotation,
        scale,
        actor_properties,
        root_component_properties,
        replace_existing,
        wait_for_ready=wait_for_ready,
        ready_timeout_seconds=ready_timeout_seconds,
        ready_poll_seconds=ready_poll_seconds,
    )


def ensure_asset_with_properties(
    asset_type: str,
    name: str,
    path: str = "/Game/",
    properties: Dict[str, Any] | None = None,
    wait_for_ready: bool = True,
    ready_timeout_seconds: int = 120,
    ready_poll_seconds: int = 5,
) -> Dict[str, Any]:
    """Guarded asset ensure workflow that creates or updates in one call."""
    return _guard_live_editor_call(
        "asset.ensure_asset_with_properties",
        asset_ensure_asset_with_properties,
        asset_type,
        name,
        path,
        properties,
        wait_for_ready=wait_for_ready,
        ready_timeout_seconds=ready_timeout_seconds,
        ready_poll_seconds=ready_poll_seconds,
    )


def query_assets_summary(
    path: str = "/Game/",
    asset_class: str | None = None,
    name_filter: str | None = None,
    limit: int = 20,
    offset: int = 0,
    wait_for_ready: bool = True,
    ready_timeout_seconds: int = 120,
    ready_poll_seconds: int = 5,
) -> Dict[str, Any]:
    """Guarded compact asset query."""
    return _guard_live_editor_call(
        "asset.query_assets_summary",
        asset_query_assets_summary,
        path,
        asset_class,
        name_filter,
        limit,
        offset,
        wait_for_ready=wait_for_ready,
        ready_timeout_seconds=ready_timeout_seconds,
        ready_poll_seconds=ready_poll_seconds,
    )


def ensure_folder(
    path: str,
    wait_for_ready: bool = True,
    ready_timeout_seconds: int = 120,
    ready_poll_seconds: int = 5,
) -> Dict[str, Any]:
    """Guarded folder ensure workflow for asset paths."""
    return _guard_live_editor_call(
        "asset.ensure_folder",
        asset_ensure_folder,
        path,
        wait_for_ready=wait_for_ready,
        ready_timeout_seconds=ready_timeout_seconds,
        ready_poll_seconds=ready_poll_seconds,
    )


def duplicate_asset_with_overrides(
    source_asset_path: str,
    destination_path: str,
    new_name: str,
    properties: Dict[str, Any] | None = None,
    wait_for_ready: bool = True,
    ready_timeout_seconds: int = 120,
    ready_poll_seconds: int = 5,
) -> Dict[str, Any]:
    """Guarded asset duplication with optional property overrides."""
    return _guard_live_editor_call(
        "asset.duplicate_asset_with_overrides",
        asset_duplicate_asset_with_overrides,
        source_asset_path,
        destination_path,
        new_name,
        properties,
        wait_for_ready=wait_for_ready,
        ready_timeout_seconds=ready_timeout_seconds,
        ready_poll_seconds=ready_poll_seconds,
    )


def move_asset_batch(
    items: list[Dict[str, str]],
    wait_for_ready: bool = True,
    ready_timeout_seconds: int = 120,
    ready_poll_seconds: int = 5,
) -> Dict[str, Any]:
    """Guarded batch asset move workflow."""
    return _guard_live_editor_call(
        "asset.move_asset_batch",
        asset_move_asset_batch,
        items,
        wait_for_ready=wait_for_ready,
        ready_timeout_seconds=ready_timeout_seconds,
        ready_poll_seconds=ready_poll_seconds,
    )


def create_asset_with_properties(
    asset_type: str,
    name: str,
    path: str = "/Game/",
    properties: Dict[str, Any] | None = None,
    wait_for_ready: bool = True,
    ready_timeout_seconds: int = 120,
    ready_poll_seconds: int = 5,
) -> Dict[str, Any]:
    """Guarded asset creation with automatic editor readiness preflight."""
    return _guard_live_editor_call(
        "asset.create_asset_with_properties",
        asset_create_asset_with_properties,
        asset_type,
        name,
        path,
        properties,
        wait_for_ready=wait_for_ready,
        ready_timeout_seconds=ready_timeout_seconds,
        ready_poll_seconds=ready_poll_seconds,
    )


def update_asset_properties(
    asset_path: str,
    properties: Dict[str, Any],
    wait_for_ready: bool = True,
    ready_timeout_seconds: int = 120,
    ready_poll_seconds: int = 5,
) -> Dict[str, Any]:
    """Guarded asset update with automatic editor readiness preflight."""
    return _guard_live_editor_call(
        "asset.update_asset_properties",
        asset_update_asset_properties,
        asset_path,
        properties,
        wait_for_ready=wait_for_ready,
        ready_timeout_seconds=ready_timeout_seconds,
        ready_poll_seconds=ready_poll_seconds,
    )


def create_material_asset(
    name: str,
    path: str = "/Game/",
    wait_for_ready: bool = True,
    ready_timeout_seconds: int = 120,
    ready_poll_seconds: int = 5,
) -> Dict[str, Any]:
    """Guarded material asset creation with automatic editor readiness preflight."""
    return _guard_live_editor_call(
        "material.create_material_asset",
        material_create_material_asset,
        name,
        path,
        wait_for_ready=wait_for_ready,
        ready_timeout_seconds=ready_timeout_seconds,
        ready_poll_seconds=ready_poll_seconds,
    )


def create_material_instance_asset(
    name: str,
    parent_material: str,
    path: str = "/Game/",
    wait_for_ready: bool = True,
    ready_timeout_seconds: int = 120,
    ready_poll_seconds: int = 5,
) -> Dict[str, Any]:
    """Guarded material instance creation with automatic editor readiness preflight."""
    return _guard_live_editor_call(
        "material.create_material_instance_asset",
        material_create_material_instance_asset,
        name,
        parent_material,
        path,
        wait_for_ready=wait_for_ready,
        ready_timeout_seconds=ready_timeout_seconds,
        ready_poll_seconds=ready_poll_seconds,
    )


def update_material_instance_properties(
    asset_path: str,
    properties: Dict[str, Any],
    wait_for_ready: bool = True,
    ready_timeout_seconds: int = 120,
    ready_poll_seconds: int = 5,
) -> Dict[str, Any]:
    """Guarded material instance update with automatic editor readiness preflight."""
    return _guard_live_editor_call(
        "material.update_material_instance_properties",
        material_update_material_instance_properties,
        asset_path,
        properties,
        wait_for_ready=wait_for_ready,
        ready_timeout_seconds=ready_timeout_seconds,
        ready_poll_seconds=ready_poll_seconds,
    )


def get_material_instance_parameter_names(
    asset_path: str,
    wait_for_ready: bool = True,
    ready_timeout_seconds: int = 120,
    ready_poll_seconds: int = 5,
) -> Dict[str, Any]:
    """Guarded material parameter inspection with automatic editor readiness preflight."""
    return _guard_live_editor_call(
        "material.get_material_instance_parameter_names",
        material_get_material_instance_parameter_names,
        asset_path,
        wait_for_ready=wait_for_ready,
        ready_timeout_seconds=ready_timeout_seconds,
        ready_poll_seconds=ready_poll_seconds,
    )


def set_material_instance_scalar_parameter(
    asset_path: str,
    parameter_name: str,
    value: float,
    wait_for_ready: bool = True,
    ready_timeout_seconds: int = 120,
    ready_poll_seconds: int = 5,
) -> Dict[str, Any]:
    """Guarded scalar parameter update with automatic editor readiness preflight."""
    return _guard_live_editor_call(
        "material.set_material_instance_scalar_parameter",
        material_set_material_instance_scalar_parameter,
        asset_path,
        parameter_name,
        value,
        wait_for_ready=wait_for_ready,
        ready_timeout_seconds=ready_timeout_seconds,
        ready_poll_seconds=ready_poll_seconds,
    )


def set_material_instance_vector_parameter(
    asset_path: str,
    parameter_name: str,
    value: Dict[str, float],
    wait_for_ready: bool = True,
    ready_timeout_seconds: int = 120,
    ready_poll_seconds: int = 5,
) -> Dict[str, Any]:
    """Guarded vector parameter update with automatic editor readiness preflight."""
    return _guard_live_editor_call(
        "material.set_material_instance_vector_parameter",
        material_set_material_instance_vector_parameter,
        asset_path,
        parameter_name,
        value,
        wait_for_ready=wait_for_ready,
        ready_timeout_seconds=ready_timeout_seconds,
        ready_poll_seconds=ready_poll_seconds,
    )


def set_material_instance_texture_parameter(
    asset_path: str,
    parameter_name: str,
    texture_asset_path: str,
    wait_for_ready: bool = True,
    ready_timeout_seconds: int = 120,
    ready_poll_seconds: int = 5,
) -> Dict[str, Any]:
    """Guarded texture parameter update with automatic editor readiness preflight."""
    return _guard_live_editor_call(
        "material.set_material_instance_texture_parameter",
        material_set_material_instance_texture_parameter,
        asset_path,
        parameter_name,
        texture_asset_path,
        wait_for_ready=wait_for_ready,
        ready_timeout_seconds=ready_timeout_seconds,
        ready_poll_seconds=ready_poll_seconds,
    )


def update_material_instance_parameters_and_verify(
    asset_path: str,
    scalar_parameters: Dict[str, float] | None = None,
    vector_parameters: Dict[str, Dict[str, float]] | None = None,
    texture_parameters: Dict[str, str] | None = None,
    wait_for_ready: bool = True,
    ready_timeout_seconds: int = 120,
    ready_poll_seconds: int = 5,
) -> Dict[str, Any]:
    """Guarded material instance batch-parameter update with verification."""
    return _guard_live_editor_call(
        "material.update_material_instance_parameters_and_verify",
        material_update_material_instance_parameters_and_verify,
        asset_path,
        scalar_parameters,
        vector_parameters,
        texture_parameters,
        wait_for_ready=wait_for_ready,
        ready_timeout_seconds=ready_timeout_seconds,
        ready_poll_seconds=ready_poll_seconds,
    )


def analyze_material_graph(
    asset_path: str,
    wait_for_ready: bool = True,
    ready_timeout_seconds: int = 120,
    ready_poll_seconds: int = 5,
) -> Dict[str, Any]:
    """Guarded material graph analysis summary."""
    return _guard_live_editor_call(
        "material_graph.analyze_material_graph",
        material_graph_analyze_material_graph,
        asset_path,
        wait_for_ready=wait_for_ready,
        ready_timeout_seconds=ready_timeout_seconds,
        ready_poll_seconds=ready_poll_seconds,
    )


def create_material_graph_recipe(
    material_name: str,
    nodes: list[Dict[str, Any]],
    connections: list[Dict[str, Any]] | None = None,
    properties: Dict[str, Any] | None = None,
    compile: bool = True,
    wait_for_ready: bool = True,
    ready_timeout_seconds: int = 120,
    ready_poll_seconds: int = 5,
) -> Dict[str, Any]:
    """Guarded material graph recipe builder."""
    return _guard_live_editor_call(
        "material_graph.create_material_graph_recipe",
        material_graph_create_material_graph_recipe,
        material_name,
        nodes,
        connections,
        properties,
        compile,
        wait_for_ready=wait_for_ready,
        ready_timeout_seconds=ready_timeout_seconds,
        ready_poll_seconds=ready_poll_seconds,
    )


def connect_material_nodes(
    material_name: str,
    connections: list[Dict[str, Any]],
    nodes: list[Dict[str, Any]] | None = None,
    compile: bool = True,
    wait_for_ready: bool = True,
    ready_timeout_seconds: int = 120,
    ready_poll_seconds: int = 5,
) -> Dict[str, Any]:
    """Guarded material graph connection workflow."""
    return _guard_live_editor_call(
        "material_graph.connect_material_nodes",
        material_graph_connect_material_nodes,
        material_name,
        connections,
        nodes,
        compile,
        wait_for_ready=wait_for_ready,
        ready_timeout_seconds=ready_timeout_seconds,
        ready_poll_seconds=ready_poll_seconds,
    )


def get_harness_domains() -> Dict[str, Any]:
    """List orchestrator domains and planned backends."""
    domains = list_domains()
    return {
        "success": True,
        "operation_id": _new_orchestrator_operation_id("get_harness_domains"),
        "domain": "orchestrator",
        "targets": ["domains"],
        "applied_changes": [],
        "failed_changes": [],
        "post_state": {"domains": domains},
        "verification": {"verified": True, "checks": []},
        "domains": domains,
        "count": len(domains),
    }


def get_domain_design(domain: str) -> Dict[str, Any]:
    """Read the design metadata for a specific harness domain."""
    try:
        domain_payload = get_domain(domain)
        return {
            "success": True,
            "operation_id": _new_orchestrator_operation_id("get_domain_design"),
            "domain": "orchestrator",
            "targets": [domain],
            "applied_changes": [],
            "failed_changes": [],
            "post_state": {domain: domain_payload},
            "verification": {"verified": True, "checks": []},
            "design": domain_payload,
        }
    except ValueError as exc:
        return {
            "success": False,
            "operation_id": _new_orchestrator_operation_id("get_domain_design"),
            "domain": "orchestrator",
            "targets": [domain],
            "applied_changes": [],
            "failed_changes": [
                {"target": domain, "field": "domain", "error": str(exc)}
            ],
            "post_state": {},
            "verification": {"verified": False, "checks": []},
            "error": str(exc),
        }


def route_harness_task(task: str) -> Dict[str, Any]:
    """Route a freeform task description to the most likely harness domain."""
    result = route_text(task)
    return {
        "success": True,
        "operation_id": _new_orchestrator_operation_id("route_harness_task"),
        "domain": "orchestrator",
        "targets": [task],
        "applied_changes": [],
        "failed_changes": [],
        "post_state": {"route": result},
        "verification": {"verified": True, "checks": []},
        **result,
    }


@asynccontextmanager
async def server_lifespan(server: FastMCP) -> AsyncIterator[Dict[str, Any]]:
    logger.info("Unreal Orchestrator server starting up")
    try:
        yield {}
    finally:
        logger.info("Unreal Orchestrator server shut down")


mcp = FastMCP("UnrealOrchestrator", lifespan=server_lifespan)

for tool in [get_harness_domains, get_domain_design, route_harness_task]:
    mcp.tool()(tool)

DEFAULT_TOOLS = [
    get_scene_harness_info,
    get_scene_backend_status,
    apply_scene_actor_batch,
    query_scene_actors,
    query_scene_lights,
    ensure_folder,
    ensure_asset_with_properties,
    duplicate_asset_with_overrides,
    move_asset_batch,
    query_assets_summary,
    set_scene_light_intensity,
    create_spot_light_ring,
    aim_actor_at,
    set_post_process_overrides,
    spawn_actor_with_defaults,
    get_asset_harness_info,
    get_material_harness_info,
    update_material_instance_parameters_and_verify,
    analyze_material_graph,
    create_material_graph_recipe,
    connect_material_nodes,
    get_material_graph_harness_info,
    get_harness_health,
    get_runtime_policy,
    get_token_usage_summary,
    get_transport_port_status,
    get_unreal_python_status,
    get_editor_process_status,
    get_commandlet_runtime_status,
    get_editor_ready_state,
    wait_for_editor_ready,
]

if ENABLE_EXTENDED_TOOLS:
    DEFAULT_TOOLS.extend(
        [
            create_asset_with_properties,
            update_asset_properties,
            import_texture_asset,
            import_fbx_asset,
            create_material_asset,
            create_material_instance_asset,
            update_material_instance_properties,
            get_material_instance_parameter_names,
            set_material_instance_scalar_parameter,
            set_material_instance_vector_parameter,
            set_material_instance_texture_parameter,
        ]
    )

if ENABLE_DEV_TOOLS:
    DEFAULT_TOOLS.append(dev_launch_editor_and_wait_ready)

for tool in DEFAULT_TOOLS:
    mcp.tool()(tool)


if __name__ == "__main__":
    mcp.run()
