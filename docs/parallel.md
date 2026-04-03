# 并行推进 Checklist

这份文档给多会话并行推进使用。

目标：

- 避免多人/多会话改到同一层核心文件
- 避免测试阶段互相打断同一个 UE 编辑器实例
- 让每个会话都知道自己的边界、交付物和验证方式

## 全局规则

### 改动边界

- 只有一个会话可以同时修改这些核心文件：
  - `unreal_harness_runtime/python_exec.py`
  - `unreal_harness_runtime/commandlet_exec.py`
  - `unreal_orchestrator/server.py`
  - `unreal_orchestrator/catalog.py`
  - `pyproject.toml`

- 其他域尽量只改自己域内目录：
  - `unreal_scene/`
  - `unreal_asset/`
  - `unreal_material/`
  - `unreal_material_graph/`
  - `unreal_diagnostics/`

### UE 实例使用规则

- 不要多个会话同时对同一个 UE 编辑器实例做重型导入测试
- `scene` 类测试和 `asset import` 类测试尽量分时进行
- 做 commandlet 导入测试时，不依赖当前打开的编辑器实例

### 交付要求

- 每个会话完成后至少交付：
  - 代码改动
  - 一条真实环境回归结果
  - 剩余问题说明

### 结果结构要求

- 新高层命令如果已经进入“可交付”阶段，应尽量补：
  - `post_state`
  - `verification.checks`
  - 批量命令的 `summary + items`

## 当前并行拆分

### 会话 A：Material Graph

范围：

- `unreal_material_graph/`

目标：

- 建立图读取和图分析
- 建立常见节点创建
- 建立连线能力

不要动：

- `unreal_material/`
- `unreal_harness_runtime/`

完成标准：

- 能读取材质图
- 能创建至少一个常见节点
- 能做至少一条有效连线

### 会话 B：Scene 高层命令

范围：

- `unreal_scene/`

目标：

- 补第二批 scene 高层命令

优先项：

- `aim_actor_at`
- `set_post_process_overrides`
- `spawn_actor_with_defaults`

不要动：

- `unreal_asset/`
- `unreal_material/`

完成标准：

- 每个新高层命令至少有一条真实回归
- 每个新高层命令至少有一条真实环境回归

### 会话 C：Asset 收尾

范围：

- `unreal_asset/`

目标：

- 补充非导入类高层命令
- 收敛返回结构
- 清理 fallback 边界说明

优先项：

- `duplicate_asset_with_overrides`
- `ensure_folder`
- `move_asset_batch`

不要动：

- `commandlets/asset_import_commandlet.py` 除非明确在修导入模型

完成标准：

- 新命令都能在不改 C++ 的前提下跑通

### 会话 D：Orchestrator

范围：

- `unreal_orchestrator/`

目标：

- 从“目录/注册器”升级到真正总控

优先项：

- 自动路由到域
- 统一 capability 查询
- 统一错误模型
- 统一返回包装

不要动：

- 各域执行细节实现

完成标准：

- 能对同一任务给出稳定域判断
- 能聚合域级元信息

### 会话 E：Diagnostics

范围：

- `unreal_diagnostics/`

目标：

- 建立排障和健康检查工具

优先项：

- 端口检查
- Python 初始化检查
- commandlet 结果检查
- 当前编辑器状态检查

完成标准：

- 至少能快速区分：
  - 端口没起
  - Python 没初始化
  - commandlet 执行失败
  - 域工具本身失败

### 会话 F：文档

范围：

- `docs/`
- `README.md`

目标：

- 跟进架构、命令清单、测试策略、已知风险

完成标准：

- 新增功能都有对应文档入口

## 会话完成前自检

- 是否修改了不该修改的核心共享文件
- 是否做了至少一条真实环境回归
- 是否记录了已知限制
- 是否说明了是否需要重启编辑器/重编插件
- 是否把返回结构写清楚
- 是否说明是否已经补 `post_state`
- 是否说明是否已经补 `verification`
- 如果是 batch，是否说明是否已有 `summary + items`
- 是否说明该功能走 live editor 还是 commandlet 工作流
