# 批量导入与材质离屏验证

2026-09-11，真实项目 `F:/GFFEngines/Main_Client/Client.uproject`，引擎 `F:/GFFEngines/Develop_Maomi/Engine`。

## 新接口

- `asset.import_assets_batch(items, destination_path, replace_existing=False)`：1–16 个纹理/FBX，独立 commandlet，显式属性设置、保存和回读；不从 live MCP TaskGraph 任务同步调用 Interchange。输出 summary/items/post_state/verification。
- `asset.inspect_static_mesh(asset_path)`：Bounds、LOD/Section/三角形数、默认材质槽。
- `asset.set_static_mesh_material(asset_path, material_path, slot=0)`：保存并核对默认材质引用。
- `material.get_material_statistics(asset_paths)`：原生已编译 Shader 指令/采样统计；不会把零指令视作编译成功，不替代渲染和错误日志检查。
- `scene.render_static_mesh_preview(...)`：临时 show-only SceneCapture，固定曝光输出 PNG；最终清理临时 Actor 和 RT，不保存关卡。可选 `profile_frames=30..300` 异步预热、每引擎帧捕获一次、记录 GPU CSV，完成后写 `.profile.json` 并清理及恢复 GPU cvar。

服务入口仍为 `python -m unreal_asset.server`、`python -m unreal_material.server`、`python -m unreal_scene.server`。现有长驻服务需要重启以刷新工具列表；没有改引擎或 UE 插件二进制。

## 修复

- 创建配方接受材质回读的 `default_value`，映射到 C++ builder 的 `value`；显式 `value` 优先。CameraVectorWS 的回读名称映射到创建名称 CameraVector。
- 删除节点时扣除其隐式移除的连接；post graph 为摘要时使用实际 `property_connection_count`，避免将属性名列表误判成空图。
- Commandlet Python print 可能只在 UE log 中出现，批量导入同时解析 stdout 和 log，避免已经导入成功却报告找不到结果。

## 回归

`/Game/PVFeature/TA/FrostedGlass/TrueImposter`：6 张纹理、外壳和参考猴头、五档复杂材质、多个实例。外壳 1 Section / 1452 三角形。多次整图重建后的参数默认值、连接、属性输出和布局均回读通过，实际 SM6 离屏图像正确。

首次试验的同步 live Interchange 导入触发 `TaskGraph.cpp:677 RecursionGuard`，编辑器崩溃；已移除此执行路径，改用隔离进程并恢复编辑器。随后两次隔离导入成功，纹理包含 R32F 和 RGBA32F。

103 个 Python 测试通过；compileall 和 git diff --check 通过。真实图片、GPU CSV 和验证 JSON 位于项目 `Saved/GeneratedAssets/TrueImposter/`。

保留了仓库已有的其他未提交改动，没有提交或回滚它们。
# 保留模型默认材质槽的预览

`render_static_mesh_preview(asset_path, material_path=None, output_path=...)` 保留 StaticMesh 每个槽的默认材质，返回 `material_slots`；传材质路径时仍对全部槽覆盖。适用于两 pass 组合模型，避免验证截图把背面、正面、内部物体覆盖成同一个材质。

真实回归：`/Game/PVFeature/TA/FrostedGlass/qiguan/SM_Qiguan_TwoPass`，三个槽依次为 `MI_Qiguan_Backfaces`、`MI_Qiguan_Frontfaces`、`MI_Qiguan_Interior`。对应截图与回读位于项目 `Saved/GeneratedAssets/Qiguan/`。测试总计 118 项通过。
