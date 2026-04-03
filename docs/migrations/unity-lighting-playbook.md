# Unity -> UE 灯光迁移工作流框架

这份文档是 `unity-to-ue` skill 的操作版配套说明。

目标：

- 不再把 Unity->UE 迁移理解成“抄几个数值”
- 而是明确一套：提取 -> 转换 -> 落地 -> 验证 的流程

## 适用范围

- Unity 场景灯光迁移到 Unreal
- 当前重点：Directional / Spot / Point / Post Process Exposure

## 标准流程

### 1. 固定输入输出

先固定：

- Unity 源场景路径
- 目标 UE 关卡或子关卡路径
- 本次迁移对象清单

### 2. 提取 Unity 侧规格

每个对象最少提取：

- 类型
- 是否启用
- 强度
- 颜色 / 色温
- Range
- Inner / Outer Angle
- 世界位置
- Quaternion 或 `forward/up`

### 3. 选择迁移策略

#### A. 保真迁移

- 目标：先接近 Unity 当前 runtime 视觉
- Spot / Point 优先按 `Candelas` 解释

#### B. 物理化重建

- 目标：按 UE PBL 重新标定
- 这不是“转换”，而是“重标定”

### 4. 坐标与朝向转换

位置：

```text
P_ue_cm = (Z_u, X_u, Y_u) * 100
```

朝向：

- 优先使用世界 `forward/up`
- 不直接硬抄 Unity Euler

简化情况下：

```text
Yaw_ue   = atan2(Forward_ue.y, Forward_ue.x)
Pitch_ue = atan2(Forward_ue.z, sqrt(Forward_ue.x^2 + Forward_ue.y^2))
Roll_ue  = 0
```

### 5. 关卡写入策略

如果要精确写进子关卡：

- 先把目标子关卡单独 load 成当前编辑关卡
- 再创建/修改灯光
- 最后保存子关卡

### 6. 在 UE 中落地

默认入口：

1. `unreal_orchestrator`
2. `get_editor_ready_state`
3. 必要时 `wait_for_editor_ready`
4. 再执行 `scene` 高层命令

不要默认：

- 猜 legacy raw 字段名
- 直接写 `LightComponent: {...}`

### 7. 验证

至少验证：

- 位置
- 旋转/朝向
- 强度
- 单位
- 半径
- cone angle
- 是否落到正确子关卡
- 视口截图

### 8. 输出

最终输出应包含：

- Unity 源对象 -> UE 目标对象映射
- 哪些值是直接迁移
- 哪些值是初值/近似
- 哪些仍未确认

## 建议高层命令草案

### 1. `collect_unity_light_spec`

输入：

- Unity 场景文件
- 目标对象名列表

输出：

- 结构化灯光规格

### 2. `convert_unity_transform_to_ue`

输入：

- Unity position
- Unity forward/up 或 quaternion

输出：

- UE location
- UE rotation

### 3. `plan_unity_light_migration`

输入：

- Unity 规格
- 迁移策略：`faithful` / `recalibrated`

输出：

- UE 落地计划
- 单位选择
- 需要人工确认的字段

### 4. `apply_unity_light_migration`

输入：

- UE 落地计划
- 目标关卡/子关卡

输出：

- 创建/修改结果
- 对象映射
- 失败项

### 5. `verify_unity_light_migration`

输入：

- 计划值
- UE 当前状态

输出：

- transform 对比
- intensity / unit 对比
- 视口截图路径
- 差异摘要

## 当前建议

在真正把这套高层命令做出来前，先把它作为工作流骨架使用，不要继续在每次迁移时从零开始猜。
