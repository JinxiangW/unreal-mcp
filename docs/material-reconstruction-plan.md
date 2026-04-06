# Material Reconstruction Plan

## Purpose

`reconstruction plan` is the agent-authored execution contract for Unreal MCP.

It should describe:

- what the agent decided to build in UE
- which source evidence informed that decision
- which parts are exact versus approximate
- what Unreal operations must be executed
- what must be verified afterward

This is the right place for agent reasoning output.

## Workflow Role

The intended pipeline is:

1. Source exporter writes a `material package`.
2. Agent reads the package and decides on a reconstruction strategy.
3. Agent emits a `reconstruction plan`.
4. Unreal MCP executes the plan.
5. Unreal MCP verifies the result and returns machine-readable evidence.

## Design Principles

- readable by both agents and deterministic tooling
- explicit about approximations
- explicit about unresolved items
- explicit about resource binding
- explicit about verification expectations

## Recommended Top-Level Shape

```json
{
  "schemaVersion": "material-reconstruction-plan/0.1",
  "planId": "material-plan:Wing_L:2026-04-05T12:00:00Z",
  "sourcePackage": {
    "root": "D:/exports/Wing_L",
    "manifest": "D:/exports/Wing_L/manifest.json"
  },
  "target": {
    "projectPath": "/Game/Materials/Wings",
    "materialName": "M_Wing_L",
    "materialInstanceName": null
  },
  "strategy": {
    "mode": "semantic_surface",
    "reason": "Unity export provides reliable PBR semantics but graph snapshot lacks stable pin names and node parameters.",
    "confidence": 0.74
  },
  "resourceBindings": [],
  "execution": {},
  "approximations": [],
  "unresolved": [],
  "verificationGoals": []
}
```

## Required Top-Level Fields

- `schemaVersion`
- `planId`
- `sourcePackage`
- `target`
- `strategy`
- `resourceBindings`
- `execution`
- `approximations`
- `unresolved`
- `verificationGoals`

## Convergence Rules

To keep plans reusable across agents and execution flows, the plan should be
split conceptually into two layers:

- `decision layer`
  Includes `strategy`, `approximations`, and `unresolved`.
  This is where the agent explains intent, confidence, tradeoffs, and gaps.

- `execution layer`
  Includes `resourceBindings`, `execution`, and `verificationGoals`.
  This should be as deterministic as possible and avoid long-form reasoning.

Practical rules:

- `strategy.reason` may be long; fields inside `execution` should not be.
- `execution` should prefer MCP-facing structures over narrative prose.
- `resourceBindings` should be explicit enough that another agent can import or
  reuse assets without re-reading the source package.
- `verificationGoals` should be minimal, stable, and machine-checkable.
- Source evidence that cannot yet be executed should go into `unresolved`,
  not into ad hoc fields inside `execution`.

## Example

A converged example is provided at:

- [material-reconstruction-plan-wing_l.json](/D:/unreal-mcp/docs/examples/material-reconstruction-plan-wing_l.json)
- [material-reconstruction-plan-wing_l-layout-v2.json](/D:/unreal-mcp/docs/examples/material-reconstruction-plan-wing_l-layout-v2.json)
  This variant keeps the same first-pass semantic strategy but uses a cleaner lane-based node layout.

## `strategy.mode`

Recommended values:

- `semantic_surface`
  Rebuild a UE graph from semantic channels and known material conventions.

- `graph_guided_semantic_surface`
  Mainly rebuild from semantics, but use graph evidence to disambiguate or carry
  custom logic forward where possible.

- `manual_custom_graph`
  Build a custom graph where the agent has enough confidence to specify exact
  nodes and connections.

- `material_instance_only`
  Reuse a known UE parent and only set parameters/textures.

- `partial_reconstruction`
  Reconstruct only the reliable subset and record the rest as unresolved.

## `resourceBindings`

This section bridges package resources to UE assets.

Recommended entry shape:

```json
{
  "resourceId": "baseColor",
  "packageFile": "textures/Wing_L__BaseColor.psd",
  "ueAssetPath": "/Game/Imported/Wings/T_Wing_L_BaseColor",
  "status": "needs_import",
  "usageHints": {
    "samplerType": "Color",
    "compression": "Default",
    "srgb": true
  }
}
```

Recommended `status` values:

- `existing`
- `needs_import`
- `missing`
- `rejected`

## `execution`

This section is the MCP-facing plan.

Recommended shape:

```json
{
  "material": {
    "create": true,
    "path": "/Game/Materials/Wings",
    "name": "M_Wing_L",
    "properties": {
      "shading_model": "DefaultLit",
      "blend_mode": "Masked",
      "two_sided": true
    }
  },
  "graph": {
    "recipe": {
      "nodes": [],
      "connections": [],
      "properties": {}
    }
  },
  "instance": null
}
```

### `execution.graph.recipe`

This should match or translate directly into the current UE material graph
builder payload:

- `nodes`
- `connections`
- `properties`

The key point is:

- the package is for the agent
- the recipe is for Unreal execution

## `approximations`

This section records intentional deviations from source behavior.

Recommended entry shape:

```json
{
  "kind": "semantic_conversion",
  "source": "roughness",
  "decision": "Derived roughness from Unity smoothness using OneMinus.",
  "impact": "May differ from source shader if the graph modifies smoothness downstream."
}
```

Recommended approximation kinds:

- `semantic_conversion`
- `graph_simplification`
- `resource_substitution`
- `output_mapping_guess`
- `uv_mapping_assumption`

## `unresolved`

This section records source evidence the agent could not safely turn into UE
operations.

Recommended entry shape:

```json
{
  "kind": "custom_graph_logic",
  "source": "custom.guideTexture",
  "reason": "No stable UE-side equivalent has been defined yet.",
  "evidence": {
    "rawPropertyNames": ["_GuideTexture", "_GuideTiling", "_GuideStrength"]
  },
  "severity": "warning"
}
```

Recommended unresolved kinds:

- `missing_texture_binding`
- `custom_graph_logic`
- `subgraph_translation_missing`
- `unknown_node_type`
- `insufficient_port_semantics`

## `verificationGoals`

This section defines what the MCP layer must verify after execution.

Recommended entry shape:

```json
[
  {
    "kind": "material_property",
    "field": "blend_mode",
    "expected": "Masked"
  },
  {
    "kind": "graph_output_connected",
    "output": "BaseColor"
  },
  {
    "kind": "graph_output_connected",
    "output": "Normal"
  },
  {
    "kind": "resource_bound",
    "resourceId": "baseColor",
    "expectedAssetPath": "/Game/Imported/Wings/T_Wing_L_BaseColor"
  }
]
```

## Minimum Useful Plan

For the current Unity workflow, the minimum useful plan should support:

- creating a material
- importing or binding textures
- building a core PBR graph
- recording approximations
- recording unresolved custom logic
- requesting graph verification

That is enough to make the agent useful before solving arbitrary Shader Graph
translation.

## Recommended Near-Term Execution Modes

### Mode A: semantic reconstruction

Use:

- `manifest.json`
- semantic channels
- texture bindings
- surface settings

Ignore:

- most graph internals except as evidence

### Mode B: graph-guided reconstruction

Use:

- semantic channels as the main path
- graph evidence to detect special outputs, custom branches, or subgraph usage

Do not require:

- exact Unity node-for-node replay

### Mode C: exact custom recipe

Only use when the agent has enough evidence to specify an exact UE recipe.

This should be opt-in and confidence-gated, not the default.
