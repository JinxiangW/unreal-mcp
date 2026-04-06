import json
import math
from pathlib import Path
from typing import Any, Dict, List

from unreal_backend_tcp.common import send_command
from unreal_backend_tcp.tools import get_material_graph


MANIFEST_PATH = Path(r"D:\unity-mcp\exports\Wing_L\manifest.json")
MATERIAL_PATH = "/Game/Materials/Wings/M_Wing_L_Rebuild"


def load_manifest() -> Dict[str, Any]:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def get_material_properties(asset_path: str) -> Dict[str, Any]:
    response = send_command(
        "get_asset_properties",
        {
            "asset_path": asset_path,
            "properties": ["OpacityMaskClipValue", "BlendMode", "TwoSided"],
        },
    )
    return (response or {}).get("result", {}).get("properties", {})


def graph_nodes_by_name(graph: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    result: Dict[str, Dict[str, Any]] = {}
    for node in graph.get("nodes") or []:
        parameter_name = node.get("parameter_name")
        if parameter_name:
            result[parameter_name] = node
    return result


def approx_equal(a: float, b: float, tolerance: float = 1e-3) -> bool:
    return math.isfinite(a) and math.isfinite(b) and abs(a - b) <= tolerance


def add_check(checks: List[Dict[str, Any]], name: str, ok: bool, actual: Any, expected: Any) -> None:
    checks.append(
        {
            "name": name,
            "ok": ok,
            "actual": actual,
            "expected": expected,
        }
    )


def main() -> None:
    manifest = load_manifest()
    graph = get_material_graph(asset_path=MATERIAL_PATH, summary_only=False, result_handle=False)["result"]
    material_props = get_material_properties(MATERIAL_PATH)
    nodes_by_param = graph_nodes_by_name(graph)
    property_connections = graph.get("property_connections") or {}
    checks: List[Dict[str, Any]] = []

    world_runtime = manifest.get("worldDissolveRuntime") or {}
    instances = world_runtime.get("instances") or []
    first_instance = instances[0] if instances else {}

    add_check(
        checks,
        "manifest.worldDissolveRuntime.available",
        bool(world_runtime.get("available")),
        world_runtime.get("available"),
        True,
    )
    add_check(
        checks,
        "manifest.worldDissolveRuntime.instanceCount",
        len(instances) >= 1,
        len(instances),
        ">=1",
    )
    add_check(
        checks,
        "manifest.worldDissolveRuntime.activeMasks",
        first_instance.get("activeMasks") == 2,
        first_instance.get("activeMasks"),
        2,
    )
    add_check(
        checks,
        "manifest.worldDissolveRuntime.maskType",
        first_instance.get("maskType") == "Box",
        first_instance.get("maskType"),
        "Box",
    )

    surface = manifest.get("surface") or {}
    add_check(
        checks,
        "material.TwoSided",
        material_props.get("TwoSided") is True,
        material_props.get("TwoSided"),
        True,
    )
    add_check(
        checks,
        "material.BlendMode",
        material_props.get("BlendMode") == 1,
        material_props.get("BlendMode"),
        1,
    )
    add_check(
        checks,
        "material.OpacityMaskClipValue",
        approx_equal(material_props.get("OpacityMaskClipValue", float("nan")), surface.get("alphaCutoff", float("nan"))),
        material_props.get("OpacityMaskClipValue"),
        surface.get("alphaCutoff"),
    )

    required_outputs = [
        "BaseColor",
        "OpacityMask",
        "Normal",
        "Metallic",
        "Roughness",
        "AmbientOcclusion",
        "EmissiveColor",
    ]
    for output_name in required_outputs:
        add_check(
            checks,
            f"graph.output.{output_name}",
            output_name in property_connections,
            property_connections.get(output_name),
            "connected",
        )

    add_check(
        checks,
        "graph.param.UseDissolve.exists",
        "UseDissolve" in nodes_by_param,
        nodes_by_param.get("UseDissolve"),
        "present",
    )
    add_check(
        checks,
        "graph.param.UseDissolve.default",
        approx_equal((nodes_by_param.get("UseDissolve") or {}).get("default_value", float("nan")), 0.0),
        (nodes_by_param.get("UseDissolve") or {}).get("default_value"),
        0.0,
    )

    expected_groups = {
        "BaseColorTexture": "Standard Lit",
        "BaseColorTint": "Standard Lit",
        "NormalTexture": "Standard Lit",
        "Metallic": "Standard Lit",
        "Smoothness": "Standard Lit",
        "AmbientOcclusion": "Standard Lit",
        "GuideTexture": "Guide",
        "GuideTiling": "Guide",
        "GuideStrength": "Guide",
        "UseDissolve": "Dissolve",
        "Invert": "Dissolve",
        "UseDithering": "Dissolve",
        "GlareOffset": "Dissolve",
        "GlareGuideStrength": "Dissolve",
        "GlareWidth": "Dissolve",
        "GlareSmoothness": "Dissolve",
        "GlareColorRGB": "Dissolve",
        "EdgeWidth": "Dissolve",
        "EdgeSmoothness": "Dissolve",
        "EdgeColorRGB": "Dissolve",
        "AffectAlbedo": "Dissolve",
        "UseBackColor": "Dissolve",
        "BackColorRGB": "Dissolve",
    }
    for parameter_name, expected_group in expected_groups.items():
        node = nodes_by_param.get(parameter_name) or {}
        actual_group = node.get("group")
        add_check(
            checks,
            f"graph.group.{parameter_name}",
            actual_group == expected_group if actual_group is not None else False,
            actual_group,
            expected_group,
        )

    report = {
        "success": all(check["ok"] for check in checks),
        "manifest_path": str(MANIFEST_PATH),
        "material_path": MATERIAL_PATH,
        "summary": {
            "total_checks": len(checks),
            "passed": sum(1 for check in checks if check["ok"]),
            "failed": sum(1 for check in checks if not check["ok"]),
        },
        "checks": checks,
        "notes": [
            "Group checks depend on get_material_graph exposing parameter group names.",
            "This verifier proves structural alignment and exported runtime-data availability; it does not prove per-pixel visual parity.",
        ],
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
