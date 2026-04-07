"""High-level scene tools using UE Python via the editor MCP."""

from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from uuid import uuid4

from unreal_backend_tcp.tools import get_current_level
from unreal_harness_runtime.python_exec import (
    PYTHON_RESULT_MARKER,
    run_editor_python,
)
from unreal_harness_runtime.result_format import (
    build_query_summary,
    structured_query_failure,
    structured_query_success,
)


_run_editor_python = run_editor_python


_LIGHT_UNIT_MAP = {
    "unitless": "UNITLESS",
    "candelas": "CANDELAS",
    "lumens": "LUMENS",
    "nits": "NITS",
    "ev": "EV",
}

_MOBILITY_MAP = {
    "static": "STATIC",
    "stationary": "STATIONARY",
    "movable": "MOVABLE",
}

_SCENE_COMMON_PYTHON_HELPERS = """
def _mcp_find_actor(actor_name):
    for actor in unreal.EditorLevelLibrary.get_all_level_actors():
        label = None
        try:
            label = actor.get_actor_label()
        except Exception:
            pass
        if actor.get_name() == actor_name or label == actor_name:
            return actor
    return None

def _mcp_get_actor_identifier(actor):
    try:
        label = actor.get_actor_label()
        if label:
            return label
    except Exception:
        pass
    return actor.get_name()

def _mcp_to_simple(value):
    if value is None or isinstance(value, (bool, int, str)):
        return value
    if isinstance(value, float):
        return round(value, 4)
    if isinstance(value, unreal.Vector):
        return {"x": round(value.x, 4), "y": round(value.y, 4), "z": round(value.z, 4)}
    if isinstance(value, unreal.Rotator):
        return {"pitch": round(value.pitch, 4), "yaw": round(value.yaw, 4), "roll": round(value.roll, 4)}
    if isinstance(value, unreal.Vector2D):
        return {"x": round(value.x, 4), "y": round(value.y, 4)}
    if hasattr(unreal, "Vector4") and isinstance(value, unreal.Vector4):
        return {"x": round(value.x, 4), "y": round(value.y, 4), "z": round(value.z, 4), "w": round(value.w, 4)}
    if isinstance(value, unreal.LinearColor):
        return {"r": round(value.r, 4), "g": round(value.g, 4), "b": round(value.b, 4), "a": round(value.a, 4)}
    if isinstance(value, unreal.Color):
        return {"r": value.r, "g": value.g, "b": value.b, "a": value.a}
    if isinstance(value, dict):
        return {str(key): _mcp_to_simple(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_mcp_to_simple(item) for item in value]
    if hasattr(value, "get_path_name"):
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

def _mcp_check(target, field, expected, actual):
    expected_simple = _mcp_to_simple(expected)
    actual_simple = _mcp_to_simple(actual)
    return {
        "target": target,
        "field": field,
        "expected": expected_simple,
        "actual": actual_simple,
        "ok": expected_simple == actual_simple,
    }

def _mcp_read_transform(actor):
    return {
        "location": _mcp_to_simple(actor.get_actor_location()),
        "rotation": _mcp_to_simple(actor.get_actor_rotation()),
        "scale": _mcp_to_simple(actor.get_actor_scale3d()),
    }

def _mcp_make_rotator(pitch, yaw, roll):
    return unreal.Rotator(pitch=pitch, yaw=yaw, roll=roll)

def _mcp_get_root_component(actor):
    if hasattr(actor, "get_root_component"):
        try:
            return actor.get_root_component()
        except Exception:
            pass
    try:
        return actor.get_editor_property("root_component")
    except Exception:
        return None

def _mcp_coerce_property_value(value):
    if isinstance(value, str) and (value.startswith('/Game/') or value.startswith('/Engine/')):
        loaded = unreal.EditorAssetLibrary.load_asset(value)
        return loaded if loaded is not None else value
    return value
"""

_SCENE_COERCE_PYTHON_HELPERS = """
def _mcp_coerce_like(current_value, value):
    value = _mcp_coerce_property_value(value)
    if isinstance(current_value, unreal.LinearColor):
        if isinstance(value, dict):
            return unreal.LinearColor(value.get("r", 0.0), value.get("g", 0.0), value.get("b", 0.0), value.get("a", 1.0))
        if isinstance(value, (list, tuple)) and len(value) == 4:
            return unreal.LinearColor(value[0], value[1], value[2], value[3])
    if isinstance(current_value, unreal.Color):
        if isinstance(value, dict):
            return unreal.Color(value.get("r", 0), value.get("g", 0), value.get("b", 0), value.get("a", 255))
        if isinstance(value, (list, tuple)) and len(value) == 4:
            return unreal.Color(value[0], value[1], value[2], value[3])
    if isinstance(current_value, unreal.Vector):
        if isinstance(value, dict):
            return unreal.Vector(value.get("x", 0.0), value.get("y", 0.0), value.get("z", 0.0))
        if isinstance(value, (list, tuple)) and len(value) == 3:
            return unreal.Vector(value[0], value[1], value[2])
    if isinstance(current_value, unreal.Vector2D):
        if isinstance(value, dict):
            return unreal.Vector2D(value.get("x", 0.0), value.get("y", 0.0))
        if isinstance(value, (list, tuple)) and len(value) == 2:
            return unreal.Vector2D(value[0], value[1])
    if hasattr(unreal, "Vector4") and isinstance(current_value, unreal.Vector4):
        if isinstance(value, dict):
            return unreal.Vector4(value.get("x", 0.0), value.get("y", 0.0), value.get("z", 0.0), value.get("w", 0.0))
        if isinstance(value, (list, tuple)) and len(value) == 4:
            return unreal.Vector4(value[0], value[1], value[2], value[3])
    return value
"""

_SCENE_POST_PROCESS_HELPERS = """
def _mcp_find_override_flag(settings, field):
    candidates = [
        f"override_{field}",
        f"b_override_{field}",
        "bOverride" + "".join(part.capitalize() for part in field.split("_")),
    ]
    for candidate in candidates:
        try:
            settings.get_editor_property(candidate)
            return candidate
        except Exception:
            pass
    return None

def _mcp_get_post_process_binding(actor):
    for prop_name in ("settings", "post_process_settings"):
        try:
            return actor, prop_name, actor.get_editor_property(prop_name)
        except Exception:
            pass

    component_types = []
    for type_name in ("PostProcessComponent", "CameraComponent", "CineCameraComponent", "ActorComponent"):
        component_type = getattr(unreal, type_name, None)
        if component_type is not None:
            component_types.append(component_type)

    seen = set()
    for component_type in component_types:
        for component in actor.get_components_by_class(component_type):
            component_name = component.get_name()
            if component_name in seen:
                continue
            seen.add(component_name)
            for prop_name in ("settings", "post_process_settings"):
                try:
                    return component, prop_name, component.get_editor_property(prop_name)
                except Exception:
                    pass

    return None, None, None
"""

_SCENE_PYTHON_HELPERS = _SCENE_COMMON_PYTHON_HELPERS
_SCENE_COERCE_AND_COMMON_PYTHON_HELPERS = (
    _SCENE_COMMON_PYTHON_HELPERS + "\n" + _SCENE_COERCE_PYTHON_HELPERS
)
_SCENE_POST_PROCESS_PYTHON_HELPERS = (
    _SCENE_COMMON_PYTHON_HELPERS
    + "\n"
    + _SCENE_COERCE_PYTHON_HELPERS
    + "\n"
    + _SCENE_POST_PROCESS_HELPERS
)


def _json_literal(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)


def _python_literal(value: Any) -> str:
    return repr(value)


def _normalize_light_unit(unit: str) -> str:
    key = unit.strip().lower()
    if key not in _LIGHT_UNIT_MAP:
        supported = ", ".join(sorted(_LIGHT_UNIT_MAP))
        raise ValueError(f"Unsupported light unit '{unit}'. Supported: {supported}")
    return _LIGHT_UNIT_MAP[key]


def _normalize_mobility(mobility: Optional[str]) -> Optional[str]:
    if mobility is None:
        return None
    key = mobility.strip().lower()
    if key not in _MOBILITY_MAP:
        supported = ", ".join(sorted(_MOBILITY_MAP))
        raise ValueError(f"Unsupported mobility '{mobility}'. Supported: {supported}")
    return _MOBILITY_MAP[key]


def _wrap_scene_python(body: str, helpers: str = _SCENE_PYTHON_HELPERS) -> str:
    marker = _json_literal(PYTHON_RESULT_MARKER)
    indented_body = "\n".join(
        f"    {line}" if line else "" for line in body.splitlines()
    )
    return f"""
import json
import traceback
import unreal

def _mcp_emit(payload):
    print({marker} + json.dumps(payload, ensure_ascii=False))

{helpers}

try:
{indented_body}
except Exception as exc:
    _mcp_emit({{"success": False, "error": str(exc), "traceback": traceback.format_exc()}})
""".strip()


def get_scene_harness_info() -> Dict[str, Any]:
    """Describe the current scene harness backend and scope."""
    payload = {
        "domain": "scene",
        "backend": "ue_python_via_run_python",
        "target_backend": "ue_python",
        "supports": [
            "high_level_light_recipes",
            "actor_placement",
            "actor_targeting",
            "post_process_overrides",
            "level_and_viewport_workflows",
        ],
        "high_level_commands": [
            "set_scene_light_intensity",
            "create_spot_light_ring",
            "apply_scene_actor_batch",
            "delete_scene_actors_batch",
            "query_scene_actors",
            "query_scene_lights",
            "aim_actor_at",
            "set_post_process_overrides",
            "spawn_actor_with_defaults",
        ],
    }
    return {
        "success": True,
        "operation_id": _new_operation_id("get_scene_harness_info"),
        "domain": "scene",
        "targets": ["scene_harness"],
        "applied_changes": [],
        "failed_changes": [],
        "post_state": {"scene_harness": payload},
        "verification": {"verified": True, "checks": []},
        **payload,
    }


def query_scene_actors(
    actor_class: Optional[str] = None,
    name_filter: Optional[str] = None,
    limit: int = 20,
) -> Dict[str, Any]:
    """Return a compact actor list for common lookups."""
    operation_id = _new_operation_id("query_scene_actors")
    actor_class_expr = _python_literal(actor_class) if actor_class else "None"
    name_filter_expr = _python_literal(name_filter) if name_filter else "None"
    body = f"""
actor_class_name = {actor_class_expr}
name_filter = {name_filter_expr}
limit = {int(limit)}

results = []
for actor in unreal.EditorLevelLibrary.get_all_level_actors():
    actor_class_value = actor.get_class().get_name() if hasattr(actor, "get_class") else type(actor).__name__
    if actor_class_name and actor_class_value != actor_class_name:
        continue
    actor_name = actor.get_name()
    actor_label = None
    try:
        actor_label = actor.get_actor_label()
    except Exception:
        actor_label = None
    actor_identifier = _mcp_get_actor_identifier(actor)
    search_text = name_filter.lower() if name_filter else None
    if search_text and search_text not in actor_name.lower() and (not actor_label or search_text not in actor_label.lower()):
        continue
    results.append({{
        "name": actor_identifier,
        "actor_name": actor_name,
        "actor_label": actor_label,
        "class": actor_class_value,
        "path": actor.get_path_name(),
        "location": _mcp_to_simple(actor.get_actor_location()),
    }})
results.sort(key=lambda item: item["name"])
_mcp_emit({{"success": True, "actors": results[:limit], "count": len(results), "limit": limit}})
"""
    result = _run_editor_python(_wrap_scene_python(body))
    filters = {
        "actor_class": actor_class,
        "name_filter": name_filter,
        "limit": result.get("limit", limit) if result.get("success") else limit,
        "offset": 0,
    }
    summary = build_query_summary(
        requested=filters["limit"],
        returned=len(result.get("actors", [])) if result.get("success") else 0,
        total=result.get("count", 0),
        offset=0,
        verified=len(result.get("actors", [])) if result.get("success") else 0,
    )
    if not result.get("success"):
        return structured_query_failure(
            operation_id=operation_id,
            domain="scene",
            target=None,
            error=result.get("error", "query_scene_actors failed"),
            summary=summary,
            filters=filters,
        )
    actors = result.get("actors", [])
    summary = build_query_summary(
        requested=result.get("limit", limit),
        returned=len(actors),
        total=result.get("count", len(actors)),
        offset=0,
        verified=len(actors),
    )
    return structured_query_success(
        operation_id=operation_id,
        domain="scene",
        targets=[item.get("name") for item in actors if item.get("name")],
        post_state={
            "scene_query": {
                "count": result.get("count", len(actors)),
                "limit": result.get("limit", limit),
                "actors": actors,
            }
        },
        summary=summary,
        items=[
            {
                "target": item.get("name"),
                "success": True,
                "verification": {"verified": True, "checks": []},
            }
            for item in actors
        ],
        filters=filters,
        extra={"actors": actors},
    )


def query_scene_lights(limit: int = 20) -> Dict[str, Any]:
    """Return a compact list of light actors and their key intensity fields."""
    operation_id = _new_operation_id("query_scene_lights")
    body = f"""
limit = {int(limit)}
light_type_names = {{"PointLight", "SpotLight", "DirectionalLight", "SkyLight", "RectLight"}}

results = []
for actor in unreal.EditorLevelLibrary.get_all_level_actors():
    actor_class_name = actor.get_class().get_name() if hasattr(actor, "get_class") else type(actor).__name__
    if actor_class_name not in light_type_names:
        continue
    light_component = None
    for prop_name in ("light_component", "directional_light_component", "sky_light_component"):
        try:
            light_component = actor.get_editor_property(prop_name)
            if light_component is not None:
                break
        except Exception:
            pass
    intensity = None
    intensity_units = None
    if light_component is not None:
        try:
            intensity = light_component.get_editor_property("intensity")
        except Exception:
            intensity = None
        try:
            intensity_units = str(light_component.get_editor_property("intensity_units"))
        except Exception:
            intensity_units = None
    actor_label = None
    try:
        actor_label = actor.get_actor_label()
    except Exception:
        actor_label = None
    results.append({{
        "name": _mcp_get_actor_identifier(actor),
        "actor_name": actor.get_name(),
        "actor_label": actor_label,
        "class": actor_class_name,
        "path": actor.get_path_name(),
        "location": _mcp_to_simple(actor.get_actor_location()),
        "intensity": intensity,
        "intensity_units": intensity_units,
    }})

results.sort(key=lambda item: item["name"])
_mcp_emit({{"success": True, "lights": results[:limit], "count": len(results), "limit": limit}})
"""
    result = _run_editor_python(_wrap_scene_python(body))
    filters = {
        "limit": result.get("limit", limit) if result.get("success") else limit,
        "offset": 0,
    }
    summary = build_query_summary(
        requested=filters["limit"],
        returned=len(result.get("lights", [])) if result.get("success") else 0,
        total=result.get("count", 0),
        offset=0,
        verified=len(result.get("lights", [])) if result.get("success") else 0,
    )
    if not result.get("success"):
        return structured_query_failure(
            operation_id=operation_id,
            domain="scene",
            target=None,
            error=result.get("error", "query_scene_lights failed"),
            summary=summary,
            filters=filters,
        )
    lights = result.get("lights", [])
    summary = build_query_summary(
        requested=result.get("limit", limit),
        returned=len(lights),
        total=result.get("count", len(lights)),
        offset=0,
        verified=len(lights),
    )
    return structured_query_success(
        operation_id=operation_id,
        domain="scene",
        targets=[item.get("name") for item in lights if item.get("name")],
        post_state={
            "scene_query": {
                "count": result.get("count", len(lights)),
                "limit": result.get("limit", limit),
                "lights": lights,
            }
        },
        summary=summary,
        items=[
            {
                "target": item.get("name"),
                "success": True,
                "verification": {"verified": True, "checks": []},
            }
            for item in lights
        ],
        filters=filters,
        extra={"lights": lights},
    )


def _new_operation_id(command_name: str) -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return f"scene:{command_name}:{timestamp}:{uuid4().hex[:8]}"


def _normalize_xyz(
    value: Optional[Dict[str, Any]],
    *,
    default: Optional[Dict[str, float]] = None,
    name: str,
) -> Dict[str, float]:
    if value is None:
        if default is None:
            raise ValueError(f"{name} is required")
        value = default
    if not isinstance(value, dict):
        raise ValueError(f"{name} must be an object with x/y/z")
    base = default or {"x": 0.0, "y": 0.0, "z": 0.0}
    return {axis: float(value.get(axis, base[axis])) for axis in ("x", "y", "z")}


def _normalize_rotator(
    value: Optional[Dict[str, Any]],
    *,
    default: Optional[Dict[str, float]] = None,
    name: str,
) -> Dict[str, float]:
    if value is None:
        if default is None:
            raise ValueError(f"{name} is required")
        value = default
    if not isinstance(value, dict):
        raise ValueError(f"{name} must be an object with pitch/yaw/roll")
    base = default or {"pitch": 0.0, "yaw": 0.0, "roll": 0.0}
    return {
        axis: float(value.get(axis, base[axis])) for axis in ("pitch", "yaw", "roll")
    }


def _scene_input_error(
    operation_id: str,
    message: str,
    *,
    targets: Optional[list[str]] = None,
) -> Dict[str, Any]:
    return {
        "success": False,
        "operation_id": operation_id,
        "domain": "scene",
        "targets": targets or [],
        "applied_changes": [],
        "failed_changes": [{"field": "input", "error": message}],
        "post_state": {},
        "verification": {"verified": False, "checks": []},
        "error": message,
    }


def set_scene_light_intensity(
    actor_name: str,
    intensity: float,
    unit: str = "Unitless",
    mobility: Optional[str] = None,
) -> Dict[str, Any]:
    """Set a light's intensity with explicit units and optional mobility."""
    operation_id = _new_operation_id("set_scene_light_intensity")
    try:
        normalized_intensity = float(intensity)
        normalized_unit = _normalize_light_unit(unit)
        normalized_mobility = _normalize_mobility(mobility)
    except (TypeError, ValueError) as exc:
        return _scene_input_error(operation_id, str(exc), targets=[actor_name])
    mobility_literal = _python_literal(normalized_mobility)
    body = f"""
operation_id = {_json_literal(operation_id)}
actor_name = {_json_literal(actor_name)}
actor = _mcp_find_actor(actor_name)
if actor is None:
    _mcp_emit({{
        "success": False,
        "operation_id": operation_id,
        "domain": "scene",
        "targets": [actor_name],
        "applied_changes": [],
        "failed_changes": [{{"target": actor_name, "field": "actor", "error": f"Actor not found: {{actor_name}}"}}],
        "post_state": {{}},
        "verification": {{"verified": False, "checks": []}},
        "error": f"Actor not found: {{actor_name}}",
    }})
else:
    actor_key = _mcp_get_actor_identifier(actor)
    light_component = actor.get_component_by_class(unreal.LightComponent)
    if light_component is None:
        _mcp_emit({{
            "success": False,
            "operation_id": operation_id,
            "domain": "scene",
            "targets": [actor_key],
            "applied_changes": [],
            "failed_changes": [{{"target": actor_key, "field": "light_component", "error": f"LightComponent not found on {{actor_name}}"}}],
            "post_state": {{}},
            "verification": {{"verified": False, "checks": []}},
            "error": f"LightComponent not found on {{actor_name}}",
        }})
    else:
        expected_units = None
        if hasattr(light_component, "intensity_units"):
            light_component.set_editor_property("intensity_units", unreal.LightUnits.{normalized_unit})
            expected_units = str(getattr(unreal.LightUnits, {_json_literal(normalized_unit)}))
        light_component.set_editor_property("intensity", {normalized_intensity})
        requested_mobility = {mobility_literal}
        if requested_mobility is not None:
            light_component.set_editor_property("mobility", getattr(unreal.ComponentMobility, requested_mobility))
        actual_intensity = light_component.get_editor_property("intensity")
        actual_units = str(light_component.get_editor_property("intensity_units")) if hasattr(light_component, "intensity_units") else None
        actual_mobility = str(light_component.get_editor_property("mobility"))
        checks = [
            _mcp_check(actor_key, "intensity", {normalized_intensity}, actual_intensity),
        ]
        applied_changes = [
            {{"target": actor_key, "field": "intensity", "value": {normalized_intensity}}},
        ]
        if expected_units is not None:
            checks.append(_mcp_check(actor_key, "intensity_units", expected_units, actual_units))
            applied_changes.append({{"target": actor_key, "field": "intensity_units", "value": expected_units}})
        if requested_mobility is not None:
            expected_mobility = str(getattr(unreal.ComponentMobility, requested_mobility))
            checks.append(_mcp_check(actor_key, "mobility", expected_mobility, actual_mobility))
            applied_changes.append({{"target": actor_key, "field": "mobility", "value": expected_mobility}})
        verified = all(item["ok"] for item in checks)
        _mcp_emit({{
            "success": verified,
            "operation_id": operation_id,
            "domain": "scene",
            "targets": [actor_key],
            "applied_changes": applied_changes,
            "failed_changes": [],
            "post_state": {{
                actor_key: {{
                    "actor_name": actor.get_name(),
                    "actor_label": actor.get_actor_label(),
                    "intensity": actual_intensity,
                    "intensity_units": actual_units,
                    "mobility": actual_mobility,
                }}
            }},
            "verification": {{"verified": verified, "checks": checks}},
            "actor_name": actor.get_name(),
            "actor_label": actor.get_actor_label(),
            "intensity": actual_intensity,
            "intensity_units": actual_units,
            "mobility": actual_mobility,
        }})
"""
    return _run_editor_python(
        _wrap_scene_python(body, _SCENE_POST_PROCESS_PYTHON_HELPERS)
    )


def create_spot_light_ring(
    center: Dict[str, float],
    radius: float,
    z: float,
    count: int,
    target: Dict[str, float],
    intensity: float,
    intensity_unit: str = "Candelas",
    mobility: str = "Movable",
    name_prefix: str = "MCP_RingSpot",
    replace_existing: bool = True,
) -> Dict[str, Any]:
    """Create evenly spaced spot lights on a circle and aim them at a target point."""
    operation_id = _new_operation_id("create_spot_light_ring")
    if count <= 0:
        return _scene_input_error(
            operation_id,
            "count must be greater than 0",
            targets=[name_prefix],
        )
    try:
        normalized_center = _normalize_xyz(center, name="center")
        normalized_target = _normalize_xyz(target, name="target")
        normalized_radius = float(radius)
        normalized_z = float(z)
        normalized_intensity = float(intensity)
        normalized_unit = _normalize_light_unit(intensity_unit)
        normalized_mobility = _normalize_mobility(mobility) or "MOVABLE"
    except (TypeError, ValueError) as exc:
        return _scene_input_error(operation_id, str(exc), targets=[name_prefix])

    actor_updates = []
    for index in range(count):
        angle = (2.0 * math.pi * index) / count
        x = normalized_center["x"] + normalized_radius * math.cos(angle)
        y = normalized_center["y"] + normalized_radius * math.sin(angle)
        dx = normalized_target["x"] - x
        dy = normalized_target["y"] - y
        dz = normalized_target["z"] - normalized_z
        yaw = math.degrees(math.atan2(dy, dx))
        pitch = math.degrees(math.atan2(dz, math.hypot(dx, dy)))
        actor_updates.append(
            {
                "name": f"{name_prefix}_{index + 1:02d}",
                "location": {"x": x, "y": y, "z": normalized_z},
                "rotation": {"pitch": pitch, "yaw": yaw, "roll": 0.0},
            }
        )

    body = f"""
operation_id = {_json_literal(operation_id)}
actor_updates = {_json_literal(actor_updates)}
replace_existing = {str(replace_existing)}
actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
expected_units = str(getattr(unreal.LightUnits, {_json_literal(normalized_unit)}))
expected_mobility = str(getattr(unreal.ComponentMobility, {_json_literal(normalized_mobility)}))

applied_changes = []
failed_changes = []
items = []
post_state = {{}}
all_checks = []
for item in actor_updates:
    name = item["name"]
    actor = _mcp_find_actor(name)
    if actor is not None and replace_existing:
        actor_subsystem.destroy_actor(actor)
        actor = None

    if actor is None:
        actor = actor_subsystem.spawn_actor_from_class(
            unreal.SpotLight,
            unreal.Vector(item["location"]["x"], item["location"]["y"], item["location"]["z"]),
            _mcp_make_rotator(item["rotation"]["pitch"], item["rotation"]["yaw"], item["rotation"]["roll"]),
        )
        if actor is not None:
            actor.set_actor_label(name)

    if actor is None:
        failed_changes.append({{"target": name, "field": "spawn", "error": f"Failed to create spotlight {{name}}"}})
        items.append({{"target": name, "success": False, "error": f"Failed to create spotlight {{name}}"}})
        continue

    actor.set_actor_location(unreal.Vector(item["location"]["x"], item["location"]["y"], item["location"]["z"]), False, False)
    actor.set_actor_rotation(_mcp_make_rotator(item["rotation"]["pitch"], item["rotation"]["yaw"], item["rotation"]["roll"]), False)
    actor_key = _mcp_get_actor_identifier(actor)

    light_component = actor.get_component_by_class(unreal.SpotLightComponent)
    if light_component is None:
        failed_changes.append({{"target": actor_key, "field": "light_component", "error": "SpotLightComponent not found"}})
        items.append({{"target": actor_key, "success": False, "error": "SpotLightComponent not found"}})
        continue
    light_component.set_editor_property("mobility", getattr(unreal.ComponentMobility, {_json_literal(normalized_mobility)}))
    light_component.set_editor_property("intensity_units", getattr(unreal.LightUnits, {_json_literal(normalized_unit)}))
    light_component.set_editor_property("intensity", {normalized_intensity})

    actor_state = {{
        "name": actor_key,
        "actor_name": actor.get_name(),
        "actor_label": actor.get_actor_label(),
        "location": item["location"],
        "rotation": item["rotation"],
        "intensity": light_component.get_editor_property("intensity"),
        "intensity_units": str(light_component.get_editor_property("intensity_units")),
        "mobility": str(light_component.get_editor_property("mobility")),
    }}
    checks = [
        _mcp_check(actor_key, "location", item["location"], actor.get_actor_location()),
        _mcp_check(actor_key, "rotation", item["rotation"], actor.get_actor_rotation()),
        _mcp_check(actor_key, "intensity", {normalized_intensity}, actor_state["intensity"]),
        _mcp_check(actor_key, "intensity_units", expected_units, actor_state["intensity_units"]),
        _mcp_check(actor_key, "mobility", expected_mobility, actor_state["mobility"]),
    ]
    all_checks.extend(checks)
    verified = all(check["ok"] for check in checks)

    applied_changes.extend([
        {{"target": actor_key, "field": "location", "value": item["location"]}},
        {{"target": actor_key, "field": "rotation", "value": item["rotation"]}},
        {{"target": actor_key, "field": "intensity", "value": {normalized_intensity}}},
        {{"target": actor_key, "field": "intensity_units", "value": expected_units}},
        {{"target": actor_key, "field": "mobility", "value": expected_mobility}},
    ])
    post_state[actor_key] = {{
        "actor_name": actor_state["actor_name"],
        "actor_label": actor_state["actor_label"],
        "location": actor_state["location"],
        "rotation": actor_state["rotation"],
        "intensity": actor_state["intensity"],
        "intensity_units": actor_state["intensity_units"],
        "mobility": actor_state["mobility"],
    }}
    items.append({{
        "target": actor_key,
        "success": verified,
        "verification": {{"verified": verified, "checks": checks}},
    }})

verified = (not failed_changes) and all(check["ok"] for check in all_checks)
_mcp_emit({{
    "success": verified,
    "operation_id": operation_id,
    "domain": "scene",
    "targets": [item["target"] for item in items if item.get("target")],
    "applied_changes": applied_changes,
    "failed_changes": failed_changes,
    "post_state": post_state,
    "verification": {{"verified": verified, "checks": all_checks}},
    "summary": {{
        "requested": len(actor_updates),
        "succeeded": len([item for item in items if item.get("success")]),
        "failed": len([item for item in items if not item.get("success")]),
        "verified": len([item for item in items if item.get("success") and item.get("verification", {{}}).get("verified")]),
    }},
    "items": items,
    "actors": [post_state[target] | {{"name": target}} for target in post_state],
    "count": len(items),
}})
"""
    return _run_editor_python(
        _wrap_scene_python(body, _SCENE_COERCE_AND_COMMON_PYTHON_HELPERS)
    )


def aim_actor_at(
    actor_name: str,
    target: Dict[str, float],
    preserve_roll: bool = True,
    roll: Optional[float] = None,
) -> Dict[str, Any]:
    """Aim an actor toward a world-space target and verify the resulting rotation."""
    operation_id = _new_operation_id("aim_actor_at")
    try:
        target_vector = _normalize_xyz(target, name="target")
    except ValueError as exc:
        return _scene_input_error(operation_id, str(exc), targets=[actor_name])

    try:
        requested_roll = None if roll is None else float(roll)
    except (TypeError, ValueError):
        return _scene_input_error(
            operation_id,
            "roll must be a number when provided",
            targets=[actor_name],
        )
    body = f"""
operation_id = {_json_literal(operation_id)}
actor_name = {_json_literal(actor_name)}
target = {_json_literal(target_vector)}
preserve_roll = {str(preserve_roll)}
requested_roll = {_python_literal(requested_roll)}

actor = _mcp_find_actor(actor_name)
if actor is None:
    _mcp_emit({{
        "success": False,
        "operation_id": operation_id,
        "domain": "scene",
        "targets": [actor_name],
        "applied_changes": [],
        "failed_changes": [{{"target": actor_name, "field": "actor", "error": f"Actor not found: {{actor_name}}"}}],
        "post_state": {{}},
        "verification": {{"verified": False, "checks": []}},
        "error": f"Actor not found: {{actor_name}}",
    }})
else:
    actor_location = actor.get_actor_location()
    target_location = unreal.Vector(target["x"], target["y"], target["z"])
    current_rotation = actor.get_actor_rotation()
    look_rotation = unreal.MathLibrary.find_look_at_rotation(actor_location, target_location)
    final_roll = requested_roll if requested_roll is not None else (current_rotation.roll if preserve_roll else 0.0)
    desired_rotation = _mcp_make_rotator(look_rotation.pitch, look_rotation.yaw, final_roll)
    actor.set_actor_rotation(desired_rotation, False)
    post_rotation = actor.get_actor_rotation()
    checks = [
        _mcp_check(actor_name, "rotation", desired_rotation, post_rotation),
    ]
    verified = all(item["ok"] for item in checks)
    _mcp_emit({{
        "success": verified,
        "operation_id": operation_id,
        "domain": "scene",
        "targets": [actor_name],
        "applied_changes": [
            {{"target": actor_name, "field": "rotation", "value": _mcp_to_simple(desired_rotation)}},
            {{"target": actor_name, "field": "target", "value": target}},
        ],
        "failed_changes": [],
        "post_state": {{
            actor_name: {{
                "target": target,
                **_mcp_read_transform(actor),
            }}
        }},
        "verification": {{"verified": verified, "checks": checks}},
    }})
"""
    return _run_editor_python(
        _wrap_scene_python(body, _SCENE_POST_PROCESS_PYTHON_HELPERS)
    )


def set_post_process_overrides(
    actor_name: str,
    overrides: Dict[str, Any],
) -> Dict[str, Any]:
    """Set post-process override flags and values, then verify the readback state."""
    operation_id = _new_operation_id("set_post_process_overrides")
    if not isinstance(overrides, dict) or not overrides:
        return _scene_input_error(
            operation_id,
            "overrides must be a non-empty object",
            targets=[actor_name],
        )

    body = f"""
operation_id = {_json_literal(operation_id)}
actor_name = {_json_literal(actor_name)}
overrides = {_json_literal(overrides)}

actor = _mcp_find_actor(actor_name)
if actor is None:
    _mcp_emit({{
        "success": False,
        "operation_id": operation_id,
        "domain": "scene",
        "targets": [actor_name],
        "applied_changes": [],
        "failed_changes": [{{"target": actor_name, "field": "actor", "error": f"Actor not found: {{actor_name}}"}}],
        "post_state": {{}},
        "verification": {{"verified": False, "checks": []}},
        "error": f"Actor not found: {{actor_name}}",
    }})
else:
    binding_owner, settings_property, settings = _mcp_get_post_process_binding(actor)
    if binding_owner is None:
        _mcp_emit({{
            "success": False,
            "operation_id": operation_id,
            "domain": "scene",
            "targets": [actor_name],
            "applied_changes": [],
            "failed_changes": [{{"target": actor_name, "field": "post_process", "error": "No post-process settings found on actor or components"}}],
            "post_state": {{}},
            "verification": {{"verified": False, "checks": []}},
            "error": "No post-process settings found on actor or components",
        }})
    else:
        applied_changes = []
        failed_changes = []
        expected_values = {{}}
        expected_override_flags = {{}}
        for field, raw_value in overrides.items():
            try:
                override_flag = _mcp_find_override_flag(settings, field)
                if override_flag is None:
                    raise Exception(f"No override flag property found for '{{field}}'")
                current_value = settings.get_editor_property(field)
                coerced_value = _mcp_coerce_like(current_value, raw_value)
                settings.set_editor_property(override_flag, True)
                settings.set_editor_property(field, coerced_value)
                expected_values[field] = _mcp_to_simple(coerced_value)
                expected_override_flags[field] = override_flag
                applied_changes.append({{"target": actor_name, "field": field, "value": expected_values[field]}})
            except Exception as exc:
                failed_changes.append({{"target": actor_name, "field": field, "error": str(exc)}})

        if not failed_changes:
            binding_owner.set_editor_property(settings_property, settings)
            if hasattr(binding_owner, "post_edit_change"):
                binding_owner.post_edit_change()
            if hasattr(actor, "post_edit_change"):
                actor.post_edit_change()

        readback_settings = binding_owner.get_editor_property(settings_property)
        override_state = {{}}
        checks = []
        for field in overrides:
            try:
                override_flag = expected_override_flags.get(field) or _mcp_find_override_flag(readback_settings, field)
                if override_flag is None:
                    raise Exception(f"No override flag property found for '{{field}}'")
                actual_override = readback_settings.get_editor_property(override_flag)
                actual_value = readback_settings.get_editor_property(field)
                override_state[field] = {{
                    "override_flag": override_flag,
                    "override_enabled": _mcp_to_simple(actual_override),
                    "value": _mcp_to_simple(actual_value),
                }}
                checks.append(_mcp_check(actor_name, override_flag, True, actual_override))
                if field in expected_values:
                    checks.append(_mcp_check(actor_name, field, expected_values[field], actual_value))
            except Exception as exc:
                failed_changes.append({{"target": actor_name, "field": field, "error": f"Readback failed: {{exc}}"}})

        verified = (not failed_changes) and all(item["ok"] for item in checks)
        _mcp_emit({{
            "success": verified,
            "operation_id": operation_id,
            "domain": "scene",
            "targets": [actor_name],
            "applied_changes": applied_changes,
            "failed_changes": failed_changes,
            "post_state": {{
                actor_name: {{
                    "binding_owner": binding_owner.get_name(),
                    "settings_property": settings_property,
                    "overrides": override_state,
                }}
            }},
            "verification": {{"verified": verified, "checks": checks}},
        }})
"""
    return _run_editor_python(
        _wrap_scene_python(body, _SCENE_POST_PROCESS_PYTHON_HELPERS)
    )


def apply_scene_actor_batch(actor_specs: list[Dict[str, Any]]) -> Dict[str, Any]:
    """Apply a reusable batch of actor spawn/update recipes."""
    operation_id = _new_operation_id("apply_scene_actor_batch")
    if not isinstance(actor_specs, list) or not actor_specs:
        return _scene_input_error(
            operation_id, "actor_specs must be a non-empty array of actor recipes"
        )

    targets: list[str] = []
    applied_changes: list[Dict[str, Any]] = []
    failed_changes: list[Dict[str, Any]] = []
    post_state: Dict[str, Any] = {}
    all_checks: list[Dict[str, Any]] = []
    items: list[Dict[str, Any]] = []

    def _merge_post_state(target_state: Dict[str, Any], update_state: Dict[str, Any]) -> None:
        for key, value in update_state.items():
            if (
                key in target_state
                and isinstance(target_state[key], dict)
                and isinstance(value, dict)
            ):
                target_state[key].update(value)
            else:
                target_state[key] = value

    def _record_step(
        item_post_state: Dict[str, Any],
        item_steps: list[Dict[str, Any]],
        item_checks: list[Dict[str, Any]],
        step_name: str,
        result: Dict[str, Any],
    ) -> bool:
        step_success = bool(result.get("success", False))
        item_steps.append(
            {
                "operation": step_name,
                "success": step_success,
                "error": result.get("error"),
            }
        )
        applied_changes.extend(result.get("applied_changes", []))
        failed_changes.extend(result.get("failed_changes", []))
        _merge_post_state(item_post_state, result.get("post_state", {}))
        _merge_post_state(post_state, result.get("post_state", {}))
        checks = result.get("verification", {}).get("checks", [])
        item_checks.extend(checks)
        all_checks.extend(checks)
        return step_success

    for index, spec in enumerate(actor_specs):
        if not isinstance(spec, dict):
            failed_changes.append(
                {
                    "target": f"actor_specs[{index}]",
                    "field": "actor_specs",
                    "error": "Each actor recipe must be an object",
                }
            )
            items.append(
                {
                    "target": f"actor_specs[{index}]",
                    "success": False,
                    "verification": {"verified": False, "checks": []},
                    "steps": [],
                }
            )
            continue

        requested_name = spec.get("name") or spec.get("actor_name") or f"actor_specs[{index}]"
        item_post_state: Dict[str, Any] = {}
        item_steps: list[Dict[str, Any]] = []
        item_checks: list[Dict[str, Any]] = []
        item_success = True
        actor_target = requested_name

        actor_class = spec.get("actor_class")
        if actor_class is not None:
            spawn_result = spawn_actor_with_defaults(
                actor_class=str(actor_class),
                name=spec.get("name"),
                location=spec.get("location"),
                rotation=spec.get("rotation"),
                scale=spec.get("scale"),
                actor_properties=spec.get("actor_properties"),
                root_component_properties=spec.get("root_component_properties"),
                replace_existing=bool(spec.get("replace_existing", False)),
            )
            item_success = _record_step(
                item_post_state,
                item_steps,
                item_checks,
                "spawn_actor_with_defaults",
                spawn_result,
            ) and item_success
            actor_target = (
                (spawn_result.get("targets") or [requested_name])[0] or requested_name
            )
        elif not spec.get("actor_name") and not spec.get("name"):
            failed_changes.append(
                {
                    "target": requested_name,
                    "field": "actor_class",
                    "error": "actor_class is required when no existing actor name is provided",
                }
            )
            items.append(
                {
                    "target": requested_name,
                    "success": False,
                    "verification": {"verified": False, "checks": []},
                    "steps": item_steps,
                }
            )
            continue

        if "intensity" in spec:
            intensity_result = set_scene_light_intensity(
                actor_target,
                float(spec["intensity"]),
                unit=str(spec.get("unit", "Unitless")),
                mobility=spec.get("mobility"),
            )
            item_success = _record_step(
                item_post_state,
                item_steps,
                item_checks,
                "set_scene_light_intensity",
                intensity_result,
            ) and item_success

        if spec.get("aim_target") is not None:
            aim_result = aim_actor_at(
                actor_target,
                spec["aim_target"],
                preserve_roll=bool(spec.get("preserve_roll", True)),
                roll=spec.get("roll"),
            )
            item_success = _record_step(
                item_post_state,
                item_steps,
                item_checks,
                "aim_actor_at",
                aim_result,
            ) and item_success

        if spec.get("post_process_overrides") is not None:
            overrides_result = set_post_process_overrides(
                actor_target,
                spec["post_process_overrides"],
            )
            item_success = _record_step(
                item_post_state,
                item_steps,
                item_checks,
                "set_post_process_overrides",
                overrides_result,
            ) and item_success

        item_verified = item_success and all(check.get("ok", False) for check in item_checks)
        if actor_target not in targets:
            targets.append(actor_target)
        items.append(
            {
                "target": actor_target,
                "success": item_success,
                "verification": {"verified": item_verified, "checks": item_checks},
                "steps": item_steps,
                "post_state": item_post_state,
            }
        )

    verified = not failed_changes and all(check.get("ok", False) for check in all_checks)
    succeeded_items = [item for item in items if item.get("success")]
    verified_items = [
        item for item in items if item.get("verification", {}).get("verified", False)
    ]
    return {
        "success": verified,
        "operation_id": operation_id,
        "domain": "scene",
        "targets": targets,
        "applied_changes": applied_changes,
        "failed_changes": failed_changes,
        "post_state": post_state,
        "verification": {"verified": verified, "checks": all_checks},
        "summary": {
            "requested": len(actor_specs),
            "returned": len(items),
            "succeeded": len(succeeded_items),
            "failed": len(items) - len(succeeded_items),
            "verified": len(verified_items),
        },
        "items": items,
    }


def delete_scene_actors_batch(delete_specs: list[Dict[str, Any]]) -> Dict[str, Any]:
    """Delete scene actors by batch filter specs with optional exclusions and keep-counts."""
    operation_id = _new_operation_id("delete_scene_actors_batch")
    if not isinstance(delete_specs, list) or not delete_specs:
        return _scene_input_error(
            operation_id, "delete_specs must be a non-empty array of delete rules"
        )

    normalized_specs: list[Dict[str, Any]] = []
    for index, spec in enumerate(delete_specs):
        if not isinstance(spec, dict):
            return _scene_input_error(
                operation_id,
                f"delete_specs[{index}] must be an object",
            )

        actor_names = spec.get("actor_names")
        if actor_names is not None and (
            not isinstance(actor_names, list)
            or not all(isinstance(item, str) and item.strip() for item in actor_names)
        ):
            return _scene_input_error(
                operation_id,
                f"delete_specs[{index}].actor_names must be an array of non-empty strings",
            )

        exclude_names = spec.get("exclude_names")
        if exclude_names is not None and (
            not isinstance(exclude_names, list)
            or not all(isinstance(item, str) and item.strip() for item in exclude_names)
        ):
            return _scene_input_error(
                operation_id,
                f"delete_specs[{index}].exclude_names must be an array of non-empty strings",
            )

        keep_count_raw = spec.get("keep_count", 0)
        try:
            keep_count = int(keep_count_raw)
        except (TypeError, ValueError):
            return _scene_input_error(
                operation_id,
                f"delete_specs[{index}].keep_count must be an integer",
            )
        if keep_count < 0:
            return _scene_input_error(
                operation_id,
                f"delete_specs[{index}].keep_count must be >= 0",
            )

        normalized_specs.append(
            {
                "actor_class": spec.get("actor_class"),
                "name_filter": spec.get("name_filter"),
                "actor_names": actor_names or [],
                "exclude_names": exclude_names or [],
                "keep_count": keep_count,
                "rule_name": spec.get("rule_name") or f"delete_specs[{index}]",
            }
        )

    body = f"""
operation_id = {_json_literal(operation_id)}
delete_specs = json.loads({_json_literal(json.dumps(normalized_specs, ensure_ascii=False))})

actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
all_actors = list(unreal.EditorLevelLibrary.get_all_level_actors())
deleted_targets = set()
applied_changes = []
failed_changes = []
post_state = {{}}
checks = []
items = []

for spec in delete_specs:
    actor_class = spec.get("actor_class")
    name_filter = spec.get("name_filter")
    actor_names = set(spec.get("actor_names") or [])
    exclude_names = set(spec.get("exclude_names") or [])
    keep_count = int(spec.get("keep_count", 0))
    rule_name = spec.get("rule_name") or "delete_rule"

    candidates = []
    for actor in all_actors:
        actor_name = actor.get_name()
        actor_label = None
        try:
            actor_label = actor.get_actor_label()
        except Exception:
            actor_label = None

        actor_key = actor_label or actor_name
        if actor_key in deleted_targets or actor_name in deleted_targets:
            continue
        if actor_key in exclude_names or actor_name in exclude_names:
            continue

        actor_class_name = actor.get_class().get_name() if hasattr(actor, "get_class") else type(actor).__name__
        if actor_class and actor_class_name != actor_class:
            continue
        if actor_names and actor_key not in actor_names and actor_name not in actor_names:
            continue
        if name_filter:
            haystack = f"{{actor_key}} {{actor_name}}".lower()
            if name_filter.lower() not in haystack:
                continue

        candidates.append({{
            "actor": actor,
            "target": actor_key,
            "actor_name": actor_name,
            "actor_label": actor_label,
            "class": actor_class_name,
            "path": actor.get_path_name(),
            "location": _mcp_to_simple(actor.get_actor_location()),
        }})

    candidates.sort(key=lambda item: (item["target"] or item["actor_name"]))
    retained = candidates[:keep_count]
    to_delete = candidates[keep_count:]
    retained_targets = [item["target"] for item in retained]

    rule_item = {{
        "target": rule_name,
        "success": True,
        "verification": {{"verified": True, "checks": []}},
        "summary": {{
            "matched": len(candidates),
            "retained": len(retained),
            "deleted": 0,
        }},
        "retained_targets": retained_targets,
        "deleted_targets": [],
    }}

    for item in to_delete:
        actor = item["actor"]
        target = item["target"]
        try:
            deleted = actor_subsystem.destroy_actor(actor)
        except Exception as exc:
            deleted = False
            failed_changes.append({{"target": target, "field": "delete", "error": str(exc)}})

        if not deleted:
            if not any(change.get("target") == target and change.get("field") == "delete" for change in failed_changes):
                failed_changes.append({{"target": target, "field": "delete", "error": "destroy_actor returned false"}})
            rule_item["success"] = False
            rule_item["verification"]["verified"] = False
            continue

        deleted_targets.add(target)
        deleted_targets.add(item["actor_name"])
        applied_changes.append({{"target": target, "field": "deleted", "value": True}})
        post_state[target] = {{
            "deleted": True,
            "actor_name": item["actor_name"],
            "actor_label": item["actor_label"],
            "class": item["class"],
            "path": item["path"],
            "location": item["location"],
        }}
        actual_actor = _mcp_find_actor(target) or _mcp_find_actor(item["actor_name"])
        check = _mcp_check(target, "deleted", True, actual_actor is None)
        checks.append(check)
        rule_item["verification"]["checks"].append(check)
        rule_item["deleted_targets"].append(target)
        rule_item["summary"]["deleted"] += 1
        if not check["ok"]:
            rule_item["success"] = False
            rule_item["verification"]["verified"] = False

    if any(not check["ok"] for check in rule_item["verification"]["checks"]):
        rule_item["success"] = False
        rule_item["verification"]["verified"] = False
    items.append(rule_item)

verified = (not failed_changes) and all(check["ok"] for check in checks)
_mcp_emit({{
    "success": verified,
    "operation_id": operation_id,
    "domain": "scene",
    "targets": list(post_state.keys()),
    "applied_changes": applied_changes,
    "failed_changes": failed_changes,
    "post_state": post_state,
    "verification": {{"verified": verified, "checks": checks}},
    "summary": {{
        "requested": len(delete_specs),
        "matched": sum(item["summary"]["matched"] for item in items),
        "deleted": sum(item["summary"]["deleted"] for item in items),
        "retained": sum(item["summary"]["retained"] for item in items),
        "failed": len(failed_changes),
    }},
    "items": items,
}})
"""
    return _run_editor_python(_wrap_scene_python(body))


def spawn_actor_with_defaults(
    actor_class: str,
    name: Optional[str] = None,
    location: Optional[Dict[str, float]] = None,
    rotation: Optional[Dict[str, float]] = None,
    scale: Optional[Dict[str, float]] = None,
    actor_properties: Optional[Dict[str, Any]] = None,
    root_component_properties: Optional[Dict[str, Any]] = None,
    replace_existing: bool = False,
) -> Dict[str, Any]:
    """Spawn an actor and apply default actor/root-component properties with readback."""
    operation_id = _new_operation_id("spawn_actor_with_defaults")
    if not isinstance(actor_class, str) or not actor_class.strip():
        return _scene_input_error(operation_id, "actor_class must not be empty")
    if actor_properties is not None and not isinstance(actor_properties, dict):
        return _scene_input_error(
            operation_id,
            "actor_properties must be an object when provided",
            targets=[name] if name else [],
        )
    if root_component_properties is not None and not isinstance(
        root_component_properties, dict
    ):
        return _scene_input_error(
            operation_id,
            "root_component_properties must be an object when provided",
            targets=[name] if name else [],
        )

    try:
        normalized_location = _normalize_xyz(
            location, default={"x": 0.0, "y": 0.0, "z": 0.0}, name="location"
        )
        normalized_rotation = _normalize_rotator(
            rotation, default={"pitch": 0.0, "yaw": 0.0, "roll": 0.0}, name="rotation"
        )
        normalized_scale = _normalize_xyz(
            scale, default={"x": 1.0, "y": 1.0, "z": 1.0}, name="scale"
        )
    except ValueError as exc:
        return _scene_input_error(
            operation_id, str(exc), targets=[name] if name else []
        )

    actor_defaults = actor_properties or {}
    component_defaults = root_component_properties or {}
    body = f"""
operation_id = {_json_literal(operation_id)}
actor_class_name = {_json_literal(actor_class)}
requested_name = {_python_literal(name)}
location = {_json_literal(normalized_location)}
rotation = {_json_literal(normalized_rotation)}
scale = {_json_literal(normalized_scale)}
actor_properties = {_json_literal(actor_defaults)}
root_component_properties = {_json_literal(component_defaults)}
replace_existing = {str(replace_existing)}

actor_class = getattr(unreal, actor_class_name, None)
if actor_class is None and ("/" in actor_class_name or "." in actor_class_name):
    try:
        actor_class = unreal.load_class(None, actor_class_name)
    except Exception:
        actor_class = None

if actor_class is None:
    _mcp_emit({{
        "success": False,
        "operation_id": operation_id,
        "domain": "scene",
        "targets": [requested_name] if requested_name else [],
        "applied_changes": [],
        "failed_changes": [{{"field": "actor_class", "error": f"Unsupported actor class: {{actor_class_name}}"}}],
        "post_state": {{}},
        "verification": {{"verified": False, "checks": []}},
        "error": f"Unsupported actor class: {{actor_class_name}}",
    }})
else:
    existing_actor = _mcp_find_actor(requested_name) if requested_name else None
    if existing_actor is not None and not replace_existing:
        _mcp_emit({{
            "success": False,
            "operation_id": operation_id,
            "domain": "scene",
            "targets": [requested_name],
            "applied_changes": [],
            "failed_changes": [{{"target": requested_name, "field": "actor", "error": "Actor already exists; set replace_existing=True to replace it"}}],
            "post_state": {{}},
            "verification": {{"verified": False, "checks": []}},
            "error": "Actor already exists; set replace_existing=True to replace it",
        }})
    else:
        if existing_actor is not None:
            unreal.EditorLevelLibrary.destroy_actor(existing_actor)

        spawned_actor = unreal.EditorLevelLibrary.spawn_actor_from_class(
            actor_class,
            unreal.Vector(location["x"], location["y"], location["z"]),
            _mcp_make_rotator(rotation["pitch"], rotation["yaw"], rotation["roll"]),
        )
        if spawned_actor is None:
            _mcp_emit({{
                "success": False,
                "operation_id": operation_id,
                "domain": "scene",
                "targets": [requested_name] if requested_name else [],
                "applied_changes": [],
                "failed_changes": [{{"field": "spawn", "error": f"Failed to spawn actor class {{actor_class_name}}"}}],
                "post_state": {{}},
                "verification": {{"verified": False, "checks": []}},
                "error": f"Failed to spawn actor class {{actor_class_name}}",
            }})
        else:
            if requested_name:
                spawned_actor.set_actor_label(requested_name)
            actor_key = _mcp_get_actor_identifier(spawned_actor)
            spawned_actor.set_actor_location(unreal.Vector(location["x"], location["y"], location["z"]), False, False)
            spawned_actor.set_actor_rotation(_mcp_make_rotator(rotation["pitch"], rotation["yaw"], rotation["roll"]), False)
            spawned_actor.set_actor_scale3d(unreal.Vector(scale["x"], scale["y"], scale["z"]))

            root_component = _mcp_get_root_component(spawned_actor)
            applied_changes = [
                {{"target": actor_key, "field": "location", "value": location}},
                {{"target": actor_key, "field": "rotation", "value": rotation}},
                {{"target": actor_key, "field": "scale", "value": scale}},
            ]
            failed_changes = []
            actor_expected = {{}}
            for field, raw_value in actor_properties.items():
                try:
                    coerced_value = _mcp_coerce_property_value(raw_value)
                    spawned_actor.set_editor_property(field, coerced_value)
                    actor_expected[field] = _mcp_to_simple(coerced_value)
                    applied_changes.append({{"target": actor_key, "field": field, "value": actor_expected[field]}})
                except Exception as exc:
                    failed_changes.append({{"target": actor_key, "field": field, "error": str(exc)}})

            component_expected = {{}}
            if root_component is None and root_component_properties:
                failed_changes.append({{"target": actor_key, "field": "root_component", "error": "Actor has no root component"}})
            elif root_component is not None:
                for field, raw_value in root_component_properties.items():
                    try:
                        current_value = root_component.get_editor_property(field)
                        coerced_value = _mcp_coerce_like(current_value, raw_value)
                        root_component.set_editor_property(field, coerced_value)
                        component_expected[field] = _mcp_to_simple(coerced_value)
                        applied_changes.append({{"target": actor_key, "field": f"root_component.{{field}}", "value": component_expected[field]}})
                    except Exception as exc:
                        failed_changes.append({{"target": actor_key, "field": f"root_component.{{field}}", "error": str(exc)}})

            checks = [
                _mcp_check(actor_key, "location", location, spawned_actor.get_actor_location()),
                _mcp_check(actor_key, "rotation", rotation, spawned_actor.get_actor_rotation()),
                _mcp_check(actor_key, "scale", scale, spawned_actor.get_actor_scale3d()),
            ]
            actor_post_state = {{}}
            for field, expected in actor_expected.items():
                actual_value = spawned_actor.get_editor_property(field)
                actor_post_state[field] = _mcp_to_simple(actual_value)
                checks.append(_mcp_check(actor_key, field, expected, actual_value))

            component_post_state = {{}}
            if root_component is not None:
                for field, expected in component_expected.items():
                    actual_value = root_component.get_editor_property(field)
                    component_post_state[field] = _mcp_to_simple(actual_value)
                    checks.append(_mcp_check(actor_key, f"root_component.{{field}}", expected, actual_value))

            verified = (not failed_changes) and all(item["ok"] for item in checks)
            _mcp_emit({{
                "success": verified,
                "operation_id": operation_id,
                "domain": "scene",
                "targets": [actor_key],
                "applied_changes": applied_changes,
                "failed_changes": failed_changes,
                "post_state": {{
                    actor_key: {{
                        "actor_class": actor_class_name,
                        "actor_name": spawned_actor.get_name(),
                        "actor_label": spawned_actor.get_actor_label(),
                        **_mcp_read_transform(spawned_actor),
                        "actor_properties": actor_post_state,
                        "root_component": {{
                            "name": root_component.get_name() if root_component is not None else None,
                            "properties": component_post_state,
                        }},
                    }}
                }},
                "verification": {{"verified": verified, "checks": checks}},
            }})
"""
    return _run_editor_python(_wrap_scene_python(body))


def get_scene_backend_status() -> Dict[str, Any]:
    """Return a compact scene backend status snapshot."""
    payload = {
        "backend": "ue_python_via_run_python",
        "current_level": get_current_level(),
    }
    return {
        "success": True,
        "operation_id": _new_operation_id("get_scene_backend_status"),
        "domain": "scene",
        "targets": ["scene_backend"],
        "applied_changes": [],
        "failed_changes": [],
        "post_state": {"scene_backend": payload},
        "verification": {"verified": True, "checks": []},
        **payload,
    }


def inspect_scene_python_enums() -> Dict[str, Any]:
    """Inspect Unreal Python enum members used by the scene harness."""
    operation_id = _new_operation_id("inspect_scene_python_enums")
    body = """
_mcp_emit({
    "success": True,
    "light_units": [item for item in dir(unreal.LightUnits) if not item.startswith("__")],
    "component_mobility": [item for item in dir(unreal.ComponentMobility) if not item.startswith("__")],
})
"""
    result = _run_editor_python(_wrap_scene_python(body))
    if not result.get("success"):
        return {
            "success": False,
            "operation_id": operation_id,
            "domain": "scene",
            "targets": ["scene_python_enums"],
            "applied_changes": [],
            "failed_changes": [
                {
                    "target": "scene_python_enums",
                    "field": "enum_query",
                    "error": result.get("error", "enum query failed"),
                }
            ],
            "post_state": {},
            "verification": {"verified": False, "checks": []},
            "error": result.get("error", "enum query failed"),
        }
    return {
        "success": True,
        "operation_id": operation_id,
        "domain": "scene",
        "targets": ["scene_python_enums"],
        "applied_changes": [],
        "failed_changes": [],
        "post_state": {"scene_python_enums": result},
        "verification": {"verified": True, "checks": []},
        **result,
    }
