# Niagara Component Renderer 属性绑定

启动独立 MCP 域：`python -m unreal_niagara.server`。全量 `unreal_mcp.server` 也暴露以下工具；slim 入口只负责发现。

- `get_niagara_renderers(asset_path, emitter)`：读取渲染器索引、组件类、模板路径及属性绑定。
- `set_niagara_component_binding(asset_path, emitter, property_name, attribute, renderer_index=0, setter="", save=True)`：新增或替换一个组件属性绑定。

示例：

```python
set_niagara_component_binding(
    asset_path="/Game/NS_LFTest",
    emitter="LFPointLight",
    property_name="Param",
    attribute="Particles.Param",
    setter="SetParam",
)
```

原生插件沿用 `update_niagara_emitter`，新增 renderer action `set_component_binding`。写入前等待 Niagara 编译完成，从粒子数据集、图参数声明及 Set Parameters 节点检查属性存在性和类型，检查目标可编辑属性及 setter 首参类型。首次绑定允许尚未被渲染器引用、被编译器裁掉的自定义属性。仅支持 `Particles.*` 和顶层组件属性。失败不写绑定，重复写同一属性只保留一项。setter 留空时检查 BlueprintSetter 元数据和 `Set<Property>` 方法。

写入使用编辑器事务和 PostEditChange 通知；Python 工具仅保存目标系统，随后独立读取结果。`success` 只有在目标绑定唯一、源属性存在、属性名和显式 setter 匹配时才为 true。保存失败会返回 `applied=true`、`success=false`，不会把已应用但未保存误报为成功。

需更新工程中的 UnrealMCP 插件二进制。Python 端新增工具需要重启相应 MCP server 才能重新发现。不必为仅修改资产而重启编辑器。

验证：`python -m pytest -q`；真实资产回归报告另存项目 `tmp/lf_*`。当前工作引擎为 `F:/GFFEngines/Develop_Maomi/Engine`。

## 向已有发射器补充参数

原生 `update_niagara_graph` 支持 `add_parameter_assignments`：在所选 spawn/update 阶段末尾追加一个 Set Parameters 条目，保留现有模块。`parameters` 为 1–32 项，每项使用唯一的 `Particles.*` 名称；支持 `type="float", value=有限数值`，或 `type="position", source="Engine.Owner.Position"`。同时支持插值生成脚本。该操作是追加操作，不应在超时后盲目重试；先通过图查询检查返回的模块是否已创建。

原生 `update_niagara_emitter` 的 renderer action `remove_component_binding` 可以按 `property` 删除失效的旧绑定，并返回 `removed_count`。删除不存在的绑定不影响其他条目。

## 重命名与粒子位置输入

- `get_niagara_assignments(asset_path, emitter)`：读取整个发射器共享图中的赋值目标、默认值和动态输入连接。
- `rename_niagara_particle_parameter(asset_path, emitter, old_name, new_name, replace_existing=False, dry_run=True, save=True)`：保留输入连接和 Rapid Iteration 值，重命名赋值目标及引用。默认只预检查。显式替换时仅允许删除同一赋值节点中没有连接的目标输入；其它节点的冲突写入会被拒绝。
- `bind_niagara_particle_position(asset_path, emitter, module_name, target, world_space=True, dry_run=True, save=True)`：将现有 position 赋值输入连接到 `Particles.Position`。世界空间模式插入引擎 `TransformPosition` 动态输入，配置 Simulation → World。拒绝覆盖无关连接；已有匹配的 TransformPosition 可修复空间枚举和缩放设置，并保留原位置输入连接。

示例预检查：

```python
rename_niagara_particle_parameter(
    "/Game/NS_LFTest", "LFPointLight", "Particles.Param", "Particles.rad",
    replace_existing=True,
)
bind_niagara_particle_position(
    "/Game/NS_LFTest", "LFPointLight", "NiagaraNodeAssignment_6", "Particles.Center",
)
```

确认预检查结果后再传 `dry_run=False`。重命名写入后会独立读取赋值列表，检查旧目标消失、新目标数量一致、曲线输入连接保持一致。C++ 功能需加载新版插件；Python 测试不替代 UE 实测。
