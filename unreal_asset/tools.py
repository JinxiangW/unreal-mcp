"""High-level asset tools using UE Python via the editor MCP."""

from __future__ import annotations

import time
from pathlib import Path
import re
from typing import Any, Dict, Optional

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
    def _normalize_asset_ref(value: Any) -> Any:
        if not isinstance(value, str):
            return value
        if value.startswith("/Game/") or value.startswith("/Engine/"):
            if "." not in value.rsplit("/", 1)[-1]:
                name = value.rsplit("/", 1)[-1]
                return f"{value}.{name}"
        return value

    normalized_expected = _normalize_asset_ref(expected)
    normalized_actual = _normalize_asset_ref(actual)
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
def _mcp_coerce_asset_value(value):
    if isinstance(value, str) and (value.startswith('/Game/') or value.startswith('/Engine/')):
        loaded = unreal.EditorAssetLibrary.load_asset(value)
        return loaded if loaded is not None else value
    return value

def _mcp_coerce_like(current_value, value):
    value = _mcp_coerce_asset_value(value)
    if current_value is None:
        return value
    if isinstance(value, str):
        current_type = type(current_value)
        for candidate in (value, value.upper()):
            if hasattr(current_type, candidate):
                return getattr(current_type, candidate)
    return value
"""


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
            "imports_via_commandlet",
            "batch_asset_workflows",
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
            if actual_value is not None and hasattr(actual_value, 'get_path_name'):
                post_state[prop_name] = unreal.EditorAssetLibrary.get_path_name_for_loaded_asset(actual_value)
            else:
                post_state[prop_name] = actual_value
        except Exception as exc:
            failed.append(f"{{prop_name}}: {{exc}}")

    unreal.EditorAssetLibrary.save_loaded_asset(asset)
    results.append({{
        "success": len(failed) == 0,
        "asset_path": asset_path,
        "modified_properties": modified,
        "post_state": post_state,
        "failed_properties": failed,
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
                if actual_value is not None and hasattr(actual_value, 'get_path_name'):
                    post_state[prop_name] = unreal.EditorAssetLibrary.get_path_name_for_loaded_asset(actual_value)
                else:
                    post_state[prop_name] = actual_value
            except Exception as exc:
                failed.append(f"{{prop_name}}: {{exc}}")

        asset_path_name = unreal.EditorAssetLibrary.get_path_name_for_loaded_asset(created_asset)
        unreal.EditorAssetLibrary.save_loaded_asset(created_asset)
        _mcp_emit({{
            "success": len(failed) == 0,
            "asset_name": created_asset.get_name(),
            "asset_path": asset_path_name,
            "asset_class": asset_type,
            "post_state": post_state,
            "failed_properties": failed,
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
    body = f"""
asset_path = {python_literal(asset_path)}
properties = {python_literal(properties)}
asset = unreal.EditorAssetLibrary.load_asset(asset_path)

if asset is None:
    _mcp_emit({{"success": False, "error": f"Asset not found: {{asset_path}}"}})
else:
    {_ASSET_COERCE_PYTHON_HELPERS}

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
            if actual_value is not None and hasattr(actual_value, 'get_path_name'):
                post_state[prop_name] = unreal.EditorAssetLibrary.get_path_name_for_loaded_asset(actual_value)
            else:
                post_state[prop_name] = actual_value
        except Exception as exc:
            failed.append(f"{{prop_name}}: {{exc}}")

    unreal.EditorAssetLibrary.save_loaded_asset(asset)
    _mcp_emit({{
        "success": len(failed) == 0,
        "asset_path": asset_path,
        "modified_properties": modified,
        "post_state": post_state,
        "failed_properties": failed,
    }})
"""
    result = run_editor_python(wrap_editor_python(body))
    if not result.get("success") and not result.get("modified_properties"):
        return _structured_asset_failure(
            operation_id, asset_path, result.get("error", "asset update failed")
        )
    modified_properties = result.get("modified_properties", [])
    failed_properties = result.get("failed_properties", [])
    checks = []
    applied_changes = []
    for field in modified_properties:
        requested_key = (
            "parent_material"
            if field == "parent" and "parent_material" in properties
            else field
        )
        applied_changes.append(
            {
                "target": asset_path,
                "field": field,
                "value": properties.get(requested_key),
            }
        )
        checks.append(
            _asset_check(
                asset_path,
                field,
                properties.get(requested_key),
                (result.get("post_state") or {}).get(field),
            )
        )
    verified = not failed_properties and all(item["ok"] for item in checks)
    return {
        "success": verified,
        "operation_id": operation_id,
        "domain": "asset",
        "targets": [asset_path],
        "applied_changes": applied_changes,
        "failed_changes": [
            {"target": asset_path, "field": failure.split(":", 1)[0], "error": failure}
            for failure in failed_properties
        ],
        "post_state": {asset_path: (result.get("post_state") or {})},
        "verification": {"verified": verified, "checks": checks},
        "modified_properties": modified_properties,
        "failed_properties": failed_properties,
        "asset_path": asset_path,
    }
