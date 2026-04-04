---
name: unity-to-ue
description: 仅用于 Unity -> UE 迁移任务，当前重点是场景灯光、曝光、坐标/朝向、子关卡写入。
metadata:
  short-description: Unity to Unreal migration workflow for scene transfer tasks
  repo: unreal-mcp
  trigger: unity-to-ue-only
---

## Purpose
只在任务明确涉及 `Unity -> UE` 迁移时使用。

当前重点：

- Unity 灯光迁 UE
- 坐标/朝向转换
- 强度单位与衰减策略
- 曝光初值迁移
- 子关卡定点写入

## 触发条件
满足任一条件才加载：

- 用户明确提到 `Unity -> UE`
- 有 Unity 场景文件、Light YAML、Quaternion/Euler 数据
- 任务目标是把 Unity 场景/灯光复刻到 UE

## 不适用范围
不要用于：

- 纯 UE 内部灯光调整
- 纯 UE 场景搭建
- 纯资产导入
- 材质图 / 蓝图图 / Niagara 图编辑

## 先读什么
1. `docs/migrations/README.md`
2. 与当前场景对应的迁移案例文档
3. `docs/migrations/unity-lighting-playbook.md`
4. `skills/ue-harness/SKILL.md`

如果任务是 `CharacterModelScene_zhengbeishi`，先读：

- `docs/migrations/character-model-scene-zhengbeishi.md`

## 默认执行顺序
1. 先走 `unreal_orchestrator`
2. 先查：
   - `get_editor_ready_state`
   - 必要时 `wait_for_editor_ready`
3. 再执行 scene 相关命令
4. 不默认直接打 legacy raw 工具

## 迁移框架
### 1. 固定源与目标
- Unity 源场景
- 目标 UE 关卡/子关卡
- 本次只迁哪些对象

### 2. 提取 Unity 真值
- 类型
- 启用状态
- 强度
- 颜色/色温
- Range
- Inner/Outer Angle
- 世界位置
- Quaternion 或 `forward/up`
- 后处理曝光信息

### 3. 转换
- 位置：`P_ue_cm = (Z_u, X_u, Y_u) * 100`
- 朝向：优先 `forward/up`，不要硬抄 Unity Euler
- Point/Spot：优先按 `Candelas` 解释，不要默认 UE `Unitless`
- 半径：`AttenuationRadius_cm = UnityRange_m * 100`

### 4. 落地
- 如果要精确写入子关卡：先把子关卡单独 load 成当前编辑关卡
- 优先走高层 scene 工作流
- 不依赖 `LightComponent: {...}` 这种整对象写法

### 5. 验证
至少检查：

- 位置
- 朝向
- 强度
- 单位
- 半径
- cone angle
- 是否落到正确子关卡
- 视口截图

### 6. 输出
至少写清：

- Unity 源对象 -> UE 目标对象映射
- 哪些值是直接迁移
- 哪些值是初值/近似
- 哪些仍未确认

## 注意事项
- 普通使用场景不要自动静默启动编辑器
- 如果编辑器未 ready，先返回状态和 `recommended_action`
- 自动拉起编辑器只允许在 MCP 开发/回归测试里显式触发
