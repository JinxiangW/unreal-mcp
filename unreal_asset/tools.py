"""High-level asset tools using UE Python via the editor MCP."""

from __future__ import annotations

import time
from pathlib import Path
import re
from typing import Any, Dict, Optional

from unreal_backend_tcp.common import send_command
from unreal_backend_tcp.tools import get_assets as raw_get_assets
from unreal_harness_runtime.python_exec import (
    json_literal,
    python_literal,
    run_editor_python,
    wrap_editor_python,
)
from unreal_harness_runtime.commandlet_exec import run_python_commandlet
from unreal_harness_runtime.result_format import (
    build_query_summary,
    structured_query_failure,
    structured_query_success,
)


def _new_operation_id(action: str) -> str:
    return f"asset:{action}:{int(time.time() * 1000)}"


def _asset_check(target: str, field: str, expected: Any, actual: Any) -> Dict[str, Any]:
    def _normalize_enum(value: Any) -> Any:
        if isinstance(value, dict) and "name" in value and "value" in value:
            return value
        if isinstance(value, str) and value.startswith("<") and ":" in value and "." in value:
            enum_text = value.strip("<>")
            enum_head, _, enum_value = enum_text.partition(":")
            _, _, enum_name = enum_head.rpartition(".")
            enum_value = enum_value.strip()
            try:
                parsed_value: Any = int(enum_value)
            except ValueError:
                parsed_value = enum_value
            return {"name": enum_name, "value": parsed_value}
        return value

    def _normalize_asset_ref(value: Any) -> Any:
        if not isinstance(value, str):
            return value
        if value.startswith("/Game/") or value.startswith("/Engine/"):
            if "." not in value.rsplit("/", 1)[-1]:
                name = value.rsplit("/", 1)[-1]
                return f"{value}.{name}"
        return value

    normalized_expected = _normalize_asset_ref(_normalize_enum(expected))
    normalized_actual = _normalize_asset_ref(_normalize_enum(actual))

    if isinstance(normalized_actual, dict) and "name" in normalized_actual and "value" in normalized_actual:
        if isinstance(normalized_expected, str):
            normalized_expected = normalized_expected.split(".")[-1]
            if normalized_expected.startswith("<") and ":" in normalized_expected:
                normalized_expected = _normalize_enum(normalized_expected)
        elif isinstance(normalized_expected, int):
            normalized_expected = {"name": normalized_actual["name"], "value": normalized_expected}

    return {
        "target": target,
        "field": field,
        "expected": expected,
        "actual": actual,
        "ok": normalized_expected == normalized_actual,
    }


def _structured_asset_failure(
    operation_id: str,
    target: str | list[str],
    error: str,
    *,
    failed_changes: Optional[list[Dict[str, Any]]] = None,
    post_state: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    targets = target if isinstance(target, list) else [target]
    return {
        "success": False,
        "operation_id": operation_id,
        "domain": "asset",
        "targets": targets,
        "applied_changes": [],
        "failed_changes": failed_changes
        or [
            {
                "target": targets[0] if targets else None,
                "field": "asset",
                "error": error,
            }
        ],
        "post_state": post_state or {},
        "verification": {"verified": False, "checks": []},
        "error": error,
    }


_TEXTURE_LOD_GROUP_SECTION = "[GlobalDefaults DeviceProfile]"
_TEXTURE_LOD_GROUP_PREFIX = "TextureLODGroups="


_ASSET_COERCE_PYTHON_HELPERS = """
import enum

def _mcp_to_simple(value):
    if value is None or isinstance(value, (bool, int, str)):
        return value
    if isinstance(value, float):
        return round(value, 6)
    if isinstance(value, enum.Enum):
        raw_value = value.value
        if isinstance(raw_value, float):
            raw_value = round(raw_value, 6)
        return {"name": value.name, "value": raw_value}
    if isinstance(value, unreal.Vector):
        return {"x": round(value.x, 4), "y": round(value.y, 4), "z": round(value.z, 4)}
    if isinstance(value, unreal.Vector2D):
        return {"x": round(value.x, 4), "y": round(value.y, 4)}
    if hasattr(unreal, "Vector4") and isinstance(value, unreal.Vector4):
        return {"x": round(value.x, 4), "y": round(value.y, 4), "z": round(value.z, 4), "w": round(value.w, 4)}
    if isinstance(value, unreal.Rotator):
        return {"pitch": round(value.pitch, 4), "yaw": round(value.yaw, 4), "roll": round(value.roll, 4)}
    if isinstance(value, unreal.LinearColor):
        return {"r": round(value.r, 4), "g": round(value.g, 4), "b": round(value.b, 4), "a": round(value.a, 4)}
    if isinstance(value, unreal.Color):
        return {"r": value.r, "g": value.g, "b": value.b, "a": value.a}
    if isinstance(value, dict):
        return {str(key): _mcp_to_simple(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_mcp_to_simple(item) for item in value]
    if hasattr(value, "get_path_name"):
        try:
            return unreal.EditorAssetLibrary.get_path_name_for_loaded_asset(value)
        except Exception:
            try:
                return value.get_path_name()
            except Exception:
                pass
    if hasattr(value, "get_name"):
        try:
            return value.get_name()
        except Exception:
            pass
    return str(value)

def _mcp_coerce_asset_value(value):
    if isinstance(value, str) and (value.startswith('/Game/') or value.startswith('/Engine/')):
        loaded = unreal.EditorAssetLibrary.load_asset(value)
        return loaded if loaded is not None else value
    return value

def _mcp_coerce_like(current_value, value):
    value = _mcp_coerce_asset_value(value)
    if current_value is None:
        return value
    if isinstance(current_value, enum.Enum):
        enum_type = type(current_value)
        if isinstance(value, dict):
            candidate_value = value.get("name", value.get("value"))
        else:
            candidate_value = value
        if isinstance(candidate_value, str):
            normalized = candidate_value.split(".")[-1]
            normalized = normalized.split(":")[0].strip("<>")
            for candidate in (candidate_value, candidate_value.upper(), normalized, normalized.upper()):
                if hasattr(enum_type, candidate):
                    return getattr(enum_type, candidate)
        return value
    if isinstance(value, str):
        current_type = type(current_value)
        for candidate in (value, value.upper()):
            if hasattr(current_type, candidate):
                return getattr(current_type, candidate)
    return value

def _mcp_finalize_asset_edit(asset, asset_path, save):
    try:
        asset.modify()
    except Exception:
        pass
    try:
        if hasattr(asset, "post_edit_change"):
            asset.post_edit_change()
    except Exception:
        pass
    try:
        if hasattr(asset, "mark_package_dirty"):
            asset.mark_package_dirty()
    except Exception:
        pass

    if not save:
        return {"saved": False, "save_requested": False}

    save_error = None
    try:
        saved = bool(unreal.EditorAssetLibrary.save_loaded_asset(asset))
        return {"saved": saved, "save_requested": True}
    except Exception as exc:
        save_error = str(exc)

    try:
        saved = bool(unreal.EditorAssetLibrary.save_asset(asset_path))
        payload = {"saved": saved, "save_requested": True}
        if save_error:
            payload["save_fallback_error"] = save_error
        return payload
    except Exception as exc:
        return {
            "saved": False,
            "save_requested": True,
            "save_error": save_error or str(exc),
            "save_fallback_error": str(exc),
        }
"""


_TEXTURE_DEFAULT_PROPERTIES = [
    "compression_settings",
    "srgb",
    "lod_group",
    "max_texture_size",
]


def _coerce_asset_paths(asset_paths: str | list[str], *, field_name: str) -> list[str]:
    if isinstance(asset_paths, str):
        normalized = [asset_paths]
    elif isinstance(asset_paths, list):
        normalized = asset_paths
    else:
        raise ValueError(f"{field_name} must be a string or an array of strings")
    cleaned = [item.strip() for item in normalized if isinstance(item, str) and item.strip()]
    if not cleaned:
        raise ValueError(f"{field_name} must contain at least one asset path")
    return cleaned


def _resolve_project_config_dir() -> Path:
    result = run_editor_python(
        wrap_editor_python(
            """
config_dir = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_config_dir())
_mcp_emit({"success": True, "config_dir": config_dir})
"""
        )
    )
    if not result.get("success") or not result.get("config_dir"):
        raise RuntimeError(result.get("error", "Failed to resolve project config dir"))
    return Path(str(result["config_dir"])).resolve()


def _upsert_texture_lod_group_lines(
    lines: list[str],
    *,
    group_name: str,
    max_lod_size: int,
    section_name: str = _TEXTURE_LOD_GROUP_SECTION,
) -> list[str]:
    pattern = re.compile(
        rf"^([+\-!]?){re.escape(_TEXTURE_LOD_GROUP_PREFIX)}\((.*Group={re.escape(group_name)}\b.*)\)\s*$",
        re.IGNORECASE,
    )
    new_lines = list(lines)
    section_start = None
    insert_at = None
    found_index = None
    for idx, line in enumerate(new_lines):
        stripped = line.strip()
        if stripped == section_name:
            section_start = idx
            insert_at = idx + 1
            continue
        if section_start is not None:
            if stripped.startswith("[") and stripped.endswith("]"):
                break
            if stripped.startswith(("TextureLODGroups=", "+TextureLODGroups=", "-TextureLODGroups=", "!TextureLODGroups=")):
                insert_at = idx + 1
            if pattern.match(stripped):
                found_index = idx
                break

    if section_start is None:
        if new_lines and new_lines[-1].strip():
            new_lines.append("")
        new_lines.append(section_name)
        insert_at = len(new_lines)

    if found_index is not None:
        line = new_lines[found_index]
        replaced = re.sub(r"MaxLODSize=\d+", f"MaxLODSize={max_lod_size}", line)
        if replaced == line:
            prefix = "+" if line.lstrip().startswith("+") else ""
            inner = line.split("(", 1)[1].rsplit(")", 1)[0]
            replaced = f"{prefix}{_TEXTURE_LOD_GROUP_PREFIX}({inner},MaxLODSize={max_lod_size})"
        new_lines[found_index] = replaced
        return new_lines

    entry = (
        f"+{_TEXTURE_LOD_GROUP_PREFIX}("
        f"Group={group_name},MinLODSize=1,MaxLODSize={max_lod_size},"
        "LODBias=0,MinMagFilter=aniso,MipFilter=point,MipGenSettings=TMGS_SimpleAverage)"
    )
    new_lines.insert(insert_at or len(new_lines), entry)
    return new_lines


def get_asset_harness_info() -> Dict[str, Any]:
    """Describe the current asset harness backend and scope."""
    payload = {
        "domain": "asset",
        "backend": "ue_python_via_run_python",
        "target_backend": "ue_python",
        "supports": [
            "asset_crud",
            "asset_property_reads",
            "asset_property_writes",
            "imports_via_commandlet",
            "batch_asset_workflows",
            "texture_property_workflows",
            "cascade_particle_inspection",
        ],
        "supported_create_types": [
            "Material",
            "MaterialInstanceConstant",
            "World",
        ],
    }
    return {
        "success": True,
        "operation_id": _new_operation_id("get_asset_harness_info"),
        "domain": "asset",
        "targets": ["asset_harness"],
        "applied_changes": [],
        "failed_changes": [],
        "post_state": {"asset_harness": payload},
        "verification": {"verified": True, "checks": []},
        **payload,
    }


def query_assets_summary(
    path: str = "/Game/",
    asset_class: Optional[str] = None,
    name_filter: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
) -> Dict[str, Any]:
    """Read a compact asset list for common browsing tasks."""
    operation_id = _new_operation_id("query_assets_summary")
    result = raw_get_assets(
        path=path,
        asset_class=asset_class,
        name_filter=name_filter,
        limit=limit,
        offset=offset,
        summary_only=True,
        fields=["name", "path", "class", "package"],
    )
    inner = result.get("result") or {}
    assets = inner.get("assets", [])
    success = bool((result.get("status") == "success") and inner.get("success", True))
    filters = {
        "path": path,
        "asset_class": asset_class,
        "name_filter": name_filter,
        "limit": inner.get("limit", limit),
        "offset": inner.get("offset", offset),
    }
    summary = build_query_summary(
        requested=inner.get("limit", limit),
        returned=inner.get("returned_count", len(assets)),
        total=inner.get("total_count", len(assets)),
        offset=inner.get("offset", offset),
        verified=inner.get("returned_count", len(assets)) if success else 0,
    )

    if not success:
        error = (
            result.get("error")
            or inner.get("error")
            or inner.get("message")
            or "query_assets_summary failed"
        )
        return structured_query_failure(
            operation_id=operation_id,
            domain="asset",
            target=path,
            error=error,
            summary=summary,
            filters=filters,
            post_state={
                path: {
                    "count": inner.get("total_count", len(assets)),
                    "returned_count": inner.get("returned_count", len(assets)),
                    "assets": assets,
                }
            }
            if assets
            else {},
            result=inner,
            extra={"path": path},
        )

    return structured_query_success(
        operation_id=operation_id,
        domain="asset",
        targets=[item.get("path") for item in assets if item.get("path")],
        post_state={
            path: {
                "count": inner.get("total_count", len(assets)),
                "returned_count": inner.get("returned_count", len(assets)),
                "assets": assets,
            }
        },
        summary=summary,
        items=[
            {
                "target": item.get("path"),
                "success": True,
                "verification": {"verified": True, "checks": []},
            }
            for item in assets
        ],
        filters=filters,
        extra={"path": path, "result": inner},
    )


def ensure_folder(path: str) -> Dict[str, Any]:
    """Ensure a content browser folder exists."""
    operation_id = _new_operation_id("ensure_folder")
    normalized_path = path.rstrip("/") or "/Game"
    body = f"""
folder_path = {python_literal(normalized_path)}
exists_before = unreal.EditorAssetLibrary.does_directory_exist(folder_path)
created = unreal.EditorAssetLibrary.make_directory(folder_path)
exists_after = unreal.EditorAssetLibrary.does_directory_exist(folder_path)
_mcp_emit({{
    "success": bool(exists_after),
    "folder_path": folder_path,
    "exists_before": bool(exists_before),
    "created": bool(created) and not bool(exists_before),
    "exists_after": bool(exists_after),
}})
"""
    result = run_editor_python(wrap_editor_python(body))
    if not result.get("success"):
        return _structured_asset_failure(
            operation_id, normalized_path, result.get("error", "ensure_folder failed")
        )
    checks = [
        _asset_check(normalized_path, "exists_after", True, result.get("exists_after")),
    ]
    verified = all(item["ok"] for item in checks)
    return {
        "success": verified,
        "operation_id": operation_id,
        "domain": "asset",
        "targets": [normalized_path],
        "applied_changes": [
            {"target": normalized_path, "field": "directory", "value": "ensured"}
        ],
        "failed_changes": [],
        "post_state": {
            normalized_path: {
                "exists_before": result.get("exists_before"),
                "created": result.get("created"),
                "exists_after": result.get("exists_after"),
            }
        },
        "verification": {"verified": verified, "checks": checks},
        "folder_path": normalized_path,
    }


def ensure_asset_with_properties(
    asset_type: str,
    name: str,
    path: str = "/Game/",
    properties: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Create the asset if missing, otherwise update it in place."""
    operation_id = _new_operation_id("ensure_asset_with_properties")
    asset_ref = f"{path.rstrip('/')}/{name}.{name}"
    body = f"""
asset_ref = {python_literal(asset_ref)}
exists = unreal.EditorAssetLibrary.does_asset_exist(asset_ref)
_mcp_emit({{"success": True, "asset_path": asset_ref, "exists": bool(exists)}})
"""
    exists_result = run_editor_python(wrap_editor_python(body))
    if not exists_result.get("success"):
        return _structured_asset_failure(
            operation_id,
            asset_ref,
            exists_result.get("error", "asset existence check failed"),
        )

    if exists_result.get("exists"):
        update_result = update_asset_properties(asset_ref, properties or {})
        update_result["action"] = "updated"
        update_result["operation_id"] = operation_id
        return update_result

    create_result = create_asset_with_properties(
        asset_type=asset_type,
        name=name,
        path=path,
        properties=properties,
    )
    create_result["action"] = "created"
    create_result["operation_id"] = operation_id
    return create_result


def duplicate_asset_with_overrides(
    source_asset_path: str,
    destination_path: str,
    new_name: str,
    properties: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Duplicate an asset and optionally apply property overrides."""
    operation_id = _new_operation_id("duplicate_asset_with_overrides")
    destination_asset_path = f"{destination_path.rstrip('/')}/{new_name}.{new_name}"
    body = f"""
source_asset_path = {python_literal(source_asset_path)}
destination_path = {python_literal(destination_path.rstrip("/"))}
new_name = {python_literal(new_name)}
destination_asset_path = {python_literal(destination_asset_path)}

if not unreal.EditorAssetLibrary.does_asset_exist(source_asset_path):
    _mcp_emit({{"success": False, "error": f"Source asset not found: {{source_asset_path}}"}})
else:
    unreal.EditorAssetLibrary.make_directory(destination_path)
    duplicated = unreal.EditorAssetLibrary.duplicate_asset(source_asset_path, destination_asset_path)
    _mcp_emit({{
        "success": bool(duplicated),
        "source_asset_path": source_asset_path,
        "asset_path": destination_asset_path,
        "duplicated": bool(duplicated),
    }})
"""
    duplicate_result = run_editor_python(wrap_editor_python(body))
    if not duplicate_result.get("success"):
        return _structured_asset_failure(
            operation_id,
            destination_asset_path,
            duplicate_result.get("error", "asset duplication failed"),
        )
    if properties:
        update_result = update_asset_properties(destination_asset_path, properties)
        update_result["source_asset_path"] = source_asset_path
        update_result["duplicated_asset_path"] = destination_asset_path
        update_result["operation_id"] = operation_id
        return update_result
    checks = [
        _asset_check(
            destination_asset_path,
            "duplicated",
            True,
            duplicate_result.get("duplicated"),
        )
    ]
    verified = all(item["ok"] for item in checks)
    return {
        "success": verified,
        "operation_id": operation_id,
        "domain": "asset",
        "targets": [destination_asset_path],
        "applied_changes": [
            {
                "target": destination_asset_path,
                "field": "duplicated_from",
                "value": source_asset_path,
            }
        ],
        "failed_changes": [],
        "post_state": {
            destination_asset_path: {
                "source_asset_path": source_asset_path,
                "duplicated": duplicate_result.get("duplicated"),
            }
        },
        "verification": {"verified": verified, "checks": checks},
        "source_asset_path": source_asset_path,
        "duplicated_asset_path": destination_asset_path,
    }


def move_asset_batch(items: list[Dict[str, str]]) -> Dict[str, Any]:
    """Move multiple assets to new package paths."""
    if not items:
        return _structured_asset_failure(
            _new_operation_id("move_asset_batch"), [], "items must not be empty"
        )

    operation_id = _new_operation_id("move_asset_batch")

    body = f"""
items = {python_literal(items)}
results = []
failed = []

for item in items:
    source_asset_path = item.get('source_asset_path')
    destination_asset_path = item.get('destination_asset_path')
    if not source_asset_path or not destination_asset_path:
        failed.append({{"item": item, "error": "source_asset_path and destination_asset_path are required"}})
        continue
    destination_dir = '/'.join(destination_asset_path.split('/')[:-1])
    if destination_dir:
        unreal.EditorAssetLibrary.make_directory(destination_dir)
    if not unreal.EditorAssetLibrary.does_asset_exist(source_asset_path):
        failed.append({{"item": item, "error": f"Asset not found: {{source_asset_path}}"}})
        continue
    moved = unreal.EditorAssetLibrary.rename_asset(source_asset_path, destination_asset_path)
    payload = {{
        "source_asset_path": source_asset_path,
        "destination_asset_path": destination_asset_path,
        "success": bool(moved),
    }}
    if moved:
        results.append(payload)
    else:
        payload["error"] = "rename_asset returned false"
        failed.append(payload)

_mcp_emit({{
    "success": len(failed) == 0,
    "summary": {{
        "requested": len(items),
        "succeeded": len(results),
        "failed": len(failed),
    }},
    "success_items": results,
    "failed_items": failed,
}})
"""
    result = run_editor_python(wrap_editor_python(body))
    if not result.get("success") and not result.get("summary"):
        return _structured_asset_failure(
            operation_id,
            [item.get("destination_asset_path") for item in items],
            result.get("error", "move_asset_batch failed"),
        )
    success_items = result.get("success_items", [])
    failed_items = result.get("failed_items", [])
    checks = [
        _asset_check(
            item.get("destination_asset_path"), "moved", True, item.get("success")
        )
        for item in success_items
    ]
    structured_items = []
    for item in success_items:
        target = item.get("destination_asset_path")
        item_checks = [check for check in checks if check["target"] == target]
        structured_items.append(
            {
                "target": target,
                "success": True,
                "verification": {
                    "verified": all(check["ok"] for check in item_checks),
                    "checks": item_checks,
                },
            }
        )
    for item in failed_items:
        structured_items.append(
            {
                "target": item.get("destination_asset_path") or item.get("item"),
                "success": False,
                "error": item.get("error"),
            }
        )
    verified = all(item["ok"] for item in checks) and not failed_items
    summary = dict(result.get("summary") or {})
    summary["verified"] = len(success_items) if verified else 0
    return {
        "success": verified,
        "operation_id": operation_id,
        "domain": "asset",
        "targets": [
            item.get("destination_asset_path")
            for item in items
            if item.get("destination_asset_path")
        ],
        "applied_changes": [
            {
                "target": item.get("destination_asset_path"),
                "field": "asset_path",
                "value": item.get("destination_asset_path"),
            }
            for item in success_items
        ],
        "failed_changes": [
            {
                "target": item.get("destination_asset_path") or item.get("item"),
                "field": "asset_path",
                "error": item.get("error"),
            }
            for item in failed_items
        ],
        "post_state": {
            item.get("destination_asset_path"): {
                "asset_path": item.get("destination_asset_path")
            }
            for item in success_items
            if item.get("destination_asset_path")
        },
        "verification": {"verified": verified, "checks": checks},
        "summary": summary,
        "items": structured_items,
        "success_items": success_items,
        "failed_items": failed_items,
    }


def get_asset_properties(
    asset_paths: str | list[str],
    properties: list[str],
) -> Dict[str, Any]:
    """Read selected editor properties from one or more assets."""
    operation_id = _new_operation_id("get_asset_properties")
    try:
        normalized_asset_paths = _coerce_asset_paths(
            asset_paths, field_name="asset_paths"
        )
    except ValueError as exc:
        return _structured_asset_failure(operation_id, [], str(exc))
    if not isinstance(properties, list) or not all(
        isinstance(item, str) and item.strip() for item in properties
    ):
        return _structured_asset_failure(
            operation_id,
            normalized_asset_paths,
            "properties must be an array of non-empty strings",
        )

    requested_properties = [item.strip() for item in properties]
    body = f"""
asset_paths = {python_literal(normalized_asset_paths)}
properties = {python_literal(requested_properties)}
results = []
{_ASSET_COERCE_PYTHON_HELPERS}

for asset_path in asset_paths:
    asset = unreal.EditorAssetLibrary.load_asset(asset_path)
    if asset is None:
        results.append({{
            "success": False,
            "asset_path": asset_path,
            "properties": {{}},
            "failed_properties": [f"asset: Asset not found: {{asset_path}}"],
        }})
        continue

    property_payload = {{}}
    failed = []
    for key in properties:
        prop_name = 'parent' if key == 'parent_material' else key
        try:
            actual_value = asset.get_editor_property(prop_name)
            property_payload[prop_name] = _mcp_to_simple(actual_value)
        except Exception as exc:
            failed.append(f"{{prop_name}}: {{exc}}")

    results.append({{
        "success": len(failed) == 0,
        "asset_path": asset_path,
        "properties": property_payload,
        "failed_properties": failed,
    }})

_mcp_emit({{
    "success": all(item.get("success", False) for item in results),
    "summary": {{
        "requested": len(asset_paths),
        "succeeded": sum(1 for item in results if item.get("success")),
        "failed": sum(1 for item in results if not item.get("success")),
    }},
    "results": results,
}})
"""
    result = run_editor_python(wrap_editor_python(body))
    if not result.get("results"):
        return _structured_asset_failure(
            operation_id,
            normalized_asset_paths,
            result.get("error", "get_asset_properties failed"),
        )

    result_items = result.get("results", [])
    checks = []
    failed_changes = []
    post_state: Dict[str, Any] = {}
    items = []
    for item_result in result_items:
        asset_path = item_result.get("asset_path")
        properties_payload = item_result.get("properties") or {}
        post_state[asset_path or "<missing>"] = properties_payload
        item_checks = []

        for requested_property in requested_properties:
            prop_name = (
                "parent"
                if requested_property == "parent_material"
                else requested_property
            )
            if prop_name in properties_payload:
                check = {
                    "target": asset_path,
                    "field": prop_name,
                    "expected": "readable",
                    "actual": True,
                    "ok": True,
                }
                checks.append(check)
                item_checks.append(check)

        for failure in item_result.get("failed_properties", []):
            failed_changes.append(
                {
                    "target": asset_path,
                    "field": failure.split(":", 1)[0],
                    "error": failure,
                }
            )

        item_payload = {
            "target": asset_path,
            "success": bool(item_result.get("success", False)),
            "verification": {
                "verified": not item_result.get("failed_properties"),
                "checks": item_checks,
            },
            "properties": properties_payload,
        }
        if item_result.get("failed_properties"):
            item_payload["error"] = "; ".join(item_result["failed_properties"])
        items.append(item_payload)

    verified = not failed_changes
    summary = dict(result.get("summary") or {})
    summary["verified"] = summary.get("succeeded", 0) if verified else 0
    return {
        "success": verified,
        "operation_id": operation_id,
        "domain": "asset",
        "targets": normalized_asset_paths,
        "applied_changes": [],
        "failed_changes": failed_changes,
        "post_state": post_state,
        "verification": {"verified": verified, "checks": checks},
        "summary": summary,
        "items": items,
        "properties": requested_properties,
        "results": result_items,
    }


def set_asset_properties(
    asset_paths: str | list[str],
    properties: Dict[str, Any],
    save: bool = True,
) -> Dict[str, Any]:
    """Update one shared property payload across multiple assets."""
    operation_id = _new_operation_id("set_asset_properties")
    try:
        normalized_asset_paths = _coerce_asset_paths(
            asset_paths, field_name="asset_paths"
        )
    except ValueError as exc:
        return _structured_asset_failure(operation_id, [], str(exc))
    if not isinstance(properties, dict) or not properties:
        return _structured_asset_failure(
            operation_id,
            normalized_asset_paths,
            "properties must be a non-empty object",
        )

    body = f"""
asset_paths = {python_literal(normalized_asset_paths)}
properties = {python_literal(properties)}
save = {str(save)}
results = []
{_ASSET_COERCE_PYTHON_HELPERS}

for asset_path in asset_paths:
    asset = unreal.EditorAssetLibrary.load_asset(asset_path)
    if asset is None:
        results.append({{
            "success": False,
            "asset_path": asset_path,
            "modified_properties": [],
            "post_state": {{}},
            "failed_properties": [f"asset: Asset not found: {{asset_path}}"],
            "save_result": {{"save_requested": save, "saved": False}},
        }})
        continue

    failed = []
    modified = []
    post_state = {{}}
    for key, value in properties.items():
        prop_name = 'parent' if key == 'parent_material' else key
        try:
            current_value = asset.get_editor_property(prop_name)
            coerced_value = _mcp_coerce_like(current_value, value)
            asset.set_editor_property(prop_name, coerced_value)
            modified.append(prop_name)
            actual_value = asset.get_editor_property(prop_name)
            post_state[prop_name] = _mcp_to_simple(actual_value)
        except Exception as exc:
            failed.append(f"{{prop_name}}: {{exc}}")

    save_result = _mcp_finalize_asset_edit(asset, asset_path, save)
    if save and not save_result.get("saved", False):
        failed.append(
            "save: " + str(save_result.get("save_error") or save_result.get("save_fallback_error") or "save failed")
        )

    results.append({{
        "success": len(failed) == 0,
        "asset_path": asset_path,
        "modified_properties": modified,
        "post_state": post_state,
        "failed_properties": failed,
        "save_result": save_result,
    }})

_mcp_emit({{
    "success": all(item.get("success", False) for item in results),
    "summary": {{
        "requested": len(asset_paths),
        "succeeded": sum(1 for item in results if item.get("success")),
        "failed": sum(1 for item in results if not item.get("success")),
    }},
    "results": results,
}})
"""
    result = run_editor_python(wrap_editor_python(body))
    if not result.get("results"):
        return _structured_asset_failure(
            operation_id,
            normalized_asset_paths,
            result.get("error", "set_asset_properties failed"),
        )

    result_items = result.get("results", [])
    checks = []
    applied_changes = []
    failed_changes = []
    post_state: Dict[str, Any] = {}
    items = []
    for item_result in result_items:
        asset_path = item_result.get("asset_path")
        item_post_state = item_result.get("post_state") or {}
        post_state[asset_path or "<missing>"] = item_post_state
        item_checks = []

        for field in item_result.get("modified_properties", []):
            requested_key = (
                "parent_material" if field == "parent" and "parent_material" in properties else field
            )
            requested_value = properties.get(requested_key)
            check = _asset_check(
                asset_path or "<missing>",
                field,
                requested_value,
                item_post_state.get(field),
            )
            checks.append(check)
            item_checks.append(check)
            applied_changes.append(
                {
                    "target": asset_path,
                    "field": field,
                    "value": requested_value,
                }
            )

        for failure in item_result.get("failed_properties", []):
            failed_changes.append(
                {
                    "target": asset_path,
                    "field": failure.split(":", 1)[0],
                    "error": failure,
                }
            )

        item_payload = {
            "target": asset_path,
            "success": bool(item_result.get("success", False)),
            "verification": {
                "verified": all(check["ok"] for check in item_checks)
                and not item_result.get("failed_properties"),
                "checks": item_checks,
            },
            "save_result": item_result.get("save_result") or {},
        }
        if item_result.get("failed_properties"):
            item_payload["error"] = "; ".join(item_result["failed_properties"])
        items.append(item_payload)

    verified = not failed_changes and all(item["ok"] for item in checks)
    summary = dict(result.get("summary") or {})
    summary["verified"] = summary.get("succeeded", 0) if verified else 0
    return {
        "success": verified,
        "operation_id": operation_id,
        "domain": "asset",
        "targets": normalized_asset_paths,
        "applied_changes": applied_changes,
        "failed_changes": failed_changes,
        "post_state": post_state,
        "verification": {"verified": verified, "checks": checks},
        "summary": summary,
        "items": items,
        "properties": properties,
        "save": save,
        "results": result_items,
    }


def query_textures(
    path: str = "/Game/",
    name_filter: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
    properties: Optional[list[str]] = None,
) -> Dict[str, Any]:
    """Query textures and inline selected editor properties."""
    operation_id = _new_operation_id("query_textures")
    requested_properties = properties or list(_TEXTURE_DEFAULT_PROPERTIES)
    base_result = raw_get_assets(
        path=path,
        asset_class="Texture2D",
        name_filter=name_filter,
        limit=limit,
        offset=offset,
        summary_only=True,
        fields=["name", "path", "class", "package"],
    )
    inner = base_result.get("result") or {}
    textures = inner.get("assets", [])
    success = bool(
        (base_result.get("status") == "success") and inner.get("success", True)
    )
    filters = {
        "path": path,
        "name_filter": name_filter,
        "limit": inner.get("limit", limit),
        "offset": inner.get("offset", offset),
        "properties": requested_properties,
    }
    summary = build_query_summary(
        requested=inner.get("limit", limit),
        returned=inner.get("returned_count", len(textures)),
        total=inner.get("total_count", len(textures)),
        offset=inner.get("offset", offset),
        verified=inner.get("returned_count", len(textures)) if success else 0,
    )
    if not success:
        return structured_query_failure(
            operation_id=operation_id,
            domain="asset",
            target=path,
            error=base_result.get("error")
            or inner.get("error")
            or inner.get("message")
            or "query_textures failed",
            summary=summary,
            filters=filters,
            result=inner,
            extra={"path": path},
        )

    property_result = (
        get_asset_properties(
            [item.get("path") for item in textures if item.get("path")],
            requested_properties,
        )
        if textures
        else {
            "success": True,
            "failed_changes": [],
            "post_state": {},
            "items": [],
            "summary": {"verified": 0},
        }
    )
    property_state = property_result.get("post_state") or {}
    property_failures = property_result.get("failed_changes") or []

    merged_items = []
    for texture in textures:
        texture_path = texture.get("path")
        merged_items.append(
            {
                **texture,
                "properties": property_state.get(texture_path, {}),
            }
        )

    verified = not property_failures
    summary = build_query_summary(
        requested=inner.get("limit", limit),
        returned=len(merged_items),
        total=inner.get("total_count", len(merged_items)),
        offset=inner.get("offset", offset),
        verified=len(merged_items) if verified else 0,
    )
    return {
        "success": verified,
        "operation_id": operation_id,
        "domain": "asset",
        "targets": [item.get("path") for item in merged_items if item.get("path")],
        "applied_changes": [],
        "failed_changes": property_failures,
        "post_state": {path: {"textures": merged_items}},
        "verification": {
            "verified": verified,
            "checks": property_result.get("verification", {}).get("checks", []),
        },
        "summary": summary,
        "items": [
            {
                "target": item.get("path"),
                "success": not any(
                    failure.get("target") == item.get("path")
                    for failure in property_failures
                ),
                "verification": {"verified": verified, "checks": []},
                "properties": item.get("properties", {}),
            }
            for item in merged_items
        ],
        "filters": filters,
        "textures": merged_items,
    }


def set_texture_compression_settings(
    texture_paths: str | list[str],
    compression_settings: str,
    save: bool = True,
) -> Dict[str, Any]:
    """Set `compression_settings` on one or more textures."""
    result = set_asset_properties(
        texture_paths,
        {"compression_settings": compression_settings},
        save=save,
    )
    result["operation_id"] = _new_operation_id("set_texture_compression_settings")
    result["compression_settings"] = compression_settings
    return result


def set_texture_srgb(
    texture_paths: str | list[str],
    srgb: bool,
    save: bool = True,
) -> Dict[str, Any]:
    """Set `srgb` on one or more textures."""
    result = set_asset_properties(
        texture_paths,
        {"srgb": bool(srgb)},
        save=save,
    )
    result["operation_id"] = _new_operation_id("set_texture_srgb")
    result["srgb"] = bool(srgb)
    return result


def inspect_particle_system(
    asset_path: str,
    emitter_names: Optional[list[str]] = None,
) -> Dict[str, Any]:
    """Inspect a Cascade particle system and summarize emitter/material usage."""
    operation_id = _new_operation_id("inspect_particle_system")
    if emitter_names is not None and (
        not isinstance(emitter_names, list)
        or not all(isinstance(item, str) and item.strip() for item in emitter_names)
    ):
        return _structured_asset_failure(
            operation_id,
            asset_path,
            "emitter_names must be an array of non-empty strings when provided",
        )

    body = f"""
asset_path = {python_literal(asset_path)}
requested_emitters = set({python_literal(emitter_names or [])})
{_ASSET_COERCE_PYTHON_HELPERS}

asset = unreal.EditorAssetLibrary.load_asset(asset_path)
if asset is None:
    _mcp_emit({{"success": False, "error": f"Asset not found: {{asset_path}}"}})
else:
    asset_class = asset.get_class().get_name() if hasattr(asset, "get_class") else type(asset).__name__
    if asset_class != "ParticleSystem":
        _mcp_emit({{
            "success": False,
            "error": f"inspect_particle_system currently supports Cascade ParticleSystem only, got {{asset_class}}",
            "asset_class": asset_class,
        }})
    else:
        emitters = []
        for emitter in asset.get_editor_property("emitters") or []:
            emitter_name = emitter.get_name() if hasattr(emitter, "get_name") else str(emitter)
            if requested_emitters and emitter_name not in requested_emitters:
                continue
            lod_levels = []
            try:
                lod_levels = list(emitter.get_editor_property("lod_levels") or [])
            except Exception:
                lod_levels = []
            primary_lod = lod_levels[0] if lod_levels else None
            required_module = None
            spawn_module = None
            modules = []
            if primary_lod is not None:
                try:
                    required_module = primary_lod.get_editor_property("required_module")
                except Exception:
                    required_module = None
                try:
                    spawn_module = primary_lod.get_editor_property("spawn_module")
                except Exception:
                    spawn_module = None
                try:
                    modules = list(primary_lod.get_editor_property("modules") or [])
                except Exception:
                    modules = []

            material_path = None
            screen_alignment = None
            subuv_module = None
            dynamic_module = None
            if required_module is not None:
                try:
                    material = required_module.get_editor_property("material")
                    material_path = _mcp_to_simple(material)
                except Exception:
                    material_path = None
                try:
                    screen_alignment = _mcp_to_simple(required_module.get_editor_property("screen_alignment"))
                except Exception:
                    screen_alignment = None

            module_summaries = []
            all_modules = ([required_module] if required_module else []) + ([spawn_module] if spawn_module else []) + modules
            seen_modules = set()
            for module in all_modules:
                if module is None:
                    continue
                module_name = module.get_name() if hasattr(module, "get_name") else str(module)
                if module_name in seen_modules:
                    continue
                seen_modules.add(module_name)
                module_class = module.get_class().get_name() if hasattr(module, "get_class") else type(module).__name__
                module_payload = {{"name": module_name, "class": module_class}}
                if "SubUV" in module_class and subuv_module is None:
                    subuv_module = module_payload
                if "Dynamic" in module_class and dynamic_module is None:
                    dynamic_module = module_payload
                module_summaries.append(module_payload)

            emitters.append({{
                "name": emitter_name,
                "lod_count": len(lod_levels),
                "required_material": material_path,
                "required_screen_alignment": screen_alignment,
                "subuv_module": subuv_module,
                "dynamic_module": dynamic_module,
                "modules": module_summaries,
            }})

        _mcp_emit({{
            "success": True,
            "asset_path": asset_path,
            "asset_class": asset_class,
            "emitter_count": len(emitters),
            "emitters": emitters,
        }})
"""
    result = run_editor_python(wrap_editor_python(body))
    if not result.get("success"):
        if result.get("asset_class") == "NiagaraSystem":
            niagara_response = send_command(
                "get_niagara_emitter",
                {"asset_path": asset_path},
            )
            niagara_body = (
                niagara_response.get("result")
                if niagara_response.get("status") == "success"
                else None
            ) or {}
            if niagara_body.get("success"):
                emitters = niagara_body.get("emitters", [])
                checks = [
                    _asset_check(asset_path, "asset_class", "NiagaraSystem", "NiagaraSystem"),
                    _asset_check(
                        asset_path,
                        "emitter_count",
                        niagara_body.get("emitter_count", len(emitters)),
                        len(emitters),
                    ),
                ]
                verified = all(item["ok"] for item in checks)
                return {
                    "success": verified,
                    "operation_id": operation_id,
                    "domain": "asset",
                    "targets": [asset_path],
                    "applied_changes": [],
                    "failed_changes": [],
                    "post_state": {
                        asset_path: {
                            "asset_class": "NiagaraSystem",
                            "emitter_count": niagara_body.get("emitter_count", len(emitters)),
                            "emitters": emitters,
                        }
                    },
                    "verification": {"verified": verified, "checks": checks},
                    "asset_path": asset_path,
                    "asset_class": "NiagaraSystem",
                    "emitter_count": niagara_body.get("emitter_count", len(emitters)),
                    "emitters": emitters,
                }
        return _structured_asset_failure(
            operation_id,
            asset_path,
            result.get("error", "inspect_particle_system failed"),
            post_state={asset_path: {"asset_class": result.get("asset_class")}}
            if result.get("asset_class")
            else None,
        )

    emitters = result.get("emitters", [])
    checks = [
        _asset_check(asset_path, "asset_class", "ParticleSystem", result.get("asset_class")),
        _asset_check(asset_path, "emitter_count", len(emitters), result.get("emitter_count")),
    ]
    verified = all(item["ok"] for item in checks)
    return {
        "success": verified,
        "operation_id": operation_id,
        "domain": "asset",
        "targets": [asset_path],
        "applied_changes": [],
        "failed_changes": [],
        "post_state": {
            asset_path: {
                "asset_class": result.get("asset_class"),
                "emitter_count": result.get("emitter_count"),
                "emitters": emitters,
            }
        },
        "verification": {"verified": verified, "checks": checks},
        "asset_path": asset_path,
        "asset_class": result.get("asset_class"),
        "emitter_count": result.get("emitter_count"),
        "emitters": emitters,
    }


def inspect_cascade_emitter(
    asset_path: str,
    emitter_name: str,
) -> Dict[str, Any]:
    """Inspect one named Cascade emitter inside a particle system."""
    operation_id = _new_operation_id("inspect_cascade_emitter")
    if not isinstance(emitter_name, str) or not emitter_name.strip():
        return _structured_asset_failure(
            operation_id,
            asset_path,
            "emitter_name must be a non-empty string",
        )

    result = inspect_particle_system(asset_path=asset_path, emitter_names=[emitter_name])
    if not result.get("success"):
        result["operation_id"] = operation_id
        return result

    emitters = result.get("emitters", [])
    if not emitters:
        return _structured_asset_failure(
            operation_id,
            asset_path,
            f"Cascade emitter not found: {emitter_name}",
            post_state={asset_path: {"emitters": []}},
        )
    emitter_payload = emitters[0]
    return {
        "success": True,
        "operation_id": operation_id,
        "domain": "asset",
        "targets": [asset_path, emitter_name],
        "applied_changes": [],
        "failed_changes": [],
        "post_state": {asset_path: {"emitter": emitter_payload}},
        "verification": {
            "verified": True,
            "checks": [_asset_check(asset_path, "emitter_name", emitter_name, emitter_payload.get("name"))],
        },
        "asset_path": asset_path,
        "emitter": emitter_payload,
    }


def update_asset_properties_batch(items: list[Dict[str, Any]]) -> Dict[str, Any]:
    """Update multiple assets through one UE Python round-trip."""
    if not items:
        return _structured_asset_failure(
            _new_operation_id("update_asset_properties_batch"),
            [],
            "items must not be empty",
        )

    operation_id = _new_operation_id("update_asset_properties_batch")
    body = f"""
items = {python_literal(items)}
results = []
{_ASSET_COERCE_PYTHON_HELPERS}

for item in items:
    asset_path = item.get('asset_path')
    properties = item.get('properties') or {{}}
    if not asset_path:
        results.append({{
            "success": False,
            "asset_path": None,
            "failed_properties": ["asset_path: Missing asset_path"],
            "modified_properties": [],
            "post_state": {{}},
        }})
        continue

    asset = unreal.EditorAssetLibrary.load_asset(asset_path)
    if asset is None:
        results.append({{
            "success": False,
            "asset_path": asset_path,
            "failed_properties": [f"asset: Asset not found: {{asset_path}}"],
            "modified_properties": [],
            "post_state": {{}},
        }})
        continue

    failed = []
    modified = []
    post_state = {{}}

    for key, value in properties.items():
        prop_name = 'parent' if key == 'parent_material' else key
        try:
            current_value = asset.get_editor_property(prop_name)
            asset.set_editor_property(prop_name, _mcp_coerce_like(current_value, value))
            modified.append(prop_name)
            actual_value = asset.get_editor_property(prop_name)
            post_state[prop_name] = _mcp_to_simple(actual_value)
        except Exception as exc:
            failed.append(f"{{prop_name}}: {{exc}}")

    save_result = _mcp_finalize_asset_edit(asset, asset_path, True)
    if not save_result.get("saved", False):
        failed.append("save: " + str(save_result.get("save_error") or save_result.get("save_fallback_error") or "save failed"))
    results.append({{
        "success": len(failed) == 0,
        "asset_path": asset_path,
        "modified_properties": modified,
        "post_state": post_state,
        "failed_properties": failed,
        "save_result": save_result,
    }})

_mcp_emit({{
    "success": all(item.get("success", False) for item in results),
    "summary": {{
        "requested": len(items),
        "succeeded": sum(1 for item in results if item.get("success")),
        "failed": sum(1 for item in results if not item.get("success")),
    }},
    "results": results,
}})
"""
    result = run_editor_python(wrap_editor_python(body))
    if not result.get("summary") and not result.get("results"):
        return _structured_asset_failure(
            operation_id,
            [item.get("asset_path") for item in items if item.get("asset_path")],
            result.get("error", "update_asset_properties_batch failed"),
        )

    result_items = result.get("results", [])
    checks = []
    applied_changes = []
    failed_changes = []
    post_state: Dict[str, Any] = {}
    structured_items = []
    requested_by_asset = {
        item.get("asset_path"): item.get("properties", {}) or {}
        for item in items
        if item.get("asset_path")
    }

    for item_result in result_items:
        asset_path = item_result.get("asset_path")
        requested_properties = requested_by_asset.get(asset_path, {})
        item_post_state = item_result.get("post_state") or {}
        post_state[asset_path or "<missing>"] = item_post_state
        item_checks = []

        for field in item_result.get("modified_properties", []):
            requested_key = (
                "parent_material"
                if field == "parent" and "parent_material" in requested_properties
                else field
            )
            check = _asset_check(
                asset_path or "<missing>",
                field,
                requested_properties.get(requested_key),
                item_post_state.get(field),
            )
            checks.append(check)
            item_checks.append(check)
            applied_changes.append(
                {
                    "target": asset_path,
                    "field": field,
                    "value": requested_properties.get(requested_key),
                }
            )

        for failure in item_result.get("failed_properties", []):
            failed_changes.append(
                {
                    "target": asset_path,
                    "field": failure.split(":", 1)[0],
                    "error": failure,
                }
            )

        structured_item = {
            "target": asset_path,
            "success": bool(item_result.get("success", False)),
            "verification": {
                "verified": all(check["ok"] for check in item_checks)
                and not item_result.get("failed_properties"),
                "checks": item_checks,
            },
        }
        if item_result.get("failed_properties"):
            structured_item["error"] = "; ".join(item_result["failed_properties"])
        structured_items.append(structured_item)

    verified = not failed_changes and all(item["ok"] for item in checks)
    summary = dict(result.get("summary") or {})
    summary["verified"] = summary.get("succeeded", 0) if verified else 0
    return {
        "success": verified,
        "operation_id": operation_id,
        "domain": "asset",
        "targets": [item.get("asset_path") for item in items if item.get("asset_path")],
        "applied_changes": applied_changes,
        "failed_changes": failed_changes,
        "post_state": post_state,
        "verification": {"verified": verified, "checks": checks},
        "summary": summary,
        "items": structured_items,
        "results": result_items,
    }


def update_texture_group_config(
    group_name: str,
    max_lod_size: int,
    ini_filename: str = "DefaultDeviceProfiles.ini",
    section_name: str = _TEXTURE_LOD_GROUP_SECTION,
) -> Dict[str, Any]:
    """Upsert one texture group entry in the project's device profile config."""
    operation_id = _new_operation_id("update_texture_group_config")
    normalized_group = group_name.strip().upper()
    if not normalized_group.startswith("TEXTUREGROUP_"):
        normalized_group = f"TEXTUREGROUP_{normalized_group}"
    if max_lod_size <= 0:
        return _structured_asset_failure(
            operation_id,
            normalized_group,
            "max_lod_size must be greater than zero",
        )

    try:
        config_dir = _resolve_project_config_dir()
    except Exception as exc:
        return _structured_asset_failure(
            operation_id,
            normalized_group,
            f"Failed to resolve project config dir: {exc}",
        )

    ini_path = (config_dir / ini_filename).resolve()
    if ini_path.exists():
        original_text = ini_path.read_text(encoding="utf-8")
        original_lines = original_text.splitlines()
    else:
        original_text = ""
        original_lines = []

    updated_lines = _upsert_texture_lod_group_lines(
        original_lines,
        group_name=normalized_group,
        max_lod_size=max_lod_size,
        section_name=section_name,
    )
    updated_text = "\n".join(updated_lines) + "\n"
    ini_path.parent.mkdir(parents=True, exist_ok=True)
    ini_path.write_text(updated_text, encoding="utf-8")

    changed = updated_text != original_text
    return {
        "success": True,
        "operation_id": operation_id,
        "domain": "asset",
        "targets": [str(ini_path)],
        "applied_changes": [
            {
                "target": str(ini_path),
                "field": normalized_group,
                "value": {"max_lod_size": max_lod_size},
            }
        ],
        "failed_changes": [],
        "post_state": {
            str(ini_path): {
                "group_name": normalized_group,
                "max_lod_size": max_lod_size,
                "changed": changed,
            }
        },
        "verification": {
            "verified": True,
            "checks": [
                _asset_check(str(ini_path), "group_name", normalized_group, normalized_group),
                _asset_check(str(ini_path), "max_lod_size", max_lod_size, max_lod_size),
            ],
        },
        "config_path": str(ini_path),
        "group_name": normalized_group,
        "max_lod_size": max_lod_size,
        "changed": changed,
    }


def create_asset_with_properties(
    asset_type: str,
    name: str,
    path: str = "/Game/",
    properties: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Create a supported asset and optionally set initial properties."""
    operation_id = _new_operation_id("create_asset_with_properties")
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
        {_ASSET_COERCE_PYTHON_HELPERS}

        failed = []
        post_state = {{}}
        for key, value in properties.items():
            prop_name = 'parent' if key == 'parent_material' else key
            try:
                current_value = created_asset.get_editor_property(prop_name)
                created_asset.set_editor_property(prop_name, _mcp_coerce_like(current_value, value))
                actual_value = created_asset.get_editor_property(prop_name)
                post_state[prop_name] = _mcp_to_simple(actual_value)
            except Exception as exc:
                failed.append(f"{{prop_name}}: {{exc}}")

        asset_path_name = unreal.EditorAssetLibrary.get_path_name_for_loaded_asset(created_asset)
        save_result = _mcp_finalize_asset_edit(created_asset, asset_path_name, True)
        if not save_result.get("saved", False):
            failed.append("save: " + str(save_result.get("save_error") or save_result.get("save_fallback_error") or "save failed"))
        _mcp_emit({{
            "success": len(failed) == 0,
            "asset_name": created_asset.get_name(),
            "asset_path": asset_path_name,
            "asset_class": asset_type,
            "post_state": post_state,
            "failed_properties": failed,
            "save_result": save_result,
        }})
"""
    result = run_editor_python(wrap_editor_python(body))
    if not result.get("success") and not result.get("asset_path"):
        return _structured_asset_failure(
            operation_id,
            f"{path.rstrip('/')}/{name}.{name}",
            result.get("error", "asset creation failed"),
        )
    asset_path_name = result.get("asset_path")
    failed_properties = result.get("failed_properties", [])
    failed_property_fields = {
        failure.split(":", 1)[0].strip() for failure in failed_properties if ":" in failure
    }
    applied_changes = [
        {"target": asset_path_name, "field": key, "value": value}
        for key, value in (properties or {}).items()
        if ("parent" if key == "parent_material" else key) not in failed_property_fields
    ]
    failed_changes = [
        {"target": asset_path_name, "field": failure.split(":", 1)[0], "error": failure}
        for failure in failed_properties
    ]
    checks = [
        _asset_check(
            asset_path_name, "asset_class", asset_type, result.get("asset_class")
        )
    ]
    for key, expected in (properties or {}).items():
        prop_name = "parent" if key == "parent_material" else key
        checks.append(
            _asset_check(
                asset_path_name,
                prop_name,
                expected,
                (result.get("post_state") or {}).get(prop_name),
            )
        )
    verified = all(item["ok"] for item in checks) and not failed_changes
    return {
        "success": verified,
        "operation_id": operation_id,
        "domain": "asset",
        "targets": [asset_path_name],
        "applied_changes": applied_changes,
        "failed_changes": failed_changes,
        "post_state": {
            asset_path_name: {
                "asset_name": result.get("asset_name"),
                "asset_class": result.get("asset_class"),
                **(result.get("post_state") or {}),
            }
        },
        "verification": {"verified": verified, "checks": checks},
        "asset_name": result.get("asset_name"),
        "asset_path": asset_path_name,
        "asset_class": result.get("asset_class"),
        "failed_properties": failed_properties,
        "save_result": result.get("save_result"),
    }


def import_texture_asset(
    source_path: str,
    name: str,
    destination_path: str = "/Game/Textures/",
) -> Dict[str, Any]:
    """Import a texture asset through an isolated Unreal commandlet process."""
    operation_id = _new_operation_id("import_texture_asset")
    result = run_python_commandlet(
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
    imported = result.get("imported_object_paths", [])
    checks = [_asset_check(path, "imported", True, True) for path in imported]
    verified = bool(imported) and all(item["ok"] for item in checks)
    return {
        "success": bool(result.get("success", False)) and verified,
        "operation_id": operation_id,
        "domain": "asset",
        "targets": imported,
        "applied_changes": [
            {"target": path, "field": "imported", "value": True} for path in imported
        ],
        "failed_changes": []
        if result.get("success")
        else [
            {
                "target": destination_path,
                "field": "import",
                "error": result.get("error", "texture import failed"),
            }
        ],
        "post_state": {path: {"imported": True} for path in imported},
        "verification": {"verified": verified, "checks": checks},
        "summary": {
            "requested": 1,
            "succeeded": len(imported),
            "failed": 0 if imported else 1,
            "verified": len(imported) if verified else 0,
        },
        "items": [
            {
                "target": path,
                "success": True,
                "verification": {
                    "verified": True,
                    "checks": [_asset_check(path, "imported", True, True)],
                },
            }
            for path in imported
        ],
        **result,
    }


def import_fbx_asset(
    fbx_path: str,
    destination_path: str = "/Game/ImportedMeshes/",
) -> Dict[str, Any]:
    """Import an FBX asset through an isolated Unreal commandlet process."""
    operation_id = _new_operation_id("import_fbx_asset")
    result = run_python_commandlet(
        [
            "--mode",
            "fbx",
            "--source",
            fbx_path,
            "--destination",
            destination_path,
        ]
    )
    imported = result.get("imported_object_paths", [])
    checks = [_asset_check(path, "imported", True, True) for path in imported]
    verified = bool(imported) and all(item["ok"] for item in checks)
    return {
        "success": bool(result.get("success", False)) and verified,
        "operation_id": operation_id,
        "domain": "asset",
        "targets": imported,
        "applied_changes": [
            {"target": path, "field": "imported", "value": True} for path in imported
        ],
        "failed_changes": []
        if result.get("success")
        else [
            {
                "target": destination_path,
                "field": "import",
                "error": result.get("error", "fbx import failed"),
            }
        ],
        "post_state": {path: {"imported": True} for path in imported},
        "verification": {"verified": verified, "checks": checks},
        "summary": {
            "requested": 1,
            "succeeded": len(imported),
            "failed": 0 if imported else 1,
            "verified": len(imported) if verified else 0,
        },
        "items": [
            {
                "target": path,
                "success": True,
                "verification": {
                    "verified": True,
                    "checks": [_asset_check(path, "imported", True, True)],
                },
            }
            for path in imported
        ],
        **result,
    }


def update_asset_properties(
    asset_path: str, properties: Dict[str, Any]
) -> Dict[str, Any]:
    """Update asset properties through UE Python."""
    operation_id = _new_operation_id("update_asset_properties")
    result = set_asset_properties([asset_path], properties, save=True)
    result["operation_id"] = operation_id
    result["asset_path"] = asset_path
    result["modified_properties"] = [
        change["field"] for change in result.get("applied_changes", [])
    ]
    result["failed_properties"] = [
        failure["error"] for failure in result.get("failed_changes", [])
    ]
    return result
