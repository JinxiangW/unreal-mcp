"""High-level asset tools using UE Python via the editor MCP."""

from __future__ import annotations

from typing import Any, Dict, Optional

from unreal_editor_mcp.tools import get_assets as raw_get_assets
from unreal_harness_runtime.python_exec import (
    json_literal,
    python_literal,
    run_editor_python,
    wrap_editor_python,
)
from unreal_harness_runtime.commandlet_exec import run_python_commandlet


def get_asset_harness_info() -> Dict[str, Any]:
    """Describe the current asset harness backend and scope."""
    return {
        "success": True,
        "domain": "asset",
        "backend": "ue_python_via_run_python",
        "target_backend": "ue_python",
        "supports": [
            "asset_crud",
            "imports_via_commandlet",
            "batch_asset_workflows",
        ],
        "supported_create_types": [
            "Material",
            "MaterialInstanceConstant",
            "World",
        ],
    }


def query_assets_summary(
    path: str = "/Game/",
    asset_class: Optional[str] = None,
    name_filter: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
) -> Dict[str, Any]:
    """Read a compact asset list for common browsing tasks."""
    return raw_get_assets(
        path=path,
        asset_class=asset_class,
        name_filter=name_filter,
        limit=limit,
        offset=offset,
        summary_only=True,
        fields=["name", "path", "class", "package"],
    )


def ensure_asset_with_properties(
    asset_type: str,
    name: str,
    path: str = "/Game/",
    properties: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Create the asset if missing, otherwise update it in place."""
    asset_ref = f"{path.rstrip('/')}/{name}.{name}"
    body = f"""
asset_ref = {python_literal(asset_ref)}
exists = unreal.EditorAssetLibrary.does_asset_exist(asset_ref)
_mcp_emit({{"success": True, "asset_path": asset_ref, "exists": bool(exists)}})
"""
    exists_result = run_editor_python(wrap_editor_python(body))
    if not exists_result.get("success"):
        return exists_result

    if exists_result.get("exists"):
        update_result = update_asset_properties(asset_ref, properties or {})
        update_result["action"] = "updated"
        return update_result

    create_result = create_asset_with_properties(
        asset_type=asset_type,
        name=name,
        path=path,
        properties=properties,
    )
    create_result["action"] = "created"
    return create_result


def create_asset_with_properties(
    asset_type: str,
    name: str,
    path: str = "/Game/",
    properties: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Create a supported asset and optionally set initial properties."""
    body = f"""
asset_type = {python_literal(asset_type)}
asset_name = {python_literal(name)}
asset_path = {python_literal(path.rstrip("/"))}
properties = {python_literal(properties or {})}

asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
asset_class = getattr(unreal, asset_type, None)
factory_cls = None
for candidate in [f"{{asset_type}}FactoryNew", f"{{asset_type}}Factory"]:
    if hasattr(unreal, candidate):
        factory_cls = getattr(unreal, candidate)
        break

if asset_class is None:
    _mcp_emit({{"success": False, "error": f"Unsupported asset class: {{asset_type}}"}})
elif factory_cls is None:
    _mcp_emit({{"success": False, "error": f"No factory found for asset type: {{asset_type}}"}})
else:
    factory = factory_cls()
    created_asset = asset_tools.create_asset(asset_name, asset_path, asset_class, factory)
    if created_asset is None:
        _mcp_emit({{"success": False, "error": f"Failed to create asset {{asset_name}}"}})
    else:
        def _coerce_value(value):
            if isinstance(value, str) and (value.startswith('/Game/') or value.startswith('/Engine/')):
                loaded = unreal.EditorAssetLibrary.load_asset(value)
                return loaded if loaded is not None else value
            return value

        failed = []
        for key, value in properties.items():
            prop_name = 'parent' if key == 'parent_material' else key
            try:
                created_asset.set_editor_property(prop_name, _coerce_value(value))
            except Exception as exc:
                failed.append(f"{{prop_name}}: {{exc}}")

        asset_path_name = unreal.EditorAssetLibrary.get_path_name_for_loaded_asset(created_asset)
        unreal.EditorAssetLibrary.save_loaded_asset(created_asset)
        _mcp_emit({{
            "success": len(failed) == 0,
            "asset_name": created_asset.get_name(),
            "asset_path": asset_path_name,
            "asset_class": asset_type,
            "failed_properties": failed,
        }})
"""
    return run_editor_python(wrap_editor_python(body))


def import_texture_asset(
    source_path: str,
    name: str,
    destination_path: str = "/Game/Textures/",
) -> Dict[str, Any]:
    """Import a texture asset through an isolated Unreal commandlet process."""
    return run_python_commandlet(
        [
            "--mode",
            "texture",
            "--source",
            source_path,
            "--name",
            name,
            "--destination",
            destination_path,
        ]
    )


def import_fbx_asset(
    fbx_path: str,
    destination_path: str = "/Game/ImportedMeshes/",
) -> Dict[str, Any]:
    """Import an FBX asset through an isolated Unreal commandlet process."""
    return run_python_commandlet(
        [
            "--mode",
            "fbx",
            "--source",
            fbx_path,
            "--destination",
            destination_path,
        ]
    )


def update_asset_properties(
    asset_path: str, properties: Dict[str, Any]
) -> Dict[str, Any]:
    """Update asset properties through UE Python."""
    body = f"""
asset_path = {python_literal(asset_path)}
properties = {python_literal(properties)}
asset = unreal.EditorAssetLibrary.load_asset(asset_path)

if asset is None:
    _mcp_emit({{"success": False, "error": f"Asset not found: {{asset_path}}"}})
else:
    def _coerce_value(value):
        if isinstance(value, str) and (value.startswith('/Game/') or value.startswith('/Engine/')):
            loaded = unreal.EditorAssetLibrary.load_asset(value)
            return loaded if loaded is not None else value
        return value

    failed = []
    modified = []
    for key, value in properties.items():
        prop_name = 'parent' if key == 'parent_material' else key
        try:
            asset.set_editor_property(prop_name, _coerce_value(value))
            modified.append(prop_name)
        except Exception as exc:
            failed.append(f"{{prop_name}}: {{exc}}")

    unreal.EditorAssetLibrary.save_loaded_asset(asset)
    _mcp_emit({{
        "success": len(failed) == 0,
        "asset_path": asset_path,
        "modified_properties": modified,
        "failed_properties": failed,
    }})
"""
    return run_editor_python(wrap_editor_python(body))
