"""Slim Unreal MCP entry point for discovery, readiness, and diagnostics."""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, Dict

from fastmcp import FastMCP

from unreal_diagnostics.tools import (
    get_commandlet_runtime_status,
    get_editor_ready_state,
    get_runtime_policy,
    get_token_usage_summary,
    get_transport_port_status,
    wait_for_editor_ready,
)
from unreal_orchestrator.server import (
    get_domain_design,
    get_harness_domains,
    route_harness_task,
)

_CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s",
    handlers=[
        logging.FileHandler(os.path.join(_CURRENT_DIR, "unreal_mcp_slim.log"))
    ],
)
logger = logging.getLogger("UnrealMCPSlim")

TOOLS = [
    get_harness_domains,
    get_domain_design,
    route_harness_task,
    get_runtime_policy,
    get_editor_ready_state,
    wait_for_editor_ready,
    get_token_usage_summary,
    get_transport_port_status,
    get_commandlet_runtime_status,
]


@asynccontextmanager
async def server_lifespan(server: FastMCP) -> AsyncIterator[Dict[str, Any]]:
    logger.info("Unreal MCP slim server starting up")
    try:
        yield {}
    finally:
        logger.info("Unreal MCP slim server shut down")


mcp = FastMCP("UnrealMCPSlim", lifespan=server_lifespan)

for tool in TOOLS:
    mcp.tool()(tool)

if __name__ == "__main__":
    mcp.run()
