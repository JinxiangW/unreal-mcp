"""Material asset and instance tools built on the asset harness."""

from __future__ import annotations

from typing import Any, Dict

from unreal_asset.tools import create_asset_with_properties, update_asset_properties
from unreal_harness_runtime.python_exec import (
    json_literal,
    python_literal,
    run_editor_python,
    wrap_editor_python,
)


def get_material_harness_info() -> Dict[str, Any]:
    """Describe the current material asset harness backend and scope."""
    return {
        "success": True,
        "domain": "material",
        "backend": "ue_python_via_asset_harness",
        "target_backend": "ue_python",
        "supports": [
            "material_assets",
            "material_instances",
            "material_instance_property_updates",
            "material_instance_parameters",
        ],
    }


def create_material_asset(name: str, path: str = "/Game/") -> Dict[str, Any]:
    """Create a material asset through the asset harness."""
    return create_asset_with_properties(asset_type="Material", name=name, path=path)


def create_material_instance_asset(
    name: str, parent_material: str, path: str = "/Game/"
) -> Dict[str, Any]:
    """Create a material instance asset with a parent material reference."""
    return create_asset_with_properties(
        asset_type="MaterialInstanceConstant",
        name=name,
        path=path,
        properties={"parent_material": parent_material},
    )


def update_material_instance_properties(
    asset_path: str, properties: Dict[str, Any]
) -> Dict[str, Any]:
    """Update a material instance through the asset harness."""
    return update_asset_properties(asset_path=asset_path, properties=properties)


def get_material_instance_parameter_names(asset_path: str) -> Dict[str, Any]:
    """Read exposed parameter names from a material or material instance."""
    body = f"""
asset_path = {python_literal(asset_path)}
asset = unreal.EditorAssetLibrary.load_asset(asset_path)
if asset is None:
    _mcp_emit({{"success": False, "error": f"Asset not found: {{asset_path}}"}})
else:
    scalar_names = unreal.MaterialEditingLibrary.get_scalar_parameter_names(asset)
    vector_names = unreal.MaterialEditingLibrary.get_vector_parameter_names(asset)
    texture_names = unreal.MaterialEditingLibrary.get_texture_parameter_names(asset)
    static_switch_names = unreal.MaterialEditingLibrary.get_static_switch_parameter_names(asset)
    _mcp_emit({{
        "success": True,
        "asset_path": asset_path,
        "scalar": [str(x) for x in scalar_names],
        "vector": [str(x) for x in vector_names],
        "texture": [str(x) for x in texture_names],
        "static_switch": [str(x) for x in static_switch_names],
    }})
"""
    return run_editor_python(wrap_editor_python(body))


def set_material_instance_scalar_parameter(
    asset_path: str,
    parameter_name: str,
    value: float,
) -> Dict[str, Any]:
    """Set a scalar parameter on a material instance."""
    body = f"""
asset_path = {python_literal(asset_path)}
parameter_name = {python_literal(parameter_name)}
instance = unreal.EditorAssetLibrary.load_asset(asset_path)
if instance is None:
    _mcp_emit({{"success": False, "error": f"Asset not found: {{asset_path}}"}})
else:
    changed = unreal.MaterialEditingLibrary.set_material_instance_scalar_parameter_value(instance, parameter_name, {value})
    current_value = unreal.MaterialEditingLibrary.get_material_instance_scalar_parameter_value(instance, parameter_name)
    unreal.EditorAssetLibrary.save_loaded_asset(instance)
    _mcp_emit({{
        "success": True,
        "asset_path": asset_path,
        "parameter_name": parameter_name,
        "changed": bool(changed),
        "value": current_value,
    }})
"""
    return run_editor_python(wrap_editor_python(body))


def set_material_instance_vector_parameter(
    asset_path: str,
    parameter_name: str,
    value: Dict[str, float],
) -> Dict[str, Any]:
    """Set a vector parameter on a material instance."""
    body = f"""
asset_path = {python_literal(asset_path)}
parameter_name = {python_literal(parameter_name)}
vector_value = {json_literal(value)}
instance = unreal.EditorAssetLibrary.load_asset(asset_path)
if instance is None:
    _mcp_emit({{"success": False, "error": f"Asset not found: {{asset_path}}"}})
else:
    color = unreal.LinearColor(
        vector_value.get('r', 0.0),
        vector_value.get('g', 0.0),
        vector_value.get('b', 0.0),
        vector_value.get('a', 1.0),
    )
    changed = unreal.MaterialEditingLibrary.set_material_instance_vector_parameter_value(instance, parameter_name, color)
    current_value = unreal.MaterialEditingLibrary.get_material_instance_vector_parameter_value(instance, parameter_name)
    unreal.EditorAssetLibrary.save_loaded_asset(instance)
    _mcp_emit({{
        "success": True,
        "asset_path": asset_path,
        "parameter_name": parameter_name,
        "changed": bool(changed),
        "value": {{
            "r": current_value.r,
            "g": current_value.g,
            "b": current_value.b,
            "a": current_value.a,
        }},
    }})
"""
    return run_editor_python(wrap_editor_python(body))


def set_material_instance_texture_parameter(
    asset_path: str,
    parameter_name: str,
    texture_asset_path: str,
) -> Dict[str, Any]:
    """Set a texture parameter on a material instance."""
    body = f"""
asset_path = {python_literal(asset_path)}
parameter_name = {python_literal(parameter_name)}
texture_asset_path = {python_literal(texture_asset_path)}
instance = unreal.EditorAssetLibrary.load_asset(asset_path)
texture = unreal.EditorAssetLibrary.load_asset(texture_asset_path)
if instance is None:
    _mcp_emit({{"success": False, "error": f"Asset not found: {{asset_path}}"}})
elif texture is None:
    _mcp_emit({{"success": False, "error": f"Texture not found: {{texture_asset_path}}"}})
else:
    changed = unreal.MaterialEditingLibrary.set_material_instance_texture_parameter_value(instance, parameter_name, texture)
    current_value = unreal.MaterialEditingLibrary.get_material_instance_texture_parameter_value(instance, parameter_name)
    unreal.EditorAssetLibrary.save_loaded_asset(instance)
    _mcp_emit({{
        "success": True,
        "asset_path": asset_path,
        "parameter_name": parameter_name,
        "changed": bool(changed),
        "value": unreal.EditorAssetLibrary.get_path_name_for_loaded_asset(current_value) if current_value else None,
    }})
"""
    return run_editor_python(wrap_editor_python(body))
