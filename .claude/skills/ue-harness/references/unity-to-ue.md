# Unity 到 UE 迁移（Unity-to-UE Migration）

> **Language convention**: conversion formulas, coordinate math, and operational steps are in English. Context, scope decisions, and conceptual notes are in Chinese.

## 用途

仅在任务明确涉及从 Unity 迁移内容到 Unreal 时使用。

当前范围（Current focus）：

- Unity light migration（Unity 灯光迁移）
- coordinate and orientation conversion（坐标系与朝向转换）
- intensity unit and attenuation strategy（强度单位与衰减策略）
- exposure baseline migration（曝光基线迁移）
- writing into the correct level or sublevel（写入正确的关卡或子关卡）

## 适用场景

至少满足以下一项时使用：

- 用户明确说 `Unity -> UE`
- 任务包含 Unity scene files, Light YAML, Quaternion data, or Euler data
- 目标是在 Unreal 内重建 Unity 场景或灯光

不用于（Do not use for）：

- pure UE scene editing
- pure UE lighting adjustments
- pure asset import
- material graph, blueprint graph, or Niagara graph editing

## 阅读顺序

1. `migrations/README.md`
2. 当前场景的迁移案例文档（如果有）
3. `migrations/unity-lighting-playbook.md`
4. `../SKILL.md`

如果任务是 `CharacterModelScene_zhengbeishi`，还需阅读 `migrations/character-model-scene-zhengbeishi.md`。

## 默认执行顺序

1. Start from `unreal_orchestrator`
2. Check:
   - `get_editor_ready_state`
   - `wait_for_editor_ready` when needed
3. Execute scene-domain commands
4. Do not default to legacy raw tools

## 迁移流程（Migration Flow）

### 1. 确定源和目标（Fix Source and Target）

- identify the Unity source scene
- identify the UE target level or sublevel
- state exactly which objects are in scope

### 2. 提取 Unity 数据（Extract Unity Truth）

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

### 3. 转换（Convert）

核心转换公式（Key conversion formulas）：

- **position**: `P_ue_cm = (Z_u, X_u, Y_u) * 100`
- **orientation**: prefer `forward/up`; do not blindly copy Unity Euler values
- **point and spot lights**: prefer interpreting source intensity as `Candelas`; do not default to UE `Unitless`
- **radius**: `AttenuationRadius_cm = UnityRange_m * 100`

### 4. 应用（Apply）

- if exact sublevel placement matters, load that sublevel as the current editing level first
- prefer high-level scene workflows
- avoid giant whole-object property blobs such as `LightComponent: {...}`

### 5. 验证（Verify）

At minimum verify:

- position
- orientation
- intensity
- intensity unit
- radius
- cone angle
- correct target sublevel
- viewport screenshot when applicable

### 6. 报告（Report）

State clearly:

- Unity source object -> UE target object mapping
- which values were transferred directly
- which values are initial guesses or approximations
- which values remain unverified

## 注意事项（Notes）

- Do not auto-launch the editor for ordinary usage tasks
- If the editor is not ready, return the status and `recommended_action` first
- Auto-launch is acceptable only for explicit MCP development or regression work
