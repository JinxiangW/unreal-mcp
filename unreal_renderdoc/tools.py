"""UE-side RenderDoc control/context helpers."""

from __future__ import annotations

import json
import re
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional
from uuid import uuid4

from unreal_backend_tcp.common import send_command
from unreal_backend_tcp.tools import get_current_level
from unreal_diagnostics.tools import get_editor_ready_state
from unreal_harness_runtime.config import get_editor_exe_path, get_project_path
from unreal_harness_runtime.python_exec import run_editor_python, wrap_editor_python


DEFAULT_CAPTURE_CVARS = [
    "r.ScreenPercentage",
    "r.SecondaryScreenPercentage.GameViewport",
    "r.DynamicRes.OperationMode",
    "r.ViewDistanceScale",
    "r.PostProcessAAQuality",
    "r.AntiAliasingMethod",
    "r.TemporalAA.Upsampling",
    "r.Nanite",
    "r.Lumen.DiffuseIndirect.Allow",
    "r.Lumen.Reflections.Allow",
    "r.Shadow.Virtual.Enable",
    "r.RayTracing",
    "r.MotionBlurQuality",
    "r.RDG.Events",
    "r.ShowMaterialDrawEvents",
]

DEFAULT_SCALABILITY_CVARS = [
    "sg.ViewDistanceQuality",
    "sg.AntiAliasingQuality",
    "sg.ShadowQuality",
    "sg.GlobalIlluminationQuality",
    "sg.ReflectionQuality",
    "sg.PostProcessQuality",
    "sg.TextureQuality",
    "sg.EffectsQuality",
    "sg.FoliageQuality",
    "sg.ShadingQuality",
]

SIDECAR_EXCLUDED_CVARS = {
    "r.ScreenPercentage",
    "r.SecondaryScreenPercentage.GameViewport",
    *DEFAULT_SCALABILITY_CVARS,
}

DEFAULT_RENDERDOC_CAPTURE_ROOT = "RenderDocCaptures"
DEFAULT_RENDERDOC_UI = Path(r"C:\Program Files\RenderDoc\renderdocui.exe")
DEFAULT_RENDERDOC_CMD = Path(r"C:\Program Files\RenderDoc\renderdoccmd.exe")
_VIEWMODES = {
    "lit": "viewmode lit",
    "unlit": "viewmode unlit",
    "wireframe": "viewmode wireframe",
    "lighting_only": "viewmode lightingonly",
    "light_complexity": "viewmode lightcomplexity",
    "shader_complexity": "viewmode shadercomplexity",
    "quad_overdraw": "viewmode quadoverdraw",
    "buffervisualization": "viewmode buffervisualization",
    "detail_lighting": "viewmode lit_detaillighting",
    "reflections": "viewmode reflections",
}

_MATERIAL_BLEND_PASS_HINTS = {
    "BLEND_TRANSLUCENT": ["Translucency", "SeparateTranslucency"],
    "BLEND_ADDITIVE": ["Translucency", "SeparateTranslucency"],
    "BLEND_MODULATE": ["Translucency"],
    "BLEND_ALPHA_COMPOSITE": ["Translucency"],
    "BLEND_ALPHA_HOLDOUT": ["Translucency"],
    "BLEND_MASKED": ["DepthPrepass", "BasePass", "ShadowDepths"],
    "BLEND_OPAQUE": ["DepthPrepass", "BasePass", "ShadowDepths"],
}


def _new_operation_id(action: str) -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return f"renderdoc:{action}:{timestamp}:{uuid4().hex[:8]}"


def _wrap_result(
    action: str,
    *,
    success: bool,
    targets: list[str],
    post_state: Dict[str, Any],
    checks: Optional[list[Dict[str, Any]]] = None,
    applied_changes: Optional[list[Dict[str, Any]]] = None,
    failed_changes: Optional[list[Dict[str, Any]]] = None,
    extras: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "success": success,
        "operation_id": _new_operation_id(action),
        "domain": "renderdoc",
        "targets": targets,
        "applied_changes": applied_changes or [],
        "failed_changes": failed_changes or [],
        "post_state": post_state,
        "verification": {
            "verified": all(item.get("ok", False) for item in (checks or []))
            if checks
            else success,
            "checks": checks or [],
        },
    }
    if extras:
        payload.update(extras)
    return payload


def _check(target: str, field: str, expected: Any, actual: Any) -> Dict[str, Any]:
    return {
        "target": target,
        "field": field,
        "expected": expected,
        "actual": actual,
        "ok": expected == actual,
    }


def _json_literal(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)


def _python_literal(value: Any) -> str:
    return repr(value)


def _safe_name(value: str, fallback: str = "capture") -> str:
    text = re.sub(r"[^A-Za-z0-9._-]+", "_", (value or "").strip()).strip("._")
    return text or fallback


def _dedupe(items: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for item in items:
        if not item or item in seen:
            continue
        seen.add(item)
        ordered.append(item)
    return ordered


def _extract_result_body(response: Dict[str, Any]) -> Dict[str, Any]:
    if response.get("status") == "success" and isinstance(response.get("result"), dict):
        return dict(response["result"])
    return dict(response)


def _project_saved_dir(project_path: Optional[str] = None) -> Path:
    project = Path(project_path) if project_path else get_project_path()
    return project.resolve().parent / "Saved"


def _capture_dir_for_project(
    project_path: Optional[str] = None,
    *,
    explicit_capture_dir: Optional[str] = None,
) -> Path:
    if explicit_capture_dir:
        return Path(explicit_capture_dir).resolve()
    return (_project_saved_dir(project_path) / DEFAULT_RENDERDOC_CAPTURE_ROOT).resolve()


def _write_json_file(path: Path, payload: Dict[str, Any]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
    return str(path.resolve())


_LOOKUP_TEXT_SUFFIXES = {
    ".usf",
    ".ush",
    ".hlsl",
    ".h",
    ".hpp",
    ".cpp",
    ".inl",
    ".txt",
    ".json",
    ".log",
}


def _project_root_optional(project_path: Optional[str] = None) -> Optional[Path]:
    try:
        project = Path(project_path) if project_path else get_project_path()
    except RuntimeError:
        return None
    return project.resolve().parent


def _engine_root_optional() -> Optional[Path]:
    try:
        editor_exe = get_editor_exe_path().resolve()
    except Exception:
        return None
    if not editor_exe.exists():
        return None
    try:
        return editor_exe.parents[2]
    except IndexError:
        return None


def _renderdoc_lookup_roots(
    *,
    project_path: Optional[str],
    source_roots: Optional[List[str]],
) -> list[Path]:
    roots: list[Path] = []
    project_root = _project_root_optional(project_path)
    if project_root is not None:
        roots.extend(
            [
                project_root / "Saved" / "ShaderDebugInfo",
                project_root / "Source",
                project_root / "Shaders",
            ]
        )
    engine_root = _engine_root_optional()
    if engine_root is not None:
        roots.extend([engine_root / "Shaders", engine_root / "Source"])
    roots.append(Path(__file__).resolve().parents[1])
    for item in source_roots or []:
        if item and str(item).strip():
            roots.append(Path(item).resolve())

    deduped: list[Path] = []
    seen: set[str] = set()
    for root in roots:
        key = str(root.resolve()) if root.exists() else str(root)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(root)
    return deduped


def _lookup_bucket_for_path(path: Path) -> str:
    normalized = str(path).lower()
    if "shaderdebuginfo" in normalized:
        return "shader_debug_matches"
    if path.suffix.lower() in {".usf", ".ush", ".hlsl"} or "\\shaders\\" in normalized:
        return "shader_source_matches"
    return "cpp_symbol_matches"


def _search_roots_for_terms(
    *,
    roots: list[Path],
    terms: list[str],
    limit: int,
) -> Dict[str, list[Dict[str, Any]]]:
    buckets: Dict[str, list[Dict[str, Any]]] = {
        "shader_debug_matches": [],
        "shader_source_matches": [],
        "cpp_symbol_matches": [],
    }
    if not terms or limit <= 0:
        return buckets

    lowered_terms = [term.lower() for term in terms if term]
    remaining = limit
    for root in roots:
        if remaining <= 0 or not root.exists():
            break
        try:
            candidates = root.rglob("*")
        except OSError:
            continue
        for path in candidates:
            if remaining <= 0:
                break
            if not path.is_file():
                continue
            if path.suffix.lower() not in _LOOKUP_TEXT_SUFFIXES:
                continue

            normalized_path = str(path).lower()
            path_hit = next((term for term in lowered_terms if term in normalized_path), None)
            if path_hit:
                bucket = _lookup_bucket_for_path(path)
                buckets[bucket].append(
                    {
                        "path": str(path.resolve()),
                        "match_type": "path",
                        "term": path_hit,
                    }
                )
                remaining -= 1
                if remaining <= 0:
                    break

            try:
                with path.open("r", encoding="utf-8", errors="ignore") as handle:
                    for line_no, line in enumerate(handle, 1):
                        lowered_line = line.lower()
                        matched_term = next(
                            (term for term in lowered_terms if term in lowered_line),
                            None,
                        )
                        if not matched_term:
                            continue
                        bucket = _lookup_bucket_for_path(path)
                        buckets[bucket].append(
                            {
                                "path": str(path.resolve()),
                                "match_type": "content",
                                "term": matched_term,
                                "line": line_no,
                                "snippet": line.strip()[:240],
                            }
                        )
                        remaining -= 1
                        if remaining <= 0:
                            break
            except OSError:
                continue
    return buckets


def _normalize_scalar_value(value: Any) -> Any:
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value) if value.is_integer() else round(value, 4)
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return ""
    lowered = text.lower()
    if lowered in {"true", "false"}:
        return lowered == "true"
    try:
        parsed = int(text)
        if str(parsed) == text or text in {f"+{parsed}", f"-{abs(parsed)}"}:
            return parsed
    except ValueError:
        pass
    try:
        parsed_float = float(text)
        return int(parsed_float) if parsed_float.is_integer() else round(parsed_float, 4)
    except ValueError:
        return text


def _compact_cvar_value(entry: Any) -> Any:
    if isinstance(entry, dict):
        if entry.get("string", "") not in {"", None}:
            return _normalize_scalar_value(entry.get("string"))
        if entry.get("float") not in {None, ""}:
            return _normalize_scalar_value(entry.get("float"))
        if entry.get("int") not in {None, ""}:
            return _normalize_scalar_value(entry.get("int"))
        return None
    return _normalize_scalar_value(entry)


def _vector_to_list(value: Optional[Dict[str, Any]]) -> list[float]:
    if not isinstance(value, dict):
        return [0.0, 0.0, 0.0]
    return [round(float(value.get(axis, 0.0)), 4) for axis in ("x", "y", "z")]


def _rotator_to_list(value: Optional[Dict[str, Any]]) -> list[float]:
    if not isinstance(value, dict):
        return [0.0, 0.0, 0.0]
    return [
        round(float(value.get(axis, 0.0)), 4) for axis in ("pitch", "yaw", "roll")
    ]


def _screen_pct_value(primary_value: Any) -> Any:
    compact = _compact_cvar_value(primary_value)
    if compact in {None, "", 0}:
        return 100
    return compact


def _parse_project_default_cvars(project_path: Optional[str]) -> Dict[str, Any]:
    project = Path(project_path) if project_path else get_project_path()
    config_dir = project.resolve().parent / "Config"
    defaults: Dict[str, Any] = {}
    if not config_dir.exists():
        return defaults
    for ini_path in sorted(config_dir.rglob("*.ini")):
        try:
            for line in ini_path.read_text(encoding="utf-8", errors="ignore").splitlines():
                stripped = line.strip()
                if not stripped or stripped.startswith(("#", ";", "[")):
                    continue
                if "=" not in stripped:
                    continue
                key, value = stripped.split("=", 1)
                key = key.strip()
                if key.startswith(("+", "-", "!")):
                    key = key[1:]
                if not key.startswith(("r.", "sg.")):
                    continue
                defaults[key] = _normalize_scalar_value(value.strip())
        except OSError:
            continue
    return defaults


def _compact_cvar_map(
    cvars: Dict[str, Any], *, project_defaults: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    compact: Dict[str, Any] = {}
    defaults = project_defaults or {}
    for name, value in cvars.items():
        if name in SIDECAR_EXCLUDED_CVARS:
            continue
        compact_value = _compact_cvar_value(value)
        if compact_value in {None, ""}:
            continue
        if name in defaults and defaults[name] == compact_value:
            continue
        compact[name] = compact_value
    return dict(sorted(compact.items()))


def _collect_scalability(cvars: Dict[str, Any]) -> Dict[str, Any]:
    payload: Dict[str, Any] = {}
    for name in DEFAULT_SCALABILITY_CVARS:
        value = _compact_cvar_value(cvars.get(name))
        if value not in {None, ""}:
            payload[name] = value
    return dict(sorted(payload.items()))


def _selection_facts(selection_context: Optional[Dict[str, Any]]) -> Dict[str, list[str]]:
    if not isinstance(selection_context, dict):
        return {"actor": [], "component": [], "material": [], "asset": []}
    actors = sorted(
        _dedupe(
            [
                actor.get("label") or actor.get("name")
                for actor in selection_context.get("selected_actors", [])
                if actor.get("label") or actor.get("name")
            ]
        )
    )
    components = sorted(
        _dedupe(
            [
                component.get("name")
                for actor in selection_context.get("selected_actors", [])
                for component in actor.get("components", [])
                if component.get("name")
            ]
        )
    )
    materials = sorted(
        _dedupe(
            [
                material.get("path") or material.get("name")
                for actor in selection_context.get("selected_actors", [])
                for component in actor.get("components", [])
                for material in component.get("materials", [])
                if material.get("path") or material.get("name")
            ]
            + [
                material.get("path") or material.get("name")
                for material in selection_context.get("materials", [])
                if material.get("path") or material.get("name")
            ]
        )
    )
    assets = sorted(
        _dedupe(
            [
                asset.get("path") or asset.get("name")
                for asset in selection_context.get("selected_assets", [])
                if asset.get("path") or asset.get("name")
            ]
        )
    )
    return {
        "actor": actors,
        "component": components,
        "material": materials,
        "asset": assets,
    }


def _camera_name_for_context(
    *,
    workflow: str,
    selection_context: Optional[Dict[str, Any]] = None,
) -> str:
    if isinstance(selection_context, dict):
        for actor in selection_context.get("selected_actors", []):
            actor_class = str(actor.get("class") or "")
            if "Camera" in actor_class:
                return actor.get("label") or actor.get("name") or actor_class
    return "PIEViewportCamera" if workflow == "pie" else "EditorViewportCamera"


def _build_sidecar_context(
    *,
    project_path: str,
    workflow: str,
    rich_context: Dict[str, Any],
    capture_reason: Optional[str] = None,
    frame_hint: Optional[int] = None,
    user_note: Optional[str] = None,
    rdg_focus_pass: Optional[str] = None,
    rdg_pass_filters: Optional[List[str]] = None,
) -> Dict[str, Any]:
    project_defaults = _parse_project_default_cvars(project_path)
    selection_context = rich_context.get("selection_context")
    selection = _selection_facts(selection_context)
    cvars = _compact_cvar_map(
        rich_context.get("debug_cvars", {}), project_defaults=project_defaults
    )
    sidecar: Dict[str, Any] = {
        "engine": {
            "project": Path(project_path).stem,
            "build": workflow.upper(),
            "build_config": rich_context.get("render_hardware", {}).get(
                "build_configuration"
            ),
            "rhi": rich_context.get("render_hardware", {}).get("rhi_name"),
            "shader_platform": rich_context.get("render_hardware", {}).get(
                "shader_platform"
            ),
            "feature_level": rich_context.get("render_hardware", {}).get(
                "feature_level"
            ),
        },
        "scene": {
            "map": rich_context.get("map_level_world", {}).get("level_path")
            or rich_context.get("map_level_world", {}).get("level_name"),
            "world": rich_context.get("map_level_world", {}).get("world_name"),
        },
        "camera": {
            "name": _camera_name_for_context(
                workflow=workflow, selection_context=selection_context
            ),
            "loc": _vector_to_list(rich_context.get("camera", {}).get("location")),
            "rot": _rotator_to_list(rich_context.get("camera", {}).get("rotation")),
        },
        "view": {
            "size": [
                int(rich_context.get("viewport", {}).get("width") or 0),
                int(rich_context.get("viewport", {}).get("height") or 0),
            ],
            "screen_pct": _screen_pct_value(
                rich_context.get("debug_cvars", {}).get("r.ScreenPercentage")
            ),
        },
        "cvars": cvars,
    }
    sidecar["capture"] = {
        "reason": capture_reason,
        "frame_hint": frame_hint,
        "user_note": user_note,
    }
    sidecar["selection"] = selection
    sidecar["scalability"] = _collect_scalability(rich_context.get("debug_cvars", {}))
    sidecar["rdg"] = {
        "focus_pass": rdg_focus_pass,
        "pass_filters": sorted(_dedupe(rdg_pass_filters or [])),
    }
    return sidecar


def _build_fallback_sidecar(
    *,
    project_path: str,
    workflow: str,
    log_context: Dict[str, Any],
    capture_reason: Optional[str],
    frame_hint: Optional[int],
    user_note: Optional[str],
) -> Dict[str, Any]:
    return {
        "engine": {
            "project": Path(project_path).stem,
            "build": workflow.upper(),
            "build_config": None,
            "rhi": log_context.get("rhi_name"),
            "shader_platform": log_context.get("shader_platform"),
            "feature_level": log_context.get("feature_level"),
        },
        "scene": {"map": None, "world": None},
        "camera": {
            "name": None,
            "loc": [0.0, 0.0, 0.0],
            "rot": [0.0, 0.0, 0.0],
        },
        "view": {"size": [0, 0], "screen_pct": 100},
        "cvars": {},
        "capture": {
            "reason": capture_reason,
            "frame_hint": frame_hint,
            "user_note": user_note,
        },
        "selection": {"actor": [], "component": [], "material": [], "asset": []},
        "scalability": {},
        "rdg": {"focus_pass": None, "pass_filters": []},
    }


def _ensure_sidecar_minimum(
    sidecar: Dict[str, Any], *, project_path: str, workflow: str
) -> Dict[str, Any]:
    payload = dict(sidecar)
    payload.setdefault(
        "engine",
        {
            "project": Path(project_path).stem,
            "build": workflow.upper(),
            "build_config": None,
            "rhi": None,
            "shader_platform": None,
            "feature_level": None,
        },
    )
    payload.setdefault("scene", {"map": None, "world": None})
    payload.setdefault("camera", {"name": None, "loc": [0.0, 0.0, 0.0], "rot": [0.0, 0.0, 0.0]})
    payload.setdefault("view", {"size": [0, 0], "screen_pct": 100})
    payload.setdefault("cvars", {})
    payload.setdefault(
        "capture", {"reason": None, "frame_hint": None, "user_note": None}
    )
    payload.setdefault(
        "selection", {"actor": [], "component": [], "material": [], "asset": []}
    )
    payload.setdefault("scalability", {})
    payload.setdefault("rdg", {"focus_pass": None, "pass_filters": []})
    return payload


def _list_captures(capture_dir: Path) -> Dict[str, float]:
    capture_dir.mkdir(parents=True, exist_ok=True)
    return {
        path.name: path.stat().st_mtime
        for path in capture_dir.glob("*.rdc")
        if path.is_file()
    }


def _wait_for_new_capture(
    capture_dir: Path,
    before: Dict[str, float],
    *,
    timeout_seconds: int,
    poll_seconds: float,
) -> Optional[Path]:
    deadline = time.time() + timeout_seconds
    latest: Optional[Path] = None
    while time.time() < deadline:
        time.sleep(max(0.1, poll_seconds))
        for path in sorted(capture_dir.glob("*.rdc"), key=lambda item: item.stat().st_mtime):
            mtime = path.stat().st_mtime
            if path.name not in before or mtime > before[path.name]:
                latest = path
        if latest is not None:
            return latest.resolve()
    return None


def _rename_capture_if_needed(capture_path: Path, capture_name: Optional[str]) -> Path:
    if not capture_name:
        return capture_path.resolve()
    stem = _safe_name(capture_name, "capture")
    desired = capture_path.with_name(f"{stem}.rdc")
    if desired == capture_path:
        return desired.resolve()
    if desired.exists():
        desired = capture_path.with_name(
            f"{stem}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.rdc"
        )
    last_error: Optional[OSError] = None
    for _ in range(60):
        try:
            capture_path.replace(desired)
            return desired.resolve()
        except PermissionError as exc:
            last_error = exc
            time.sleep(0.5)
        except OSError as exc:
            last_error = exc
            time.sleep(0.2)
    if desired.exists():
        return desired.resolve()
    if last_error is not None:
        return capture_path.resolve()
    return desired.resolve()


def _context_path_for_capture(capture_path: Path) -> Path:
    return Path(str(capture_path) + ".context.json")


def _notes_path_for_capture(capture_path: Path) -> Path:
    return capture_path.with_suffix(".notes.txt")


def _write_notes_if_needed(capture_path: Path, notes: Optional[str]) -> Optional[str]:
    if not notes:
        return None
    path = _notes_path_for_capture(capture_path)
    path.write_text(notes, encoding="utf-8")
    return str(path.resolve())


def _renderdoc_install_paths() -> Dict[str, Optional[str]]:
    ui = DEFAULT_RENDERDOC_UI if DEFAULT_RENDERDOC_UI.exists() else None
    cmd = DEFAULT_RENDERDOC_CMD if DEFAULT_RENDERDOC_CMD.exists() else None
    dll = DEFAULT_RENDERDOC_UI.parent / "renderdoc.dll"
    return {
        "renderdoc_ui": str(ui.resolve()) if ui else None,
        "renderdoc_cmd": str(cmd.resolve()) if cmd else None,
        "renderdoc_dll": str(dll.resolve()) if dll.exists() else None,
    }


def _latest_project_log(project_path: Optional[str] = None) -> Optional[Path]:
    logs_dir = _project_saved_dir(project_path) / "Logs"
    if not logs_dir.exists():
        return None
    candidates = [path for path in logs_dir.glob("*.log") if path.is_file()]
    if not candidates:
        return None
    return max(candidates, key=lambda path: path.stat().st_mtime).resolve()


def _parse_log_render_context(log_path: Optional[Path]) -> Dict[str, Any]:
    if log_path is None or not log_path.exists():
        return {
            "log_path": str(log_path) if log_path else None,
            "rhi_name": None,
            "shader_platform": None,
            "feature_level": None,
            "build_config": None,
            "renderdoc_loaded": False,
        }
    payload: Dict[str, Any] = {
        "log_path": str(log_path.resolve()),
        "rhi_name": None,
        "shader_platform": None,
        "feature_level": None,
        "renderdoc_loaded": False,
        "renderdoc_dll": None,
    }
    patterns = [
        (re.compile(r"LogRHI: Using Default RHI: (?P<value>\S+)"), "rhi_name"),
        (
            re.compile(
                r"LogRHI: Using Highest Feature Level of \S+: (?P<value>\S+)"
            ),
            "feature_level",
        ),
        (
            re.compile(r'Metadata set : shaderplatform="(?P<value>[^"]+)"'),
            "shader_platform",
        ),
        (
            re.compile(r"RenderDoc library has been located at: (?P<value>.+)$"),
            "renderdoc_dll",
        ),
    ]
    with log_path.open("r", encoding="utf-8", errors="ignore") as handle:
        for line in handle:
            if "RenderDoc plugin is ready!" in line:
                payload["renderdoc_loaded"] = True
            for pattern, field in patterns:
                if payload.get(field):
                    continue
                match = pattern.search(line)
                if match:
                    payload[field] = match.group("value").strip()
    return payload


def _run_live_python(body: str) -> Dict[str, Any]:
    return run_editor_python(wrap_editor_python(body))


def _live_viewport_camera() -> Dict[str, Any]:
    return _extract_result_body(send_command("get_viewport_camera", {}))


def _live_viewport_size(capture_dir: Path) -> Dict[str, Any]:
    temp_path = capture_dir / "_viewport_probe.png"
    response = _extract_result_body(
        send_command(
            "get_viewport_screenshot",
            {
                "output_mode": "file",
                "output_path": str(temp_path),
                "format": "png",
                "force_redraw": False,
            },
        )
    )
    try:
        if temp_path.exists():
            temp_path.unlink()
    except OSError:
        pass
    return response


def _default_context_cvars(additional_cvars: Optional[List[str]]) -> list[str]:
    return _dedupe(list(DEFAULT_CAPTURE_CVARS) + list(additional_cvars or []))


def _selection_python_body(material_asset_paths: Optional[List[str]] = None) -> str:
    selected_materials_expr = _python_literal(material_asset_paths or [])
    return f"""
def _mcp_simple(value):
    if value is None or isinstance(value, (bool, int, str)):
        return value
    if isinstance(value, float):
        return round(value, 4)
    if isinstance(value, unreal.Vector):
        return {{"x": round(value.x, 4), "y": round(value.y, 4), "z": round(value.z, 4)}}
    if isinstance(value, unreal.Rotator):
        return {{"pitch": round(value.pitch, 4), "yaw": round(value.yaw, 4), "roll": round(value.roll, 4)}}
    if isinstance(value, unreal.LinearColor):
        return {{"r": round(value.r, 4), "g": round(value.g, 4), "b": round(value.b, 4), "a": round(value.a, 4)}}
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

def _mcp_asset_ref(asset):
    if asset is None:
        return None
    try:
        return {{"name": asset.get_name(), "path": asset.get_path_name(), "class": asset.get_class().get_name()}}
    except Exception:
        return {{"name": str(asset), "path": None, "class": None}}

def _mcp_read_material(material):
    if material is None:
        return None
    info = _mcp_asset_ref(material) or {{}}
    for field in ("blend_mode", "two_sided", "cast_dynamic_shadow_as_masked", "use_material_attributes"):
        try:
            info[field] = _mcp_simple(material.get_editor_property(field))
        except Exception:
            pass
    try:
        info["parent"] = material.get_editor_property("parent").get_path_name()
    except Exception:
        pass
    return info

def _mcp_component_entry(component):
    entry = {{
        "name": component.get_name(),
        "class": component.get_class().get_name(),
        "path": component.get_path_name(),
        "materials": [],
    }}
    for mesh_field in ("static_mesh", "skeletal_mesh_asset", "skeletal_mesh", "geometry_cache"):
        try:
            mesh_asset = component.get_editor_property(mesh_field)
            if mesh_asset is not None:
                entry["mesh"] = _mcp_asset_ref(mesh_asset)
                break
        except Exception:
            pass
    try:
        entry["cast_shadow"] = bool(component.get_editor_property("cast_shadow"))
    except Exception:
        pass
    try:
        entry["visible"] = bool(component.get_editor_property("visible"))
    except Exception:
        pass
    try:
        entry["mobility"] = str(component.get_editor_property("mobility"))
    except Exception:
        pass
    try:
        material_count = component.get_num_materials()
    except Exception:
        material_count = 0
    for material_index in range(material_count):
        try:
            material = component.get_material(material_index)
        except Exception:
            material = None
        material_info = _mcp_read_material(material)
        if material_info is not None:
            material_info["slot_index"] = material_index
            entry["materials"].append(material_info)
    return entry

selected_actors = []
for actor in unreal.EditorLevelLibrary.get_selected_level_actors():
    actor_entry = {{
        "name": actor.get_name(),
        "label": actor.get_actor_label(),
        "class": actor.get_class().get_name(),
        "path": actor.get_path_name(),
        "location": _mcp_simple(actor.get_actor_location()),
        "rotation": _mcp_simple(actor.get_actor_rotation()),
        "scale": _mcp_simple(actor.get_actor_scale3d()),
        "components": [],
    }}
    primitive_component_class = getattr(unreal, "PrimitiveComponent", None)
    components = actor.get_components_by_class(primitive_component_class) if primitive_component_class is not None else []
    for component in components:
        actor_entry["components"].append(_mcp_component_entry(component))
    selected_actors.append(actor_entry)

selected_assets = []
for asset in unreal.EditorUtilityLibrary.get_selected_assets():
    asset_entry = _mcp_asset_ref(asset)
    if asset_entry is not None:
        selected_assets.append(asset_entry)

requested_materials = []
for asset_path in {selected_materials_expr}:
    asset = unreal.EditorAssetLibrary.load_asset(asset_path)
    if asset is None:
        requested_materials.append({{"path": asset_path, "error": "Asset not found"}})
        continue
    requested_materials.append(_mcp_read_material(asset) or {{"path": asset_path}})

_mcp_emit({{
    "success": True,
    "selected_actors": selected_actors,
    "selected_assets": selected_assets,
    "requested_materials": requested_materials,
}})
"""


def _capture_context_python_body(cvar_names: List[str]) -> str:
    return f"""
import json

def _mcp_to_simple(value):
    if value is None or isinstance(value, (bool, int, str)):
        return value
    if isinstance(value, float):
        return round(value, 4)
    if isinstance(value, unreal.Vector):
        return {{"x": round(value.x, 4), "y": round(value.y, 4), "z": round(value.z, 4)}}
    if isinstance(value, unreal.Rotator):
        return {{"pitch": round(value.pitch, 4), "yaw": round(value.yaw, 4), "roll": round(value.roll, 4)}}
    return str(value)

editor_subsystem = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
camera_location, camera_rotation = editor_subsystem.get_level_viewport_camera_info()
world = unreal.EditorLevelLibrary.get_editor_world()
level_subsystem = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
cvars = {{}}
for cvar_name in json.loads({_json_literal(json.dumps(cvar_names, ensure_ascii=False))}):
    cvars[cvar_name] = {{
        "int": unreal.SystemLibrary.get_console_variable_int_value(cvar_name),
        "float": unreal.SystemLibrary.get_console_variable_float_value(cvar_name),
        "string": unreal.SystemLibrary.get_console_variable_string_value(cvar_name),
    }}

_mcp_emit({{
    "success": True,
    "world_name": world.get_name() if world is not None else None,
    "world_path": world.get_path_name() if world is not None else None,
    "camera": {{
        "location": _mcp_to_simple(camera_location),
        "rotation": _mcp_to_simple(camera_rotation),
    }},
    "projection": {{
        "is_in_pie": bool(level_subsystem.is_in_play_in_editor()),
        "build_configuration": str(unreal.SystemLibrary.get_build_configuration()),
        "build_version": unreal.SystemLibrary.get_build_version(),
    }},
    "cvars": cvars,
}})
"""


def _material_pass_hints(material_info: Dict[str, Any]) -> list[str]:
    blend_mode = str(material_info.get("blend_mode") or "").upper()
    hints = list(
        _MATERIAL_BLEND_PASS_HINTS.get(
            blend_mode, ["DepthPrepass", "BasePass", "ShadowDepths"]
        )
    )
    if material_info.get("two_sided"):
        hints.append("TwoSided")
    return _dedupe(hints)


def _selection_semantic_mapping(
    selected_actors: List[Dict[str, Any]], cvar_snapshot: Dict[str, Any]
) -> Dict[str, Any]:
    marker_candidates: list[str] = []
    pass_candidates: list[str] = []
    for actor in selected_actors:
        actor_name = actor.get("label") or actor.get("name")
        marker_candidates.extend(
            filter(None, [actor_name, actor.get("name"), actor.get("class")])
        )
        for component in actor.get("components", []):
            marker_candidates.extend(
                filter(
                    None,
                    [
                        component.get("name"),
                        component.get("class"),
                        (component.get("mesh") or {}).get("name"),
                    ],
                )
            )
            cast_shadow = component.get("cast_shadow")
            for material in component.get("materials", []):
                marker_candidates.extend(
                    filter(None, [material.get("name"), material.get("path")])
                )
                pass_candidates.extend(_material_pass_hints(material))
                if cast_shadow:
                    pass_candidates.append("ShadowDepths")
            if (
                str(cvar_snapshot.get("r.Nanite", {}).get("string", "")).strip() == "1"
                and component.get("mesh")
            ):
                pass_candidates.append("Nanite")
    if not pass_candidates:
        pass_candidates = ["BasePass", "DepthPrepass"]
    return {
        "marker_candidates": _dedupe(marker_candidates),
        "likely_pass_families": _dedupe(pass_candidates),
    }


def _normalize_labels(labels: List[str]) -> List[Dict[str, Any]]:
    normalized: List[Dict[str, Any]] = []
    for label in labels:
        stable_id = re.sub(r"[^a-z0-9]+", "_", (label or "").lower()).strip("_")
        tokens = [token for token in stable_id.split("_") if token]
        normalized.append(
            {
                "label": label,
                "stable_id": stable_id,
                "tokens": tokens,
                "query_key": ".".join(tokens[:6]),
            }
        )
    return normalized


def _set_cvar_commands(cvars: Dict[str, Any]) -> list[str]:
    commands = []
    for key, value in cvars.items():
        commands.append(f"{key} {value}")
    return commands


def _live_console(commands: List[str]) -> Dict[str, Any]:
    if not commands:
        return {"success": True, "commands": []}
    body_lines = ["import unreal"]
    for command in commands:
        body_lines.append(
            f"unreal.SystemLibrary.execute_console_command(None, {_python_literal(command)})"
        )
    body_lines.append(
        f"_mcp_emit({{'success': True, 'commands': {json.dumps(commands, ensure_ascii=False)}}})"
    )
    return _run_live_python("\n".join(body_lines))


def _apply_live_configuration(config: Dict[str, Any]) -> Dict[str, Any]:
    applied: list[Dict[str, Any]] = []
    failed: list[Dict[str, Any]] = []
    checks: list[Dict[str, Any]] = []
    commands: list[str] = []

    cvars = config.get("cvars") or {}
    if cvars and not isinstance(cvars, dict):
        raise ValueError("config.cvars must be an object")
    commands.extend(_set_cvar_commands(cvars))

    viewmode = config.get("viewmode")
    if viewmode:
        key = str(viewmode).strip().lower()
        if key not in _VIEWMODES:
            raise ValueError(
                f"Unsupported viewmode '{viewmode}'. Supported: {', '.join(sorted(_VIEWMODES))}"
            )
        commands.append(_VIEWMODES[key])

    if commands:
        result = _live_console(commands)
        if not result.get("success"):
            failed.append(
                {
                    "target": "console",
                    "field": "commands",
                    "error": result.get("error", "failed to apply console commands"),
                }
            )
        else:
            for command in commands:
                applied.append({"target": "console", "field": "command", "value": command})

    camera = config.get("camera")
    if camera:
        body = f"""
import unreal
editor_subsystem = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
location = unreal.Vector(
    {float(camera.get("location", {}).get("x", 0.0))},
    {float(camera.get("location", {}).get("y", 0.0))},
    {float(camera.get("location", {}).get("z", 0.0))}
)
rotation = unreal.Rotator(
    pitch={float(camera.get("rotation", {}).get("pitch", 0.0))},
    yaw={float(camera.get("rotation", {}).get("yaw", 0.0))},
    roll={float(camera.get("rotation", {}).get("roll", 0.0))}
)
editor_subsystem.set_level_viewport_camera_info(location, rotation)
_mcp_emit({{"success": True}})
"""
        result = _run_live_python(body)
        if not result.get("success"):
            failed.append(
                {
                    "target": "viewport_camera",
                    "field": "camera",
                    "error": result.get("error", "failed to set viewport camera"),
                }
            )
        else:
            applied.append({"target": "viewport_camera", "field": "camera", "value": camera})

    return {
        "success": not failed,
        "applied_changes": applied,
        "failed_changes": failed,
        "checks": checks,
    }


def get_renderdoc_harness_info() -> Dict[str, Any]:
    """Describe the UE-side RenderDoc MCP domain."""
    payload = {
        "domain": "renderdoc",
        "backend": "ue_python_plus_renderdoc_console",
        "target_backend": "ue_context_and_capture_control",
        "supports": [
            "renderdoc_capture_control",
            "capture_context_snapshot",
            "selection_semantic_mapping",
            "debug_view_toggles",
            "capture_pair_diff_metadata",
            "shader_symbol_reverse_lookup",
        ],
        "high_level_commands": [
            "get_renderdoc_runtime_status",
            "get_renderdoc_capture_context",
            "get_renderdoc_selection_context",
            "map_material_to_renderdoc_context",
            "normalize_renderdoc_debug_labels",
            "reverse_lookup_renderdoc_symbols",
            "set_renderdoc_debug_workflow",
            "request_renderdoc_capture",
            "capture_current_selection",
            "capture_current_viewport_issue",
            "capture_renderdoc_diff_pair",
        ],
    }
    return _wrap_result(
        "get_renderdoc_harness_info",
        success=True,
        targets=["renderdoc_harness"],
        post_state={"renderdoc_harness": payload},
        checks=[_check("renderdoc_harness", "domain", "renderdoc", payload["domain"])],
        extras=payload,
    )


def get_renderdoc_runtime_status(
    project_path: Optional[str] = None,
    capture_dir: Optional[str] = None,
) -> Dict[str, Any]:
    """Return RenderDoc availability and latest-capture facts."""
    project = Path(project_path) if project_path else get_project_path()
    resolved_capture_dir = _capture_dir_for_project(
        str(project), explicit_capture_dir=capture_dir
    )
    latest_capture = None
    capture_files = sorted(
        resolved_capture_dir.glob("*.rdc"),
        key=lambda item: item.stat().st_mtime,
        reverse=True,
    )
    if capture_files:
        latest_capture = str(capture_files[0].resolve())
    log_context = _parse_log_render_context(_latest_project_log(str(project)))
    install_paths = _renderdoc_install_paths()
    editor_ready = get_editor_ready_state(debug=False)
    payload = {
        "project_path": str(project.resolve()),
        "capture_dir": str(resolved_capture_dir),
        "latest_capture": latest_capture,
        "renderdoc_install": install_paths,
        "log_context": log_context,
        "editor_ready": {
            "ready": bool(editor_ready.get("ready")),
            "transport_ok": bool(editor_ready.get("transport_ok")),
            "python_ready": bool(editor_ready.get("python_ready")),
        },
    }
    checks = [
        _check(
            "renderdoc_runtime",
            "renderdoc_ui_available",
            True,
            bool(install_paths.get("renderdoc_ui")),
        ),
        _check(
            "renderdoc_runtime",
            "capture_dir_exists",
            True,
            resolved_capture_dir.exists(),
        ),
    ]
    return _wrap_result(
        "get_renderdoc_runtime_status",
        success=all(item["ok"] for item in checks),
        targets=[str(project.resolve())],
        post_state={"renderdoc_runtime": payload},
        checks=checks,
        failed_changes=[
            {
                "target": "renderdoc_runtime",
                "field": item["field"],
                "error": "missing runtime prerequisite",
            }
            for item in checks
            if not item["ok"]
        ],
        extras=payload,
    )


def _extract_selection_context(
    *,
    cvar_snapshot: Optional[Dict[str, Any]] = None,
    material_asset_paths: Optional[List[str]] = None,
) -> Dict[str, Any]:
    selection_result = _run_live_python(_selection_python_body(material_asset_paths))
    if not selection_result.get("success"):
        return {
            "success": False,
            "error": selection_result.get("error", "selection inspection failed"),
            "selected_actors": [],
            "selected_assets": [],
            "materials": [],
            "semantic_mapping": {"marker_candidates": [], "likely_pass_families": []},
        }
    actors = selection_result.get("selected_actors", [])
    assets = selection_result.get("selected_assets", [])
    materials = selection_result.get("requested_materials", [])
    semantic_mapping = _selection_semantic_mapping(actors, cvar_snapshot or {})
    semantic_mapping["normalized_marker_candidates"] = _normalize_labels(
        semantic_mapping["marker_candidates"]
    )
    return {
        "success": True,
        "selected_actors": actors,
        "selected_assets": assets,
        "materials": materials,
        "semantic_mapping": semantic_mapping,
    }


def get_renderdoc_capture_context(
    additional_cvars: Optional[List[str]] = None,
    persist_path: Optional[str] = None,
    notes: Optional[str] = None,
    capture_label: Optional[str] = None,
    include_selection: bool = True,
    workflow: str = "editor",
    capture_reason: Optional[str] = None,
    frame_hint: Optional[int] = None,
    rdg_focus_pass: Optional[str] = None,
    rdg_pass_filters: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Collect UE-side capture context used alongside RenderDoc captures."""
    capture_dir = _capture_dir_for_project()
    project_path = str(get_project_path().resolve())
    cvar_names = _default_context_cvars(additional_cvars)
    cvar_names = _dedupe(cvar_names + list(DEFAULT_SCALABILITY_CVARS))
    python_result = _run_live_python(_capture_context_python_body(cvar_names))
    if not python_result.get("success"):
        error = python_result.get("error", "failed to gather live capture context")
        return _wrap_result(
            "get_renderdoc_capture_context",
            success=False,
            targets=[],
            post_state={},
            failed_changes=[{"target": "capture_context", "field": "live_context", "error": error}],
            extras={"error": error},
        )

    level_info = _extract_result_body(get_current_level())
    viewport_camera = _live_viewport_camera()
    viewport_size = _live_viewport_size(capture_dir)
    log_context = _parse_log_render_context(_latest_project_log())
    selection_context = (
        _extract_selection_context(cvar_snapshot=python_result.get("cvars", {}))
        if include_selection
        else None
    )

    rich_context = {
        "capture_label": capture_label,
        "notes": notes,
        "map_level_world": {
            "level_name": level_info.get("level_name"),
            "level_path": level_info.get("level_path"),
            "world_name": python_result.get("world_name"),
            "world_path": python_result.get("world_path"),
        },
        "camera": {
            "location": python_result.get("camera", {}).get("location"),
            "rotation": python_result.get("camera", {}).get("rotation"),
            "projection": {
                "perspective": viewport_camera.get("perspective"),
                "fov": viewport_camera.get("fov"),
                "ortho_zoom": viewport_camera.get("ortho_zoom"),
                "is_in_pie": python_result.get("projection", {}).get("is_in_pie"),
            },
        },
        "viewport": {
            "type": viewport_size.get("viewport_type") or viewport_camera.get("viewport_type"),
            "width": viewport_size.get("width"),
            "height": viewport_size.get("height"),
            "screen_percentage": {
                "primary": python_result.get("cvars", {})
                .get("r.ScreenPercentage", {})
                .get("string"),
                "secondary_game_viewport": python_result.get("cvars", {})
                .get("r.SecondaryScreenPercentage.GameViewport", {})
                .get("string"),
                "dynamic_res_mode": python_result.get("cvars", {})
                .get("r.DynamicRes.OperationMode", {})
                .get("string"),
            },
        },
        "render_hardware": {
            "rhi_name": log_context.get("rhi_name"),
            "shader_platform": log_context.get("shader_platform"),
            "feature_level": log_context.get("feature_level"),
            "build_configuration": python_result.get("projection", {}).get(
                "build_configuration"
            ),
            "build_version": python_result.get("projection", {}).get("build_version"),
        },
        "debug_cvars": python_result.get("cvars", {}),
        "selection_context": selection_context,
        "context_sources": {
            "live_python": True,
            "viewport_camera_command": viewport_camera.get("success", True),
            "viewport_probe": viewport_size.get("success", True),
            "log_path": log_context.get("log_path"),
        },
    }
    sidecar = _build_sidecar_context(
        project_path=project_path,
        workflow=workflow,
        rich_context=rich_context,
        capture_reason=capture_reason or capture_label,
        frame_hint=frame_hint,
        user_note=notes,
        rdg_focus_pass=rdg_focus_pass,
        rdg_pass_filters=rdg_pass_filters,
    )
    saved_to = None
    if persist_path:
        saved_to = _write_json_file(Path(persist_path), sidecar)
    checks = [
        _check("capture_context", "engine.project", True, bool(sidecar["engine"]["project"])),
        _check("capture_context", "scene.world", True, bool(sidecar["scene"]["world"])),
        _check("capture_context", "view.size", True, sidecar["view"]["size"][0] > 0),
        _check("capture_context", "engine.rhi", True, bool(sidecar["engine"]["rhi"])),
    ]
    extras = {"context": sidecar, "rich_context": rich_context}
    if saved_to:
        extras["saved_to"] = saved_to
    return _wrap_result(
        "get_renderdoc_capture_context",
        success=all(item["ok"] for item in checks),
        targets=[saved_to] if saved_to else ["capture_context"],
        post_state={"capture_context": sidecar, "capture_context_raw": rich_context},
        checks=checks,
        failed_changes=[
            {
                "target": "capture_context",
                "field": item["field"],
                "error": "missing expected context field",
            }
            for item in checks
            if not item["ok"]
        ],
        extras=extras,
    )


def get_renderdoc_selection_context() -> Dict[str, Any]:
    """Return the current editor selection plus RenderDoc-facing semantic hints."""
    context_result = get_renderdoc_capture_context(include_selection=True)
    selection_context = context_result.get("rich_context", {}).get("selection_context")
    if not selection_context or not selection_context.get("success"):
        error = (selection_context or {}).get(
            "error", "selection context was not available"
        )
        return _wrap_result(
            "get_renderdoc_selection_context",
            success=False,
            targets=[],
            post_state={},
            failed_changes=[{"target": "selection_context", "field": "selection", "error": error}],
            extras={"error": error},
        )
    checks = [
        _check(
            "selection_context",
            "semantic_mapping_present",
            True,
            bool(selection_context.get("semantic_mapping")),
        )
    ]
    return _wrap_result(
        "get_renderdoc_selection_context",
        success=True,
        targets=[
            actor.get("label") or actor.get("name")
            for actor in selection_context.get("selected_actors", [])
            if actor.get("label") or actor.get("name")
        ],
        post_state={"selection_context": selection_context},
        checks=checks,
        extras={"selection_context": selection_context},
    )


def map_material_to_renderdoc_context(
    material_asset_paths: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Map material or material instance assets into pass/shader context hints."""
    if material_asset_paths is not None and (
        not isinstance(material_asset_paths, list)
        or not all(isinstance(item, str) and item.strip() for item in material_asset_paths)
    ):
        return _wrap_result(
            "map_material_to_renderdoc_context",
            success=False,
            targets=[],
            post_state={},
            failed_changes=[
                {
                    "target": "material_context",
                    "field": "material_asset_paths",
                    "error": "material_asset_paths must be an array of non-empty strings",
                }
            ],
            extras={"error": "invalid material_asset_paths"},
        )

    selection_context = _extract_selection_context(material_asset_paths=material_asset_paths)
    materials = selection_context.get("materials", [])
    material_context = []
    for material in materials:
        material_context.append(
            {
                **material,
                "likely_pass_families": _material_pass_hints(material),
                "normalized_labels": _normalize_labels(
                    [item for item in [material.get("name"), material.get("path")] if item]
                ),
            }
        )
    checks = [
        _check("material_context", "material_count", len(material_context), len(material_context))
    ]
    return _wrap_result(
        "map_material_to_renderdoc_context",
        success=True,
        targets=[item.get("path") or item.get("name") for item in material_context if item.get("path") or item.get("name")],
        post_state={"material_context": material_context},
        checks=checks,
        extras={"material_context": material_context},
    )


def normalize_renderdoc_debug_labels(labels: List[str]) -> Dict[str, Any]:
    """Normalize pass/debug labels into stable query keys."""
    if not isinstance(labels, list) or not all(isinstance(item, str) for item in labels):
        return _wrap_result(
            "normalize_renderdoc_debug_labels",
            success=False,
            targets=[],
            post_state={},
            failed_changes=[
                {
                    "target": "debug_labels",
                    "field": "labels",
                    "error": "labels must be an array of strings",
                }
            ],
            extras={"error": "invalid labels"},
        )
    normalized = _normalize_labels(labels)
    return _wrap_result(
        "normalize_renderdoc_debug_labels",
        success=True,
        targets=[item["stable_id"] for item in normalized],
        post_state={"normalized_labels": normalized},
        checks=[_check("debug_labels", "count", len(labels), len(normalized))],
        extras={"normalized_labels": normalized},
    )


def set_renderdoc_debug_workflow(
    viewmode: Optional[str] = None,
    cvars: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Apply debug viewmodes or diagnostic CVars useful for RenderDoc workflows."""
    try:
        result = _apply_live_configuration({"viewmode": viewmode, "cvars": cvars or {}})
    except ValueError as exc:
        return _wrap_result(
            "set_renderdoc_debug_workflow",
            success=False,
            targets=[],
            post_state={},
            failed_changes=[{"target": "debug_workflow", "field": "input", "error": str(exc)}],
            extras={"error": str(exc)},
        )
    success = result["success"]
    checks = result["checks"] or [
        _check(
            "debug_workflow",
            "commands_applied",
            True,
            success,
        )
    ]
    return _wrap_result(
        "set_renderdoc_debug_workflow",
        success=success,
        targets=["debug_workflow"],
        post_state={"debug_workflow": {"viewmode": viewmode, "cvars": cvars or {}}},
        checks=checks,
        applied_changes=result["applied_changes"],
        failed_changes=result["failed_changes"],
        extras={"viewmode": viewmode, "cvars": cvars or {}},
    )


def reverse_lookup_renderdoc_symbols(
    shader_hints: List[str],
    parameter_hints: Optional[List[str]] = None,
    source_roots: Optional[List[str]] = None,
    project_path: Optional[str] = None,
    limit: int = 20,
) -> Dict[str, Any]:
    """Search shader debug/source/C++ files using RenderDoc-facing symbol hints."""
    if not isinstance(shader_hints, list) or not all(
        isinstance(item, str) and item.strip() for item in shader_hints
    ):
        return _wrap_result(
            "reverse_lookup_renderdoc_symbols",
            success=False,
            targets=[],
            post_state={},
            failed_changes=[
                {
                    "target": "renderdoc_symbol_lookup",
                    "field": "shader_hints",
                    "error": "shader_hints must be an array of non-empty strings",
                }
            ],
            extras={"error": "invalid shader_hints"},
        )
    if parameter_hints is not None and (
        not isinstance(parameter_hints, list)
        or not all(isinstance(item, str) and item.strip() for item in parameter_hints)
    ):
        return _wrap_result(
            "reverse_lookup_renderdoc_symbols",
            success=False,
            targets=[],
            post_state={},
            failed_changes=[
                {
                    "target": "renderdoc_symbol_lookup",
                    "field": "parameter_hints",
                    "error": "parameter_hints must be an array of non-empty strings when provided",
                }
            ],
            extras={"error": "invalid parameter_hints"},
        )

    shader_terms = _dedupe([item.strip() for item in shader_hints if item.strip()])
    parameter_terms = _dedupe(
        [item.strip() for item in (parameter_hints or []) if item.strip()]
    )
    roots = _renderdoc_lookup_roots(
        project_path=project_path,
        source_roots=source_roots,
    )
    shader_matches = _search_roots_for_terms(
        roots=roots,
        terms=shader_terms,
        limit=max(1, int(limit)),
    )
    parameter_matches = _search_roots_for_terms(
        roots=roots,
        terms=parameter_terms,
        limit=max(1, int(limit)),
    )

    merged_matches = {
        key: shader_matches.get(key, []) + parameter_matches.get(key, [])
        for key in (
            "shader_debug_matches",
            "shader_source_matches",
            "cpp_symbol_matches",
        )
    }
    match_count = sum(len(items) for items in merged_matches.values())
    checks = [
        _check("renderdoc_symbol_lookup", "roots_scanned", True, bool(roots)),
        _check("renderdoc_symbol_lookup", "matches_found", True, match_count > 0),
    ]
    return _wrap_result(
        "reverse_lookup_renderdoc_symbols",
        success=bool(roots),
        targets=[str(root) for root in roots],
        post_state={"renderdoc_symbol_lookup": merged_matches},
        checks=checks,
        failed_changes=[]
        if roots
        else [
            {
                "target": "renderdoc_symbol_lookup",
                "field": "roots",
                "error": "no searchable source roots were available",
            }
        ],
        extras={
            "shader_hints": shader_terms,
            "parameter_hints": parameter_terms,
            "searched_roots": [str(root) for root in roots],
            **merged_matches,
        },
    )


def _live_capture_command(
    *,
    workflow: str,
    after_frames: int,
    capture_frame_count: int,
    launch_ui: bool,
) -> Dict[str, Any]:
    commands = [
        "renderdoc.CaptureDelayInSeconds 0",
        f"renderdoc.CaptureDelay {after_frames}",
        f"renderdoc.CaptureFrameCount {max(1, capture_frame_count)}",
    ]
    if workflow == "pie":
        body = f"""
import unreal
level_subsystem = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
for command in {json.dumps(commands, ensure_ascii=False)}:
    unreal.SystemLibrary.execute_console_command(None, command)
if not level_subsystem.is_in_play_in_editor():
    level_subsystem.editor_request_begin_play()
unreal.SystemLibrary.execute_console_command(None, "renderdoc.CaptureFrame")
_mcp_emit({{"success": True, "commands": {json.dumps(commands + ['renderdoc.CaptureFrame'], ensure_ascii=False)}, "workflow": "pie"}})
"""
        return _run_live_python(body)

    commands.append("renderdoc.CaptureFrame")
    return _live_console(commands)


def _renderdoc_capture_template(
    capture_dir: Path,
    capture_name: Optional[str],
) -> Path:
    stem = _safe_name(capture_name or f"capture_{int(time.time())}")
    capture_dir.mkdir(parents=True, exist_ok=True)
    return (capture_dir / stem).resolve()


def _terminate_process_tree(pid: int) -> None:
    subprocess.run(
        ["taskkill", "/PID", str(pid), "/T", "/F"],
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )


def _external_capture_command(
    *,
    workflow: str,
    executable_path: Path,
    capture_dir: Path,
    capture_name: Optional[str],
    after_frames: int,
    extra_program_args: Optional[List[str]],
    project_path: Optional[str],
    launch_ui: bool,
) -> list[str]:
    renderdoc_cmd = DEFAULT_RENDERDOC_CMD
    if not renderdoc_cmd.exists():
        raise FileNotFoundError(f"RenderDoc command-line tool not found: {renderdoc_cmd}")
    capture_template = _renderdoc_capture_template(capture_dir, capture_name)
    exec_cmds = [
        "renderdoc.CaptureDelayInSeconds 0",
        f"renderdoc.CaptureDelay {after_frames}",
        "renderdoc.CaptureFrameCount 1",
        "renderdoc.CaptureFrame",
    ]
    if after_frames == 0:
        exec_cmds.append("quit")

    program_args: list[str] = []
    if workflow == "standalone":
        if project_path is None:
            raise ValueError("project_path is required for standalone capture")
        program_args.extend([project_path, "-game"])
    program_args.extend(extra_program_args or [])
    program_args.append(f"-ExecCmds={','.join(exec_cmds)}")

    command = [
        str(renderdoc_cmd.resolve()),
        "capture",
        "--opt-hook-children",
        "-c",
        str(capture_template),
        str(executable_path.resolve()),
        *program_args,
    ]
    if launch_ui:
        command.insert(2, "--opt-api-validation")
    return command


def request_renderdoc_capture(
    workflow: str = "editor",
    after_frames: int = 0,
    capture_name: Optional[str] = None,
    notes: Optional[str] = None,
    include_selection: bool = True,
    persist_context: bool = True,
    additional_cvars: Optional[List[str]] = None,
    capture_dir: Optional[str] = None,
    executable_path: Optional[str] = None,
    project_path: Optional[str] = None,
    program_args: Optional[List[str]] = None,
    wait_timeout_seconds: int = 90,
    poll_seconds: float = 1.0,
    launch_ui: bool = False,
    capture_frame_count: int = 1,
    capture_reason: Optional[str] = None,
    rdg_focus_pass: Optional[str] = None,
    rdg_pass_filters: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Trigger a RenderDoc capture and persist a UE context blob beside it."""
    if workflow not in {"editor", "pie", "standalone", "packaged"}:
        return _wrap_result(
            "request_renderdoc_capture",
            success=False,
            targets=[],
            post_state={},
            failed_changes=[
                {
                    "target": "capture_request",
                    "field": "workflow",
                    "error": "workflow must be one of: editor, pie, standalone, packaged",
                }
            ],
            extras={"error": "invalid workflow"},
        )
    if after_frames < 0:
        return _wrap_result(
            "request_renderdoc_capture",
            success=False,
            targets=[],
            post_state={},
            failed_changes=[
                {
                    "target": "capture_request",
                    "field": "after_frames",
                    "error": "after_frames must be >= 0",
                }
            ],
            extras={"error": "invalid after_frames"},
        )

    resolved_project_path = str(Path(project_path).resolve()) if project_path else str(get_project_path().resolve())
    resolved_capture_dir = _capture_dir_for_project(
        resolved_project_path, explicit_capture_dir=capture_dir
    )
    before = _list_captures(resolved_capture_dir)
    context_result = None
    if workflow in {"editor", "pie"}:
        context_result = get_renderdoc_capture_context(
            additional_cvars=additional_cvars,
            notes=notes,
            capture_label=capture_name,
            include_selection=include_selection,
            workflow=workflow,
            capture_reason=capture_reason,
            frame_hint=after_frames,
            rdg_focus_pass=rdg_focus_pass,
            rdg_pass_filters=rdg_pass_filters,
        )
        if not context_result.get("success"):
            return _wrap_result(
                "request_renderdoc_capture",
                success=False,
                targets=[],
                post_state={},
                failed_changes=context_result.get("failed_changes"),
                extras={"error": context_result.get("error", "failed to gather capture context")},
            )
        issued = _live_capture_command(
            workflow=workflow,
            after_frames=after_frames,
            capture_frame_count=max(1, capture_frame_count),
            launch_ui=launch_ui,
        )
        if not issued.get("success"):
            return _wrap_result(
                "request_renderdoc_capture",
                success=False,
                targets=[],
                post_state={},
                failed_changes=[
                    {
                        "target": "capture_request",
                        "field": "issue_capture",
                        "error": issued.get("error", "failed to issue capture command"),
                    }
                ],
                extras={"error": issued.get("error", "failed to issue capture command")},
            )
        launched_process = None
    else:
        chosen_executable = (
            Path(executable_path).resolve()
            if executable_path
            else get_editor_exe_path().resolve()
        )
        if not chosen_executable.exists():
            return _wrap_result(
                "request_renderdoc_capture",
                success=False,
                targets=[],
                post_state={},
                failed_changes=[
                    {
                        "target": str(chosen_executable),
                        "field": "executable_path",
                        "error": "capture executable does not exist",
                    }
                ],
                extras={"error": "capture executable does not exist"},
            )
        try:
            command = _external_capture_command(
                workflow=workflow,
                executable_path=chosen_executable,
                capture_dir=resolved_capture_dir,
                capture_name=capture_name,
                after_frames=after_frames,
                extra_program_args=program_args,
                project_path=resolved_project_path if workflow == "standalone" else project_path,
                launch_ui=launch_ui,
            )
        except (FileNotFoundError, ValueError) as exc:
            return _wrap_result(
                "request_renderdoc_capture",
                success=False,
                targets=[],
                post_state={},
                failed_changes=[
                    {
                        "target": "capture_request",
                        "field": "command",
                        "error": str(exc),
                    }
                ],
                extras={"error": str(exc)},
            )
        launched_process = subprocess.Popen(
            command,
            cwd=str(chosen_executable.parent),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        context_result = {
            "success": True,
            "context": {
                "capture_label": capture_name,
            },
        }
        if get_editor_ready_state().get("ready"):
            live_context = get_renderdoc_capture_context(
                additional_cvars=additional_cvars,
                notes=notes,
                capture_label=capture_name,
                include_selection=include_selection,
                workflow=workflow,
                capture_reason=capture_reason,
                frame_hint=after_frames,
                rdg_focus_pass=rdg_focus_pass,
                rdg_pass_filters=rdg_pass_filters,
            )
            if live_context.get("success"):
                context_result = live_context
        if not context_result.get("rich_context"):
            log_context = _parse_log_render_context(_latest_project_log(resolved_project_path))
            sidecar = _build_fallback_sidecar(
                project_path=resolved_project_path,
                workflow=workflow,
                log_context=log_context,
                capture_reason=capture_reason or capture_name,
                frame_hint=after_frames,
                user_note=notes,
            )
            context_result["context"] = sidecar
            context_result["rich_context"] = {
                "launch_workflow": workflow,
                "launch_command": command,
                "project_path": resolved_project_path,
                "capture_dir": str(resolved_capture_dir),
                "selection_context": None,
                "debug_cvars": {},
            }

    capture_path = _wait_for_new_capture(
        resolved_capture_dir,
        before,
        timeout_seconds=wait_timeout_seconds,
        poll_seconds=poll_seconds,
    )

    if launched_process is not None and launched_process.poll() is None and after_frames > 0:
        _terminate_process_tree(launched_process.pid)

    if capture_path is None:
        return _wrap_result(
            "request_renderdoc_capture",
            success=False,
            targets=[],
            post_state={"capture_request": {"workflow": workflow, "capture_dir": str(resolved_capture_dir)}},
            failed_changes=[
                {
                    "target": str(resolved_capture_dir),
                    "field": "capture_path",
                    "error": f"Timed out waiting for new capture after {wait_timeout_seconds} seconds",
                }
            ],
            extras={
                "error": "timed out waiting for capture",
                "workflow": workflow,
                "capture_dir": str(resolved_capture_dir),
            },
        )

    if capture_name:
        capture_path = _rename_capture_if_needed(capture_path, capture_name)

    sidecar_payload = _ensure_sidecar_minimum(
        dict(context_result.get("context") or {}),
        project_path=resolved_project_path,
        workflow=workflow,
    )
    rich_context = dict(context_result.get("rich_context") or {})
    sidecar_payload.setdefault("capture", {})
    sidecar_payload["capture"]["path"] = str(capture_path)
    sidecar_payload["capture"]["saved_name"] = capture_path.name
    sidecar_payload["capture"]["workflow"] = workflow
    sidecar_payload["capture"]["frame_hint"] = after_frames
    sidecar_payload["capture"]["reason"] = (
        capture_reason
        or sidecar_payload["capture"].get("reason")
        or capture_name
    )
    sidecar_payload["capture"]["user_note"] = notes
    rich_context["capture_path"] = str(capture_path)
    rich_context["workflow"] = workflow
    rich_context["after_frames"] = after_frames
    rich_context["capture_frame_count"] = max(1, capture_frame_count)
    notes_path = _write_notes_if_needed(capture_path, notes)
    if notes_path:
        rich_context["notes_path"] = notes_path

    saved_context_path = None
    if persist_context:
        saved_context_path = _write_json_file(
            _context_path_for_capture(capture_path), sidecar_payload
        )

    checks = [_check(str(capture_path), "capture_exists", True, capture_path.exists())]
    extras = {
        "capture_path": str(capture_path),
        "context": sidecar_payload,
        "rich_context": rich_context,
        "workflow": workflow,
    }
    if saved_context_path:
        extras["context_path"] = saved_context_path
    return _wrap_result(
        "request_renderdoc_capture",
        success=all(item["ok"] for item in checks),
        targets=[str(capture_path)],
        post_state={
            "capture_request": {
                "capture_path": str(capture_path),
                "context_path": saved_context_path,
                "workflow": workflow,
                "after_frames": after_frames,
            }
        },
        checks=checks,
        applied_changes=[
            {"target": str(capture_path), "field": "capture_requested", "value": True}
        ],
        failed_changes=[],
        extras=extras,
    )


def capture_current_selection(
    capture_name: Optional[str] = None,
    notes: Optional[str] = None,
    after_frames: int = 0,
) -> Dict[str, Any]:
    """One-shot capture focused on the current editor selection."""
    selection_result = get_renderdoc_selection_context()
    if not selection_result.get("success"):
        return selection_result
    selection_context = selection_result.get("selection_context") or {}
    selected_targets = [
        actor.get("label") or actor.get("name")
        for actor in selection_context.get("selected_actors", [])
        if actor.get("label") or actor.get("name")
    ]
    final_notes = notes or f"Capture current selection: {', '.join(selected_targets) or 'no explicit actor selection'}"
    result = request_renderdoc_capture(
        workflow="editor",
        after_frames=after_frames,
        capture_name=capture_name or "selection_capture",
        notes=final_notes,
        include_selection=True,
    )
    if result.get("success"):
        result["selection_context"] = selection_context
    return result


def capture_current_viewport_issue(
    capture_name: Optional[str] = None,
    notes: Optional[str] = None,
    after_frames: int = 0,
) -> Dict[str, Any]:
    """One-shot capture that also saves a viewport screenshot."""
    capture_dir = _capture_dir_for_project()
    screenshot_path = capture_dir / f"{_safe_name(capture_name or 'viewport_issue')}.png"
    screenshot_result = _extract_result_body(
        send_command(
            "get_viewport_screenshot",
            {
                "output_mode": "file",
                "output_path": str(screenshot_path),
                "format": "png",
                "force_redraw": True,
            },
        )
    )
    capture_result = request_renderdoc_capture(
        workflow="editor",
        after_frames=after_frames,
        capture_name=capture_name or "viewport_issue",
        notes=notes or "Capture current viewport issue",
        include_selection=True,
    )
    if capture_result.get("success"):
        capture_result["viewport_screenshot"] = {
            "path": screenshot_result.get("file_path"),
            "width": screenshot_result.get("width"),
            "height": screenshot_result.get("height"),
        }
    return capture_result


def _build_diff_metadata(
    base_capture: Dict[str, Any],
    variant_capture: Dict[str, Any],
    *,
    base_config: Dict[str, Any],
    variant_config: Dict[str, Any],
) -> Dict[str, Any]:
    base_context = base_capture.get("context") or {}
    variant_context = variant_capture.get("context") or {}
    base_cvars = (base_context.get("cvars") or base_config.get("cvars") or {})
    variant_cvars = (variant_context.get("cvars") or variant_config.get("cvars") or {})
    changed_cvars = []
    for key in sorted(set(base_cvars) | set(variant_cvars)):
        base_value = base_cvars.get(key)
        variant_value = variant_cvars.get(key)
        if base_value != variant_value:
            changed_cvars.append(
                {
                    "name": key,
                    "base": base_value,
                    "variant": variant_value,
                }
            )
    return {
        "base_capture_path": base_capture.get("capture_path"),
        "variant_capture_path": variant_capture.get("capture_path"),
        "base_context_path": base_capture.get("context_path"),
        "variant_context_path": variant_capture.get("context_path"),
        "structured_inputs": {
            "cvars": changed_cvars,
            "material_switches": {
                "base": base_config.get("material_switches"),
                "variant": variant_config.get("material_switches"),
            },
            "scalability": {
                "base": base_config.get("scalability"),
                "variant": variant_config.get("scalability"),
            },
            "rhi": {
                "base": base_config.get("rhi"),
                "variant": variant_config.get("rhi"),
            },
        },
    }


def capture_renderdoc_diff_pair(
    base_config: Dict[str, Any],
    variant_config: Dict[str, Any],
    workflow: str = "editor",
    comparison_name: Optional[str] = None,
) -> Dict[str, Any]:
    """Capture the same scene twice and emit downstream diff metadata."""
    if not isinstance(base_config, dict) or not isinstance(variant_config, dict):
        return _wrap_result(
            "capture_renderdoc_diff_pair",
            success=False,
            targets=[],
            post_state={},
            failed_changes=[
                {
                    "target": "diff_pair",
                    "field": "config",
                    "error": "base_config and variant_config must be objects",
                }
            ],
            extras={"error": "invalid configs"},
        )

    restore_keys = _dedupe(
        list((base_config.get("cvars") or {}).keys())
        + list((variant_config.get("cvars") or {}).keys())
    )
    original_context = get_renderdoc_capture_context(additional_cvars=restore_keys, include_selection=False)
    original_cvars = original_context.get("rich_context", {}).get(
        "debug_cvars", {}
    ) or {
        key: {"string": value}
        for key, value in (original_context.get("context", {}).get("cvars") or {}).items()
    }

    applied_failures: list[Dict[str, Any]] = []
    base_apply = _apply_live_configuration(base_config)
    applied_failures.extend(base_apply["failed_changes"])
    base_capture = request_renderdoc_capture(
        workflow=workflow,
        after_frames=int(base_config.get("after_frames", 0)),
        capture_name=base_config.get("capture_name") or f"{comparison_name or 'diff'}_base",
        notes=base_config.get("notes"),
        include_selection=True,
        additional_cvars=restore_keys,
    )

    variant_apply = _apply_live_configuration(variant_config)
    applied_failures.extend(variant_apply["failed_changes"])
    variant_capture = request_renderdoc_capture(
        workflow=workflow,
        after_frames=int(variant_config.get("after_frames", 0)),
        capture_name=variant_config.get("capture_name") or f"{comparison_name or 'diff'}_variant",
        notes=variant_config.get("notes"),
        include_selection=True,
        additional_cvars=restore_keys,
    )

    if restore_keys:
        restore_values = {
            key: (original_cvars.get(key) or {}).get("string", "")
            for key in restore_keys
        }
        _apply_live_configuration({"cvars": restore_values})

    success = base_capture.get("success") and variant_capture.get("success") and not applied_failures
    metadata = _build_diff_metadata(
        base_capture,
        variant_capture,
        base_config=base_config,
        variant_config=variant_config,
    )
    metadata_path = None
    if success and comparison_name:
        capture_dir = _capture_dir_for_project()
        metadata_path = _write_json_file(
            capture_dir / f"{_safe_name(comparison_name, 'capture_diff')}.comparison.json",
            metadata,
        )
    checks = [
        _check("diff_pair", "base_capture_success", True, base_capture.get("success")),
        _check("diff_pair", "variant_capture_success", True, variant_capture.get("success")),
    ]
    extras = {
        "base_capture": base_capture,
        "variant_capture": variant_capture,
        "comparison_metadata": metadata,
    }
    if metadata_path:
        extras["comparison_metadata_path"] = metadata_path
    return _wrap_result(
        "capture_renderdoc_diff_pair",
        success=success,
        targets=[
            item
            for item in [
                base_capture.get("capture_path"),
                variant_capture.get("capture_path"),
                metadata_path,
            ]
            if item
        ],
        post_state={
            "diff_pair": {
                "base_capture_path": base_capture.get("capture_path"),
                "variant_capture_path": variant_capture.get("capture_path"),
                "comparison_metadata_path": metadata_path,
            }
        },
        checks=checks,
        failed_changes=applied_failures
        + base_capture.get("failed_changes", [])
        + variant_capture.get("failed_changes", []),
        extras=extras,
    )
