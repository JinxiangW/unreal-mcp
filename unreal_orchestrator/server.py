"""FastMCP entry point for the harness orchestrator.

The orchestrator exposes only cross-cutting routing/discovery tools.
Domain tools live in their own servers (``unreal_<domain>/server.py``).
Connect to domain servers directly for domain-specific work.
"""

from __future__ import annotations

import logging
import os
import time
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, Dict

from fastmcp import FastMCP

from .catalog import get_domain, list_domains, route_text

_CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s",
    handlers=[
        logging.FileHandler(os.path.join(_CURRENT_DIR, "unreal_orchestrator.log"))
    ],
)
logger = logging.getLogger("UnrealOrchestrator")


def _new_orchestrator_operation_id(action: str) -> str:
    return f"orchestrator:{action}:{int(time.time() * 1000)}"


# ── orchestrator routing tools ──────────────────────────────────────────


def get_harness_domains() -> Dict[str, Any]:
    """List all registered harness domains with backend and status metadata."""
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
    """Read the design metadata for a specific harness domain.

    Returns backend info, keywords, status, and the server_module path
    for connecting to the domain's standalone MCP server.
    """
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


# ── server bootstrap ────────────────────────────────────────────────────


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


if __name__ == "__main__":
    mcp.run()
