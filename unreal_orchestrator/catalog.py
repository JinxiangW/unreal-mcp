"""Domain catalog for the new harness architecture."""

from __future__ import annotations

from typing import Any, Dict, List


def _domain_connection(
    server_module: str | None,
    *,
    requires_editor_ready: bool,
) -> Dict[str, Any]:
    if not server_module:
        return {
            "available": False,
            "reason": "No standalone domain server is available yet.",
        }
    return {
        "available": True,
        "command": "python",
        "args": ["-m", server_module],
        "server_module": server_module,
        "requires_editor_ready": requires_editor_ready,
    }


DOMAIN_CATALOG: Dict[str, Dict[str, Any]] = {
    "scene": {
        "domain": "scene",
        "backend": "internal_tcp_backend",
        "target_backend": "ue_python",
        "status": "active_fallback",
        "summary": "Scene, actor, light, post process, level and viewport workflows.",
        "keywords": [
            "scene",
            "actor",
            "light",
            "lighting",
            "post process",
            "postprocess",
            "level",
            "viewport",
            "camera",
            "spotlight",
            "directional light",
        ],
        "packages": ["unreal_scene"],
        "server_module": "unreal_scene.server",
        "recommended_connection": _domain_connection(
            "unreal_scene.server",
            requires_editor_ready=True,
        ),
        "recommended_usage": "Enable this domain for actor, light, level, viewport, and post-process edits.",
    },
    "asset": {
        "domain": "asset",
        "backend": "internal_tcp_backend",
        "target_backend": "ue_python",
        "status": "active_fallback",
        "summary": "Generic asset CRUD, import, and batch asset workflows.",
        "keywords": ["asset", "import", "texture", "fbx", "folder", "content browser"],
        "packages": ["unreal_asset"],
        "server_module": "unreal_asset.server",
        "recommended_connection": _domain_connection(
            "unreal_asset.server",
            requires_editor_ready=True,
        ),
        "recommended_usage": "Enable this domain for asset queries, CRUD, import, texture properties, and batch asset edits.",
    },
    "material": {
        "domain": "material",
        "backend": "internal_tcp_backend",
        "target_backend": "ue_python",
        "status": "active_fallback",
        "summary": "Material assets, material instances, and parameter workflows.",
        "keywords": [
            "material instance",
            "material parameter",
            "material asset",
            "mi_",
            "m_",
        ],
        "packages": ["unreal_material"],
        "server_module": "unreal_material.server",
        "recommended_connection": _domain_connection(
            "unreal_material.server",
            requires_editor_ready=True,
        ),
        "recommended_usage": "Enable this domain for material assets, material functions, material instances, and parameters.",
    },
    "material_graph": {
        "domain": "material_graph",
        "backend": "internal_tcp_backend",
        "target_backend": "cpp_primary",
        "status": "planned_split",
        "summary": "Material graph editing, node creation, wiring, and graph analysis.",
        "keywords": [
            "material graph",
            "material node",
            "connect node",
            "base color",
            "roughness",
        ],
        "packages": ["unreal_material_graph"],
        "server_module": "unreal_material_graph.server",
        "recommended_connection": _domain_connection(
            "unreal_material_graph.server",
            requires_editor_ready=True,
        ),
        "recommended_usage": "Enable this domain for material graph readback, node creation, wiring, and patch operations.",
    },
    "renderdoc": {
        "domain": "renderdoc",
        "backend": "python",
        "target_backend": "ue_context_and_capture_control",
        "status": "active",
        "summary": "RenderDoc capture control, UE context snapshots, selection mapping, and diff metadata helpers.",
        "keywords": [
            "renderdoc",
            "capture",
            "rdc",
            "gpu debug",
            "viewport issue",
            "selection capture",
            "render graph",
            "rdg pass",
        ],
        "packages": ["unreal_renderdoc"],
        "server_module": "unreal_renderdoc.server",
        "recommended_connection": _domain_connection(
            "unreal_renderdoc.server",
            requires_editor_ready=False,
        ),
        "recommended_usage": "Enable this domain for UE-side RenderDoc capture context, capture requests, and symbol lookup helpers.",
    },
    "niagara": {
        "domain": "niagara",
        "backend": "internal_tcp_backend",
        "target_backend": "hybrid",
        "status": "planned_split",
        "summary": "Niagara graph and emitter workflows.",
        "keywords": ["niagara", "emitter", "particle", "vfx"],
        "packages": [],
        "recommended_connection": _domain_connection(
            None,
            requires_editor_ready=True,
        ),
        "recommended_usage": "Niagara remains a planned split; use legacy/internal fallback only when needed.",
    },
    "blueprint_info": {
        "domain": "blueprint_info",
        "backend": "internal_tcp_backend",
        "target_backend": "ue_python",
        "status": "active_fallback",
        "summary": "Blueprint inspection, snapshots, and structural analysis.",
        "keywords": [
            "blueprint info",
            "blueprint analyze",
            "widget blueprint",
            "bp info",
        ],
        "packages": ["unreal_blueprint"],
        "server_module": "unreal_blueprint.server",
        "recommended_connection": _domain_connection(
            "unreal_blueprint.server",
            requires_editor_ready=True,
        ),
        "recommended_usage": "Enable this domain for blueprint inspection and structural analysis.",
    },
    "blueprint_graph": {
        "domain": "blueprint_graph",
        "backend": "internal_tcp_backend",
        "target_backend": "cpp_primary",
        "status": "active_fallback",
        "summary": "Blueprint graph editing, node wiring, variables, and functions.",
        "keywords": [
            "blueprint graph",
            "blueprint node",
            "connect nodes",
            "create variable",
        ],
        "packages": ["unreal_blueprint"],
        "server_module": "unreal_blueprint.server",
        "recommended_connection": _domain_connection(
            "unreal_blueprint.server",
            requires_editor_ready=True,
        ),
        "recommended_usage": "Enable this domain for blueprint graph node, pin, variable, and function edits.",
    },
    "diagnostics": {
        "domain": "diagnostics",
        "backend": "python",
        "target_backend": "python",
        "status": "active",
        "summary": "Harness routing, capability discovery, and troubleshooting helpers.",
        "keywords": [
            "diagnostic",
            "debug",
            "unknown command",
            "connection closed",
            "route",
        ],
        "packages": ["unreal_diagnostics"],
        "server_module": "unreal_diagnostics.server",
        "recommended_connection": _domain_connection(
            "unreal_diagnostics.server",
            requires_editor_ready=False,
        ),
        "recommended_usage": "Enable this domain for deeper health, transport, ready-state, and token diagnostics.",
    },
}


def list_domains() -> List[Dict[str, Any]]:
    return [DOMAIN_CATALOG[key] for key in sorted(DOMAIN_CATALOG)]


def get_domain(domain: str) -> Dict[str, Any]:
    key = domain.strip().lower()
    if key not in DOMAIN_CATALOG:
        supported = ", ".join(sorted(DOMAIN_CATALOG))
        raise ValueError(f"Unsupported domain '{domain}'. Supported: {supported}")
    return DOMAIN_CATALOG[key]


def route_text(text: str) -> Dict[str, Any]:
    query = (text or "").lower()
    scored = []
    for domain, info in DOMAIN_CATALOG.items():
        score = sum(1 for keyword in info["keywords"] if keyword in query)
        if score > 0:
            scored.append((score, domain, info))

    if not scored:
        return {
            "primary_domain": "diagnostics",
            "candidate_domains": ["scene", "asset", "material", "material_graph", "renderdoc"],
            "reason": "No strong keyword match; default to diagnostics and manual classification.",
        }

    scored.sort(key=lambda item: (-item[0], item[1]))
    primary = scored[0][1]
    return {
        "primary_domain": primary,
        "candidate_domains": [item[1] for item in scored[:3]],
        "reason": f"Matched keywords for domain '{primary}'.",
    }
