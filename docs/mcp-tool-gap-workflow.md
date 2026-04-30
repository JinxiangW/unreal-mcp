# MCP Tool Gap Workflow

This workflow defines when an agent should treat a workaround as an MCP capability gap and record it for later implementation.

## Goal

Keep normal task execution moving, while collecting repeatable MCP tool needs in one place.

Agents should not stop every time a fallback is needed. They should finish the user task when it is safe, then record the missing or weak MCP capability with enough evidence for implementation.

## What Counts As A Gap

Record a gap when any of these are true:

- A high-level MCP tool for the user intent does not exist.
- A high-level MCP tool exists but omits fields required for the task.
- A high-level MCP tool returns mixed, ambiguous, or poorly normalized data that forces extra filtering.
- A high-level MCP tool reports failure when the UE operation actually succeeded, or reports success without enough verification.
- The agent must use `run_python`, raw backend commands, local Python imports, or editor reflection to perform a normal user-facing workflow.
- The same Python workaround or manual inspection would likely be reused for another asset, graph, blueprint, scene, or render-debug task.
- The MCP operation works only for a small case but fails for normal batch size, timeout, save, compile, or transaction needs.

Do not record a gap for these cases:

- One-off source reading, grep, build, test, or local file inspection.
- User explicitly asks for arbitrary Python execution.
- The task is exploratory and no stable user-facing workflow is clear yet.
- The MCP tool already supports the workflow and the agent only used Python out of convenience.

## Detection Steps

1. Classify the domain: `scene / asset / material / material_graph / blueprint / niagara / diagnostics / renderdoc`.
2. Check `unreal_orchestrator` first, then the domain harness.
3. Check `docs/inventory.md`, `docs/commands.md`, and the domain tool module before falling back.
4. If a fallback is used, identify whether it was for missing capability, missing fields, incorrect behavior, stability, performance, or poor error reporting.
5. Complete the user task if the fallback is safe and verifiable.
6. Append a new item to `docs/mcp-tool-gap-checklist.md`.

## Required Evidence

Each checklist item must include:

- Domain and affected tool.
- User-facing workflow that failed or required fallback.
- Exact fallback used, for example `run_python`, raw command, local import, or manual source read.
- Expected MCP behavior.
- Minimum proposed tool or parameter change.
- Verification scenario that should pass after implementation.

## Priority

Use this priority scale:

- `P0`: Blocks common workflow or can corrupt assets/graphs.
- `P1`: Common workflow requires fallback or returns wrong success/failure.
- `P2`: Missing fields, weak error details, or awkward but workable API.
- `P3`: Convenience wrapper or documentation-only improvement.

## Output Rules

When the repo is writable, append the item to `docs/mcp-tool-gap-checklist.md`.

When the repo is not writable, include the same checklist item in the final response under `MCP Tool Gap`.

Do not mix implementation details with speculation. If root cause is unknown, write `Root cause: unknown` and keep the evidence concrete.

## Implementation Readiness

A gap is ready for implementation when it includes:

- A reproducible task or asset path pattern.
- The current tool behavior.
- The fallback that succeeded or partially succeeded.
- The expected stable MCP contract.
- At least one acceptance test or live regression target.
