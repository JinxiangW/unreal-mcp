"""Domain catalog for the new harness architecture."""

from __future__ import annotations

from typing import Any, Dict, List


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
    },
    "asset": {
        "domain": "asset",
        "backend": "internal_tcp_backend",
        "target_backend": "ue_python",
        "status": "active_fallback",
        "summary": "Generic asset CRUD, import, and batch asset workflows.",
        "keywords": ["asset", "import", "texture", "fbx", "folder", "content browser"],
        "packages": ["unreal_asset"],
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
    },
    "niagara": {
        "domain": "niagara",
        "backend": "internal_tcp_backend",
        "target_backend": "hybrid",
        "status": "planned_split",
        "summary": "Niagara graph and emitter workflows.",
        "keywords": ["niagara", "emitter", "particle", "vfx"],
        "packages": [],
    },
    "blueprint_info": {
        "domain": "blueprint_info",
        "backend": "internal_tcp_backend",
        "target_backend": "ue_python",
        "status": "planned_split",
        "summary": "Blueprint inspection, snapshots, and structural analysis.",
        "keywords": [
            "blueprint info",
            "blueprint analyze",
            "widget blueprint",
            "bp info",
        ],
        "packages": [],
    },
    "blueprint_graph": {
        "domain": "blueprint_graph",
        "backend": "internal_tcp_backend",
        "target_backend": "cpp_primary",
        "status": "planned_split",
        "summary": "Blueprint graph editing, node wiring, variables, and functions.",
        "keywords": [
            "blueprint graph",
            "blueprint node",
            "connect nodes",
            "create variable",
        ],
        "packages": [],
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
            "candidate_domains": ["scene", "asset", "material", "material_graph"],
            "reason": "No strong keyword match; default to diagnostics and manual classification.",
        }

    scored.sort(key=lambda item: (-item[0], item[1]))
    primary = scored[0][1]
    return {
        "primary_domain": primary,
        "candidate_domains": [item[1] for item in scored[:3]],
        "reason": f"Matched keywords for domain '{primary}'.",
    }
