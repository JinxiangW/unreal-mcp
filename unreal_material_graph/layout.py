"""Read-only layout analysis for Unreal material graphs."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from itertools import combinations
import re
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Tuple


LAYOUT_PROFILE = "material_readable_v1"
LAYOUT_THRESHOLDS = {
    "grid_size": 100,
    "dependency_gap": 300,
    "parallel_gap": 100,
    "comment_padding": 200,
    "long_shared_span": 1200,
    "long_shared_fanout": 2,
    "cross_group_span": 600,
}
MAX_REPORTED_VIOLATIONS = 200
_WARNING_PRIORITY = {
    "long_shared_direct_route": 10,
    "cross_group_direct_edge": 20,
    "parallel_order_mismatch": 30,
    "dependency_spacing": 40,
    "comment_padding": 50,
    "insufficient_horizontal_gap": 60,
    "insufficient_parallel_gap": 60,
    "nonsemantic_reroute_name": 70,
    "empty_comment": 80,
    "wire_crossing_heuristic": 90,
    "grid_misalignment": 100,
}


@dataclass(frozen=True)
class _Rect:
    x: float
    y: float
    width: float
    height: float

    @property
    def right(self) -> float:
        return self.x + self.width

    @property
    def bottom(self) -> float:
        return self.y + self.height

    @property
    def center(self) -> Tuple[float, float]:
        return (self.x + self.width * 0.5, self.y + self.height * 0.5)

    @property
    def area(self) -> float:
        return self.width * self.height

    def intersects(self, other: "_Rect") -> bool:
        return (
            self.x < other.right
            and other.x < self.right
            and self.y < other.bottom
            and other.y < self.bottom
        )

    def contains(self, other: "_Rect") -> bool:
        return (
            self.x <= other.x
            and self.y <= other.y
            and self.right >= other.right
            and self.bottom >= other.bottom
        )

    def contains_point(self, point: Tuple[float, float]) -> bool:
        return (
            self.x <= point[0] <= self.right
            and self.y <= point[1] <= self.bottom
        )


def analyze_layout(
    *,
    nodes: Sequence[Mapping[str, Any]],
    connections: Sequence[Mapping[str, Any]],
    comments: Sequence[Mapping[str, Any]] | None = None,
) -> Dict[str, Any]:
    """Analyze graph readability without changing node coordinates or wiring."""
    node_by_id = {
        node_id: dict(node)
        for node in nodes
        if (node_id := _node_id(node)) and _node_type(node) != "Comment"
    }
    comment_by_id = _collect_comments(nodes, comments or [])
    node_rects = {
        node_id: _node_rect(node)
        for node_id, node in node_by_id.items()
    }
    comment_rects = {
        comment_id: _comment_rect(comment)
        for comment_id, comment in comment_by_id.items()
    }

    reported_errors: List[Dict[str, Any]] = []
    reported_warnings: List[Dict[str, Any]] = []
    rule_counts: Counter[str] = Counter()
    hard_error_count = 0
    warning_count = 0

    def add_violation(
        rule_id: str,
        severity: str,
        node_ids: Iterable[str],
        message: str,
        suggestion: str,
        **details: Any,
    ) -> None:
        nonlocal hard_error_count, warning_count
        rule_counts[rule_id] += 1
        if severity == "error":
            hard_error_count += 1
        else:
            warning_count += 1
        violation = {
            "rule_id": rule_id,
            "severity": severity,
            "node_ids": list(dict.fromkeys(node_ids)),
            "message": message,
            "suggestion": suggestion,
        }
        violation.update(details)
        if severity == "error":
            reported_errors.append(violation)
        else:
            reported_warnings.append(violation)

    _check_grid_alignment(node_by_id, add_violation)
    _check_node_collisions(node_rects, add_violation)
    _check_comments(comment_rects, node_rects, add_violation)
    node_groups = _assign_comment_groups(node_rects, comment_rects)

    normalized_connections = [
        item
        for connection in connections
        if (item := _connection(connection)) is not None
    ]
    _check_dependencies(
        normalized_connections,
        node_by_id,
        node_rects,
        add_violation,
    )
    _check_parallel_order(
        normalized_connections,
        node_by_id,
        node_rects,
        add_violation,
    )
    _check_reroutes(node_by_id, add_violation)
    _check_long_shared_routes(
        normalized_connections,
        node_by_id,
        node_rects,
        add_violation,
    )
    _check_cross_group_edges(
        normalized_connections,
        node_by_id,
        node_rects,
        node_groups,
        add_violation,
    )
    _check_wire_crossings(
        normalized_connections,
        node_by_id,
        node_rects,
        add_violation,
    )

    violation_count = hard_error_count + warning_count
    warning_slots = max(0, MAX_REPORTED_VIOLATIONS - len(reported_errors))
    prioritized_warnings = sorted(
        reported_warnings,
        key=lambda item: (_WARNING_PRIORITY.get(item["rule_id"], 999), item["node_ids"]),
    )
    reported = [*reported_errors, *prioritized_warnings[:warning_slots]]
    rule_count_map = dict(sorted(rule_counts.items()))
    metrics = {
        "node_count": len(node_by_id),
        "comment_count": len(comment_by_id),
        "connection_count": len(normalized_connections),
        "hard_error_count": hard_error_count,
        "warning_count": warning_count,
        "violation_count": violation_count,
        "node_overlap_count": rule_counts["node_overlap"],
        "backward_dependency_count": rule_counts["backward_dependency"],
        "comment_violation_count": (
            rule_counts["comment_partial_overlap"]
            + rule_counts["comment_node_escape"]
        ),
        "invalid_reroute_count": (
            rule_counts["duplicate_reroute_declaration"]
            + rule_counts["unbound_reroute_usage"]
            + rule_counts["reroute_binding_mismatch"]
        ),
        "long_shared_direct_route_count": rule_counts["long_shared_direct_route"],
        "cross_group_direct_edge_count": rule_counts["cross_group_direct_edge"],
        "wire_crossing_count": rule_counts["wire_crossing_heuristic"],
        "parallel_order_mismatch_count": rule_counts["parallel_order_mismatch"],
        "rule_counts": rule_count_map,
    }
    return {
        "profile": LAYOUT_PROFILE,
        "bounds_mode": "estimated",
        "thresholds": dict(LAYOUT_THRESHOLDS),
        "metrics": metrics,
        "violations": reported,
        "violations_truncated": violation_count > len(reported),
    }


def _node_id(node: Mapping[str, Any]) -> str:
    return str(node.get("node_id") or node.get("id") or "")


def _node_type(node: Mapping[str, Any]) -> str:
    node_type = str(node.get("type") or "Unknown")
    prefix = "MaterialExpression"
    return node_type[len(prefix) :] if node_type.startswith(prefix) else node_type


def _number(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _position(node: Mapping[str, Any]) -> Tuple[float, float]:
    position = node.get("position") if isinstance(node.get("position"), Mapping) else {}
    return (
        _number(node.get("pos_x", position.get("x")), 0.0),
        _number(node.get("pos_y", position.get("y")), 0.0),
    )


def _pin_counts(node: Mapping[str, Any]) -> Tuple[int, int]:
    node_type = _node_type(node)
    input_count = len(node.get("inputs") or [])
    output_count = 1 + len(node.get("additional_outputs") or [])

    if node_type == "MaterialFunctionCall":
        input_count = int(node.get("function_input_count") or len(node.get("function_inputs") or []))
        output_count = int(node.get("function_output_count") or len(node.get("function_outputs") or []))
    elif node_type == "GetMaterialAttributes":
        input_count = 1
        output_count = max(1, len(node.get("attribute_names") or []) + 1)
    elif node_type == "SetMaterialAttributes":
        input_count = max(1, len(node.get("attribute_names") or []) + 1)
        output_count = 1
    elif node_type == "MakeMaterialAttributes":
        input_count = max(input_count, 27)
    elif node_type == "BreakMaterialAttributes":
        output_count = max(output_count, 27)

    return input_count, output_count


def _estimate_node_size(node: Mapping[str, Any]) -> Tuple[float, float]:
    node_type = _node_type(node)
    input_count, output_count = _pin_counts(node)
    visible_rows = max(input_count, output_count, 1)

    if node_type == "Custom":
        return (360.0, max(180.0, 90.0 + visible_rows * 22.0))
    if node_type == "MaterialFunctionCall":
        return (340.0, max(140.0, 80.0 + visible_rows * 22.0))
    if node_type in {"MakeMaterialAttributes", "BreakMaterialAttributes"}:
        return (300.0, max(220.0, 80.0 + visible_rows * 22.0))
    if node_type in {"GetMaterialAttributes", "SetMaterialAttributes"}:
        return (300.0, max(140.0, 80.0 + visible_rows * 22.0))
    if "TextureSample" in node_type or node_type in {"TextureObject", "TextureObjectParameter"}:
        return (260.0, 220.0)
    if "VectorParameter" in node_type or node_type in {"Constant3Vector", "Constant4Vector"}:
        return (240.0, 150.0)
    if "Switch" in node_type:
        return (220.0, max(130.0, 70.0 + visible_rows * 22.0))
    if node_type in {"NamedRerouteDeclaration", "NamedRerouteUsage"}:
        return (180.0, 60.0)
    if node_type in {"FunctionInput", "FunctionOutput"}:
        return (260.0, 110.0)
    if "Parameter" in node_type:
        return (220.0, 100.0)
    return (200.0, max(90.0, 60.0 + visible_rows * 20.0))


def _node_rect(node: Mapping[str, Any]) -> _Rect:
    x, y = _position(node)
    width, height = _estimate_node_size(node)
    return _Rect(x, y, width, height)


def _collect_comments(
    nodes: Sequence[Mapping[str, Any]],
    comments: Sequence[Mapping[str, Any]],
) -> Dict[str, Dict[str, Any]]:
    collected: Dict[str, Dict[str, Any]] = {}
    for item in [*nodes, *comments]:
        if _node_type(item) != "Comment":
            continue
        if comment_id := _node_id(item):
            collected[comment_id] = dict(item)
    return collected


def _comment_rect(comment: Mapping[str, Any]) -> _Rect:
    x, y = _position(comment)
    size = comment.get("size") if isinstance(comment.get("size"), Mapping) else {}
    width = _number(comment.get("size_x", size.get("x")), 400.0)
    height = _number(comment.get("size_y", size.get("y")), 300.0)
    return _Rect(x, y, max(width, 1.0), max(height, 1.0))


def _connection(connection: Mapping[str, Any]) -> Dict[str, str] | None:
    source = str(connection.get("source") or connection.get("from") or "")
    target = str(connection.get("target") or connection.get("to") or "")
    if not source or not target:
        return None
    return {
        "source": source,
        "target": target,
        "source_output": str(connection.get("source_output") or connection.get("from_output") or "Output_0"),
        "target_input": str(connection.get("target_input") or connection.get("to_input") or ""),
    }


def _check_grid_alignment(nodes: Mapping[str, Mapping[str, Any]], add: Any) -> None:
    grid = LAYOUT_THRESHOLDS["grid_size"]
    for node_id, node in nodes.items():
        x, y = _position(node)
        if x % grid or y % grid:
            add(
                "grid_misalignment",
                "warning",
                [node_id],
                f"Node is not aligned to the {grid}-unit grid.",
                "Snap the node position to the nearest 100-unit coordinate.",
                position={"x": x, "y": y},
            )


def _check_node_collisions(node_rects: Mapping[str, _Rect], add: Any) -> None:
    parallel_gap = LAYOUT_THRESHOLDS["parallel_gap"]
    dependency_gap = LAYOUT_THRESHOLDS["dependency_gap"]
    for left_id, right_id in combinations(node_rects, 2):
        left = node_rects[left_id]
        right = node_rects[right_id]
        if left.intersects(right):
            add(
                "node_overlap",
                "error",
                [left_id, right_id],
                "Estimated node bounds overlap.",
                "Move the nodes using their visible bounds, not only their origin coordinates.",
            )
            continue

        vertical_overlap = left.y < right.bottom and right.y < left.bottom
        horizontal_overlap = left.x < right.right and right.x < left.right
        horizontal_gap = max(right.x - left.right, left.x - right.right)
        vertical_gap = max(right.y - left.bottom, left.y - right.bottom)
        if vertical_overlap and 0 <= horizontal_gap < dependency_gap:
            add(
                "insufficient_horizontal_gap",
                "warning",
                [left_id, right_id],
                f"Visible horizontal gap is {horizontal_gap:g}, below {dependency_gap}.",
                "Separate adjacent dependency columns by at least 300 units.",
            )
        elif horizontal_overlap and 0 <= vertical_gap < parallel_gap:
            add(
                "insufficient_parallel_gap",
                "warning",
                [left_id, right_id],
                f"Visible vertical gap is {vertical_gap:g}, below {parallel_gap}.",
                "Separate parallel nodes by at least 100 units.",
            )


def _check_comments(
    comment_rects: Mapping[str, _Rect],
    node_rects: Mapping[str, _Rect],
    add: Any,
) -> None:
    padding = LAYOUT_THRESHOLDS["comment_padding"]
    for left_id, right_id in combinations(comment_rects, 2):
        left = comment_rects[left_id]
        right = comment_rects[right_id]
        if left.intersects(right) and not left.contains(right) and not right.contains(left):
            add(
                "comment_partial_overlap",
                "error",
                [left_id, right_id],
                "Comment boxes partially overlap without full nesting.",
                "Resize or move the comments so they are disjoint or fully nested.",
            )

    for comment_id, comment_rect in comment_rects.items():
        contained_count = 0
        for node_id, node_rect in node_rects.items():
            if not comment_rect.intersects(node_rect):
                continue
            if not comment_rect.contains(node_rect):
                add(
                    "comment_node_escape",
                    "error",
                    [comment_id, node_id],
                    "A node partially crosses the comment boundary.",
                    "Resize the comment from the union of child bounds plus 200 units of padding.",
                )
                continue
            contained_count += 1
            margins = (
                node_rect.x - comment_rect.x,
                node_rect.y - comment_rect.y,
                comment_rect.right - node_rect.right,
                comment_rect.bottom - node_rect.bottom,
            )
            if min(margins) < padding:
                add(
                    "comment_padding",
                    "warning",
                    [comment_id, node_id],
                    f"Comment padding is {min(margins):g}, below {padding}.",
                    "Expand the comment to preserve 200 units around contained nodes.",
                )
        if contained_count == 0:
            add(
                "empty_comment",
                "warning",
                [comment_id],
                "Comment does not fully contain any estimated node bounds.",
                "Resize, move, or remove the empty comment.",
            )


def _assign_comment_groups(
    node_rects: Mapping[str, _Rect],
    comment_rects: Mapping[str, _Rect],
) -> Dict[str, str]:
    groups: Dict[str, str] = {}
    for node_id, node_rect in node_rects.items():
        containing = [
            (comment_rect.area, comment_id)
            for comment_id, comment_rect in comment_rects.items()
            if comment_rect.contains_point(node_rect.center)
        ]
        if containing:
            groups[node_id] = min(containing)[1]
    return groups


def _check_dependencies(
    connections: Sequence[Mapping[str, str]],
    nodes: Mapping[str, Mapping[str, Any]],
    node_rects: Mapping[str, _Rect],
    add: Any,
) -> None:
    gap = LAYOUT_THRESHOLDS["dependency_gap"]
    for connection in connections:
        source_id = connection["source"]
        target_id = connection["target"]
        if source_id not in nodes or target_id not in nodes:
            continue
        source = node_rects[source_id]
        target = node_rects[target_id]
        if target.x < source.x:
            add(
                "backward_dependency",
                "error",
                [source_id, target_id],
                "A dependency flows from right to left.",
                "Place the producer to the left of the consumer.",
                connection=dict(connection),
            )
        elif target.x - source.right < gap:
            add(
                "dependency_spacing",
                "warning",
                [source_id, target_id],
                f"Dependency column gap is {target.x - source.right:g}, below {gap}.",
                "Move the consumer right until visible node bounds have 300 units of clearance.",
                connection=dict(connection),
            )


def _target_pin_order(node: Mapping[str, Any]) -> Dict[str, int]:
    ordered_inputs = node.get("inputs") or node.get("function_inputs") or []
    result: Dict[str, int] = {}
    for index, item in enumerate(ordered_inputs):
        if not isinstance(item, Mapping):
            continue
        name = item.get("input_name") or item.get("pin_name") or item.get("name")
        if name:
            result[str(name)] = int(item.get("input_index", index))
    return result


def _fallback_pin_order(pin_name: str) -> int | None:
    simple = {"A": 0, "B": 1, "Alpha": 2, "True": 0, "False": 1, "Value": 2}
    if pin_name in simple:
        return simple[pin_name]
    match = re.search(r"(\d+)$", pin_name)
    return int(match.group(1)) if match else None


def _check_parallel_order(
    connections: Sequence[Mapping[str, str]],
    nodes: Mapping[str, Mapping[str, Any]],
    node_rects: Mapping[str, _Rect],
    add: Any,
) -> None:
    incoming: Dict[str, List[Mapping[str, str]]] = defaultdict(list)
    for connection in connections:
        if connection["source"] in nodes and connection["target"] in nodes:
            incoming[connection["target"]].append(connection)

    for target_id, target_connections in incoming.items():
        pin_order = _target_pin_order(nodes[target_id])
        ordered = []
        for connection in target_connections:
            target_input = connection["target_input"]
            index = pin_order.get(target_input)
            if index is None:
                index = _fallback_pin_order(target_input)
            if index is not None:
                ordered.append((index, connection["source"]))
        if len(ordered) < 2:
            continue
        expected = [node_id for _, node_id in sorted(ordered)]
        actual = sorted(expected, key=lambda node_id: node_rects[node_id].y)
        if actual != expected:
            add(
                "parallel_order_mismatch",
                "warning",
                [target_id, *expected],
                "Parallel producers do not follow target input order from top to bottom.",
                "Stack sibling branches vertically using the target pin or declared semantic order.",
                expected_top_to_bottom=expected,
                actual_top_to_bottom=actual,
            )


def _check_reroutes(nodes: Mapping[str, Mapping[str, Any]], add: Any) -> None:
    declarations = {
        node_id: node
        for node_id, node in nodes.items()
        if _node_type(node) == "NamedRerouteDeclaration"
    }
    names: Dict[str, List[str]] = defaultdict(list)
    for node_id, declaration in declarations.items():
        name = str(declaration.get("declaration_name") or "").strip()
        if name:
            names[name].append(node_id)
        if re.fullmatch(r"(?i)(temp|tmp|value|var|reroute)\d*", name):
            add(
                "nonsemantic_reroute_name",
                "warning",
                [node_id],
                f"Named reroute '{name}' uses a temporary-style name.",
                "Rename it after the data semantic, for example WaterDepthCm.",
            )
    for name, node_ids in names.items():
        if len(node_ids) > 1:
            add(
                "duplicate_reroute_declaration",
                "error",
                node_ids,
                f"Named reroute declaration '{name}' is duplicated.",
                "Keep one declaration per semantic value.",
            )

    for usage_id, usage in nodes.items():
        if _node_type(usage) != "NamedRerouteUsage":
            continue
        declaration_id = str(usage.get("declaration_node_id") or "")
        declaration = declarations.get(declaration_id)
        if declaration is None:
            add(
                "unbound_reroute_usage",
                "error",
                [usage_id, declaration_id] if declaration_id else [usage_id],
                "Named reroute usage has no valid declaration binding.",
                "Bind the usage to a declaration pointer and synchronized GUID.",
            )
            continue
        usage_name = str(usage.get("declaration_name") or "")
        declaration_name = str(declaration.get("declaration_name") or "")
        usage_guid = str(usage.get("declaration_guid") or "")
        declaration_guid = str(declaration.get("declaration_guid") or "")
        if (usage_name and usage_name != declaration_name) or (
            usage_guid and declaration_guid and usage_guid != declaration_guid
        ):
            add(
                "reroute_binding_mismatch",
                "error",
                [declaration_id, usage_id],
                "Named reroute usage name or GUID does not match its declaration.",
                "Rebind the usage so declaration pointer, name, and GUID agree.",
            )


def _check_long_shared_routes(
    connections: Sequence[Mapping[str, str]],
    nodes: Mapping[str, Mapping[str, Any]],
    node_rects: Mapping[str, _Rect],
    add: Any,
) -> None:
    outgoing: Dict[Tuple[str, str], List[str]] = defaultdict(list)
    for connection in connections:
        if connection["source"] in nodes and connection["target"] in nodes:
            outgoing[(connection["source"], connection["source_output"])].append(connection["target"])

    minimum_fanout = LAYOUT_THRESHOLDS["long_shared_fanout"]
    minimum_span = LAYOUT_THRESHOLDS["long_shared_span"]
    for (source_id, source_output), target_ids in outgoing.items():
        if len(target_ids) < minimum_fanout:
            continue
        if _node_type(nodes[source_id]) in {"NamedRerouteDeclaration", "NamedRerouteUsage"}:
            continue
        source_x = node_rects[source_id].x
        span = max(abs(node_rects[target_id].x - source_x) for target_id in target_ids)
        if span >= minimum_span:
            add(
                "long_shared_direct_route",
                "warning",
                [source_id, *target_ids],
                f"One output fans out to {len(target_ids)} consumers across {span:g} units.",
                "Create one semantic Named Reroute declaration near the producer and usages near remote consumers.",
                source_output=source_output,
                fanout=len(target_ids),
                span=span,
            )


def _check_cross_group_edges(
    connections: Sequence[Mapping[str, str]],
    nodes: Mapping[str, Mapping[str, Any]],
    node_rects: Mapping[str, _Rect],
    node_groups: Mapping[str, str],
    add: Any,
) -> None:
    minimum_span = LAYOUT_THRESHOLDS["cross_group_span"]
    for connection in connections:
        source_id = connection["source"]
        target_id = connection["target"]
        source_group = node_groups.get(source_id)
        target_group = node_groups.get(target_id)
        if not source_group or not target_group or source_group == target_group:
            continue
        if source_id not in nodes or target_id not in nodes:
            continue
        if _node_type(nodes[source_id]) in {"NamedRerouteDeclaration", "NamedRerouteUsage"}:
            continue
        if _node_type(nodes[target_id]) in {"NamedRerouteDeclaration", "NamedRerouteUsage"}:
            continue
        span = abs(node_rects[target_id].x - node_rects[source_id].x)
        if span >= minimum_span:
            add(
                "cross_group_direct_edge",
                "warning",
                [source_group, target_group, source_id, target_id],
                f"A direct edge crosses semantic groups over {span:g} units.",
                "Keep one-use routes local; use a semantic Named Reroute when the value is also shared.",
                connection=dict(connection),
            )


def _edge_segment(connection: Mapping[str, str], rects: Mapping[str, _Rect]) -> Tuple[Tuple[float, float], Tuple[float, float]]:
    source = rects[connection["source"]]
    target = rects[connection["target"]]
    return ((source.right, source.center[1]), (target.x, target.center[1]))


def _segments_cross(
    first: Tuple[Tuple[float, float], Tuple[float, float]],
    second: Tuple[Tuple[float, float], Tuple[float, float]],
) -> bool:
    def orientation(a: Tuple[float, float], b: Tuple[float, float], c: Tuple[float, float]) -> float:
        return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])

    a, b = first
    c, d = second
    return orientation(a, b, c) * orientation(a, b, d) < 0 and orientation(c, d, a) * orientation(c, d, b) < 0


def _check_wire_crossings(
    connections: Sequence[Mapping[str, str]],
    nodes: Mapping[str, Mapping[str, Any]],
    node_rects: Mapping[str, _Rect],
    add: Any,
) -> None:
    visible = [
        connection
        for connection in connections
        if connection["source"] in nodes
        and connection["target"] in nodes
        and _node_type(nodes[connection["source"]]) not in {"NamedRerouteDeclaration", "NamedRerouteUsage"}
        and _node_type(nodes[connection["target"]]) not in {"NamedRerouteDeclaration", "NamedRerouteUsage"}
    ]
    for first, second in combinations(visible, 2):
        endpoints = {
            first["source"],
            first["target"],
            second["source"],
            second["target"],
        }
        if len(endpoints) < 4:
            continue
        if _segments_cross(_edge_segment(first, node_rects), _edge_segment(second, node_rects)):
            add(
                "wire_crossing_heuristic",
                "warning",
                endpoints,
                "Straight-line edge estimates cross.",
                "Reorder parallel lanes or add local reroute structure when it improves readability.",
                connections=[dict(first), dict(second)],
            )
