# Legacy 移除 Checklist

状态：`[ ]` 未开始，`[-]` 进行中，`[x]` 已完成，`[!]` 阻塞。

## 边界

- [x] 确认要移除的 legacy 包是 `unreal_editor_mcp`，不是 UE 插件侧 TCP bridge。
- [x] 确认剩余依赖主要分为两类：
  - transport / connection / send_command
  - raw wrapper（`material_graph / niagara / blueprint_info / blueprint_graph / get_current_level / get_assets`）

## 迁移

- [x] 新建中性的内部 TCP backend 包，接管 `connection / common / tools`。
- [x] 把 `python_exec / diagnostics / scene / asset / material_graph` 重定向到新 backend。
- [x] 保留当前剩余 raw 能力，但不再通过 `unreal_editor_mcp` 包名暴露。

## 删除

- [x] 删除 `unreal_editor_mcp` 包内代码文件。
- [x] 删除 raw/internal server 启动入口和配置样例里的旧条目。
- [x] 移除 `pyproject.toml` 里的 `unreal_editor_mcp*` 打包声明。

## 文档

- [x] 更新 `README.md`，移除 `unreal_editor_mcp` 作为当前组成部分的描述。
- [x] 更新 `inventory.md`，去掉当前态里的 legacy 入口描述，改为 internal TCP backend。
- [x] 更新 `legacy.md`，改成“legacy 已移除”的历史说明。
- [x] 更新其余 docs 里对 `unreal_editor_mcp / legacy tcp / legacy fallback` 的当前态描述。

## 验证

- [x] 重新编译 `RenderingMCPEditor`。
- [x] 验证 `ping / get_current_level / TCP 拆包`。
- [x] 验证新的 backend 路径已接管 `python_exec.run_editor_python` 调用链。
- [x] 验证 `material_graph` 读图入口仍可调用。

## 收尾

- [x] 更新 checklist 为最终状态。
- [x] 检查工作树，确认只保留迁移与删改结果。
