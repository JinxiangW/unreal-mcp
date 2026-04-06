# Material Graph IR Plan

This document describes an internal translator layer.

It is not intended to be the user-facing package contract and not intended to
be the agent-facing planning contract.

The recommended top-level workflow is:

1. Source tool exports an agent-readable `material package`.
2. Agent reads the package and produces a UE `reconstruction plan`.
3. Internal translator helpers may normalize parts of that data into a smaller
   canonical IR before building a UE recipe.
4. Unreal MCP executes the UE recipe and verifies the result.

## Goal

Provide a stable intermediate representation that lets agents rebuild Unreal material graphs from external JSON sources without coupling the Unreal builder to Unity-specific payloads.

The intended pipeline is:

1. External source exports JSON.
2. Source-specific translator normalizes it into canonical IR.
3. Unreal-side translator converts canonical IR into a UE material recipe.
4. `material_graph` builder creates nodes, connects edges, applies material properties, and verifies the result.

## Source Formats Observed

### Unity material export package

Observed in `D:\unity-mcp\exports\Wing_L\manifest.json`.

Characteristics:

- Good transfer semantics for PBR-style reconstruction.
- Contains material metadata, surface settings, textures, texture usage, and normalized semantics.
- Does not contain an explicit, engine-agnostic graph.
- Best suited for a `semantic_surface` IR, not direct graph replay.

### Unity ShaderGraph export

Observed in `D:\unity-mcp\exports\Wing_L\shadergraph.json`.

Characteristics:

- Contains structural graph information: nodes, edges, properties, keywords, output blocks.
- Node `type` values remain Unity-specific.
- Edge wiring uses Unity slot ids, not stable cross-engine pin names.
- Does not expose enough cross-engine semantics to act as UE builder input directly.
- Best suited for an `explicit_graph_snapshot` IR that still requires source-specific translation.

## Canonical IR

Canonical IR should support two graph kinds:

### 1. `semantic_surface`

Used when the source can describe the material intent but not a reusable cross-engine node graph.

Recommended shape:

```json
{
  "schema_version": "material-graph-ir/0.1",
  "source": {
    "format": "unity-material-export-spec/1.0"
  },
  "graph": {
    "kind": "semantic_surface",
    "asset": {
      "name": "Wing_L",
      "path": "Assets/Art/Wings/Wing_L.mat"
    },
    "material": {
      "blend_mode": "Masked",
      "shading_model": "DefaultLit",
      "two_sided": true
    },
    "resources": [
      {
        "id": "baseColor",
        "kind": "texture2d",
        "semantic": "baseColor"
      }
    ],
    "semantics": {
      "baseColor": {},
      "normal": {},
      "metallic": {},
      "roughness": {},
      "emission": {},
      "opacity": {},
      "occlusion": {}
    },
    "metadata": {}
  }
}
```

This is the right landing zone for the current Unity material package export.

### 2. `explicit_graph`

Used when the source already describes graph nodes and edges.

Recommended shape:

```json
{
  "schema_version": "material-graph-ir/0.1",
  "source": {
    "format": "unity-shadergraph-export/1.0"
  },
  "graph": {
    "kind": "explicit_graph",
    "asset": {},
    "nodes": [],
    "edges": [],
    "outputs": [],
    "resources": [],
    "metadata": {}
  }
}
```

Important rule:

- `explicit_graph` must use stable node ids and named inputs/outputs where possible.
- Opaque source slot ids may be preserved in `metadata`, but they should not be the long-term execution contract for the UE builder.

## UE Recipe Boundary

The current UE builder still consumes a UE-specific recipe:

- `nodes`
- `connections`
- `properties`

That recipe should stay UE-specific. Canonical IR should translate into it, not replace it directly.

Immediate implication:

- Do not make `get_material_graph` export format the canonical IR.
- Do not feed Unity export JSON straight into `build_material_graph`.

## Translator Boundary

Recommended split:

- `unity material export spec -> canonical semantic_surface IR`
- `unity shadergraph export -> canonical explicit_graph snapshot`
- `canonical semantic_surface IR -> UE material recipe`
- `canonical explicit_graph IR -> UE material recipe`

Only the last step should depend on Unreal node names and builder payload details.

## First Milestone

1. Add canonical IR helpers in `unreal_material_graph/ir.py`.
2. Support `unity-material-export-spec/1.0 -> semantic_surface IR`.
3. Support `semantic_surface IR -> UE recipe` for the core PBR subset:
   `baseColor`, `normal`, `metallic`, `roughness`, `emission`, `opacity`, `occlusion`.
4. Preserve unresolved resource bindings explicitly instead of silently dropping textures.
5. Add golden fixtures for:
   `unity manifest`
   `unity shadergraph snapshot`
   `canonical IR`
   `generated UE recipe`

## Known Gaps To Fix Next

- UE-side builder and exporter still have protocol drift risk around texture/resource fields.
- Unity ShaderGraph edges currently expose slot ids, not stable pin names.
- Alpha cutoff and some advanced surface settings need explicit UE-side handling.
- Custom ShaderGraph logic and subgraphs need a source-specific translator, not generic builder branches.
