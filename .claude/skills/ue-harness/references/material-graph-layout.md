# Material Graph 排版规范（Layout Contract）

## 问题定义

当前 Material Graph 排版容易退化为“创建顺序驱动”：节点按写入顺序落点，而不是根据依赖、语义分支、节点尺寸和共享数据流组织。典型结果是依赖线反向、并列分支错位、大节点重叠，以及同一值跨越多个功能区重复连线。

本规范仅适用于 Material Graph。它约束 agent 的布局决策，并通过只读分析进行验收；不会自动移动节点或插入 Named Reroute。

## 固定 Profile

`material_readable_v1` 使用以下 UE 图坐标阈值：

| 项目 | 值 |
|---|---:|
| Grid size | 100 |
| Dependency column gap | 300 |
| Parallel lane gap | 100 |
| Comment padding | 200 |
| Long shared route span | 1200 |
| Long shared route fan-out | 2 |
| Cross-group route span | 600 |

节点间距按估算后的可见包围盒计算，不按节点原点计算。`Custom`、`MaterialFunctionCall`、Get/Set/Make/Break Material Attributes 等节点必须根据动态引脚数量增加估算高度。

## 布局工作流

Apply this sequence before writing final coordinates:

1. Partition the graph into semantic groups such as inputs, coverage, normal, volume, reflection, and outputs.
2. Compute dependency depth and place producers left of consumers.
3. Stack independent or sibling branches from top to bottom. Follow target input order when available; otherwise use an explicit semantic order.
4. Estimate visible node bounds from node type and pin count, then resolve collisions using bounds plus required gaps.
5. Snap final coordinates to the 100-unit grid.
6. Create comments after node placement from the union of child bounds plus 200 units of padding.
7. Replace long, reused values with semantic Named Reroute declarations and local usages.
8. Re-read the graph and run `analyze_material_graph_layout`.

不要先画 Comment 再把节点塞进去；Comment 应由最终子节点包围盒反推。不要通过把节点无限拉远来消除重叠，应保持相邻依赖列紧凑且留出固定间距。

## 依赖和并列关系

- Every material dependency must flow left to right. A target placed left of its producer is a blocking defect.
- Keep directly dependent nodes in adjacent columns where practical. The visible boundary gap should be at least 300 units.
- Place sources feeding ordered inputs in the same top-to-bottom order as those inputs.
- Keep parallel lanes at least 100 units apart after accounting for estimated node height.
- A complex branch may occupy multiple columns, but its local flow must remain left to right.

## Named Reroute 规则

Use a Named Reroute when one source output has at least two consumers and the farthest consumer is at least 1200 units away.

- Put one declaration beside the producer.
- Put one usage beside each remote consumer group.
- Name the declaration after the data semantic, for example `WaterDepthCm` or `WaterNormalWS`.
- Do not use placeholder names such as `Temp1`, `Value`, or `Var2`.
- Do not add a Named Reroute for a short, single-use, same-group connection.
- Declaration pointer, name, and GUID must agree on readback.

## Comment 和碰撞规则

- Node bounds must not overlap.
- Comments may be disjoint or fully nested; partial overlap is invalid.
- A node intersecting a comment must be fully contained or fully outside it.
- A containing comment should preserve 200 units of padding on all sides.
- Line-crossing checks are heuristic because readback does not expose Slate spline geometry.

## 校验和严重级别

Run:

```text
analyze_material_graph_layout(asset_path)
```

The tool is read-only. `success=true` means analysis completed. Delivery uses `verification.verified`, which is false only when a blocking rule fails.

Blocking rules:

- right-to-left dependency
- estimated node overlap
- partial comment overlap or node escape
- unbound, duplicated, or mismatched Named Reroute declaration/usage

Advisory rules:

- grid misalignment or insufficient spacing
- parallel order mismatch
- long shared direct route
- long cross-group direct edge
- non-semantic Named Reroute names
- straight-line wire-crossing heuristic
- insufficient Comment padding or empty Comment

Treat advisory results as repair guidance. Do not weaken blocking rules solely to make an existing graph pass; either fix the graph under the task's authorization or record the existing layout debt.
