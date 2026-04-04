"""Domain-scoped FastMCP entry point for scene tools."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, Dict

from fastmcp import FastMCP

from .tools import (
    apply_scene_actor_batch,
    aim_actor_at,
    create_spot_light_ring,
    delete_scene_actors_batch,
    get_scene_backend_status,
    get_scene_harness_info,
    query_scene_actors,
    query_scene_lights,
    set_post_process_overrides,
    set_scene_light_intensity,
    spawn_actor_with_defaults,
)


@asynccontextmanager
async def server_lifespan(server: FastMCP) -> AsyncIterator[Dict[str, Any]]:
    yield {}


mcp = FastMCP("UnrealSceneHarness", lifespan=server_lifespan)

for tool in [
    get_scene_harness_info,
    apply_scene_actor_batch,
    delete_scene_actors_batch,
    get_scene_backend_status,
    query_scene_actors,
    query_scene_lights,
    set_scene_light_intensity,
    create_spot_light_ring,
    aim_actor_at,
    set_post_process_overrides,
    spawn_actor_with_defaults,
]:
    mcp.tool()(tool)


if __name__ == "__main__":
    mcp.run()
