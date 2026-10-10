from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from unreal_material_graph import ir
from unreal_material_graph import tools


REPO_ROOT = Path(__file__).resolve().parents[1]
MATERIAL_COMMANDS_CPP = (
    REPO_ROOT
    / "RenderingMCP"
    / "Plugins"
    / "UnrealMCP"
    / "Source"
    / "UnrealMCP"
    / "Private"
    / "Commands"
    / "EpicUnrealMCPMaterialCommands.cpp"
)


def test_material_attribute_nodes_use_native_safe_pin_apis() -> None:
    source = MATERIAL_COMMANDS_CPP.read_text(encoding="utf-8")

    assert "GetAttributes->CreateOrGetOutputAttribute(Attribute)" in source
    assert "SetAttributes->CreateOrGetInputAttribute(Attribute)" in source
    assert "AttributeGetTypes.Add(" not in source
    assert "AttributeSetTypes.Add(" not in source


def test_named_reroutes_and_comments_use_native_graph_collections() -> None:
    source = MATERIAL_COMMANDS_CPP.read_text(encoding="utf-8")

    assert "Binding.Usage->Declaration = Declaration" in source
    assert "Binding.Usage->DeclarationGuid = Declaration->VariableGuid" in source
    assert "GetExpressionCollection().AddComment(Comment)" in source
    assert 'SetArrayField(TEXT("comments"), CommentsArray)' in source


def test_recipe_node_schema_normalizes_new_node_extensions() -> None:
    get_node = tools._normalize_recipe_node_schema(
        {
            "id": "get_attrs",
            "type": "MaterialExpressionGetMaterialAttributes",
            "attributes": [" BaseColor ", "Roughness"],
        }
    )
    usage_node = tools._normalize_recipe_node_schema(
        {
            "id": "water_depth_use",
            "type": "NamedRerouteUsage",
            "declaration_name": "WaterDepthCm",
        }
    )

    assert get_node["type"] == "GetMaterialAttributes"
    assert get_node["attributes"] == ["BaseColor", "Roughness"]
    assert usage_node["declaration_name"] == "WaterDepthCm"


def test_recipe_node_schema_rejects_unbound_named_reroute_usage() -> None:
    with pytest.raises(ValueError, match="declaration_node_id or declaration_name"):
        tools._normalize_recipe_node_schema(
            {"id": "unbound_usage", "type": "NamedRerouteUsage"}
        )


@patch("unreal_material_graph.tools.analyze_material_graph")
@patch("unreal_material_graph.tools.build_material_graph")
def test_recipe_extensions_reach_cpp_backend(
    mock_build_material_graph, mock_analyze_material_graph
) -> None:
    mock_analyze_material_graph.side_effect = [
        {
            "success": True,
            "node_count": 0,
            "connection_count": 0,
            "property_connections": {},
            "asset_path": "/Game/MaterialFunctions/MF_Test",
        },
        {
            "success": True,
            "node_count": 5,
            "connection_count": 0,
            "property_connections": {},
            "asset_path": "/Game/MaterialFunctions/MF_Test",
        },
    ]
    mock_build_material_graph.return_value = {
        "status": "success",
        "result": {"success": True, "node_count": 5, "connection_count": 0},
    }
    nodes = [
        {
            "id": "get_attrs",
            "type": "MaterialExpressionGetMaterialAttributes",
            "attributes": ["BaseColor", "Roughness"],
        },
        {
            "id": "set_attrs",
            "type": "SetMaterialAttributes",
            "attributes": ["BaseColor", "Roughness"],
        },
        {
            "id": "depth_decl",
            "type": "NamedRerouteDeclaration",
            "declaration_name": "WaterDepthCm",
            "color": [0.1, 0.4, 0.8, 1.0],
        },
        {
            "id": "depth_use",
            "type": "NamedRerouteUsage",
            "declaration_node_id": "depth_decl",
        },
        {
            "id": "inputs_comment",
            "type": "MaterialExpressionComment",
            "text": "01 Inputs & Base Attributes",
            "position": {"x": -1200, "y": -800},
            "size": {"x": 1000, "y": 1400},
            "font_size": 18,
            "group_mode": True,
        },
    ]

    result = tools.create_material_graph_recipe(
        material_name="/Game/MaterialFunctions/MF_Test",
        nodes=nodes,
        compile=False,
    )

    assert result["success"] is True
    backend_nodes = mock_build_material_graph.call_args.kwargs["nodes"]
    assert [node["type"] for node in backend_nodes] == [
        "GetMaterialAttributes",
        "SetMaterialAttributes",
        "NamedRerouteDeclaration",
        "NamedRerouteUsage",
        "Comment",
    ]
    assert backend_nodes[0]["attributes"] == ["BaseColor", "Roughness"]


def test_graph_normalization_returns_comments_and_attribute_names() -> None:
    normalized = tools._normalize_graph_payload(
        {
            "nodes": [
                {
                    "node_id": "get_attrs",
                    "type": "GetMaterialAttributes",
                    "attribute_names": ["BaseColor", "Roughness"],
                }
            ],
            "comments": [
                {
                    "node_id": "comment_1",
                    "type": "Comment",
                    "text": "01 Inputs & Base Attributes",
                }
            ],
            "connections": [],
            "property_connections": {},
        },
        include_legacy_connection_keys=False,
    )

    assert normalized["nodes"][0]["attribute_names"] == [
        "BaseColor",
        "Roughness",
    ]
    assert normalized["comments"][0]["text"] == "01 Inputs & Base Attributes"


def test_ue_ir_round_trip_preserves_comment_without_duplication() -> None:
    comment = {
        "node_id": "comment_1",
        "type": "Comment",
        "text": "Coverage & Depth",
    }
    payload = {
        "asset_type": "MaterialFunction",
        "name": "MF_ShallowWater",
        "path": "/Game/PVFeature/TA/MaterialFunctions/MF_ShallowWater",
        "nodes": [comment],
        "comments": [comment],
        "connections": [],
        "property_connections": {},
    }

    recipe = ir.build_ue_material_recipe(payload)

    assert [node["node_id"] for node in recipe["nodes"]] == ["comment_1"]
    assert recipe["nodes"][0]["text"] == "Coverage & Depth"
