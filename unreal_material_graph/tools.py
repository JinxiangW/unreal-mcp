"""Metadata for the future material graph harness."""

from __future__ import annotations

from typing import Any, Dict


def get_material_graph_harness_info() -> Dict[str, Any]:
    """Describe the planned material graph harness boundary."""
    return {
        "success": True,
        "domain": "material_graph",
        "backend": "fallback_unreal_editor_mcp",
        "target_backend": "cpp_primary",
        "status": "planned_split",
        "supports": [
            "material_node_creation",
            "graph_connections",
            "graph_analysis",
            "complex_graph_refactors",
        ],
    }
