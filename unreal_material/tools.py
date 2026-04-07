"""Material asset and instance tools built on the asset harness."""

from __future__ import annotations

import time
from typing import Any, Dict

from unreal_asset.tools import create_asset_with_properties, update_asset_properties
from unreal_harness_runtime.python_exec import (
    json_literal,
    python_literal,
    run_editor_python,
    wrap_editor_python,
)


def _new_operation_id(action: str) -> str:
    return f"material:{action}:{int(time.time() * 1000)}"


def _material_check(
    target: str, field: str, expected: Any, actual: Any
) -> Dict[str, Any]:
    def _matches(lhs: Any, rhs: Any, tolerance: float = 1e-4) -> bool:
        if isinstance(lhs, (int, float)) and isinstance(rhs, (int, float)):
            return abs(float(lhs) - float(rhs)) < tolerance
        if isinstance(lhs, dict) and isinstance(rhs, dict):
            if set(lhs) != set(rhs):
                return False
            return all(_matches(lhs[key], rhs[key], tolerance) for key in lhs)
        if isinstance(lhs, (list, tuple)) and isinstance(rhs, (list, tuple)):
            if len(lhs) != len(rhs):
                return False
            return all(_matches(left, right, tolerance) for left, right in zip(lhs, rhs))
        return lhs == rhs

    return {
        "target": target,
        "field": field,
        "expected": expected,
        "actual": actual,
        "ok": _matches(expected, actual),
    }


def _structured_material_failure(
    operation_id: str, target: str, error: str
) -> Dict[str, Any]:
    return {
        "success": False,
        "operation_id": operation_id,
        "domain": "material",
        "targets": [target],
        "applied_changes": [],
        "failed_changes": [{"target": target, "field": "asset", "error": error}],
        "post_state": {},
        "verification": {"verified": False, "checks": []},
        "error": error,
    }


def get_material_harness_info() -> Dict[str, Any]:
    """Describe the current material asset harness backend and scope."""
    payload = {
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
    return {
        "success": True,
        "operation_id": _new_operation_id("get_material_harness_info"),
        "domain": "material",
        "targets": ["material_harness"],
        "applied_changes": [],
        "failed_changes": [],
        "post_state": {"material_harness": payload},
        "verification": {"verified": True, "checks": []},
        **payload,
    }


def create_material_asset(name: str, path: str = "/Game/") -> Dict[str, Any]:
    """Create a material asset through the asset harness."""
    result = create_asset_with_properties(asset_type="Material", name=name, path=path)
    result["operation_id"] = _new_operation_id("create_material_asset")
    result["domain"] = "material"
    return result


def create_material_instance_asset(
    name: str, parent_material: str, path: str = "/Game/"
) -> Dict[str, Any]:
    """Create a material instance asset with a parent material reference."""
    result = create_asset_with_properties(
        asset_type="MaterialInstanceConstant",
        name=name,
        path=path,
        properties={"parent_material": parent_material},
    )
    result["operation_id"] = _new_operation_id("create_material_instance_asset")
    result["domain"] = "material"
    return result


def update_material_instance_properties(
    asset_path: str, properties: Dict[str, Any]
) -> Dict[str, Any]:
    """Update a material instance through the asset harness."""
    result = update_asset_properties(asset_path=asset_path, properties=properties)
    result["operation_id"] = _new_operation_id("update_material_instance_properties")
    result["domain"] = "material"
    return result


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
    result = run_editor_python(wrap_editor_python(body))
    if not result.get("success"):
        return _structured_material_failure(
            _new_operation_id("get_material_instance_parameter_names"),
            asset_path,
            result.get("error", "parameter name query failed"),
        )
    names = {
        "scalar": result.get("scalar", []),
        "vector": result.get("vector", []),
        "texture": result.get("texture", []),
        "static_switch": result.get("static_switch", []),
    }
    return {
        "success": True,
        "operation_id": _new_operation_id("get_material_instance_parameter_names"),
        "domain": "material",
        "targets": [asset_path],
        "applied_changes": [],
        "failed_changes": [],
        "post_state": {asset_path: names},
        "verification": {"verified": True, "checks": []},
        "asset_path": asset_path,
        **names,
    }


def set_material_instance_scalar_parameter(
    asset_path: str,
    parameter_name: str,
    value: float,
) -> Dict[str, Any]:
    """Set a scalar parameter on a material instance."""
    operation_id = _new_operation_id("set_material_instance_scalar_parameter")
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
    result = run_editor_python(wrap_editor_python(body))
    if not result.get("success"):
        return _structured_material_failure(
            operation_id,
            asset_path,
            result.get("error", "scalar parameter update failed"),
        )
    check = _material_check(asset_path, parameter_name, value, result.get("value"))
    return {
        "success": bool(check["ok"]),
        "operation_id": operation_id,
        "domain": "material",
        "targets": [asset_path],
        "applied_changes": [
            {"target": asset_path, "field": parameter_name, "value": value}
        ],
        "failed_changes": [],
        "post_state": {asset_path: {parameter_name: result.get("value")}},
        "verification": {"verified": bool(check["ok"]), "checks": [check]},
        "asset_path": asset_path,
        "parameter_name": parameter_name,
        "changed": result.get("changed"),
        "value": result.get("value"),
    }


def set_material_instance_vector_parameter(
    asset_path: str,
    parameter_name: str,
    value: Dict[str, float],
) -> Dict[str, Any]:
    """Set a vector parameter on a material instance."""
    operation_id = _new_operation_id("set_material_instance_vector_parameter")
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
    result = run_editor_python(wrap_editor_python(body))
    if not result.get("success"):
        return _structured_material_failure(
            operation_id,
            asset_path,
            result.get("error", "vector parameter update failed"),
        )
    check = _material_check(asset_path, parameter_name, value, result.get("value"))
    return {
        "success": bool(check["ok"]),
        "operation_id": operation_id,
        "domain": "material",
        "targets": [asset_path],
        "applied_changes": [
            {"target": asset_path, "field": parameter_name, "value": value}
        ],
        "failed_changes": [],
        "post_state": {asset_path: {parameter_name: result.get("value")}},
        "verification": {"verified": bool(check["ok"]), "checks": [check]},
        "asset_path": asset_path,
        "parameter_name": parameter_name,
        "changed": result.get("changed"),
        "value": result.get("value"),
    }


def set_material_instance_texture_parameter(
    asset_path: str,
    parameter_name: str,
    texture_asset_path: str,
) -> Dict[str, Any]:
    """Set a texture parameter on a material instance."""
    operation_id = _new_operation_id("set_material_instance_texture_parameter")
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
    result = run_editor_python(wrap_editor_python(body))
    if not result.get("success"):
        return _structured_material_failure(
            operation_id,
            asset_path,
            result.get("error", "texture parameter update failed"),
        )
    check = _material_check(
        asset_path, parameter_name, texture_asset_path, result.get("value")
    )
    return {
        "success": bool(check["ok"]),
        "operation_id": operation_id,
        "domain": "material",
        "targets": [asset_path],
        "applied_changes": [
            {"target": asset_path, "field": parameter_name, "value": texture_asset_path}
        ],
        "failed_changes": [],
        "post_state": {asset_path: {parameter_name: result.get("value")}},
        "verification": {"verified": bool(check["ok"]), "checks": [check]},
        "asset_path": asset_path,
        "parameter_name": parameter_name,
        "changed": result.get("changed"),
        "value": result.get("value"),
    }


def update_material_instance_parameters_and_verify(
    asset_path: str,
    scalar_parameters: Dict[str, float] | None = None,
    vector_parameters: Dict[str, Dict[str, float]] | None = None,
    texture_parameters: Dict[str, str] | None = None,
) -> Dict[str, Any]:
    """Apply multiple parameter updates and return structured verification results."""
    scalar_parameters = scalar_parameters or {}
    vector_parameters = vector_parameters or {}
    texture_parameters = texture_parameters or {}

    if not scalar_parameters and not vector_parameters and not texture_parameters:
        return _structured_material_failure(
            _new_operation_id("update_material_instance_parameters_and_verify"),
            asset_path,
            "No parameter updates requested",
        )

    operation_id = _new_operation_id("update_material_instance_parameters_and_verify")

    body = f"""
asset_path = {python_literal(asset_path)}
scalar_parameters = {json_literal(scalar_parameters)}
vector_parameters = {json_literal(vector_parameters)}
texture_parameters = {json_literal(texture_parameters)}

instance = unreal.EditorAssetLibrary.load_asset(asset_path)
if instance is None:
    _mcp_emit({{"success": False, "error": f"Asset not found: {{asset_path}}"}})
else:
    changes = []
    failed = []
    verification = []

    for parameter_name, value in scalar_parameters.items():
        try:
            changed = unreal.MaterialEditingLibrary.set_material_instance_scalar_parameter_value(instance, parameter_name, float(value))
            actual = unreal.MaterialEditingLibrary.get_material_instance_scalar_parameter_value(instance, parameter_name)
            changes.append({{"type": "scalar", "parameter": parameter_name, "changed": bool(changed)}})
            verification.append({{"type": "scalar", "parameter": parameter_name, "expected": float(value), "actual": actual, "ok": abs(actual - float(value)) < 0.0001}})
        except Exception as exc:
            failed.append({{"type": "scalar", "parameter": parameter_name, "error": str(exc)}})

    for parameter_name, value in vector_parameters.items():
        try:
            color = unreal.LinearColor(value.get('r', 0.0), value.get('g', 0.0), value.get('b', 0.0), value.get('a', 1.0))
            changed = unreal.MaterialEditingLibrary.set_material_instance_vector_parameter_value(instance, parameter_name, color)
            actual = unreal.MaterialEditingLibrary.get_material_instance_vector_parameter_value(instance, parameter_name)
            actual_value = {{"r": actual.r, "g": actual.g, "b": actual.b, "a": actual.a}}
            expected_value = {{"r": color.r, "g": color.g, "b": color.b, "a": color.a}}
            changes.append({{"type": "vector", "parameter": parameter_name, "changed": bool(changed)}})
            verification.append({{"type": "vector", "parameter": parameter_name, "expected": expected_value, "actual": actual_value, "ok": actual_value == expected_value}})
        except Exception as exc:
            failed.append({{"type": "vector", "parameter": parameter_name, "error": str(exc)}})

    for parameter_name, texture_asset_path in texture_parameters.items():
        try:
            texture = unreal.EditorAssetLibrary.load_asset(texture_asset_path)
            if texture is None:
                raise Exception(f"Texture not found: {{texture_asset_path}}")
            changed = unreal.MaterialEditingLibrary.set_material_instance_texture_parameter_value(instance, parameter_name, texture)
            actual = unreal.MaterialEditingLibrary.get_material_instance_texture_parameter_value(instance, parameter_name)
            actual_path = unreal.EditorAssetLibrary.get_path_name_for_loaded_asset(actual) if actual else None
            changes.append({{"type": "texture", "parameter": parameter_name, "changed": bool(changed)}})
            verification.append({{"type": "texture", "parameter": parameter_name, "expected": texture_asset_path, "actual": actual_path, "ok": actual_path == texture_asset_path}})
        except Exception as exc:
            failed.append({{"type": "texture", "parameter": parameter_name, "error": str(exc)}})

    unreal.EditorAssetLibrary.save_loaded_asset(instance)
    verified = (not failed) and all(item.get('ok', False) for item in verification)
    _mcp_emit({{
        "success": verified,
        "asset_path": asset_path,
        "requested": {{
            "scalar": list(scalar_parameters.keys()),
            "vector": list(vector_parameters.keys()),
            "texture": list(texture_parameters.keys()),
        }},
        "changes": changes,
        "failed": failed,
        "verification": verification,
    }})
"""
    result = run_editor_python(wrap_editor_python(body))
    if (
        not result.get("success")
        and not result.get("changes")
        and not result.get("verification")
    ):
        return _structured_material_failure(
            operation_id,
            asset_path,
            result.get("error", "material parameter update failed"),
        )
    verification_checks = []
    for item in result.get("verification", []):
        verification_checks.append(
            {
                "target": asset_path,
                "field": item.get("parameter"),
                "expected": item.get("expected"),
                "actual": item.get("actual"),
                "ok": item.get("ok", False),
                "type": item.get("type"),
            }
        )
    post_state = {
        asset_path: {
            item.get("parameter"): item.get("actual")
            for item in result.get("verification", [])
        }
    }
    return {
        "success": bool(result.get("success", False)),
        "operation_id": operation_id,
        "domain": "material",
        "targets": [asset_path],
        "applied_changes": [
            {
                "target": asset_path,
                "field": item.get("parameter"),
                "value": item.get("actual"),
                "type": item.get("type"),
            }
            for item in result.get("verification", [])
        ],
        "failed_changes": [
            {
                "target": asset_path,
                "field": item.get("parameter"),
                "error": item.get("error"),
                "type": item.get("type"),
            }
            for item in result.get("failed", [])
        ],
        "post_state": post_state,
        "verification": {
            "verified": bool(result.get("success", False)),
            "checks": verification_checks,
        },
        "requested": result.get("requested"),
    }
