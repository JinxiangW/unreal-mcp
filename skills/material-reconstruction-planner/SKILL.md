---
name: material-reconstruction-planner
description: Use when turning an exported material package such as a Unity `manifest.json` plus optional `shadergraph.json` into a `material-reconstruction-plan/0.1`. Use for package inspection, reconstruction-mode selection, plan JSON structure, approximations, unresolved branches, and readable graph layout. Do not use this skill for direct Unreal execution; pair it with `ue-harness` when applying the plan.
---

# Material Reconstruction Planner

## Purpose

Use this skill to plan a reconstruction.

This skill plans only. It does not replace Unreal execution tools.

When execution is about to begin, also read `../ue-harness/SKILL.md`.

## Read First

Read these in order:

1. `../../docs/material-package.md`
2. `../../docs/material-reconstruction-plan.md`
3. The package `manifest.json`, if present
4. The package `shadergraph.json`, if present
5. One package-specific example under `../../docs/examples/`, if present

## Workflow

- Do not skip stages
- Do not jump from package inspection straight to arbitrary UE graph edits
- Do not claim alignment from visual impression alone
- Do not treat `success: true` from one MCP call as proof of correctness

### 1. Inspect the Package

Extract at least these facts:

- source engine and shader family
- surface settings: blend, alpha clip, two-sided, domain
- transferable semantics: baseColor, normal, metallic, roughness, emission, opacity, occlusion
- texture resources and import hints
- graph evidence availability
- warnings, missing subgraphs, and confidence notes

For Unity Shader Graph packages, also check:

- whether `shadergraph.json` exists
- whether subgraph exports exist
- whether any `CustomFunctionNode` exists
- whether copied shader sources exist under `shader_sources/`
- whether runtime-only graph inputs exist and whether matching runtime state was exported

If a custom function exists but its source evidence is missing, stop and fix export first.

If a branch depends on runtime state such as world-space arrays, scene-driven masks, or global shader values, stop and export that runtime state before planning that branch as reconstructable.

### 2. Choose a Reconstruction Mode

Prefer one of these:

- `semantic_surface`
- `graph_guided_semantic_surface`
- `manual_custom_graph`
- `partial_reconstruction`

Decision rule:

- if semantics are sufficient and runtime-only graph logic is missing, stay in `semantic_surface`
- if graph evidence is useful but only part of it is safely reconstructable, use `graph_guided_semantic_surface`
- if a branch depends on missing runtime evidence, mark that branch unresolved instead of guessing

Do not default to exact graph replay when the source exposes opaque slot ids, missing subgraph bodies, or source-specific node types.

### 3. Build the Plan

Always emit these sections:

- `strategy`
- `resourceBindings`
- `execution`
- `approximations`
- `unresolved`
- `verificationGoals`

Also emit these when execution is expected in the same task:

- `executionOrder`
- `stopConditions`
- `validationGate`
- `verificationArtifacts`

Keep the boundary clear:

- `strategy`, `approximations`, and `unresolved` explain planning decisions
- `resourceBindings`, `execution`, and `verificationGoals` are execution-facing

### 3.1 Function Strategy

When the source graph already has meaningful subgraph boundaries, preserve those boundaries in the plan.

Planning rules:

- plan by source subgraph or semantic branch, not by tiny arithmetic steps
- record whether each planned function is expected to be:
  - a project-local reusable function
  - an engine-function reuse
  - a native-node rebuild
  - a small custom fragment
- if the source subgraph is a custom function, preserve that dependency explicitly in the plan unless a clearly better native equivalent is already known
- if the source subgraph depends on external source files or runtime arrays, record those dependencies as required evidence before the branch can be claimed complete
- do not silently replace a source custom subgraph with a guessed scalar or constant

The detailed execution rules for function reuse, custom-node constraints, and stop conditions live in `../ue-harness/SKILL.md`.

### 4. Apply Layout Rules

When generating `execution.graph.recipe.nodes`, choose readable coordinates.

Default layout:

- left-to-right flow
- shared inputs on the far left
- one semantic lane per output group
- utility nodes in the middle
- material outputs on the right

Recommended lanes:

- `BaseColor`
- `Opacity` or `OpacityMask`
- `Normal`
- `Metallic`
- `Roughness`
- `AmbientOcclusion`
- `Emissive`
- custom branches below the core PBR lanes

Recommended placement rules:

- place texture coordinates near the top-left
- place texture and parameter nodes in the first working column
- place combine or transform nodes in the second column
- place the final node of each lane close to the material output
- avoid crossings when a simple lane layout can remove them
- add reroute nodes in the plan when a branch requires a long shared route

### 5. Hand Off to UE Execution

When execution begins, follow the material execution order, stop conditions, and validation rules in `../ue-harness/SKILL.md`.

This planner should not duplicate those execution instructions.

### 6. Record Approximations and Unresolved Logic

Be explicit when simplifying source behavior.

Common approximations:

- roughness derived from smoothness
- alpha inferred from base texture alpha
- default lit used instead of source custom lighting
- guide texture imported but left unconnected
- AO left unconnected when only an occlusion-strength control exists without an occlusion texture

Common unresolved items:

- missing subgraph bodies
- source-specific dissolve logic
- vertex displacement or wind branches
- insufficient port semantics for exact replay
- runtime global arrays not yet exported
- scene-driven mask transforms not yet exported
- source-side object references not stored in the material asset itself
- keyword-controlled branch families without active runtime state

## Output Standard

Output one converged `material-reconstruction-plan/0.1` JSON object.

Prefer:

- stable field names
- short machine-usable strings in `execution`
- long-form reasoning only in `strategy.reason`
- specific `verificationGoals` for properties, output connections, and resource bindings

Recommended `verificationArtifacts`:

- exported package path
- UE material path
- UE function paths
- verification script path
- verification report path

## Package-Specific Patterns

Do not hardcode task-specific package knowledge into this skill.

- Package-specific strategies belong in:
  - the package-level reconstruction plan
  - task-specific examples
  - task-specific validation scripts
- Keep this skill generic across materials and source projects

## Validation Gate

Do not claim reconstruction alignment until all of the following are true:

- the source package contains the graph evidence required by the chosen plan
- runtime evidence exists for every runtime-dependent branch that is claimed reconstructed
- UE material compilation and readback validation pass according to `../ue-harness/SKILL.md`
- parameter grouping is readable and aligned
- a machine-readable verification report exists and passes
