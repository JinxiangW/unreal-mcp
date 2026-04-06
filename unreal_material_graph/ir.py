"""Canonical IR helpers for external material graph translation."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, List, Mapping


CANONICAL_IR_SCHEMA_VERSION = "material-graph-ir/0.1"
FORMAT_CANONICAL_IR = "material-graph-ir"
FORMAT_UNITY_MATERIAL_EXPORT_SPEC = "unity-material-export-spec"
FORMAT_UNITY_SHADERGRAPH_EXPORT = "unity-shadergraph-export"
FORMAT_UE_MATERIAL_GRAPH_EXPORT = "ue-material-graph-export"
FORMAT_UNKNOWN = "unknown"


def detect_graph_payload_format(payload: Mapping[str, Any]) -> str:
    """Best-effort detection for supported external graph payloads."""
    schema_version = str(payload.get("schemaVersion") or payload.get("schema_version") or "")
    if schema_version.startswith("material-graph-ir/"):
        return FORMAT_CANONICAL_IR
    if schema_version.startswith("unity-material-export-spec/"):
        return FORMAT_UNITY_MATERIAL_EXPORT_SPEC
    if schema_version.startswith("unity-shadergraph-export/"):
        return FORMAT_UNITY_SHADERGRAPH_EXPORT
    if "asset_type" in payload and "nodes" in payload and "connections" in payload:
        return FORMAT_UE_MATERIAL_GRAPH_EXPORT
    return FORMAT_UNKNOWN


def normalize_graph_ir(payload: Mapping[str, Any]) -> Dict[str, Any]:
    """Normalize a supported payload into the canonical material graph IR."""
    source_format = detect_graph_payload_format(payload)
    if source_format == FORMAT_CANONICAL_IR:
        return _normalize_canonical_ir(payload)
    if source_format == FORMAT_UNITY_MATERIAL_EXPORT_SPEC:
        return _normalize_unity_material_export_spec(payload)
    if source_format == FORMAT_UNITY_SHADERGRAPH_EXPORT:
        return _normalize_unity_shadergraph_export(payload)
    if source_format == FORMAT_UE_MATERIAL_GRAPH_EXPORT:
        return _normalize_ue_material_graph_export(payload)
    raise ValueError("Unsupported graph payload format")


def build_ue_material_recipe(
    payload: Mapping[str, Any],
    *,
    texture_bindings: Mapping[str, str] | None = None,
    material_name: str | None = None,
) -> Dict[str, Any]:
    """Translate a supported payload into the current UE material builder recipe."""
    canonical_ir = normalize_graph_ir(payload)
    graph = canonical_ir["graph"]
    graph_kind = graph.get("kind")

    if graph_kind == "semantic_surface":
        return _build_ue_recipe_from_semantic_surface_ir(
            canonical_ir,
            texture_bindings=texture_bindings or {},
            material_name=material_name,
        )

    if graph_kind == "explicit_graph" and graph.get("dialect") == "ue":
        return {
            "material_name": material_name or graph.get("asset", {}).get("name") or "M_FromCanonicalIR",
            "nodes": deepcopy(graph.get("nodes") or []),
            "connections": deepcopy(graph.get("edges") or []),
            "properties": deepcopy(graph.get("material") or {}),
            "source_format": canonical_ir["source"]["format"],
            "unresolved_resources": [],
            "warnings": list(graph.get("metadata", {}).get("warnings") or []),
        }

    raise ValueError(
        f"Graph kind '{graph_kind}' is not yet translatable into a UE recipe"
    )


def _normalize_canonical_ir(payload: Mapping[str, Any]) -> Dict[str, Any]:
    graph = deepcopy(dict(payload.get("graph") or {}))
    source = deepcopy(dict(payload.get("source") or {}))
    source.setdefault("format", FORMAT_CANONICAL_IR)
    return {
        "schema_version": CANONICAL_IR_SCHEMA_VERSION,
        "source": source,
        "graph": graph,
    }


def _normalize_unity_material_export_spec(payload: Mapping[str, Any]) -> Dict[str, Any]:
    material = deepcopy(dict(payload.get("material") or {}))
    shader = deepcopy(dict(payload.get("shader") or {}))
    surface = deepcopy(dict(payload.get("surface") or {}))
    semantics = deepcopy(dict(payload.get("semantics") or {}))
    textures = deepcopy(list(payload.get("textures") or []))
    warnings = deepcopy(list(payload.get("warnings") or []))

    resources = []
    for texture in textures:
        usage = dict(texture.get("usage") or {})
        resource = {
            "id": texture.get("id"),
            "kind": "texture2d",
            "semantic": texture.get("semantic"),
            "unity_property_name": texture.get("unityPropertyName"),
            "asset": deepcopy(dict(texture.get("asset") or {})),
            "source_file": deepcopy(dict(texture.get("sourceFile") or {})),
            "usage": usage,
            "import_settings": deepcopy(dict(texture.get("importSettings") or {})),
        }
        if resource["id"]:
            resources.append(resource)

    graph = {
        "kind": "semantic_surface",
        "asset": {
            "name": material.get("name"),
            "path": material.get("path"),
            "guid": material.get("guid"),
        },
        "material": {
            "blend_mode": _normalize_blend_mode(surface.get("blendMode")),
            "surface_type": surface.get("surfaceType"),
            "shading_model": "DefaultLit",
            "two_sided": bool(surface.get("twoSided", False)),
            "alpha_clip": bool(surface.get("alphaClip", False)),
            "alpha_cutoff": surface.get("alphaCutoff"),
        },
        "resources": resources,
        "semantics": semantics,
        "metadata": {
            "unity_context": deepcopy(dict(payload.get("unityContext") or {})),
            "shader": shader,
            "classification": deepcopy(dict(payload.get("classification") or {})),
            "keywords": deepcopy(dict(payload.get("keywords") or {})),
            "warnings": warnings,
            "raw_properties": deepcopy(list(payload.get("unityRawProperties") or [])),
        },
    }
    return {
        "schema_version": CANONICAL_IR_SCHEMA_VERSION,
        "source": {
            "format": payload.get("schemaVersion") or "unity-material-export-spec/unknown",
            "tool": "unity-mcp",
        },
        "graph": graph,
    }


def _normalize_unity_shadergraph_export(payload: Mapping[str, Any]) -> Dict[str, Any]:
    graph_payload = dict(payload.get("graph") or {})
    nodes = []
    for node in graph_payload.get("nodes") or []:
        nodes.append(
            {
                "id": node.get("objectId"),
                "type": node.get("type"),
                "label": node.get("displayName"),
                "position": deepcopy(dict(node.get("position") or {})),
                "metadata": {
                    "group_id": node.get("groupId"),
                    "category_ids": deepcopy(list(node.get("categoryIds") or [])),
                    "subgraph_guid": node.get("subGraphGuid"),
                    "subgraph_path": node.get("subGraphPath"),
                    "slot_count": node.get("slots"),
                },
            }
        )

    edges = []
    for edge in graph_payload.get("edges") or []:
        edges.append(
            {
                "source": edge.get("outputNodeId"),
                "source_output": edge.get("outputSlotId"),
                "target": edge.get("inputNodeId"),
                "target_input": edge.get("inputSlotId"),
                "metadata": {"object_id": edge.get("objectId")},
            }
        )

    output = dict(graph_payload.get("output") or {})
    fragment_blocks = list(output.get("fragmentBlocks") or [])
    vertex_blocks = list(output.get("vertexBlocks") or [])

    graph = {
        "kind": "explicit_graph",
        "dialect": "unity_shadergraph_snapshot",
        "asset": deepcopy(dict(payload.get("asset") or {})),
        "material": {},
        "resources": [],
        "nodes": nodes,
        "edges": edges,
        "outputs": {
            "fragment_blocks": fragment_blocks,
            "vertex_blocks": vertex_blocks,
            "output_node": deepcopy(dict(output.get("outputNode") or {})),
        },
        "metadata": {
            "warnings": deepcopy(list(graph_payload.get("warnings") or [])),
            "properties": deepcopy(list(graph_payload.get("properties") or [])),
            "keywords": deepcopy(list(graph_payload.get("keywords") or [])),
            "targets": deepcopy(list(graph_payload.get("targets") or [])),
            "summary": deepcopy(dict(graph_payload.get("summary") or {})),
        },
    }
    return {
        "schema_version": CANONICAL_IR_SCHEMA_VERSION,
        "source": {
            "format": payload.get("schemaVersion") or "unity-shadergraph-export/unknown",
            "tool": "unity-mcp",
        },
        "graph": graph,
    }


def _normalize_ue_material_graph_export(payload: Mapping[str, Any]) -> Dict[str, Any]:
    graph = {
        "kind": "explicit_graph",
        "dialect": "ue",
        "asset": {
            "name": payload.get("name"),
            "path": payload.get("path"),
            "asset_type": payload.get("asset_type"),
        },
        "material": {},
        "resources": [],
        "nodes": deepcopy(list(payload.get("nodes") or [])),
        "edges": deepcopy(list(payload.get("connections") or [])),
        "outputs": deepcopy(dict(payload.get("property_connections") or {})),
        "metadata": {},
    }
    return {
        "schema_version": CANONICAL_IR_SCHEMA_VERSION,
        "source": {
            "format": "ue-material-graph-export/legacy",
            "tool": "unreal-mcp",
        },
        "graph": graph,
    }


def _build_ue_recipe_from_semantic_surface_ir(
    canonical_ir: Mapping[str, Any],
    *,
    texture_bindings: Mapping[str, str],
    material_name: str | None,
) -> Dict[str, Any]:
    graph = dict(canonical_ir["graph"])
    asset = dict(graph.get("asset") or {})
    semantics = dict(graph.get("semantics") or {})
    resources = {
        item.get("id"): item for item in graph.get("resources") or [] if item.get("id")
    }
    warnings = list(graph.get("metadata", {}).get("warnings") or [])
    unresolved_resources: List[Dict[str, Any]] = []
    nodes: List[Dict[str, Any]] = []
    connections: List[Dict[str, Any]] = []
    positions = _PositionCursor()

    def add_node(node_type: str, **fields: Any) -> str:
        node_id = fields.pop("id", f"node_{len(nodes) + 1}")
        x, y = positions.next()
        node = {"id": node_id, "type": node_type, "pos_x": x, "pos_y": y}
        node.update(fields)
        nodes.append(node)
        return node_id

    def add_connection(
        source: str,
        target: str,
        *,
        target_input: str,
        source_output: str = "Output",
    ) -> None:
        connections.append(
            {
                "source": source,
                "source_output": source_output,
                "target": target,
                "target_input": target_input,
            }
        )

    def add_material_connection(
        source: str,
        property_name: str,
        *,
        source_output: str = "Output",
    ) -> None:
        add_connection(
            source,
            "Material",
            target_input=property_name,
            source_output=source_output,
        )

    def resolve_texture_binding(texture_id: str | None) -> str | None:
        if not texture_id:
            return None
        bound = texture_bindings.get(texture_id)
        if bound:
            return bound
        unresolved_resources.append(
            {
                "resource_id": texture_id,
                "semantic": resources.get(texture_id, {}).get("semantic"),
                "reason": "missing_texture_binding",
            }
        )
        return None

    def add_color_constant(value: Mapping[str, Any], *, node_id: str) -> str:
        rgb = [
            float(value.get("r", 0.0)),
            float(value.get("g", 0.0)),
            float(value.get("b", 0.0)),
        ]
        return add_node("Constant3Vector", id=node_id, value=rgb)

    def add_scalar_constant(value: Any, *, node_id: str) -> str:
        return add_node("Constant", id=node_id, value=float(value))

    def add_texture_sample(
        *,
        texture_id: str,
        node_id: str,
        sampler_type: str | None = None,
    ) -> str | None:
        texture_asset_path = resolve_texture_binding(texture_id)
        if not texture_asset_path:
            return None
        node_fields: Dict[str, Any] = {"id": node_id, "texture": texture_asset_path}
        if sampler_type:
            node_fields["sampler_type"] = sampler_type
        return add_node("TextureSample", **node_fields)

    def choose_sampler_type(resource: Mapping[str, Any] | None) -> str | None:
        if not resource:
            return None
        usage = dict(resource.get("usage") or {})
        if usage.get("isNormalMap"):
            return "Normal"
        color_space = str(usage.get("colorSpace") or "").lower()
        if color_space == "linear":
            return "LinearColor"
        semantic = str(resource.get("semantic") or "").lower()
        if semantic in {"metallicroughnessmask", "occlusion"}:
            return "Masks"
        return "Color"

    base_color = dict(semantics.get("baseColor") or {})
    base_texture_id = base_color.get("textureId")
    base_value = dict(base_color.get("value") or {})
    base_texture_node = add_texture_sample(
        texture_id=base_texture_id,
        node_id="basecolor_tex",
        sampler_type=choose_sampler_type(resources.get(base_texture_id)),
    ) if base_texture_id else None
    base_color_node = (
        add_color_constant(base_value, node_id="basecolor_const")
        if base_value
        else None
    )
    if base_texture_node and base_color_node and not _is_identity_color(base_value):
        multiply_node = add_node("Multiply", id="basecolor_mul")
        add_connection(base_texture_node, multiply_node, target_input="A")
        add_connection(base_color_node, multiply_node, target_input="B")
        add_material_connection(multiply_node, "BaseColor")
    elif base_texture_node:
        add_material_connection(base_texture_node, "BaseColor")
    elif base_color_node:
        add_material_connection(base_color_node, "BaseColor")

    normal = dict(semantics.get("normal") or {})
    normal_texture_id = normal.get("textureId")
    if normal_texture_id:
        normal_node = add_texture_sample(
            texture_id=normal_texture_id,
            node_id="normal_tex",
            sampler_type="Normal",
        )
        if normal_node:
            add_material_connection(normal_node, "Normal")

    metallic = dict(semantics.get("metallic") or {})
    metallic_texture_id = metallic.get("textureId")
    metallic_node = add_texture_sample(
        texture_id=metallic_texture_id,
        node_id="metallic_tex",
        sampler_type=choose_sampler_type(resources.get(metallic_texture_id)),
    ) if metallic_texture_id else None
    if metallic_node:
        add_material_connection(metallic_node, "Metallic", source_output=_channel_to_output_name(metallic.get("channel")) or "R")
    elif metallic.get("value") is not None:
        metallic_const = add_scalar_constant(metallic["value"], node_id="metallic_const")
        add_material_connection(metallic_const, "Metallic")

    roughness = dict(semantics.get("roughness") or {})
    roughness_texture_id = roughness.get("textureId")
    roughness_node = add_texture_sample(
        texture_id=roughness_texture_id,
        node_id="roughness_tex",
        sampler_type=choose_sampler_type(resources.get(roughness_texture_id)),
    ) if roughness_texture_id else None
    if roughness_node:
        add_material_connection(roughness_node, "Roughness", source_output=_channel_to_output_name(roughness.get("channel")) or "R")
    elif roughness.get("value") is not None:
        roughness_const = add_scalar_constant(roughness["value"], node_id="roughness_const")
        add_material_connection(roughness_const, "Roughness")

    occlusion = dict(semantics.get("occlusion") or {})
    occlusion_texture_id = occlusion.get("textureId")
    occlusion_node = add_texture_sample(
        texture_id=occlusion_texture_id,
        node_id="occlusion_tex",
        sampler_type=choose_sampler_type(resources.get(occlusion_texture_id)),
    ) if occlusion_texture_id else None
    if occlusion_node:
        add_material_connection(occlusion_node, "AmbientOcclusion", source_output=_channel_to_output_name(occlusion.get("channel")) or "G")
    elif occlusion.get("value") is not None:
        occlusion_const = add_scalar_constant(occlusion["value"], node_id="occlusion_const")
        add_material_connection(occlusion_const, "AmbientOcclusion")

    emission = dict(semantics.get("emission") or {})
    if emission.get("enabled"):
        emission_texture_id = emission.get("textureId")
        emission_texture_node = add_texture_sample(
            texture_id=emission_texture_id,
            node_id="emission_tex",
            sampler_type=choose_sampler_type(resources.get(emission_texture_id)),
        ) if emission_texture_id else None
        emission_color = dict(emission.get("color") or {})
        emission_color_node = (
            add_color_constant(emission_color, node_id="emission_color")
            if emission_color
            else None
        )
        if emission_texture_node and emission_color_node and not _is_identity_color(emission_color):
            emission_mul = add_node("Multiply", id="emission_mul")
            add_connection(emission_texture_node, emission_mul, target_input="A")
            add_connection(emission_color_node, emission_mul, target_input="B")
            add_material_connection(emission_mul, "EmissiveColor")
        elif emission_texture_node:
            add_material_connection(emission_texture_node, "EmissiveColor")
        elif emission_color_node:
            add_material_connection(emission_color_node, "EmissiveColor")

    opacity = dict(semantics.get("opacity") or {})
    blend_mode = graph.get("material", {}).get("blend_mode") or "Opaque"
    opacity_property = "OpacityMask" if blend_mode == "Masked" else "Opacity"
    opacity_texture_id = opacity.get("textureId")
    opacity_texture_node = add_texture_sample(
        texture_id=opacity_texture_id,
        node_id="opacity_tex",
        sampler_type=choose_sampler_type(resources.get(opacity_texture_id)),
    ) if opacity_texture_id else None
    if opacity_texture_node:
        add_material_connection(
            opacity_texture_node,
            opacity_property,
            source_output=_channel_to_output_name(opacity.get("channel")) or "A",
        )
    elif opacity.get("value") is not None and blend_mode != "Opaque":
        opacity_const = add_scalar_constant(opacity["value"], node_id="opacity_const")
        add_material_connection(opacity_const, opacity_property)

    properties = deepcopy(dict(graph.get("material") or {}))
    if properties.get("surface_type") == "Opaque" and properties.get("blend_mode") not in {"Masked", "Translucent", "Additive"}:
        properties["blend_mode"] = "Opaque"

    material_recipe_name = material_name or asset.get("name") or "M_FromCanonicalIR"
    return {
        "material_name": material_recipe_name,
        "nodes": nodes,
        "connections": connections,
        "properties": {
            "shading_model": properties.get("shading_model", "DefaultLit"),
            "blend_mode": properties.get("blend_mode", "Opaque"),
            "two_sided": bool(properties.get("two_sided", False)),
        },
        "source_format": canonical_ir["source"]["format"],
        "canonical_ir": canonical_ir,
        "unresolved_resources": unresolved_resources,
        "warnings": warnings,
    }


def _normalize_blend_mode(value: Any) -> str:
    normalized = str(value or "").strip().lower()
    if normalized == "masked":
        return "Masked"
    if normalized == "translucent" or normalized == "transparent":
        return "Translucent"
    if normalized == "additive":
        return "Additive"
    return "Opaque"


def _channel_to_output_name(channel: Any) -> str | None:
    mapping = {
        "r": "R",
        "g": "G",
        "b": "B",
        "a": "A",
        "rgb": "RGB",
        "rgba": "RGBA",
    }
    if channel is None:
        return None
    return mapping.get(str(channel).strip().lower())


def _is_identity_color(value: Mapping[str, Any]) -> bool:
    return (
        float(value.get("r", 1.0)) == 1.0
        and float(value.get("g", 1.0)) == 1.0
        and float(value.get("b", 1.0)) == 1.0
    )


class _PositionCursor:
    def __init__(self) -> None:
        self._index = 0

    def next(self) -> tuple[int, int]:
        row = self._index // 4
        col = self._index % 4
        self._index += 1
        return col * 320, row * 220
