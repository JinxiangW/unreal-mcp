from __future__ import annotations

from unittest.mock import patch

from unreal_material_graph import layout
from unreal_material_graph import server
from unreal_material_graph import tools


def _node(node_id: str, x: int, y: int, node_type: str = "Constant", **fields):
    return {"node_id": node_id, "type": node_type, "pos_x": x, "pos_y": y, **fields}


def _connection(source: str, target: str, target_input: str = "A", source_output: str = "Output_0"):
    return {
        "source": source,
        "target": target,
        "source_output": source_output,
        "target_input": target_input,
    }


def _analyze(nodes, connections=(), comments=()):
    return layout.analyze_layout(nodes=nodes, connections=connections, comments=comments)


def _rule_count(report, rule_id: str) -> int:
    return report["metrics"]["rule_counts"].get(rule_id, 0)


def test_linear_dependency_chain_passes_hard_validation() -> None:
    nodes = [
        _node("source", 0, 0),
        _node("middle", 500, 0),
        _node("target", 1000, 0),
    ]
    report = _analyze(
        nodes,
        [_connection("source", "middle"), _connection("middle", "target")],
    )

    assert report["profile"] == "material_readable_v1"
    assert report["bounds_mode"] == "estimated"
    assert report["metrics"]["hard_error_count"] == 0
    assert _rule_count(report, "backward_dependency") == 0


def test_backward_dependency_is_blocking() -> None:
    report = _analyze(
        [_node("source", 500, 0), _node("target", 0, 0)],
        [_connection("source", "target")],
    )

    assert report["metrics"]["hard_error_count"] == 1
    assert _rule_count(report, "backward_dependency") == 1
    assert report["metrics"]["backward_dependency_count"] == 1


def test_parallel_input_order_and_overlap_are_checked() -> None:
    target = _node(
        "target",
        500,
        100,
        "Custom",
        inputs=[
            {"input_name": "Top", "input_index": 0},
            {"input_name": "Bottom", "input_index": 1},
        ],
    )
    connections = [
        _connection("top", "target", "Top"),
        _connection("bottom", "target", "Bottom"),
    ]

    ordered = _analyze(
        [_node("top", 0, 0), _node("bottom", 0, 300), target],
        connections,
    )
    reversed_order = _analyze(
        [_node("top", 0, 300), _node("bottom", 0, 0), target],
        connections,
    )
    overlapping = _analyze(
        [_node("top", 0, 0), _node("bottom", 0, 50), target],
        connections,
    )

    assert _rule_count(ordered, "parallel_order_mismatch") == 0
    assert _rule_count(reversed_order, "parallel_order_mismatch") == 1
    assert _rule_count(overlapping, "node_overlap") == 1
    assert overlapping["metrics"]["hard_error_count"] == 1


def test_large_pin_nodes_use_larger_estimated_bounds() -> None:
    small = _node("small", 0, 0)
    custom = _node(
        "custom",
        0,
        0,
        "Custom",
        inputs=[{"input_name": f"Input{index}"} for index in range(12)],
    )
    function_call = _node(
        "call",
        300,
        100,
        "MaterialFunctionCall",
        function_input_count=10,
        function_output_count=4,
    )

    assert layout._estimate_node_size(custom)[1] > layout._estimate_node_size(small)[1]
    assert layout._estimate_node_size(function_call)[1] > layout._estimate_node_size(small)[1]
    assert _rule_count(_analyze([custom, function_call]), "node_overlap") == 1


def test_long_shared_value_warns_until_named_reroutes_are_used() -> None:
    direct_nodes = [
        _node("source", 0, 0),
        _node("consumer_a", 1500, 0),
        _node("consumer_b", 1500, 300),
    ]
    direct = _analyze(
        direct_nodes,
        [
            _connection("source", "consumer_a"),
            _connection("source", "consumer_b"),
        ],
    )

    rerouted_nodes = [
        _node("source", 0, 0),
        _node(
            "declaration",
            400,
            0,
            "NamedRerouteDeclaration",
            declaration_name="WaterDepthCm",
            declaration_guid="GUID_A",
        ),
        _node(
            "usage_a",
            1300,
            0,
            "NamedRerouteUsage",
            declaration_node_id="declaration",
            declaration_name="WaterDepthCm",
            declaration_guid="GUID_A",
        ),
        _node(
            "usage_b",
            1300,
            300,
            "NamedRerouteUsage",
            declaration_node_id="declaration",
            declaration_name="WaterDepthCm",
            declaration_guid="GUID_A",
        ),
        _node("consumer_a", 1800, 0),
        _node("consumer_b", 1800, 300),
    ]
    rerouted = _analyze(
        rerouted_nodes,
        [
            _connection("source", "declaration", "Input"),
            _connection("usage_a", "consumer_a"),
            _connection("usage_b", "consumer_b"),
        ],
    )

    assert _rule_count(direct, "long_shared_direct_route") == 1
    assert direct["metrics"]["long_shared_direct_route_count"] == 1
    assert next(
        item for item in direct["violations"] if item["severity"] == "warning"
    )["rule_id"] == "long_shared_direct_route"
    assert _rule_count(rerouted, "long_shared_direct_route") == 0
    assert _rule_count(rerouted, "unbound_reroute_usage") == 0


def test_invalid_duplicate_and_mismatched_reroutes_are_blocking() -> None:
    nodes = [
        _node(
            "declaration_a",
            0,
            0,
            "NamedRerouteDeclaration",
            declaration_name="WaterDepthCm",
            declaration_guid="GUID_A",
        ),
        _node(
            "declaration_b",
            0,
            200,
            "NamedRerouteDeclaration",
            declaration_name="WaterDepthCm",
            declaration_guid="GUID_B",
        ),
        _node(
            "usage_missing",
            500,
            0,
            "NamedRerouteUsage",
            declaration_node_id="missing",
        ),
        _node(
            "usage_mismatch",
            500,
            200,
            "NamedRerouteUsage",
            declaration_node_id="declaration_a",
            declaration_name="OtherName",
            declaration_guid="GUID_B",
        ),
    ]
    report = _analyze(nodes)

    assert _rule_count(report, "duplicate_reroute_declaration") == 1
    assert _rule_count(report, "unbound_reroute_usage") == 1
    assert _rule_count(report, "reroute_binding_mismatch") == 1
    assert report["metrics"]["hard_error_count"] == 3


def test_comment_containment_nesting_and_partial_overlap() -> None:
    node = _node("node", 0, 0)
    outer = _node("outer", -200, -200, "Comment", size_x=900, size_y=700)
    inner = _node("inner", -100, -100, "Comment", size_x=500, size_y=400)
    nested = _analyze([node, outer, inner], comments=[outer, inner])

    partial_a = _node("partial_a", 0, 0, "Comment", size_x=500, size_y=500)
    partial_b = _node("partial_b", 400, 100, "Comment", size_x=500, size_y=500)
    partial = _analyze([partial_a, partial_b], comments=[partial_a, partial_b])

    escaping_comment = _node("comment", 0, 0, "Comment", size_x=300, size_y=300)
    escaping = _analyze(
        [_node("escaping_node", 250, 100), escaping_comment],
        comments=[escaping_comment],
    )

    assert nested["metrics"]["hard_error_count"] == 0
    assert _rule_count(partial, "comment_partial_overlap") == 1
    assert _rule_count(escaping, "comment_node_escape") == 1


def test_cross_group_routes_and_wire_crossings_are_advisory() -> None:
    source_group = _node("source_group", -200, -200, "Comment", size_x=600, size_y=490)
    target_group = _node("target_group", 800, -200, "Comment", size_x=600, size_y=490)
    cross_group = _analyze(
        [
            _node("source", 0, 0),
            _node("target", 1000, 0),
            source_group,
            target_group,
        ],
        [_connection("source", "target")],
        [source_group, target_group],
    )
    crossing = _analyze(
        [
            _node("top_left", 0, 0),
            _node("bottom_left", 0, 400),
            _node("top_right", 1000, 0),
            _node("bottom_right", 1000, 400),
        ],
        [
            _connection("top_left", "bottom_right"),
            _connection("bottom_left", "top_right"),
        ],
    )

    assert _rule_count(cross_group, "cross_group_direct_edge") == 1
    assert cross_group["metrics"]["hard_error_count"] == 0
    assert _rule_count(crossing, "wire_crossing_heuristic") == 1
    assert crossing["metrics"]["hard_error_count"] == 0


@patch("unreal_material_graph.tools.analyze_material_graph")
def test_layout_tool_returns_structured_non_mutating_verification(mock_analyze) -> None:
    mock_analyze.return_value = {
        "success": True,
        "asset_path": "/Game/MF_Test",
        "nodes": [_node("source", 500, 0), _node("target", 0, 0)],
        "connections": [_connection("source", "target")],
        "comments": [],
    }

    result = tools.analyze_material_graph_layout("/Game/MF_Test")

    assert result["success"] is True
    assert result["applied_changes"] == []
    assert result["verification"]["verified"] is False
    assert result["metrics"]["hard_error_count"] == 1
    assert result["post_state"]["/Game/MF_Test"]["bounds_mode"] == "estimated"


def test_material_graph_server_exposes_layout_analysis() -> None:
    assert any(
        getattr(tool, "__name__", "") == "analyze_material_graph_layout"
        for tool in server.TOOLS
    )


def test_harness_info_describes_fixed_layout_profile() -> None:
    result = tools.get_material_graph_harness_info()

    assert "layout_analysis" in result["supports"]
    assert result["layout_analysis_profile"] == "material_readable_v1"
    assert result["layout_thresholds"]["grid_size"] == 100
    assert result["layout_thresholds"]["long_shared_span"] == 1200


def test_comment_size_update_aliases_match_readback_fields() -> None:
    comment = {"size_x": 1300, "size_y": 1600}

    assert tools._read_node_property(comment, "SizeX") == 1300
    assert tools._read_node_property(comment, "SizeY") == 1600
