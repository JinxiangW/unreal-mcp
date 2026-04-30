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
    get_asset_properties as asset_get_asset_properties,
    get_asset_harness_info,
    import_fbx_asset,
    import_texture_asset,
    inspect_cascade_emitter as asset_inspect_cascade_emitter,
    inspect_particle_system as asset_inspect_particle_system,
    move_asset_batch as asset_move_asset_batch,
    query_assets_summary as asset_query_assets_summary,
    query_textures as asset_query_textures,
    set_asset_properties as asset_set_asset_properties,
    set_texture_compression_settings as asset_set_texture_compression_settings,
    set_texture_srgb as asset_set_texture_srgb,
    update_texture_group_config as asset_update_texture_group_config,
    update_asset_properties_batch as asset_update_asset_properties_batch,
    update_asset_properties as asset_update_asset_properties,
)
from unreal_blueprint.tools import (
    add_blueprint_node as blueprint_add_blueprint_node,
    add_point_light_component_node as blueprint_add_point_light_component_node,
    analyze_blueprint_graph as blueprint_analyze_blueprint_graph,
    connect_blueprint_nodes as blueprint_connect_blueprint_nodes,
    find_blueprint_nodes as blueprint_find_blueprint_nodes,
    get_blueprint_function_details as blueprint_get_blueprint_function_details,
    get_blueprint_harness_info,
    get_blueprint_variable_details as blueprint_get_blueprint_variable_details,
    read_blueprint_content as blueprint_read_blueprint_content,
    set_blueprint_node_property as blueprint_set_blueprint_node_property,
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
    create_material_function_asset as material_create_material_function_asset,
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
    patch_material_graph as material_graph_patch_material_graph,
    set_material_graph_property_connections as material_graph_set_material_graph_property_connections,
)
from unreal_scene.tools import (
    apply_scene_actor_batch as scene_apply_scene_actor_batch,
    aim_actor_at as scene_aim_actor_at,
    create_spot_light_ring as scene_create_spot_light_ring,
    delete_scene_actors_batch as scene_delete_scene_actors_batch,
    get_scene_backend_status,
    get_scene_harness_info,
    query_scene_actors as scene_query_scene_actors,
    query_scene_lights as scene_query_scene_lights,
    set_actor_component_material as scene_set_actor_component_material,
    set_post_process_overrides as scene_set_post_process_overrides,
    set_scene_light_intensity as scene_set_scene_light_intensity,
    spawn_actor_with_defaults as scene_spawn_actor_with_defaults,
)
from unreal_renderdoc.tools import (
    capture_current_selection as renderdoc_capture_current_selection,
    capture_current_viewport_issue as renderdoc_capture_current_viewport_issue,
    capture_renderdoc_diff_pair as renderdoc_capture_renderdoc_diff_pair,
    get_renderdoc_capture_context,
    get_renderdoc_harness_info,
    get_renderdoc_runtime_status,
    get_renderdoc_selection_context,
    map_material_to_renderdoc_context,
    normalize_renderdoc_debug_labels,
    reverse_lookup_renderdoc_symbols,
    request_renderdoc_capture,
    set_renderdoc_debug_workflow,
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


def delete_scene_actors_batch(
    delete_specs: list[Dict[str, Any]],
    wait_for_ready: bool = True,
    ready_timeout_seconds: int = 120,
    ready_poll_seconds: int = 5,
) -> Dict[str, Any]:
    """Guarded batch actor deletion command for scene cleanup workflows."""
    return _guard_live_editor_call(
        "scene.delete_scene_actors_batch",
        scene_delete_scene_actors_batch,
        delete_specs,
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


def set_actor_component_material(
    actor_name_or_label: str,
    material_asset_path: str,
    material_slot: int = 0,
    component_name: str | None = None,
    save_level: bool = False,
    wait_for_ready: bool = True,
    ready_timeout_seconds: int = 120,
    ready_poll_seconds: int = 5,
) -> Dict[str, Any]:
    """Guarded existing StaticMeshComponent material override with readback verification."""
    return _guard_live_editor_call(
        "scene.set_actor_component_material",
        scene_set_actor_component_material,
        actor_name_or_label,
        material_asset_path,
        material_slot,
        component_name,
        save_level,
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


def query_textures(
    path: str = "/Game/",
    name_filter: str | None = None,
    limit: int = 20,
    offset: int = 0,
    properties: list[str] | None = None,
    wait_for_ready: bool = True,
    ready_timeout_seconds: int = 120,
    ready_poll_seconds: int = 5,
) -> Dict[str, Any]:
    """Guarded texture query with selected editor-property readback."""
    return _guard_live_editor_call(
        "asset.query_textures",
        asset_query_textures,
        path,
        name_filter,
        limit,
        offset,
        properties,
        wait_for_ready=wait_for_ready,
        ready_timeout_seconds=ready_timeout_seconds,
        ready_poll_seconds=ready_poll_seconds,
    )


def get_asset_properties(
    asset_paths: str | list[str],
    properties: list[str],
    wait_for_ready: bool = True,
    ready_timeout_seconds: int = 120,
    ready_poll_seconds: int = 5,
) -> Dict[str, Any]:
    """Guarded generic editor-property readback for assets."""
    return _guard_live_editor_call(
        "asset.get_asset_properties",
        asset_get_asset_properties,
        asset_paths,
        properties,
        wait_for_ready=wait_for_ready,
        ready_timeout_seconds=ready_timeout_seconds,
        ready_poll_seconds=ready_poll_seconds,
    )


def set_asset_properties(
    asset_paths: str | list[str],
    properties: Dict[str, Any],
    save: bool = True,
    wait_for_ready: bool = True,
    ready_timeout_seconds: int = 120,
    ready_poll_seconds: int = 5,
) -> Dict[str, Any]:
    """Guarded generic editor-property update for assets."""
    return _guard_live_editor_call(
        "asset.set_asset_properties",
        asset_set_asset_properties,
        asset_paths,
        properties,
        save,
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


def update_asset_properties_batch(
    items: list[Dict[str, Any]],
    wait_for_ready: bool = True,
    ready_timeout_seconds: int = 120,
    ready_poll_seconds: int = 5,
) -> Dict[str, Any]:
    """Guarded batch asset update with automatic editor readiness preflight."""
    return _guard_live_editor_call(
        "asset.update_asset_properties_batch",
        asset_update_asset_properties_batch,
        items,
        wait_for_ready=wait_for_ready,
        ready_timeout_seconds=ready_timeout_seconds,
        ready_poll_seconds=ready_poll_seconds,
    )


def update_texture_group_config(
    group_name: str,
    max_lod_size: int,
    ini_filename: str = "DefaultDeviceProfiles.ini",
) -> Dict[str, Any]:
    """Update one project texture group config entry."""
    return asset_update_texture_group_config(
        group_name=group_name,
        max_lod_size=max_lod_size,
        ini_filename=ini_filename,
    )


def set_texture_compression_settings(
    texture_paths: str | list[str],
    compression_settings: str,
    save: bool = True,
    wait_for_ready: bool = True,
    ready_timeout_seconds: int = 120,
    ready_poll_seconds: int = 5,
) -> Dict[str, Any]:
    """Guarded texture compression update workflow."""
    return _guard_live_editor_call(
        "asset.set_texture_compression_settings",
        asset_set_texture_compression_settings,
        texture_paths,
        compression_settings,
        save,
        wait_for_ready=wait_for_ready,
        ready_timeout_seconds=ready_timeout_seconds,
        ready_poll_seconds=ready_poll_seconds,
    )


def set_texture_srgb(
    texture_paths: str | list[str],
    srgb: bool,
    save: bool = True,
    wait_for_ready: bool = True,
    ready_timeout_seconds: int = 120,
    ready_poll_seconds: int = 5,
) -> Dict[str, Any]:
    """Guarded texture sRGB update workflow."""
    return _guard_live_editor_call(
        "asset.set_texture_srgb",
        asset_set_texture_srgb,
        texture_paths,
        srgb,
        save,
        wait_for_ready=wait_for_ready,
        ready_timeout_seconds=ready_timeout_seconds,
        ready_poll_seconds=ready_poll_seconds,
    )


def read_blueprint_content(
    blueprint_path: str | None = None,
    blueprint_name: str | None = None,
    include_event_graph: bool = True,
    include_functions: bool = True,
    include_variables: bool = True,
    include_components: bool = True,
    include_interfaces: bool = True,
    wait_for_ready: bool = True,
    ready_timeout_seconds: int = 120,
    ready_poll_seconds: int = 5,
) -> Dict[str, Any]:
    """Guarded blueprint asset inspection."""
    return _guard_live_editor_call(
        "blueprint.read_blueprint_content",
        blueprint_read_blueprint_content,
        blueprint_path,
        blueprint_name,
        include_event_graph,
        include_functions,
        include_variables,
        include_components,
        include_interfaces,
        wait_for_ready=wait_for_ready,
        ready_timeout_seconds=ready_timeout_seconds,
        ready_poll_seconds=ready_poll_seconds,
    )


def analyze_blueprint_graph(
    blueprint_path: str | None = None,
    blueprint_name: str | None = None,
    graph_name: str = "EventGraph",
    include_node_details: bool = True,
    include_pin_connections: bool = True,
    trace_execution_flow: bool = True,
    include_full_graph: bool = True,
    wait_for_ready: bool = True,
    ready_timeout_seconds: int = 120,
    ready_poll_seconds: int = 5,
) -> Dict[str, Any]:
    """Guarded blueprint graph analysis."""
    return _guard_live_editor_call(
        "blueprint.analyze_blueprint_graph",
        blueprint_analyze_blueprint_graph,
        blueprint_path,
        blueprint_name,
        graph_name,
        include_node_details,
        include_pin_connections,
        trace_execution_flow,
        include_full_graph,
        wait_for_ready=wait_for_ready,
        ready_timeout_seconds=ready_timeout_seconds,
        ready_poll_seconds=ready_poll_seconds,
    )


def find_blueprint_nodes(
    blueprint_path: str | None = None,
    blueprint_name: str | None = None,
    graph_name: str = "EventGraph",
    title_filter: str | None = None,
    class_filter: str | None = None,
    node_name_filter: str | None = None,
    pin_name_filter: str | None = None,
    pin_direction: str | None = None,
    wait_for_ready: bool = True,
    ready_timeout_seconds: int = 120,
    ready_poll_seconds: int = 5,
) -> Dict[str, Any]:
    """Guarded blueprint node discovery."""
    return _guard_live_editor_call(
        "blueprint.find_blueprint_nodes",
        blueprint_find_blueprint_nodes,
        blueprint_path,
        blueprint_name,
        graph_name,
        title_filter,
        class_filter,
        node_name_filter,
        pin_name_filter,
        pin_direction,
        wait_for_ready=wait_for_ready,
        ready_timeout_seconds=ready_timeout_seconds,
        ready_poll_seconds=ready_poll_seconds,
    )


def add_blueprint_node(
    blueprint_path: str | None = None,
    blueprint_name: str | None = None,
    node_type: str = "",
    node_params: Dict[str, Any] | None = None,
    wait_for_ready: bool = True,
    ready_timeout_seconds: int = 120,
    ready_poll_seconds: int = 5,
) -> Dict[str, Any]:
    """Guarded blueprint node creation."""
    return _guard_live_editor_call(
        "blueprint.add_blueprint_node",
        blueprint_add_blueprint_node,
        blueprint_path,
        blueprint_name,
        node_type,
        node_params,
        wait_for_ready=wait_for_ready,
        ready_timeout_seconds=ready_timeout_seconds,
        ready_poll_seconds=ready_poll_seconds,
    )


def connect_blueprint_nodes(
    blueprint_path: str | None = None,
    blueprint_name: str | None = None,
    source_node_id: str = "",
    source_pin_name: str = "",
    target_node_id: str = "",
    target_pin_name: str = "",
    function_name: str | None = None,
    wait_for_ready: bool = True,
    ready_timeout_seconds: int = 120,
    ready_poll_seconds: int = 5,
) -> Dict[str, Any]:
    """Guarded blueprint graph connection workflow."""
    return _guard_live_editor_call(
        "blueprint.connect_blueprint_nodes",
        blueprint_connect_blueprint_nodes,
        blueprint_path,
        blueprint_name,
        source_node_id,
        source_pin_name,
        target_node_id,
        target_pin_name,
        function_name,
        wait_for_ready=wait_for_ready,
        ready_timeout_seconds=ready_timeout_seconds,
        ready_poll_seconds=ready_poll_seconds,
    )


def set_blueprint_node_property(
    blueprint_path: str | None = None,
    blueprint_name: str | None = None,
    node_id: str = "",
    function_name: str | None = None,
    property_name: str | None = None,
    property_value: Any = None,
    action: str | None = None,
    extra: Dict[str, Any] | None = None,
    wait_for_ready: bool = True,
    ready_timeout_seconds: int = 120,
    ready_poll_seconds: int = 5,
) -> Dict[str, Any]:
    """Guarded blueprint node property / pin-default update."""
    return _guard_live_editor_call(
        "blueprint.set_blueprint_node_property",
        blueprint_set_blueprint_node_property,
        blueprint_path,
        blueprint_name,
        node_id,
        function_name,
        property_name,
        property_value,
        action,
        extra,
        wait_for_ready=wait_for_ready,
        ready_timeout_seconds=ready_timeout_seconds,
        ready_poll_seconds=ready_poll_seconds,
    )


def get_blueprint_variable_details(
    blueprint_path: str | None = None,
    blueprint_name: str | None = None,
    variable_name: str | None = None,
    wait_for_ready: bool = True,
    ready_timeout_seconds: int = 120,
    ready_poll_seconds: int = 5,
) -> Dict[str, Any]:
    """Guarded blueprint variable inspection."""
    return _guard_live_editor_call(
        "blueprint.get_blueprint_variable_details",
        blueprint_get_blueprint_variable_details,
        blueprint_path,
        blueprint_name,
        variable_name,
        wait_for_ready=wait_for_ready,
        ready_timeout_seconds=ready_timeout_seconds,
        ready_poll_seconds=ready_poll_seconds,
    )


def get_blueprint_function_details(
    blueprint_path: str | None = None,
    blueprint_name: str | None = None,
    function_name: str | None = None,
    include_graph: bool = True,
    wait_for_ready: bool = True,
    ready_timeout_seconds: int = 120,
    ready_poll_seconds: int = 5,
) -> Dict[str, Any]:
    """Guarded blueprint function inspection."""
    return _guard_live_editor_call(
        "blueprint.get_blueprint_function_details",
        blueprint_get_blueprint_function_details,
        blueprint_path,
        blueprint_name,
        function_name,
        include_graph,
        wait_for_ready=wait_for_ready,
        ready_timeout_seconds=ready_timeout_seconds,
        ready_poll_seconds=ready_poll_seconds,
    )


def add_point_light_component_node(
    blueprint_path: str | None = None,
    blueprint_name: str | None = None,
    node_params: Dict[str, Any] | None = None,
    wait_for_ready: bool = True,
    ready_timeout_seconds: int = 120,
    ready_poll_seconds: int = 5,
) -> Dict[str, Any]:
    """Guarded high-frequency Add PointLightComponent node template."""
    return _guard_live_editor_call(
        "blueprint.add_point_light_component_node",
        blueprint_add_point_light_component_node,
        blueprint_path,
        blueprint_name,
        node_params,
        wait_for_ready=wait_for_ready,
        ready_timeout_seconds=ready_timeout_seconds,
        ready_poll_seconds=ready_poll_seconds,
    )


def inspect_particle_system(
    asset_path: str,
    emitter_names: list[str] | None = None,
    wait_for_ready: bool = True,
    ready_timeout_seconds: int = 120,
    ready_poll_seconds: int = 5,
) -> Dict[str, Any]:
    """Guarded Cascade particle-system inspection."""
    return _guard_live_editor_call(
        "asset.inspect_particle_system",
        asset_inspect_particle_system,
        asset_path,
        emitter_names,
        wait_for_ready=wait_for_ready,
        ready_timeout_seconds=ready_timeout_seconds,
        ready_poll_seconds=ready_poll_seconds,
    )


def inspect_cascade_emitter(
    asset_path: str,
    emitter_name: str,
    wait_for_ready: bool = True,
    ready_timeout_seconds: int = 120,
    ready_poll_seconds: int = 5,
) -> Dict[str, Any]:
    """Guarded single-emitter Cascade inspection."""
    return _guard_live_editor_call(
        "asset.inspect_cascade_emitter",
        asset_inspect_cascade_emitter,
        asset_path,
        emitter_name,
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


def create_material_function_asset(
    name: str,
    path: str = "/Game/MaterialFunctions/",
    description: str | None = None,
    wait_for_ready: bool = True,
    ready_timeout_seconds: int = 120,
    ready_poll_seconds: int = 5,
) -> Dict[str, Any]:
    """Guarded MaterialFunction asset creation."""
    return _guard_live_editor_call(
        "material.create_material_function_asset",
        material_create_material_function_asset,
        name,
        path,
        description,
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
    include_full_graph: bool = False,
    wait_for_ready: bool = True,
    ready_timeout_seconds: int = 120,
    ready_poll_seconds: int = 5,
) -> Dict[str, Any]:
    """Guarded material graph analysis summary."""
    return _guard_live_editor_call(
        "material_graph.analyze_material_graph",
        material_graph_analyze_material_graph,
        asset_path,
        include_full_graph,
        wait_for_ready=wait_for_ready,
        ready_timeout_seconds=ready_timeout_seconds,
        ready_poll_seconds=ready_poll_seconds,
    )


def create_material_graph_recipe(
    material_name: str,
    nodes: list[Dict[str, Any]],
    connections: list[Dict[str, Any]] | None = None,
    properties: Dict[str, Any] | None = None,
    property_connections: Dict[str, Any] | None = None,
    delete_nodes: list[str] | None = None,
    disconnect_connections: list[Dict[str, Any]] | None = None,
    disconnect_properties: list[str] | None = None,
    compile: bool = True,
    include_full_graph: bool = False,
    update_nodes: list[Dict[str, Any]] | None = None,
    wait_for_ready: bool = True,
    ready_timeout_seconds: int = 120,
    ready_poll_seconds: int = 5,
) -> Dict[str, Any]:
    """Guarded material graph recipe builder."""
    return _guard_live_editor_call(
        "material_graph.create_material_graph_recipe",
        material_graph_create_material_graph_recipe,
        material_name=material_name,
        nodes=nodes,
        connections=connections,
        properties=properties,
        property_connections=property_connections,
        delete_nodes=delete_nodes,
        disconnect_connections=disconnect_connections,
        disconnect_properties=disconnect_properties,
        update_nodes=update_nodes,
        compile=compile,
        include_full_graph=include_full_graph,
        wait_for_ready=wait_for_ready,
        ready_timeout_seconds=ready_timeout_seconds,
        ready_poll_seconds=ready_poll_seconds,
    )


def connect_material_nodes(
    material_name: str,
    connections: list[Dict[str, Any]],
    nodes: list[Dict[str, Any]] | None = None,
    property_connections: Dict[str, Any] | None = None,
    compile: bool = True,
    include_full_graph: bool = False,
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
        property_connections,
        compile,
        include_full_graph,
        wait_for_ready=wait_for_ready,
        ready_timeout_seconds=ready_timeout_seconds,
        ready_poll_seconds=ready_poll_seconds,
    )


def set_material_graph_property_connections(
    material_name: str,
    property_connections: Dict[str, Any],
    disconnect_properties: list[str] | None = None,
    compile: bool = True,
    include_full_graph: bool = False,
    wait_for_ready: bool = True,
    ready_timeout_seconds: int = 120,
    ready_poll_seconds: int = 5,
) -> Dict[str, Any]:
    """Guarded material property-connection patch workflow."""
    return _guard_live_editor_call(
        "material_graph.set_material_graph_property_connections",
        material_graph_set_material_graph_property_connections,
        material_name,
        property_connections,
        disconnect_properties,
        compile,
        include_full_graph,
        wait_for_ready=wait_for_ready,
        ready_timeout_seconds=ready_timeout_seconds,
        ready_poll_seconds=ready_poll_seconds,
    )


def patch_material_graph(
    material_name: str,
    add_nodes: list[Dict[str, Any]] | None = None,
    add_connections: list[Dict[str, Any]] | None = None,
    delete_nodes: list[str] | None = None,
    disconnect_connections: list[Dict[str, Any]] | None = None,
    property_connections: Dict[str, Any] | None = None,
    disconnect_properties: list[str] | None = None,
    properties: Dict[str, Any] | None = None,
    compile: bool = True,
    include_full_graph: bool = False,
    update_nodes: list[Dict[str, Any]] | None = None,
    wait_for_ready: bool = True,
    ready_timeout_seconds: int = 120,
    ready_poll_seconds: int = 5,
) -> Dict[str, Any]:
    """Guarded material graph patch workflow."""
    return _guard_live_editor_call(
        "material_graph.patch_material_graph",
        material_graph_patch_material_graph,
        material_name=material_name,
        add_nodes=add_nodes,
        add_connections=add_connections,
        delete_nodes=delete_nodes,
        disconnect_connections=disconnect_connections,
        property_connections=property_connections,
        disconnect_properties=disconnect_properties,
        properties=properties,
        update_nodes=update_nodes,
        compile=compile,
        include_full_graph=include_full_graph,
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
    get_renderdoc_harness_info,
    get_renderdoc_runtime_status,
    get_renderdoc_capture_context,
    get_renderdoc_selection_context,
    map_material_to_renderdoc_context,
    normalize_renderdoc_debug_labels,
    reverse_lookup_renderdoc_symbols,
    set_renderdoc_debug_workflow,
    request_renderdoc_capture,
    renderdoc_capture_current_selection,
    renderdoc_capture_current_viewport_issue,
    renderdoc_capture_renderdoc_diff_pair,
    apply_scene_actor_batch,
    delete_scene_actors_batch,
    query_scene_actors,
    query_scene_lights,
    get_blueprint_harness_info,
    read_blueprint_content,
    analyze_blueprint_graph,
    find_blueprint_nodes,
    get_blueprint_variable_details,
    get_blueprint_function_details,
    add_blueprint_node,
    connect_blueprint_nodes,
    set_blueprint_node_property,
    add_point_light_component_node,
    ensure_folder,
    ensure_asset_with_properties,
    duplicate_asset_with_overrides,
    move_asset_batch,
    query_assets_summary,
    query_textures,
    get_asset_properties,
    set_asset_properties,
    create_asset_with_properties,
    update_asset_properties,
    update_asset_properties_batch,
    update_texture_group_config,
    set_texture_compression_settings,
    set_texture_srgb,
    inspect_particle_system,
    inspect_cascade_emitter,
    import_texture_asset,
    import_fbx_asset,
    set_scene_light_intensity,
    set_actor_component_material,
    create_spot_light_ring,
    aim_actor_at,
    set_post_process_overrides,
    spawn_actor_with_defaults,
    get_asset_harness_info,
    get_material_harness_info,
    create_material_asset,
    create_material_function_asset,
    create_material_instance_asset,
    update_material_instance_properties,
    get_material_instance_parameter_names,
    set_material_instance_scalar_parameter,
    set_material_instance_vector_parameter,
    set_material_instance_texture_parameter,
    update_material_instance_parameters_and_verify,
    analyze_material_graph,
    create_material_graph_recipe,
    connect_material_nodes,
    set_material_graph_property_connections,
    patch_material_graph,
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

if ENABLE_DEV_TOOLS:
    DEFAULT_TOOLS.append(dev_launch_editor_and_wait_ready)

for tool in DEFAULT_TOOLS:
    mcp.tool()(tool)


if __name__ == "__main__":
    mcp.run()
