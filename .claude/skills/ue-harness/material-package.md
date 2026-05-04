# Material Package

## Purpose

`material package` is the source-side delivery format for the agent.

It is not required to be a strict cross-engine IR.
It should optimize for:

- readability by an LLM agent
- retention of source evidence
- enough semantic information to plan a UE reconstruction
- enough raw structure to diagnose complex custom graphs

The package should preserve source truth, not prematurely force a rigid
cross-engine graph model.

## Workflow Role

The intended pipeline is:

1. Unity or another source exporter writes a `material package`.
2. Agent reads the package and infers a UE reconstruction strategy.
3. Agent emits a `reconstruction plan`.
4. Unreal MCP executes the plan.

## Package Directory

Recommended directory layout:

```text
<MaterialName>/
  manifest.json
  shadergraph.json                # optional
  subgraphs/
    index.json                    # optional
    *.json                        # optional
  textures/
    <exported texture files>      # optional but recommended
```

Notes:

- `manifest.json` is required.
- `shadergraph.json` is optional, but should be present when the source material
  is driven by a graph and the exporter can inspect it.
- `subgraphs/` is optional.
- Texture binaries may live at package root for backward compatibility, but
  `textures/` is the preferred target for new exports.

## Manifest Goals

`manifest.json` should answer these questions directly:

- what material was exported
- what shader/pipeline it came from
- whether the material is suitable for semantic reconstruction, graph-aware
  reconstruction, or only partial transfer
- what textures and non-texture parameters exist
- what surface settings matter in UE
- what warnings or ambiguities the agent must consider
- where the optional graph evidence files are

## Recommended Manifest Shape

```json
{
  "schemaVersion": "material-package/0.1",
  "source": {
    "engine": "Unity",
    "tool": "unity-mcp",
    "toolSchema": "unity-material-export-spec/1.0",
    "exportedAtUtc": "2026-04-05T12:00:00Z"
  },
  "material": {
    "name": "Wing_L",
    "path": "Assets/Art/Wings/Wing_L.mat",
    "guid": "..."
  },
  "shader": {
    "name": "Shader Graphs/World Dissolve Smooth",
    "path": "Assets/Shaders/World Dissolve Smooth.shadergraph",
    "guid": "...",
    "pipeline": "HDRP",
    "isGraphDriven": true
  },
  "classification": {
    "reconstructionMode": "semantic_surface_with_graph_evidence",
    "confidence": 0.45,
    "notes": []
  },
  "surface": {
    "surfaceType": "Opaque",
    "blendMode": "Masked",
    "alphaClip": true,
    "alphaCutoff": 0.309,
    "twoSided": true
  },
  "semantics": {
    "baseColor": {},
    "normal": {},
    "metallic": {},
    "roughness": {},
    "emission": {},
    "opacity": {},
    "occlusion": {},
    "custom": []
  },
  "textures": [],
  "parameters": {
    "rawProperties": [],
    "keywords": {}
  },
  "graphEvidence": {
    "mainGraphFile": "shadergraph.json",
    "subgraphIndexFile": "subgraphs/index.json",
    "available": true
  },
  "warnings": []
}
```

## Required Top-Level Fields

- `schemaVersion`
- `source`
- `material`
- `shader`
- `classification`
- `surface`
- `semantics`
- `textures`
- `warnings`

## `classification.reconstructionMode`

Recommended values:

- `semantic_surface`
  Use when the exporter can provide reliable surface semantics and graph details
  are missing or not useful.

- `semantic_surface_with_graph_evidence`
  Use when surface semantics are the main reconstruction path, but graph files
  are available as supporting evidence.

- `graph_snapshot`
  Use when the exporter can only provide graph structure and very limited
  transfer semantics.

- `partial_transfer_only`
  Use when only some textures/parameters are reliable and full graph rebuilding
  is not realistic.

## `semantics`

This section should be agent-friendly and source-agnostic where possible.

Recommended standard keys:

- `baseColor`
- `normal`
- `metallic`
- `roughness`
- `emission`
- `opacity`
- `occlusion`
- `uvTransform`
- `custom`

Each semantic entry may carry:

- `value`
- `textureId`
- `channel`
- `uv`
- `rawPropertyNames`
- `conversion`
- `enabled`
- source-specific extra fields when needed

## `textures`

Each texture entry should be a reusable evidence record, not just a filename.

Recommended fields:

```json
{
  "id": "baseColor",
  "semantic": "baseColor",
  "asset": {
    "name": "T_Valkyrie_Wings",
    "path": "Assets/Art/Wings/T_Valkyrie_Wings.psd",
    "guid": "...",
    "type": "UnityEngine.Texture2D"
  },
  "packageFile": {
    "relativePath": "textures/Wing_L__BaseColor.psd",
    "exists": true
  },
  "sourceFile": {
    "absolutePath": "C:/Project/.../T_Valkyrie_Wings.psd",
    "exists": true
  },
  "usage": {
    "colorSpace": "sRGB",
    "isNormalMap": false,
    "uvSet": 0,
    "channelPacking": {}
  },
  "importHints": {}
}
```

## `graphEvidence`

This section should point to optional graph files and summarize their trust
level.

Recommended fields:

- `available`
- `mainGraphFile`
- `subgraphIndexFile`
- `schema`
- `nodeCount`
- `edgeCount`
- `limitations`

## Evidence Preservation Rule

The package should preserve source evidence even when it is not yet fully
usable by Unreal.

Examples:

- keep Unity keywords
- keep raw property names
- keep graph node types and slot ids
- keep warnings and confidence notes

The agent can ignore some of this data when planning, but should not lose it at
export time.

## First Exporter Target

For the current Unity exporter, the near-term target should be:

- retain the current `manifest.json` strengths
- rename or wrap it as a `material package`
- make graph evidence references explicit
- move copied textures under `textures/`
- preserve Unity-specific data under clearly named source fields instead of
  pretending it is already canonical
