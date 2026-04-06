---
name: unity-to-ue
description: Use only for Unity-to-Unreal scene or lighting migration work. Covers Unity scene and lighting transfer, coordinate and orientation conversion, intensity-unit and attenuation mapping, exposure baseline migration, and writing results into the correct UE level or sublevel. Do not use for material graph, blueprint graph, Niagara, or general Unreal-only editing tasks.
---

# Unity to UE

## Purpose

Use this skill only when the task is explicitly about migrating content from Unity to Unreal.

Current focus:

- Unity light migration
- coordinate and orientation conversion
- intensity unit and attenuation strategy
- exposure baseline migration
- writing into the correct level or sublevel

## Use This Skill When

Use it when at least one of these is true:

- the user explicitly says `Unity -> UE`
- the task includes Unity scene files, Light YAML, Quaternion data, or Euler data
- the goal is to recreate a Unity scene or lighting setup inside Unreal

Do not use it for:

- pure UE scene editing
- pure UE lighting adjustments
- pure asset import
- material graph, blueprint graph, or Niagara graph editing

## Read First

1. `docs/migrations/README.md`
2. The migration case doc for the current scene, if one exists
3. `docs/migrations/unity-lighting-playbook.md`
4. `../ue-harness/SKILL.md`

If the task is `CharacterModelScene_zhengbeishi`, also read:

- `docs/migrations/character-model-scene-zhengbeishi.md`

## Default Execution Order

1. Start from `unreal_orchestrator`
2. Check:
   - `get_editor_ready_state`
   - `wait_for_editor_ready` when needed
3. Execute scene-domain commands
4. Do not default to legacy raw tools

## Migration Flow

### 1. Fix Source and Target

- identify the Unity source scene
- identify the UE target level or sublevel
- state exactly which objects are in scope

### 2. Extract Unity Truth

Capture:

- type
- enabled state
- intensity
- color or color temperature
- range
- inner and outer angle
- world position
- quaternion or `forward/up`
- post-process exposure data

### 3. Convert

- position: `P_ue_cm = (Z_u, X_u, Y_u) * 100`
- orientation: prefer `forward/up`; do not blindly copy Unity Euler values
- point and spot lights: prefer interpreting source intensity as `Candelas`; do not default to UE `Unitless`
- radius: `AttenuationRadius_cm = UnityRange_m * 100`

### 4. Apply

- if exact sublevel placement matters, load that sublevel as the current editing level first
- prefer high-level scene workflows
- avoid giant whole-object property blobs such as `LightComponent: {...}`

### 5. Verify

At minimum verify:

- position
- orientation
- intensity
- intensity unit
- radius
- cone angle
- correct target sublevel
- viewport screenshot when applicable

### 6. Report

State clearly:

- Unity source object -> UE target object mapping
- which values were transferred directly
- which values are initial guesses or approximations
- which values remain unverified

## Notes

- Do not auto-launch the editor for ordinary usage tasks
- If the editor is not ready, return the status and `recommended_action` first
- Auto-launch is acceptable only for explicit MCP development or regression work
