"""Domain-scoped Niagara MCP server."""

from unreal_harness_runtime.editor_guard import make_guarded_tool
from .tools import get_niagara_renderers, set_niagara_component_binding, get_niagara_assignments, rename_niagara_particle_parameter, bind_niagara_particle_position

TOOLS = [
    make_guarded_tool("niagara.get_niagara_renderers", get_niagara_renderers),
    make_guarded_tool("niagara.set_niagara_component_binding", set_niagara_component_binding),
    make_guarded_tool("niagara.get_niagara_assignments", get_niagara_assignments),
    make_guarded_tool("niagara.rename_niagara_particle_parameter", rename_niagara_particle_parameter),
    make_guarded_tool("niagara.bind_niagara_particle_position", bind_niagara_particle_position),
]

if __name__ == "__main__":
    from fastmcp import FastMCP
    mcp = FastMCP("UnrealNiagaraHarness")
    for tool in TOOLS:
        mcp.tool()(tool)
    mcp.run()
