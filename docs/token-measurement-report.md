# Token 用量量化报告

日期：`2026-04-04`

这份报告基于当前仓库代码和本地 `logs/token_usage.jsonl` 生成，目标是回答两件事：

1. 目前这个 MCP 的 token 用量是否有收紧
2. 目前的实现和 `docs/token-optimization-checklist.md` 的方向是否一致

## 方法

本次量化分三层：

### 1. 工具面规模

统计：

- `unreal_orchestrator` 默认暴露工具数
- `unreal_editor_mcp` internal/raw 工具数
- domain 数量

用途：

- 近似反映默认 schema 面积
- 观察默认模式是否继续偏向更小的工具面

### 2. 历史 token 日志

数据源：

- `logs/token_usage.jsonl`

统计：

- 总条目数
- session 数
- 冷启动条目数
- 热会话条目数
- 冷/热平均响应 token
- 冷/热平均延迟
- Top 10 高成本操作

用途：

- 延续 `token-optimization-checklist.md` 里已有的统计口径
- 看当前高成本主要集中在哪些操作

### 3. 代表性返回体测量

直接对当前结果结构做字节数与估算 token 测量：

- `scene_query_success`
- `asset_query_success`
- `create_spot_light_ring_success`

用途：

- 量化当前结构化返回的大致成本上限
- 和历史 raw 操作日志做近似对比

## 核心数据

### 工具面规模

- `unreal_orchestrator` 路由/元工具：`3`
- `unreal_orchestrator` 默认工具：`30`
- 默认总工具面：`33`
- `unreal_editor_mcp` raw/internal 工具：`40`
- 默认工具面相对 raw 减少：`17.5%`
- 当前 domain 数量：`8`

解释：

- 默认模式继续维持“orchestrator 为主，raw/internal 不直接暴露”的方向
- 这个数字只反映工具数量，不等于完整 schema token，但能说明默认入口仍然在收口

### Token 日志汇总

- 总日志条目：`1134`
- session 数：`41`
- 冷启动条目：`41`
- 热会话条目：`1043`
- 冷启动平均响应 token：`149.73`
- 热会话平均响应 token：`47.14`
- 冷启动平均延迟：`8851.61 ms`
- 热会话平均延迟：`13898.51 ms`

解释：

- 响应 token 上，热会话显著低于冷启动，约低 `68.5%`
- 延迟数据当前被 `run_python` timeout/transport_error 明显拉高，不能直接拿来做性能结论
- 这说明日志还能用来看 token 量级，但当前不适合作为稳定 latency 基线

### Top 10 高成本操作

按累计响应 token 排序：

1. `unreal_editor_mcp.transport / run_python`
   - 次数：`319`
   - 平均请求 token：`271.35`
   - 平均响应 token：`64.84`
   - 平均延迟：`15463.25 ms`
   - 累计响应 token：`20685`

2. `unreal_editor_mcp.transport / get_current_level`
   - 次数：`443`
   - 平均请求 token：`1.0`
   - 平均响应 token：`33.94`
   - 平均延迟：`11246.81 ms`
   - 累计响应 token：`15034`

3. `unreal_editor_mcp.transport / get_actors`
   - 次数：`5`
   - 平均请求 token：`5.0`
   - 平均响应 token：`2491.6`
   - 平均延迟：`516.75 ms`
   - 累计响应 token：`12458`

4. `unreal_harness_runtime.python_exec / run_editor_python`
   - 次数：`319`
   - 平均请求 token：`271.35`
   - 平均响应 token：`38.04`
   - 平均延迟：`15463.68 ms`
   - 累计响应 token：`12136`

5. `unreal_editor_mcp.transport / read_blueprint_content`
   - 次数：`7`
   - 平均响应 token：`945.0`

6. `unreal_editor_mcp.transport / get_assets`
   - 次数：`9`
   - 平均响应 token：`378.67`

7. `unreal_editor_mcp.transport / get_asset_properties`
   - 次数：`3`
   - 平均响应 token：`730.0`

8. `unreal_editor_mcp.transport / get_actor_properties`
   - 次数：`5`
   - 平均响应 token：`426.4`

9. `unreal_editor_mcp.transport / get_material_graph`
   - 次数：`8`
   - 平均响应 token：`170.5`

10. `unreal_editor_mcp.transport / batch_spawn_actors`
    - 次数：`3`
    - 平均响应 token：`170.0`

解释：

- 最高成本仍然集中在：
  - `run_python`
  - raw 全量查询
  - blueprint/material graph 这类大对象读取
- 这和 `token-optimization-checklist.md` 的判断一致

### 代表性返回体测量

- `scene_query_success`
  - `1053 bytes`
  - 估算 `264 tokens`

- `asset_query_success`
  - `1209 bytes`
  - 估算 `303 tokens`

- `create_spot_light_ring_success`
  - `1407 bytes`
  - 估算 `352 tokens`

解释：

- 当前结构化高层写命令返回体已经被控制在几百 token 量级
- 查询类 compact 返回也落在 `264~303 tokens` 量级

## 对比结论

### 1. raw `get_actors` vs 当前 `query_scene_actors`

- 历史 raw `get_actors` 平均响应：`2491.6 tokens`
- 当前结构化 `query_scene_actors` 代表性返回：`264 tokens`
- 估算下降：`89.4%`

结论：

- scene 查询这条线已经明显达到并超过 checklist 里“常见查询 token 下降 `60%+`”的目标

### 2. raw `get_assets` vs 当前 `query_assets_summary`

- 历史 raw `get_assets` 平均响应：`378.67 tokens`
- 当前结构化 `query_assets_summary` 代表性返回：`303 tokens`
- 估算下降：`19.98%`

结论：

- 这条线有收紧，但没有 scene 查询那么明显
- 原因很可能是历史日志里的 `get_assets` 本身已经吃到了之前的 `summary_only / fields / limit` 优化
- 所以这里更像“在已优化基础上的继续收口”，而不是从全量 raw 一步降下来的效果

## 和既有文档的对齐情况

对应 `docs/token-optimization-checklist.md`：

- `记录 schema / input / output / total token 估算与 latency`
  - 已延续
  - 当前有日志统计，也补了代表性 payload 测量

- `输出高成本工具 Top 10`
  - 已延续
  - 当前报告已给出 Top 10

- `区分冷启动和热会话成本`
  - 已延续
  - 当前报告给出冷/热平均响应 token 和延迟

- `常见查询改成服务端筛选`
  - 已延续
  - `query_scene_actors / query_scene_lights / query_assets_summary` 已统一成 compact query contract

- `用高层命令替代多轮链路`
  - 已延续
  - `create_spot_light_ring` 等高层命令已经补齐结构化返回

## 当前可以明确下的结论

- 有收紧，而且不是停留在文档层面，已经反映在当前工具面和查询返回结构上
- scene 查询这条线的 token 收益最明显，按当前测量约降 `89.4%`
- asset 查询这条线也有继续收紧，但当前量化收益约 `20%`，低于 scene
- 默认工具面相对 raw/internal 继续收口，当前是 `33 vs 40`，减少 `17.5%`

## 当前不能夸大的结论

下面这些，这次不能严谨地下结论：

- “当前完整 schema token 比以前下降了多少 %”
- “所有查询都已经达到 `60%+` 的下降目标”
- “当前 latency 明显改善”

原因：

- 这次没有重新导出完整 schema 做同口径对比
- 历史 token 日志混有多轮 ready/timeout 重试，延迟数据被污染
- asset 查询的历史日志很可能已经处于优化后状态，不是原始 baseline

## 下一步建议

如果要把这份量化做成真正的验收数据，建议只补这两件事：

1. 导出当前默认 orchestrator schema，和之前同口径做一次 token 估算
2. 单独做一轮“干净会话”的 token smoke：
   - 冷启动
   - `query_scene_actors`
   - `query_scene_lights`
   - `query_assets_summary`
   - `create_spot_light_ring`

这样就能把现在的“结构收口有效”进一步变成“可复现的量化验收结果”。
