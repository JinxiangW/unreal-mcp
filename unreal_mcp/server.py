"""Unified Unreal MCP entry point — imports TOOLS from all domain servers."""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, Dict

from fastmcp import FastMCP

from unreal_asset.server import TOOLS as ASSET_TOOLS
from unreal_blueprint.server import TOOLS as BLUEPRINT_TOOLS
from unreal_diagnostics.server import TOOLS as DIAGNOSTICS_TOOLS
from unreal_material.server import TOOLS as MATERIAL_TOOLS
from unreal_material_graph.server import TOOLS as MATERIAL_GRAPH_TOOLS
from unreal_renderdoc.server import TOOLS as RENDERDOC_TOOLS
from unreal_scene.server import TOOLS as SCENE_TOOLS

_CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s",
    handlers=[
        logging.FileHandler(os.path.join(_CURRENT_DIR, "unreal_mcp.log"))
    ],
)
logger = logging.getLogger("UnrealMCP")

ENABLE_DEV_TOOLS = os.environ.get("UNREAL_MCP_ENABLE_DEV_TOOLS", "0") == "1"

_diag_tools = list(DIAGNOSTICS_TOOLS)
if not ENABLE_DEV_TOOLS:
    _diag_tools = [
        t for t in _diag_tools
        if t.__name__ != "dev_launch_editor_and_wait_ready"
    ]

TOOLS = [
    *SCENE_TOOLS,
    *ASSET_TOOLS,
    *BLUEPRINT_TOOLS,
    *MATERIAL_TOOLS,
    *MATERIAL_GRAPH_TOOLS,
    *RENDERDOC_TOOLS,
    *_diag_tools,
]


@asynccontextmanager
async def server_lifespan(server: FastMCP) -> AsyncIterator[Dict[str, Any]]:
    logger.info("Unreal MCP server starting up")
    try:
        yield {}
    finally:
        logger.info("Unreal MCP server shut down")


mcp = FastMCP("UnrealMCP", lifespan=server_lifespan)

for tool in TOOLS:
    mcp.tool()(tool)

if __name__ == "__main__":
    mcp.run()
