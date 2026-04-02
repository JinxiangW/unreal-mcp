"""
Workflow-oriented tools for Unreal Editor MCP.

This module keeps the tool surface aligned with the TCP plugin backend,
while grouping commands around editor workflows instead of legacy wrappers.
"""

from typing import Any, Dict, List, Optional

from .common import (
    save_json_to_file,
    send_command,
    with_unreal_connection,
)


SUPPORTED_BLUEPRINT_GRAPH_COMMANDS = {
    "add_blueprint_node",
    "connect_nodes",
    "create_variable",
    "set_blueprint_variable_properties",
    "add_event_node",
    "delete_node",
    "set_node_property",
    "create_function",
    "add_function_input",
    "add_function_output",
    "delete_function",
    "rename_function",
}


@with_unreal_connection
def get_assets(
    path: str = "/Game/",
    asset_class: Optional[str] = None,
    name_filter: Optional[str] = None,
) -> Dict[str, Any]:
    """List assets in the project with optional class and name filters."""
    params: Dict[str, Any] = {"path": path}
    if asset_class:
        params["asset_class"] = asset_class
    if name_filter:
        params["name_filter"] = name_filter
    return send_command("get_assets", params)


@with_unreal_connection
def get_asset_properties(
    asset_path: str, properties: Optional[List[str]] = None
) -> Dict[str, Any]:
    """Read editable properties from an asset."""
    params: Dict[str, Any] = {"asset_path": asset_path}
    if properties:
        params["properties"] = properties
    return send_command("get_asset_properties", params)


@with_unreal_connection
def create_asset(
    asset_type: str,
    name: str,
    path: str = "/Game/",
    properties: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Create a new asset using the generic asset backend."""
    params: Dict[str, Any] = {
        "asset_type": asset_type,
        "name": name,
        "path": path,
    }
    if properties:
        params["properties"] = properties
    return send_command("create_asset", params)


@with_unreal_connection
def set_asset_properties(asset_path: str, properties: Dict[str, Any]) -> Dict[str, Any]:
    """Set editable properties on an asset."""
    return send_command(
        "set_asset_properties",
        {
            "asset_path": asset_path,
            "properties": properties,
        },
    )


@with_unreal_connection
def delete_asset(asset_path: str) -> Dict[str, Any]:
    """Delete an asset by path."""
    return send_command("delete_asset", {"asset_path": asset_path})


@with_unreal_connection
def batch_create_assets(items: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Create multiple assets in one request."""
    return send_command("batch_create_assets", {"items": items})


@with_unreal_connection
def batch_set_assets_properties(items: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Update multiple assets in one request."""
    return send_command("batch_set_assets_properties", {"items": items})


@with_unreal_connection
def get_current_level() -> Dict[str, Any]:
    """Get the current editor level."""
    return send_command("get_current_level", {})


@with_unreal_connection
def create_level(level_path: str) -> Dict[str, Any]:
    """Create a level asset."""
    return send_command("create_level", {"level_path": level_path})


@with_unreal_connection
def load_level(level_path: str) -> Dict[str, Any]:
    """Load a level into the editor."""
    return send_command("load_level", {"level_path": level_path})


@with_unreal_connection
def save_current_level() -> Dict[str, Any]:
    """Save the active level."""
    return send_command("save_current_level", {})


@with_unreal_connection
def get_viewport_camera() -> Dict[str, Any]:
    """Read the active editor viewport camera."""
    return send_command("get_viewport_camera", {})


@with_unreal_connection
def set_viewport_camera(
    location: Optional[Dict[str, float]] = None,
    rotation: Optional[Dict[str, float]] = None,
    fov: Optional[float] = None,
    ortho_width: Optional[float] = None,
    perspective: bool = True,
) -> Dict[str, Any]:
    """Set the active editor viewport camera."""
    params: Dict[str, Any] = {"perspective": perspective}
    if location is not None:
        params["location"] = location
    if rotation is not None:
        params["rotation"] = rotation
    if fov is not None:
        params["fov"] = fov
    if ortho_width is not None:
        params["ortho_width"] = ortho_width
    return send_command("set_viewport_camera", params)


@with_unreal_connection
def get_viewport_screenshot(
    output_path: str,
    format: str = "png",
    quality: int = 85,
    include_ui: bool = False,
    output_mode: str = "file",
    force_redraw: bool = True,
) -> Dict[str, Any]:
    """Capture the active editor or PIE viewport."""
    return send_command(
        "get_viewport_screenshot",
        {
            "output_path": output_path,
            "format": format,
            "quality": quality,
            "include_ui": include_ui,
            "output_mode": output_mode,
            "force_redraw": force_redraw,
        },
    )


@with_unreal_connection
def get_actors(
    actor_class: Optional[str] = None, detailed: bool = False
) -> Dict[str, Any]:
    """List actors in the current level."""
    params: Dict[str, Any] = {"detailed": detailed}
    if actor_class:
        params["actor_class"] = actor_class
    return send_command("get_actors", params)


@with_unreal_connection
def get_actor_properties(name: str) -> Dict[str, Any]:
    """Read editable properties from an actor."""
    return send_command("get_actor_properties", {"name": name})


@with_unreal_connection
def spawn_actor(
    actor_class: str,
    name: Optional[str] = None,
    location: Optional[Dict[str, float]] = None,
    rotation: Optional[Dict[str, float]] = None,
    scale: Optional[Dict[str, float]] = None,
    properties: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Spawn an actor in the current level."""
    params: Dict[str, Any] = {"actor_class": actor_class}
    if name:
        params["name"] = name
    if location is not None:
        params["location"] = location
    if rotation is not None:
        params["rotation"] = rotation
    if scale is not None:
        params["scale"] = scale
    if properties:
        params["properties"] = properties
    return send_command("spawn_actor", params)


@with_unreal_connection
def set_actor_properties(name: str, properties: Dict[str, Any]) -> Dict[str, Any]:
    """Set editable properties on an actor."""
    return send_command(
        "set_actor_properties",
        {
            "name": name,
            "properties": properties,
        },
    )


@with_unreal_connection
def delete_actor(name: str) -> Dict[str, Any]:
    """Delete an actor by name."""
    return send_command("delete_actor", {"name": name})


@with_unreal_connection
def batch_spawn_actors(items: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Spawn multiple actors in one request."""
    return send_command("batch_spawn_actors", {"items": items})


@with_unreal_connection
def batch_delete_actors(names: List[str]) -> Dict[str, Any]:
    """Delete multiple actors in one request."""
    return send_command("batch_delete_actors", {"names": names})


@with_unreal_connection
def batch_set_actors_properties(actors: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Update multiple actors in one request."""
    return send_command("batch_set_actors_properties", {"actors": actors})


@with_unreal_connection
def import_texture(
    source_path: str,
    name: str,
    destination_path: str = "/Game/Textures/",
    delete_source: bool = False,
    srgb: Optional[bool] = None,
    compression_settings: Optional[str] = None,
    filter: Optional[str] = None,
    address_x: Optional[str] = None,
    address_y: Optional[str] = None,
) -> Dict[str, Any]:
    """Import a texture into the project."""
    params: Dict[str, Any] = {
        "source_path": source_path,
        "name": name,
        "destination_path": destination_path,
        "delete_source": delete_source,
    }
    if srgb is not None:
        params["srgb"] = srgb
    if compression_settings is not None:
        params["compression_settings"] = compression_settings
    if filter is not None:
        params["filter"] = filter
    if address_x is not None:
        params["address_x"] = address_x
    if address_y is not None:
        params["address_y"] = address_y
    return send_command("import_texture", params)


@with_unreal_connection
def import_fbx(
    fbx_path: str,
    destination_path: str = "/Game/ImportedMeshes/",
    asset_name: Optional[str] = None,
    spawn_in_level: bool = True,
    location: Optional[List[float]] = None,
) -> Dict[str, Any]:
    """Import an FBX asset and optionally spawn it."""
    params: Dict[str, Any] = {
        "fbx_path": fbx_path,
        "destination_path": destination_path,
        "spawn_in_level": spawn_in_level,
    }
    if asset_name is not None:
        params["asset_name"] = asset_name
    if location is not None:
        params["location"] = location
    return send_command("import_fbx", params)


@with_unreal_connection
def build_material_graph(
    material_name: str,
    nodes: List[Dict[str, Any]],
    connections: Optional[List[Dict[str, Any]]] = None,
    properties: Optional[Dict[str, Any]] = None,
    compile: bool = True,
) -> Dict[str, Any]:
    """Build an entire material graph in one request."""
    params: Dict[str, Any] = {
        "material_name": material_name,
        "nodes": nodes,
        "compile": compile,
    }
    if connections:
        params["connections"] = connections
    if properties:
        params["properties"] = properties
    return send_command("build_material_graph", params)


@with_unreal_connection
def get_material_graph(
    asset_path: str, save_to: Optional[str] = None
) -> Dict[str, Any]:
    """Inspect a material or material function graph."""
    result = send_command("get_material_graph", {"asset_path": asset_path})
    if save_to and result.get("success"):
        asset_name = result.get("name", asset_path.split("/")[-1])
        result.update(save_json_to_file(result, save_to, "material_graph", asset_name))
    return result


@with_unreal_connection
def get_niagara_graph(
    asset_path: Optional[str] = None,
    emitter: Optional[str] = None,
    script: str = "spawn",
    script_path: Optional[str] = None,
    module: str = "",
    save_to: Optional[str] = None,
) -> Dict[str, Any]:
    """Inspect a Niagara graph from a system emitter or standalone script."""
    params: Dict[str, Any] = {"script": script, "module": module}
    if script_path:
        params["script_path"] = script_path
    elif asset_path and emitter:
        params["asset_path"] = asset_path
        params["emitter"] = emitter
    else:
        return {
            "success": False,
            "error": "Must provide either (asset_path + emitter) or script_path",
        }

    result = send_command("get_niagara_graph", params)
    if save_to and result.get("success"):
        graph_name = (
            script_path.split("/")[-1] if script_path else f"{emitter}_{script}"
        )
        result.update(save_json_to_file(result, save_to, "niagara_graph", graph_name))
    return result


@with_unreal_connection
def update_niagara_graph(
    asset_path: Optional[str] = None,
    emitter: Optional[str] = None,
    script: str = "spawn",
    script_path: Optional[str] = None,
    operations: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Apply graph operations to a Niagara graph."""
    params: Dict[str, Any] = {"script": script, "operations": operations or []}
    if script_path:
        params["script_path"] = script_path
    elif asset_path and emitter:
        params["asset_path"] = asset_path
        params["emitter"] = emitter
    else:
        return {
            "success": False,
            "error": "Must provide either (asset_path + emitter) or script_path",
        }
    return send_command("update_niagara_graph", params)


@with_unreal_connection
def get_niagara_emitter(
    asset_path: str,
    detail_level: str = "overview",
    emitters: Optional[List[str]] = None,
    include: Optional[List[str]] = None,
    save_to: Optional[str] = None,
) -> Dict[str, Any]:
    """Inspect Niagara emitter structure and settings."""
    params: Dict[str, Any] = {"asset_path": asset_path, "detail_level": detail_level}
    if emitters is not None:
        params["emitters"] = emitters
    if include is not None:
        params["include"] = include
    result = send_command("get_niagara_emitter", params)
    if save_to and result.get("success"):
        asset_name = result.get("asset_name", asset_path.split("/")[-1])
        result.update(save_json_to_file(result, save_to, "niagara_emitter", asset_name))
    return result


@with_unreal_connection
def update_niagara_emitter(
    asset_path: str, operations: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """Apply emitter-level Niagara operations."""
    return send_command(
        "update_niagara_emitter",
        {
            "asset_path": asset_path,
            "operations": operations,
        },
    )


@with_unreal_connection
def get_niagara_compiled_code(
    asset_path: str,
    emitter: Optional[str] = None,
    script: str = "spawn",
) -> Dict[str, Any]:
    """Get compiled Niagara HLSL for debugging."""
    params: Dict[str, Any] = {"asset_path": asset_path, "script": script}
    if emitter:
        params["emitter"] = emitter
    return send_command("get_niagara_compiled_code", params)


@with_unreal_connection
def get_niagara_particle_attributes(
    component_name: str,
    emitter: Optional[str] = None,
    frame: int = 0,
) -> Dict[str, Any]:
    """Inspect runtime particle attributes from a Niagara component."""
    params: Dict[str, Any] = {"component_name": component_name, "frame": frame}
    if emitter:
        params["emitter"] = emitter
    return send_command("get_niagara_particle_attributes", params)


@with_unreal_connection
def get_blueprint_info(
    blueprint_path: str,
    include_variables: bool = True,
    include_functions: bool = True,
    include_widget_tree: bool = True,
) -> Dict[str, Any]:
    """Read high-level blueprint info.

    This uses the existing blueprint info command, which works best for
    Editor Utility Widgets but also returns useful metadata for regular blueprints.
    """
    return send_command(
        "get_editor_widget_blueprint_info",
        {
            "blueprint_path": blueprint_path,
            "include_variables": include_variables,
            "include_functions": include_functions,
            "include_widget_tree": include_widget_tree,
        },
    )


@with_unreal_connection
def update_blueprint(
    blueprint_path: str,
    properties: Optional[Dict[str, Any]] = None,
    compile_after: bool = False,
) -> Dict[str, Any]:
    """Save and optionally compile a blueprint update request."""
    params: Dict[str, Any] = {
        "blueprint_path": blueprint_path,
        "compile_after": compile_after,
    }
    if properties:
        params["properties"] = properties
    return send_command("update_editor_widget_blueprint", params)


@with_unreal_connection
def read_blueprint_content(
    blueprint_path: str,
    include_event_graph: bool = True,
    include_functions: bool = True,
    include_variables: bool = True,
    include_components: bool = True,
    include_interfaces: bool = True,
) -> Dict[str, Any]:
    """Read a fuller blueprint content snapshot."""
    return send_command(
        "read_blueprint_content",
        {
            "blueprint_path": blueprint_path,
            "include_event_graph": include_event_graph,
            "include_functions": include_functions,
            "include_variables": include_variables,
            "include_components": include_components,
            "include_interfaces": include_interfaces,
        },
    )


@with_unreal_connection
def analyze_blueprint_graph(blueprint_path: str) -> Dict[str, Any]:
    """Analyze blueprint graphs using the plugin backend."""
    return send_command("analyze_blueprint_graph", {"blueprint_path": blueprint_path})


@with_unreal_connection
def blueprint_graph_command(command: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """Run an advanced blueprint graph command.

    Supported commands:
    add_blueprint_node, connect_nodes, create_variable,
    set_blueprint_variable_properties, add_event_node, delete_node,
    set_node_property, create_function, add_function_input,
    add_function_output, delete_function, rename_function.
    """
    if command not in SUPPORTED_BLUEPRINT_GRAPH_COMMANDS:
        supported = ", ".join(sorted(SUPPORTED_BLUEPRINT_GRAPH_COMMANDS))
        return {
            "success": False,
            "error": f"Unsupported blueprint graph command: {command}. Supported: {supported}",
        }
    return send_command(command, params or {})


__all__ = [
    "get_assets",
    "get_asset_properties",
    "create_asset",
    "set_asset_properties",
    "delete_asset",
    "batch_create_assets",
    "batch_set_assets_properties",
    "get_current_level",
    "create_level",
    "load_level",
    "save_current_level",
    "get_viewport_camera",
    "set_viewport_camera",
    "get_viewport_screenshot",
    "get_actors",
    "get_actor_properties",
    "spawn_actor",
    "set_actor_properties",
    "delete_actor",
    "batch_spawn_actors",
    "batch_delete_actors",
    "batch_set_actors_properties",
    "import_texture",
    "import_fbx",
    "build_material_graph",
    "get_material_graph",
    "get_niagara_graph",
    "update_niagara_graph",
    "get_niagara_emitter",
    "update_niagara_emitter",
    "get_niagara_compiled_code",
    "get_niagara_particle_attributes",
    "get_blueprint_info",
    "update_blueprint",
    "read_blueprint_content",
    "analyze_blueprint_graph",
    "blueprint_graph_command",
]
