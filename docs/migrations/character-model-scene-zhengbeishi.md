# CharacterModelScene_zhengbeishi Unity -> UE 对照

## 1. 文档目的

这份文档用于把 Unity 场景 `CharacterModelScene_zhengbeishi` 的关键灯光同步到 UE 子关卡时，先把坐标、朝向、单位和后处理曝光相关结论固化下来，避免边试边猜。

Unity 源场景：

- `E:\snqx2\Client\Assets\ArtsResource_Discard\Scene\TestSceneModelNew\CharacterModelScene_zhengbeishi.unity`

目标 UE 子关卡：

- `/Game/PVFeature/TA/Scene/ShowRoom/ShowRoom_Lighting_mcptest.ShowRoom_Lighting_mcptest`

## 2. 这次确认过的资料来源

Unity：

- Unity Manual: `Quaternion and euler rotations in Unity`
- Unity Scripting API: `Transform.forward`
- Unity Manual: `Light component Inspector window reference for the Built-In Render Pipeline`
- Unity HDRP docs: `Light component reference`

Unreal / UE MCP：

- `D:\ue-mcp\unreal-mcp\README.md`
- `D:\ue-mcp\unreal-mcp\docs\workflow.md`
- `D:\ue-mcp\unreal-mcp\skills\ue-harness\SKILL.md`
- `D:\ue-mcp\unreal-mcp\docs\inventory.md`
- `D:\ue-mcp\unreal-mcp\unreal_scene\tools.py`

补充参考：

- Silicon Studio: `Using physical lighting units with Enlighten and UE4`
- Magnopus: `Lighting in Unreal with photography principles using PBL`

## 3. UE MCP / skill 结论

- `unreal-mcp` 当前对场景类操作的推荐后端是 `live editor python`。
- `scene` 类工作优先走 live editor，不适合 commandlet。
- 当前暴露的基础 actor 能力包括 `spawn_actor`、`get_actor_properties`、`load_level`、`save_current_level`。
- 仓库里的高层 scene 命令已经规划了 `set_post_process_overrides`、`spawn_actor_with_defaults` 等，但这次会话里直接暴露给我的工具主要还是基础包装。
- `spawn_actor` 底层实现明确写的是 `Spawn an actor in the current level`，也就是默认刷进“当前编辑关卡”。
- 这意味着如果一定要精确写入某个子关卡，最稳妥的方法不是在 Persistent Level 里直接刷，而是把子关卡单独 load 为当前关卡后再写入并保存。

## 4. Unity 场景里的关键灯光

### 4.1 主方向光候选

#### `main_light`

- 行号：`28003-28108`
- 类型：Directional
- 激活：是
- 组件启用：是
- 强度：`0.9`
- 颜色：`(1, 1, 1, 1)`
- 阴影：启用，`m_Type: 2`
- Unity 位置：`(-0.1704, 3.5702, -7.5145)`
- Unity 欧拉提示：`(22.0000, 301.9, 0)`
- 这是当前场景里真正启用中的主方向光候选。

#### `Skybox-Panoramic Light`

- 行号：`70960-71049`
- 类型：Directional
- 激活：是
- 组件启用：否
- 强度：`1`
- 颜色：`(1, 0.7725, 0.4941, 1)`
- 场景 `RenderSettings.m_Sun` 指向的是它：`line 40`
- 这是“登记为 Sun 的方向光”，但当前是禁用状态。

### 4.2 最亮的两盏聚光

#### `Spot Light (1)`

- 行号：`33961-34052`
- 类型：Spot
- 激活：是
- 组件启用：是
- 强度：`100`
- 颜色：`(1, 0.9137, 0.78, 1)`
- Range：`10`
- Outer Angle：`110`
- Inner Angle：`40`
- 阴影：启用，`m_Type: 2`
- Unity 位置：`(0.68, 2.49, 12.3)`
- Unity 欧拉提示：`(126.228, 0, 0)`

#### `Spot Light (2)`

- 行号：`64514-64605`
- 类型：Spot
- 激活：是
- 组件启用：是
- 强度：`100`
- 颜色：`(1, 0.9137, 0.78, 1)`
- Range：`10`
- Outer Angle：`110`
- Inner Angle：`40`
- 阴影：启用，`m_Type: 2`
- Unity 位置：`(5.09, 2.172, 12.73)`
- Unity 欧拉提示：`(126.228, 0, 0)`

## 5. Unity 后处理与曝光

### 5.1 场景内直接确认到的内容

场景里有一个 `_PostEffect` 对象：

- 名称：`_PostEffect`
- 行号：`14862-14875`
- Volume 组件：`14949-14965`
- `sharedProfile` GUID：`2d61a2d3eb4b0574ca2c97b0b7111d6e`
- `isGlobal: 0`
- `blendDistance: 0`
- `weight: 1`

### 5.2 曝光信息当前能确认到什么

当前真正被 `_PostEffect` 引用的 `sharedProfile` 资源本体没有在已拉下来的正常资产目录里找到，只能看到 GUID 引用，没法从它直接读出最终的 `postExposure`。

能确认的只有这些：

- 场景主相机开启了后处理：`m_RenderPostProcessing: 1`
- 当前目录里本地有一个 `TestSceneModel_postprocess.asset`，但它只明确包含 `Tonemapping`，没有 `ColorAdjustments.postExposure`
- 同目录 `LF/_PostEffect Profile_loungePC_20230802.asset` 里有 `ColorAdjustments.postExposure = 0`，但它不是当前场景引用的同一个 GUID
- `Client\Assets\Scene\Character_Editor_Scene_ed\Main Camera Profile.asset` 里有 `ColorAdjustments.postExposure = 1`，但它也不是当前场景引用的同一个 GUID

### 5.3 当前关于曝光补偿的结论

- 这次能确认“场景启用了后处理”，但不能把 `CharacterModelScene_zhengbeishi` 的真实 `postExposure` 当成已经百分百读到。
- 当前可作为参考值的只有两个近似样本：`0` 和 `1`。
- 如果后面 UE 侧需要先给一个安全初值，建议先从 `Exposure Compensation = 0` 起，再根据视口对比决定是否推到 `1`。
- 不建议把一个并未找到本体的 Unity Volume Profile 强行当成已知真值。

## 6. Unity -> UE 坐标和朝向转换

## 6.1 坐标系结论

Unity：

- 左手系
- `+X` 向右
- `+Y` 向上
- `+Z` 向前

Unreal：

- 左手系
- `+X` 向前
- `+Y` 向右
- `+Z` 向上

两边都是左手系，所以这次转换不需要额外做镜像翻转，主要是轴重排加单位缩放。

## 6.2 位置转换

Unity 单位通常按米理解，UE 世界单位默认是厘米。

位置建议按下面转换：

```text
X_ue = Z_unity * 100
Y_ue = X_unity * 100
Z_ue = Y_unity * 100
```

写成向量就是：

```text
P_ue_cm = (Z_u, X_u, Y_u) * 100
```

## 6.3 forward / up 向量转换

Unity 的 `Transform.forward` 是物体的蓝轴，也就是本地前向。

如果你已经有 Unity 世界空间的 `forward` 和 `up`，直接按同样的轴重排即可：

```text
Forward_ue = (Forward_u.z, Forward_u.x, Forward_u.y)
Up_ue      = (Up_u.z,      Up_u.x,      Up_u.y)
```

这一步对灯光尤其重要，因为灯光真正需要对齐的是“照射方向”。

## 6.4 旋转转换建议

不要直接硬套 Unity Euler -> UE Rotator 的单行公式。原因：

- Unity 编辑器显示的是 Euler，但内部存的是 quaternion
- Unity 和 UE 的 Euler 轴定义与应用顺序不同
- 直接抄欧拉角非常容易在边界角度上出错

更稳的做法：

1. 先从 Unity quaternion 算出世界 `forward` 和 `up`
2. 把 `forward/up` 映射到 UE
3. 在 UE 里由 `forward/up` 重建朝向

对这次的灯光同步，有一个简化：

- DirectionalLight 和 SpotLight 都是绕光轴对称的
- 只要光照方向对了，`roll` 通常不影响结果

所以实操里可以：

```text
Yaw_ue   = atan2(Forward_ue.y, Forward_ue.x)
Pitch_ue = atan2(Forward_ue.z, sqrt(Forward_ue.x^2 + Forward_ue.y^2))
Roll_ue  = 0
```

如果后面要同步的是非对称相机 rig、cookie 或带明显 roll 含义的对象，再按 `forward + up` 还原完整姿态。

## 7. Unity -> UE 灯光单位换算

## 7.0 这次真正缺的不是“单位”，而是“衰减模型 + 单位一起看”

你提到的问题是对的：

- `Unity intensity = 100 (unitless)` 看起来可用
- 但 `UE intensity = 100 (unitless)` 在 `Inverse Squared Falloff` 下会很快变暗

这不是单纯的“数值大小不一样”，而是因为：

1. Unity 这套项目的 shader 里，point/spot 的 runtime 衰减就是 `1 / d^2`
2. UE 的 `Unitless` 在 inverse-squared 分支里是 legacy 标度，不等于 `Candela`

所以必须把：

- Unity shader
- UE 引擎本身的 local light 单位换算

一起看。

## 7.1 Unity 这份项目里 point / spot 的 runtime 衰减公式

`Client\Packages\com.sunborn.rp.universal\ShaderLibrary\Lighting.hlsl:52-77`

Unity 运行时本体：

```text
attenuation = 1 / distance^2 * smoothFactor
```

而在非 mobile 路径下，`smoothFactor` 是：

```text
factor = distance^2 / range^2
smoothFactor = (1 - factor^2)^2
```

也就是：

```text
attenuation_unity = 1 / d^2 * (1 - (d^2 / r^2)^2)^2
```

关键证据：

- `Lighting.hlsl:58` `lightAtten = rcp(distanceSqr)`
- `Lighting.hlsl:62-64` `smoothFactor = (1 - factor*factor)^2`
- `ForwardLights.cs:179-201` 明确写了 `attenuation = 1.0 / distanceToLightSqr`

另外，`Common.hlsl:10` 还明确写了：

```text
1 Unity unit == 1 meter
```

这意味着 Unity 这边的数值语义，其实已经非常接近“按米工作的 inverse-square 强度”。

## 7.2 先判断这份 Unity 场景是不是物理单位灯光

不是。

判断依据：

- 当前场景的 Light YAML 里只有传统的 `m_Intensity / m_Range / m_SpotAngle`
- 没有 HDRP 额外的光照单位字段
- Unity Built-In Light 文档对这类灯的 `Intensity` 只定义为 brightness，没有给物理单位

所以这份场景里的：

- `main_light.intensity = 0.9`
- `Spot Light (1/2).intensity = 100`

本质上都是 **unitless authoring value**，不是直接可换算成 lux / lumen / candela 的物理量。

## 7.3 UE 标准 inverse-squared local light 的关键结论

UE 默认 LocalLight：

- 世界单位：厘米
- `AttenuationRadius`：厘米
- Point / Spot 默认：`bUseInverseSquaredFalloff = true`
- 默认 `AttenuationRadius = 1000`

关键代码：

- `LocalLightComponent.cpp:17-20`
- `PointLightComponent.cpp:119-123`

### 7.3.1 为什么 UE `Unitless` 会比你预期暗很多

`PointLightComponent.cpp:212-235` 和 `SpotLightComponent.cpp:250-273` 里，inverse-squared 分支对不同单位做了不同的亮度换算。

对 Spot：

- `Candela`：乘 `100 * 100`
- `Lumens`：乘 `100 * 100 / (2*pi*(1-cosHalfCone))`
- `Unitless`：只乘 `16`

对 Point：

- `Candela`：乘 `100 * 100`
- `Lumens`：乘 `100 * 100 / (4*pi)`
- `Unitless`：只乘 `16`

这说明：

```text
在 UE inverse-squared 分支里，Unitless 是 legacy scale，不是物理强度单位。
```

如果按 point light 近似比较：

```text
1 candela -> brightness scale 10000
1 unitless -> brightness scale 16
```

所以：

```text
1 UE unitless ~= 0.0016 candela
100 UE unitless ~= 0.16 candela
```

这就是你观察到“UE 100 unitless 稍微远一点几乎没亮度”的根本原因。

## 7.4 Unity 100 unitless 最接近 UE 里的什么单位

对 Unity 这份项目的 point / spot 来说，**最接近的是 UE Candela，不是 UE Unitless。**

原因：

- Unity shader 里直接是 `I / d^2`
- Unity 世界单位按米算
- Candela 的数值语义就是“某方向上的光强”，在 1 米处轴向照度数值上和 `I / d^2` 是直接对应的

也就是说：

```text
Unity intensity 100
```

对 point/spot 的 runtime 视觉语义，最像：

```text
UE intensity_units = Candelas
UE intensity = 100
```

尤其是 Spot Light，比用 `Lumens` 更接近 Unity。

原因是 UE 的 `Lumens` 会按锥角做一次总光通量到轴向强度的 remap，而 Unity 这边并没有做这种能量归一化。

## 7.5 Unity range 与 UE attenuation radius 的关系

如果只是看标准 point/spot 衰减范围：

```text
UE AttenuationRadius(cm) = Unity Range(m) * 100
```

这次这两盏 Unity spot 的 `range = 10`，所以对应：

```text
UE AttenuationRadius = 1000 cm
```

而 UE `LocalLightComponent` 的默认 `AttenuationRadius` 恰好就是 `1000`，所以这次半径本身不是主要问题，主要问题是我们上次用了 `Unitless 100`。

## 7.6 Unity smooth range cutoff 与 UE inverse-squared cutoff 的关系

有个很关键的结论：

Unity 非 mobile 的平滑截断项：

```text
(1 - (d^2 / r^2)^2)^2
```

UE inverse-squared local light 的 mask：

`DeferredLightingCommon.ush:263-266`

```text
Square( saturate( 1 - Square( DistanceSqr * Square(InvRadius) ) ) )
```

展开后也是：

```text
(1 - (d^2 / r^2)^2)^2
```

所以只要走的是 **UE 标准 inverse-squared + Candela + 正确半径**，它和 Unity 的额外 cutoff 形状其实是高度一致的。

这也是为什么正确迁移路径应该是：

```text
Unity point/spot unitless -> UE candelas
```

而不是：

```text
Unity point/spot unitless -> UE unitless
```

UE 的物理灯光工作流通常这样理解：

- Directional Light：用 `Lux`
- Point / Spot：常用 `Candela` 或 `Lumens`
- Area / emissive 面光：会涉及 `Nits`
- 也可以退回 `Unitless`

补充公式：

- `1 lux = 1 lumen / m^2`
- 轴向照度：`lux = candela / distance^2`
- `lumens = candela * steradian`

对圆锥聚光，若已知完整光束角 `theta`，其立体角：

```text
Omega = 2*pi*(1 - cos(theta/2))
```

## 7.7 Unity 100 能不能直接等于 UE 314 lux

不能直接这么认。

原因很简单：Unity 这里的 `100` 不是物理单位，先天就没有唯一答案。

如果你强行套物理关系，只能得到“假设某个 UE 单位后”的结果，而不是“Unity 官方定义的真换算”。

## 7.8 以这两盏 Spot Light 为例

它们的参数是：

- Unity intensity: `100`
- Outer Angle: `110 deg`

如果在 UE 里把这 `100` 当成 **100 candelas**：

- 轴线上 `1m` 处照度约为 `100 lux`
- 对应总光通量约为：

```text
Omega = 2*pi*(1 - cos(55 deg)) = 2.681 sr
Lumens ~= 100 * 2.681 = 268.1 lm
```

如果在 UE 里把这 `100` 当成 **100 lumens**：

```text
Candela ~= 100 / 2.681 = 37.3 cd
1m 轴线上照度 ~= 37.3 lux
```

所以：

- `Unity 100 -> UE 314 lux` 没有标准依据
- 同一个数字 `100`，在 UE 里到底变成多少 lux，完全取决于你先把它解释成 `cd` 还是 `lm`

但如果目标是复刻 Unity 这份项目的 point/spot runtime 视觉，优先解释成 **Candela**。

## 7.9 这次迁移的推荐策略

### 推荐策略 A：保真迁移 point / spot

如果目标是“先把 Unity point / spot 的 runtime 衰减搬过去”，推荐：

- `IntensityUnits = Candelas`
- `Intensity ~= Unity Intensity`
- `AttenuationRadius = Unity Range * 100`
- 保持 `UseInverseSquaredFalloff = true`
- Spot 保持相同内外锥角

这条对当前这两盏 Spot 最稳。

### 推荐策略 B：物理化重建

如果目标是“按 UE PBL 工作流重建”：

- Directional Light 不直接继承 `0.9`
- 需要基于目标日景 / 室内棚拍方案，重新选一个合理的 `Lux`
- Spot Light 需要先决定用 `Candela` 还是 `Lumens`
- 再用锥角公式倒推

这条路不能叫“转换”，而叫“重标定”。

## 8. 这次建议实际同步到 UE 的灯

优先同步：

1. `main_light`
2. `Spot Light (1)`
3. `Spot Light (2)`

可选保留但默认不启用：

4. `Skybox-Panoramic Light`

原因：

- 它虽然被 Unity `m_Sun` 引用，但当前灯组件是关闭的
- 如果目的是复刻当前可见效果，不应默认把它当启用灯加入

## 9. 已算好的 UE 落灯目标值

下面是按 `P_ue_cm = (Z_u, X_u, Y_u) * 100` 和“由 mapped forward 求 pitch/yaw，roll 先置 0”得到的结果。

### 9.1 `main_light`

```text
UE location cm: (-751.450, -17.044, 357.024)
UE forward:     (0.489959, -0.787153, -0.374607)
UE up:          (0.197956, -0.318030, 0.927184)
UE rotation:    Pitch=-22.000, Yaw=-58.100, Roll=0
```

建议：

- 类型：Directional Light
- 迁移初值：先用 `Unitless 0.9`
- 若走项目内现有角色主光控制蓝图，则需要按该蓝图约定再二次映射，不建议把 `0.9` 直接套到它的自定义参数上。

### 9.2 `Spot Light (1)`

```text
UE location cm: (1230.000, 68.000, 249.000)
UE forward:     (-0.591000, 0.000000, -0.806672)
UE up:          (0.806672, 0.000000, -0.591000)
UE rotation:    Pitch=-53.772, Yaw=180.000, Roll=0
```

建议：

- 类型：Spot Light
- Range 先按项目当前灯衰减习惯调，不要直接假设 Unity 的 `10` 和 UE 半径一一等价
- Outer Cone: `110`
- Inner Cone: `40`
- 强度迁移优先用 `Unitless 100`

### 9.3 `Spot Light (2)`

```text
UE location cm: (1273.000, 509.000, 217.200)
UE forward:     (-0.591000, 0.000000, -0.806672)
UE up:          (0.806672, 0.000000, -0.591000)
UE rotation:    Pitch=-53.772, Yaw=180.000, Roll=0
```

建议：

- 类型：Spot Light
- Outer Cone: `110`
- Inner Cone: `40`
- 强度迁移优先用 `Unitless 100`

### 9.4 `Skybox-Panoramic Light`

```text
UE location cm: (-1630.645, -888.533, 172.025)
UE forward:     (0.831832, 0.377651, -0.406737)
UE up:          (0.370356, 0.168141, 0.913545)
UE rotation:    Pitch=-24.000, Yaw=24.418, Roll=0
```

建议：

- 类型：Directional Light
- 默认保持禁用，仅作为 Unity `m_Sun` 参考位姿保留

## 10. 本次落地修正建议

由于上一次已经把两盏 Spot 以 `Unitless 100` 落到了 UE，这次应修正为：

```text
Unity_SpotLight_01 -> Candelas 100, Radius 1000cm
Unity_SpotLight_02 -> Candelas 100, Radius 1000cm
```

`main_light` 是方向光，不涉及这次说的半径衰减问题，先不按这一套改。

## 11. 这次真正落 UE 时的执行建议

1. 先把目标子关卡单独 load 成当前关卡
2. 再创建 `main_light`、`Spot Light (1)`、`Spot Light (2)`
3. 灯强度先走 `Unitless`
4. Spot 的 cone angle 先同步过去
5. 再根据 UE 视口观察决定是否把 Post Process `Exposure Compensation` 设为 `0` 或 `1`
6. 如果后面找回 Unity 的真实 `sharedProfile` 资源，再对曝光补偿做二次校准

## 12. 当前未决项

- Unity 当前场景真正引用的 Volume Profile 本体还没找到，所以 `postExposure` 还不是最终真值
- 当前会话里的 UE live editor 连接出现过掉线，正式写灯前需要先确认连接恢复
- 当前基础 `spawn_actor` 默认写当前关卡，不会自动写入指定子关卡
