"""Typed Niagara operations with native validation and independent readback."""

from __future__ import annotations

from typing import Any

from unreal_backend_tcp.common import send_command
from unreal_harness_runtime.python_exec import run_editor_python, wrap_editor_python


def get_niagara_assignments(asset_path: str, emitter: str) -> dict[str, Any]:
    """Read assignment targets and input links across the emitter's shared graph."""
    result = _native("get_niagara_graph", {"asset_path": asset_path, "emitter": emitter, "script": "spawn"})
    if not result.get("success"):
        return result
    if "assignments" not in result:
        return {"success": False, "error": "Native plugin upgrade required: assignment inspection is unavailable"}
    return {"success": True, "domain": "niagara", "asset_path": asset_path,
            "post_state": {"assignments": result["assignments"]}}


def _parameter_operation(asset_path: str, emitter: str, operation: dict, save: bool) -> dict:
    native = _native("update_niagara_graph", {"asset_path": asset_path, "emitter": emitter, "script": "spawn", "operations": [operation]})
    items = native.get("results", [])
    if not native.get("success") or native.get("fail_count", 0) or len(items) != 1 or not items[0].get("success"):
        return {"success": False, "domain": "niagara", "error": native.get("error") or (items[0].get("error") if items else None) or "Native operation failed",
                "post_state": items[0].get("post_state", {}) if items else {}, "verification": {"verified": False}}
    item = items[0]
    if operation["dry_run"]:
        return {"success": True, "domain": "niagara", "summary": {"dry_run": True, "applied": False}, "post_state": item}
    saved = False
    if save:
        response = run_editor_python(wrap_editor_python(
            f"asset = unreal.load_asset({asset_path!r})\n"
            "_mcp_emit({'success': bool(asset and unreal.EditorAssetLibrary.save_loaded_asset(asset))})"))
        saved = response.get("success") is True
        if not saved:
            return {"success": False, "domain": "niagara", "summary": {"applied": True, "saved": False},
                    "error": response.get("error", "Applied but save failed"), "verification": {"verified": False}}
    read = get_niagara_assignments(asset_path, emitter)
    rows = read.get("post_state", {}).get("assignments", [])
    verified = read.get("success") is True and item.get("compiled") is True
    if operation["action"] == "rename_particle_parameter":
        old, new = operation["old_name"], operation["new_name"]
        before = {r["node"]: r for r in item["before"]["assignments"] if r["name"] == old}
        after = {r["node"]: r for r in rows if r["name"] == new}
        verified = verified and not any(r["name"] == old for r in rows) and set(before) == set(after)
        verified = verified and all(sorted(r["input_links"]) == sorted(after[n]["input_links"]) for n, r in before.items() if n in after)
    else:
        targets = [r for r in rows if r["node"] == operation["module_name"] and r["name"] == operation["target"]]
        verified = verified and len(targets) == 1 and bool(targets[0]["input_links"])
        if targets and operation["world_space"]:
            inputs = targets[0].get("transform_inputs", {})
            verified = verified and inputs.get("Position") == "Particles.Position" and inputs.get("Source Space") == "Simulation" and inputs.get("Destination Space") == "World" and inputs.get("Apply Scale", "").lower() == "true"
        elif targets:
            verified = verified and any(link.endswith(".Particles.Position") for link in targets[0]["input_links"])
    return {"success": bool(verified), "domain": "niagara", "asset_path": asset_path,
            "summary": {"applied": True, "saved": saved}, "post_state": read.get("post_state", {}),
            "verification": {"verified": bool(verified)},
            **({} if verified else {"error": "Independent readback did not preserve the requested assignment/links"})}


def rename_niagara_particle_parameter(asset_path: str, emitter: str, old_name: str, new_name: str,
                                     replace_existing: bool = False, dry_run: bool = True, save: bool = True) -> dict[str, Any]:
    """Rename an emitter's particle assignments, retaining dynamic inputs and rapid values.

    Dry run is the default. replace_existing permits discarding only unlinked
    destination inputs in the same assignment nodes; unrelated writers are rejected.
    """
    if not asset_path or not emitter or any(not n.startswith("Particles.") or len(n) <= 10 for n in [old_name, new_name]) or old_name.lower() == new_name.lower():
        return {"success": False, "error": "Distinct Particles.* old_name/new_name and asset_path/emitter are required"}
    return _parameter_operation(asset_path, emitter, {"action": "rename_particle_parameter", "old_name": old_name,
        "new_name": new_name, "replace_existing": replace_existing, "dry_run": dry_run}, save)


def bind_niagara_particle_position(asset_path: str, emitter: str, module_name: str, target: str,
                                  world_space: bool = True, dry_run: bool = True, save: bool = True) -> dict[str, Any]:
    """Bind an existing position assignment to Particles.Position, optionally Simulation → World.

    Refuses unrelated connected inputs; an existing matching TransformPosition
    input may be repaired without replacing its source link. Requires the engine TransformPosition
    dynamic input for world_space=True. Dry run is the default.
    """
    if not asset_path or not emitter or not module_name or not target.startswith("Particles.") or len(target) <= 10:
        return {"success": False, "error": "asset_path, emitter, module_name and a Particles.* target are required"}
    return _parameter_operation(asset_path, emitter, {"action": "bind_particle_position", "module_name": module_name,
        "target": target, "source": "Particles.Position", "world_space": world_space, "dry_run": dry_run}, save)


def _native(command: str, params: dict) -> dict:
    response = send_command(command, params)
    if response.get("status") == "error":
        return {"success": False, "error": response.get("error", "Transport failed")}
    return response.get("result", response)


def get_niagara_renderers(asset_path: str, emitter: str) -> dict[str, Any]:
    """Read one emitter's renderers, template paths and component property bindings."""
    result = _native("get_niagara_emitter", {
        "asset_path": asset_path, "emitters": [emitter],
        "detail_level": "full", "include": ["renderers"],
    })
    if not result.get("success"):
        return result
    matches = [item for item in result.get("emitters", []) if item.get("name") == emitter]
    if len(matches) != 1:
        return {"success": False, "error": f"Emitter not found: {emitter}"}
    renderers = [{"index": i, **r} for i, r in enumerate(matches[0].get("renderers", []))]
    return {
        "success": True, "asset_path": asset_path, "emitter": emitter, "renderers": renderers,
        "post_state": {"emitter": emitter, "renderers": renderers},
    }


def set_niagara_component_binding(
    asset_path: str, emitter: str, property_name: str, attribute: str,
    renderer_index: int = 0, setter: str = "", save: bool = True,
) -> dict[str, Any]:
    """Create or replace a Component Renderer property binding to Particles.*.

    Native validation checks the actual graph type, editable template property,
    conversion and setter signature before mutation. Repeated calls replace the
    same property binding. Save only this system, then independently read it back.
    Requires the native set_component_binding renderer operation.
    """
    failure = lambda error: {
        "success": False, "domain": "niagara", "error": error,
        "verification": {"verified": False},
    }
    if not asset_path or not emitter or not property_name or not attribute.startswith("Particles."):
        return failure("asset_path, emitter, property_name and a Particles.* attribute are required")
    if isinstance(renderer_index, bool) or not isinstance(renderer_index, int) or renderer_index < 0:
        return failure("renderer_index must be a nonnegative integer")
    result = _native("update_niagara_emitter", {"asset_path": asset_path, "operations": [{
        "target": "renderer", "action": "set_component_binding", "emitter": emitter,
        "index": renderer_index, "property": property_name, "attribute": attribute, "setter": setter,
    }]})
    items = result.get("results", [])
    if not result.get("success") or result.get("fail_count", 0) or len(items) != 1 or not items[0].get("success"):
        return failure(result.get("error") or (items[0].get("error") if items else None) or "Native binding operation failed")
    saved = False
    if save:
        saved_result = run_editor_python(wrap_editor_python(
            f"asset = unreal.load_asset({asset_path!r})\n"
            "_mcp_emit({'success': bool(asset and unreal.EditorAssetLibrary.save_loaded_asset(asset))})"
        ))
        saved = saved_result.get("success") is True
        if not saved:
            out = failure(saved_result.get("error", "Binding applied, but system save failed"))
            out["applied"] = True
            out["summary"] = {"applied": True, "saved": False}
            return out
    readback = get_niagara_renderers(asset_path, emitter)
    renderers = readback.get("renderers", [])
    state = next((r for r in renderers if r["index"] == renderer_index), {})
    bindings = [b for b in state.get("property_bindings", []) if b.get("property") == property_name]
    verified = (readback.get("success") is True and len(bindings) == 1
                and bindings[0].get("attribute") == attribute
                and bindings[0].get("attribute_exists") is True
                and (not setter or bindings[0].get("setter") == setter))
    return {
        "success": verified, "domain": "niagara", "asset_path": asset_path,
        "emitter": emitter, "saved": saved, "applied": True,
        "summary": {"applied": True, "saved": saved},
        "post_state": state, "verification": {"verified": verified},
        **({} if verified else {"error": readback.get("error", "Binding readback did not match")}),
    }
