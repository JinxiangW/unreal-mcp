"""FastMCP entry point for the new harness orchestrator."""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, Dict

from fastmcp import FastMCP

from .catalog import get_domain, list_domains, route_text
from unreal_asset.tools import (
    create_asset_with_properties as asset_create_asset_with_properties,
    get_asset_harness_info,
    import_fbx_asset,
    import_texture_asset,
    update_asset_properties as asset_update_asset_properties,
)
from unreal_diagnostics.tools import (
    dev_launch_editor_and_wait_ready,
    get_editor_ready_state,
    get_harness_health,
    get_runtime_policy,
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
    update_material_instance_properties as material_update_material_instance_properties,
)
from unreal_material_graph.tools import get_material_graph_harness_info
from unreal_scene.tools import (
    create_spot_light_ring as scene_create_spot_light_ring,
    get_scene_backend_status,
    get_scene_harness_info,
    set_scene_light_intensity as scene_set_scene_light_intensity,
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


def _guard_live_editor_call(
    operation: str,
    func,
    *args,
    wait_for_ready: bool = True,
    ready_timeout_seconds: int = 120,
    ready_poll_seconds: int = 5,
    **kwargs,
) -> Dict[str, Any]:
    preflight = (
        wait_for_editor_ready(
            timeout_seconds=ready_timeout_seconds,
            poll_seconds=ready_poll_seconds,
        )
        if wait_for_ready
        else get_editor_ready_state()
    )

    if not preflight.get("ready"):
        return {
            "success": False,
            "operation": operation,
            "preflight": preflight,
            "error": "Editor is not ready for this live-editor operation",
        }

    result = func(*args, **kwargs)
    return {
        "success": bool(result.get("success", False))
        if isinstance(result, dict)
        else True,
        "operation": operation,
        "preflight": preflight,
        "result": result,
    }


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


def get_harness_domains() -> Dict[str, Any]:
    """List orchestrator domains and planned backends."""
    return {"success": True, "domains": list_domains(), "count": len(list_domains())}


def get_domain_design(domain: str) -> Dict[str, Any]:
    """Read the design metadata for a specific harness domain."""
    try:
        return {"success": True, "domain": get_domain(domain)}
    except ValueError as exc:
        return {"success": False, "error": str(exc)}


def route_harness_task(task: str) -> Dict[str, Any]:
    """Route a freeform task description to the most likely harness domain."""
    result = route_text(task)
    return {"success": True, **result}


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

for tool in [
    get_scene_harness_info,
    get_scene_backend_status,
    create_asset_with_properties,
    update_asset_properties,
    import_texture_asset,
    import_fbx_asset,
    set_scene_light_intensity,
    create_spot_light_ring,
    get_asset_harness_info,
    get_material_harness_info,
    create_material_asset,
    create_material_instance_asset,
    update_material_instance_properties,
    get_material_instance_parameter_names,
    set_material_instance_scalar_parameter,
    set_material_instance_vector_parameter,
    set_material_instance_texture_parameter,
    get_material_graph_harness_info,
    get_harness_health,
    get_runtime_policy,
    get_editor_ready_state,
    wait_for_editor_ready,
    dev_launch_editor_and_wait_ready,
]:
    mcp.tool()(tool)


if __name__ == "__main__":
    mcp.run()
