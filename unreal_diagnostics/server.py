"""Domain-scoped FastMCP entry point for diagnostics tools."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, Dict

from fastmcp import FastMCP

from .tools import (
    dev_launch_editor_and_wait_ready,
    get_commandlet_runtime_status,
    get_editor_process_status,
    get_editor_ready_state,
    get_harness_health,
    get_runtime_policy,
    get_token_usage_summary,
    get_transport_port_status,
    get_unreal_python_status,
    wait_for_editor_ready,
)


@asynccontextmanager
async def server_lifespan(server: FastMCP) -> AsyncIterator[Dict[str, Any]]:
    yield {}


mcp = FastMCP("UnrealDiagnosticsHarness", lifespan=server_lifespan)

for tool in [
    get_harness_health,
    get_runtime_policy,
    get_token_usage_summary,
    get_transport_port_status,
    get_unreal_python_status,
    get_editor_process_status,
    get_commandlet_runtime_status,
    get_editor_ready_state,
    wait_for_editor_ready,
    dev_launch_editor_and_wait_ready,
]:
    mcp.tool()(tool)


if __name__ == "__main__":
    mcp.run()
