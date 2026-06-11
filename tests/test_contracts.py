import unittest
from pathlib import Path
from unittest.mock import patch
import importlib
import json
import tempfile
import tomllib

from unreal_asset import tools as asset_tools
from unreal_backend_tcp import tools as backend_tools
from unreal_blueprint import tools as blueprint_tools
from unreal_diagnostics import tools as diagnostics_tools
from unreal_harness_runtime import config as runtime_config
from unreal_material import tools as material_tools
from unreal_material_graph import tools as material_graph_tools
from unreal_orchestrator import server as orchestrator_server
from unreal_renderdoc import tools as renderdoc_tools
from unreal_scene import tools as scene_tools


class AssetToolContractTests(unittest.TestCase):
    def test_asset_check_treats_enum_name_and_serialized_enum_as_equal(self) -> None:
        result = asset_tools._asset_check(
            "/Game/Textures/T_RMO.T_RMO",
            "compression_settings",
            "TC_MASKS",
            "<TextureCompressionSettings.TC_MASKS: 2>",
        )

        self.assertTrue(result["ok"])

    @patch("unreal_asset.tools.run_editor_python")
    def test_get_asset_properties_normalizes_enum_payloads(self, mock_run_editor_python) -> None:
        mock_run_editor_python.return_value = {
            "success": True,
            "summary": {"requested": 1, "succeeded": 1, "failed": 0},
            "results": [
                {
                    "success": True,
                    "asset_path": "/Game/Textures/T_Normal.T_Normal",
                    "properties": {
                        "compression_settings": {"name": "TC_NORMALMAP", "value": 1},
                        "srgb": False,
                    },
                    "failed_properties": [],
                }
            ],
        }

        result = asset_tools.get_asset_properties(
            ["/Game/Textures/T_Normal.T_Normal"],
            ["compression_settings", "srgb"],
        )

        self.assertTrue(result["success"])
        props = result["post_state"]["/Game/Textures/T_Normal.T_Normal"]
        self.assertEqual(props["compression_settings"]["name"], "TC_NORMALMAP")
        self.assertEqual(props["compression_settings"]["value"], 1)
        self.assertFalse(props["srgb"])

    def test_asset_harness_advertises_material_function_creation(self) -> None:
        result = asset_tools.get_asset_harness_info()

        self.assertIn("MaterialFunction", result["supported_create_types"])

    @patch("unreal_asset.tools.raw_create_material_function")
    def test_create_asset_with_properties_supports_material_function(
        self, mock_create_material_function
    ) -> None:
        mock_create_material_function.return_value = {
            "status": "success",
            "result": {
                "success": True,
                "name": "MF_Test",
                "path": "/Game/MaterialFunctions/MF_Test",
            },
        }

        result = asset_tools.create_asset_with_properties(
            "MaterialFunction",
            "MF_Test",
            path="/Game/MaterialFunctions/",
            properties={"description": "Test function"},
        )

        self.assertTrue(result["success"])
        self.assertEqual(result["asset_class"], "MaterialFunction")
        self.assertEqual(result["failed_properties"], [])
        mock_create_material_function.assert_called_once_with(
            name="MF_Test",
            path="/Game/MaterialFunctions/",
            description="Test function",
        )

    @patch("unreal_asset.tools.create_asset_with_properties")
    @patch("unreal_asset.tools.run_editor_python")
    def test_ensure_asset_with_properties_supports_material_function(
        self, mock_run_editor_python, mock_create_asset
    ) -> None:
        mock_run_editor_python.return_value = {
            "success": True,
            "asset_path": "/Game/MaterialFunctions/MF_Test.MF_Test",
            "exists": False,
        }
        mock_create_asset.return_value = {
            "success": True,
            "operation_id": "asset:create_asset_with_properties:123",
            "domain": "asset",
            "asset_class": "MaterialFunction",
        }

        result = asset_tools.ensure_asset_with_properties(
            "MaterialFunction",
            "MF_Test",
            path="/Game/MaterialFunctions/",
            properties={"description": "Test function"},
        )

        self.assertTrue(result["success"])
        self.assertEqual(result["action"], "created")
        mock_create_asset.assert_called_once_with(
            asset_type="MaterialFunction",
            name="MF_Test",
            path="/Game/MaterialFunctions/",
            properties={"description": "Test function"},
        )

    @patch("unreal_asset.tools.run_editor_python")
    def test_set_asset_properties_reports_save_result(self, mock_run_editor_python) -> None:
        mock_run_editor_python.return_value = {
            "success": True,
            "summary": {"requested": 1, "succeeded": 1, "failed": 0},
            "results": [
                {
                    "success": True,
                    "asset_path": "/Game/Textures/T_Albedo.T_Albedo",
                    "modified_properties": ["srgb"],
                    "post_state": {"srgb": False},
                    "failed_properties": [],
                    "save_result": {"save_requested": True, "saved": True},
                }
            ],
        }

        result = asset_tools.set_asset_properties(
            ["/Game/Textures/T_Albedo.T_Albedo"],
            {"srgb": False},
            save=True,
        )

        self.assertTrue(result["success"])
        self.assertEqual(result["items"][0]["save_result"]["saved"], True)
        self.assertEqual(result["applied_changes"][0]["field"], "srgb")

    @patch("unreal_asset.tools.get_asset_properties")
    @patch("unreal_asset.tools.raw_get_assets")
    def test_query_textures_merges_requested_properties(
        self, mock_raw_get_assets, mock_get_asset_properties
    ) -> None:
        mock_raw_get_assets.return_value = {
            "status": "success",
            "result": {
                "success": True,
                "assets": [
                    {
                        "name": "T_Normal",
                        "path": "/Game/Textures/T_Normal.T_Normal",
                        "class": "Texture2D",
                        "package": "/Game/Textures",
                    },
                    {
                        "name": "SK_Enemy",
                        "path": "/Game/Textures/SK_Enemy.SK_Enemy",
                        "class": "SkeletalMesh",
                        "package": "/Game/Textures",
                    }
                ],
                "total_count": 2,
                "returned_count": 2,
                "limit": 20,
                "offset": 0,
            },
        }
        mock_get_asset_properties.return_value = {
            "success": True,
            "failed_changes": [],
            "post_state": {
                "/Game/Textures/T_Normal.T_Normal": {
                    "compression_settings": {"name": "TC_NORMALMAP", "value": 1},
                    "srgb": False,
                }
            },
            "verification": {"checks": []},
        }

        result = asset_tools.query_textures(
            path="/Game/Textures",
            properties=["compression_settings", "srgb"],
        )

        self.assertTrue(result["success"])
        self.assertEqual(len(result["textures"]), 1)
        texture = result["textures"][0]
        self.assertEqual(
            texture["properties"]["compression_settings"]["name"], "TC_NORMALMAP"
        )
        self.assertFalse(texture["properties"]["srgb"])
        self.assertEqual(result["raw_asset_count"], 2)
        self.assertEqual(result["filtered_texture_count"], 1)

    @patch("unreal_asset.tools.send_command")
    @patch("unreal_asset.tools.run_editor_python")
    def test_inspect_particle_system_falls_back_to_niagara_backend(
        self, mock_run_editor_python, mock_send_command
    ) -> None:
        mock_run_editor_python.return_value = {
            "success": False,
            "asset_class": "NiagaraSystem",
            "error": "inspect_particle_system currently supports Cascade ParticleSystem only, got NiagaraSystem",
        }
        mock_send_command.return_value = {
            "status": "success",
            "result": {
                "success": True,
                "emitter_count": 1,
                "emitters": [{"name": "EmitterA", "renderer_count": 1}],
            },
        }

        result = asset_tools.inspect_particle_system("/Game/VFX/NS_Test.NS_Test")

        self.assertTrue(result["success"])
        self.assertEqual(result["asset_class"], "NiagaraSystem")
        self.assertEqual(result["emitters"][0]["name"], "EmitterA")

    @patch("unreal_asset.tools.run_editor_python")
    def test_update_asset_properties_batch_chunks_large_requests(self, mock_run_editor_python) -> None:
        mock_run_editor_python.side_effect = [
            {
                "success": True,
                "summary": {"requested": 25, "succeeded": 25, "failed": 0},
                "results": [
                    {
                        "success": True,
                        "asset_path": f"/Game/Tex/T_{i}.T_{i}",
                        "modified_properties": ["lod_group"],
                        "post_state": {"lod_group": {"name": "TEXTUREGROUP_PROJECT02", "value": 35}},
                        "failed_properties": [],
                        "save_result": {"save_requested": True, "saved": True},
                    }
                    for i in range(25)
                ],
            },
            {
                "success": True,
                "summary": {"requested": 5, "succeeded": 5, "failed": 0},
                "results": [
                    {
                        "success": True,
                        "asset_path": f"/Game/Tex/T_{i}.T_{i}",
                        "modified_properties": ["lod_group"],
                        "post_state": {"lod_group": {"name": "TEXTUREGROUP_PROJECT02", "value": 35}},
                        "failed_properties": [],
                        "save_result": {"save_requested": True, "saved": True},
                    }
                    for i in range(25, 30)
                ],
            },
        ]

        items = [
            {
                "asset_path": f"/Game/Tex/T_{i}.T_{i}",
                "properties": {"lod_group": "TEXTUREGROUP_PROJECT02"},
            }
            for i in range(30)
        ]
        result = asset_tools.update_asset_properties_batch(items)

        self.assertTrue(result["success"])
        self.assertEqual(mock_run_editor_python.call_count, 2)
        self.assertEqual(result["summary"]["chunks"], 2)
        self.assertEqual(result["summary"]["succeeded"], 30)


class BlueprintToolContractTests(unittest.TestCase):
    @patch("unreal_blueprint.tools.raw_read_blueprint_content")
    def test_read_blueprint_content_normalizes_simple_name_to_default_path(
        self, mock_read_blueprint_content
    ) -> None:
        mock_read_blueprint_content.return_value = {
            "status": "success",
            "result": {
                "success": True,
                "blueprint_path": "/Game/Blueprints/BP_Test.BP_Test",
                "blueprint_name": "BP_Test",
            },
        }

        result = blueprint_tools.read_blueprint_content(blueprint_name="BP_Test")

        self.assertTrue(result["success"])
        self.assertEqual(
            mock_read_blueprint_content.call_args.kwargs["blueprint_path"],
            "/Game/Blueprints/BP_Test.BP_Test",
        )

    @patch("unreal_blueprint.tools.analyze_blueprint_graph")
    def test_find_blueprint_nodes_filters_by_title_and_pin(
        self, mock_analyze_blueprint_graph
    ) -> None:
        mock_analyze_blueprint_graph.return_value = {
            "success": True,
            "blueprint_path": "/Game/Blueprints/BP_Test.BP_Test",
            "graph_name": "EventGraph",
            "graph_data": {
                "nodes": [
                    {
                        "name": "K2Node_CallFunction_20",
                        "class": "K2Node_CallFunction",
                        "title": "Add Component by Class",
                        "pins": [
                            {"name": "Class", "direction": "Input"},
                            {"name": "ReturnValue", "direction": "Output"},
                        ],
                    },
                    {
                        "name": "K2Node_CallFunction_21",
                        "class": "K2Node_CallFunction",
                        "title": "Print String",
                        "pins": [{"name": "InString", "direction": "Input"}],
                    },
                ]
            },
        }

        result = blueprint_tools.find_blueprint_nodes(
            blueprint_path="/Game/Blueprints/BP_Test.BP_Test",
            title_filter="Add Component",
            pin_name_filter="Class",
            pin_direction="input",
        )

        self.assertTrue(result["success"])
        self.assertEqual(result["matched_count"], 1)
        self.assertEqual(result["nodes"][0]["name"], "K2Node_CallFunction_20")
        self.assertEqual(result["nodes"][0]["matched_pins"][0]["name"], "Class")

    @patch("unreal_blueprint.tools.raw_analyze_blueprint_graph")
    def test_analyze_blueprint_graph_defaults_to_summary_payload(
        self, mock_raw_analyze_blueprint_graph
    ) -> None:
        mock_raw_analyze_blueprint_graph.return_value = {
            "status": "success",
            "result": {
                "success": True,
                "blueprint_path": "/Game/Blueprints/BP_Test.BP_Test",
                "graph_name": "EventGraph",
                "node_count": 7,
                "connection_count": 3,
            },
        }

        result = blueprint_tools.analyze_blueprint_graph(
            blueprint_path="/Game/Blueprints/BP_Test.BP_Test"
        )

        self.assertTrue(result["success"])
        self.assertEqual(result["node_count"], 7)
        self.assertEqual(result["connection_count"], 3)
        self.assertNotIn("graph_data", result)
        self.assertTrue(mock_raw_analyze_blueprint_graph.call_args.kwargs["summary_only"])
        self.assertFalse(mock_raw_analyze_blueprint_graph.call_args.kwargs["result_handle"])

    @patch("unreal_blueprint.tools.raw_add_blueprint_node")
    def test_add_point_light_component_node_uses_add_component_by_class(
        self, mock_add_blueprint_node
    ) -> None:
        mock_add_blueprint_node.return_value = {
            "status": "success",
            "result": {
                "success": True,
                "node_id": "K2Node_AddComponentByClass_1",
                "node_type": "AddComponentByClass",
            },
        }

        result = blueprint_tools.add_point_light_component_node(
            blueprint_path="/Game/Blueprints/BP_Test.BP_Test"
        )

        self.assertTrue(result["success"])
        self.assertEqual(
            mock_add_blueprint_node.call_args.kwargs["node_params"]["component_class"],
            "/Script/Engine.PointLightComponent",
        )

    def test_upsert_texture_lod_group_lines_appends_missing_group(self) -> None:
        lines = [
            "[GlobalDefaults DeviceProfile]",
            "TextureLODGroups=(Group=TEXTUREGROUP_World,MinLODSize=1,MaxLODSize=16384)",
        ]

        updated = asset_tools._upsert_texture_lod_group_lines(
            lines,
            group_name="TEXTUREGROUP_PROJECT01",
            max_lod_size=2048,
        )

        joined = "\n".join(updated)
        self.assertIn("Group=TEXTUREGROUP_PROJECT01", joined)
        self.assertIn("MaxLODSize=2048", joined)

    @patch("unreal_asset.tools.run_editor_python")
    def test_create_asset_with_properties_preserves_partial_creation_details(
        self, mock_run_editor_python
    ) -> None:
        mock_run_editor_python.return_value = {
            "success": False,
            "asset_name": "MI_Test",
            "asset_path": "/Game/Test/MI_Test.MI_Test",
            "asset_class": "MaterialInstanceConstant",
            "post_state": {"parent": "/Game/Base/M_Base.M_Base"},
            "failed_properties": ["scalar_a: bad value"],
        }

        result = asset_tools.create_asset_with_properties(
            asset_type="MaterialInstanceConstant",
            name="MI_Test",
            path="/Game/Test",
            properties={"parent_material": "/Game/Base/M_Base.M_Base", "scalar_a": 1.0},
        )

        self.assertFalse(result["success"])
        self.assertEqual(result["asset_path"], "/Game/Test/MI_Test.MI_Test")
        self.assertEqual(result["targets"], ["/Game/Test/MI_Test.MI_Test"])
        self.assertEqual(result["failed_changes"][0]["field"], "scalar_a")
        self.assertIn("/Game/Test/MI_Test.MI_Test", result["post_state"])

    @patch("unreal_asset.tools.run_editor_python")
    def test_update_asset_properties_uses_requested_key_for_parent_material(
        self, mock_run_editor_python
    ) -> None:
        mock_run_editor_python.return_value = {
            "success": True,
            "summary": {"requested": 1, "succeeded": 1, "failed": 0},
            "results": [
                {
                    "success": True,
                    "asset_path": "/Game/Test/MI_Test.MI_Test",
                    "modified_properties": ["parent"],
                    "post_state": {"parent": "/Game/Base/M_Base.M_Base"},
                    "failed_properties": [],
                    "save_result": {"save_requested": True, "saved": True},
                }
            ],
        }

        result = asset_tools.update_asset_properties(
            "/Game/Test/MI_Test.MI_Test",
            {"parent_material": "/Game/Base/M_Base.M_Base"},
        )

        self.assertEqual(len(result["applied_changes"]), 1)
        self.assertEqual(
            result["applied_changes"][0]["value"], "/Game/Base/M_Base.M_Base"
        )

    @patch("unreal_asset.tools._resolve_project_config_dir")
    def test_update_texture_group_config_writes_default_device_profiles(
        self, mock_resolve_project_config_dir
    ) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir)
            ini_path = config_dir / "DefaultDeviceProfiles.ini"
            ini_path.write_text("[GlobalDefaults DeviceProfile]\n", encoding="utf-8")
            mock_resolve_project_config_dir.return_value = config_dir

            result = asset_tools.update_texture_group_config(
                "TEXTUREGROUP_PROJECT01",
                2048,
            )

            written = ini_path.read_text(encoding="utf-8")
            self.assertTrue(result["success"])
            self.assertIn("Group=TEXTUREGROUP_PROJECT01", written)
            self.assertIn("MaxLODSize=2048", written)

    @patch("unreal_asset.tools.run_editor_python")
    def test_update_asset_properties_batch_preserves_requested_parent_key(
        self, mock_run_editor_python
    ) -> None:
        mock_run_editor_python.return_value = {
            "success": True,
            "summary": {"requested": 1, "succeeded": 1, "failed": 0},
            "results": [
                {
                    "success": True,
                    "asset_path": "/Game/Test/MI_Test.MI_Test",
                    "modified_properties": ["parent"],
                    "post_state": {"parent": "/Game/Base/M_Base.M_Base"},
                    "failed_properties": [],
                }
            ],
        }

        result = asset_tools.update_asset_properties_batch(
            [
                {
                    "asset_path": "/Game/Test/MI_Test.MI_Test",
                    "properties": {"parent_material": "/Game/Base/M_Base.M_Base"},
                }
            ]
        )

        self.assertTrue(result["success"])
        self.assertEqual(result["summary"]["verified"], 1)
        self.assertEqual(len(result["applied_changes"]), 1)
        self.assertEqual(
            result["applied_changes"][0]["value"], "/Game/Base/M_Base.M_Base"
        )


class MaterialToolContractTests(unittest.TestCase):
    @patch("unreal_material.tools.create_asset_with_properties")
    def test_material_wrappers_replace_operation_id(self, mock_create_asset) -> None:
        mock_create_asset.return_value = {
            "success": True,
            "operation_id": "asset:create_asset_with_properties:123",
            "domain": "asset",
        }

        result = material_tools.create_material_asset("M_Test")

        self.assertEqual(result["domain"], "material")
        self.assertTrue(result["operation_id"].startswith("material:create_material_asset:"))

    @patch("unreal_material.tools.run_editor_python")
    def test_scalar_parameter_uses_tolerant_float_comparison(
        self, mock_run_editor_python
    ) -> None:
        mock_run_editor_python.return_value = {
            "success": True,
            "asset_path": "/Game/Test/MI_Test.MI_Test",
            "parameter_name": "Roughness",
            "changed": True,
            "value": 0.10000001,
        }

        result = material_tools.set_material_instance_scalar_parameter(
            "/Game/Test/MI_Test.MI_Test",
            "Roughness",
            0.1,
        )

        self.assertTrue(result["success"])
        self.assertTrue(result["verification"]["verified"])

    @patch("unreal_material.tools.create_material_function")
    def test_create_material_function_asset_wraps_backend_command(
        self, mock_create_material_function
    ) -> None:
        mock_create_material_function.return_value = {
            "status": "success",
            "result": {
                "success": True,
                "name": "MF_Test",
                "path": "/Game/MaterialFunctions/MF_Test",
            },
        }

        result = material_tools.create_material_function_asset(
            "MF_Test",
            path="/Game/MaterialFunctions/",
            description="Test function",
        )

        self.assertTrue(result["success"])
        self.assertEqual(result["asset_class"], "MaterialFunction")
        mock_create_material_function.assert_called_once_with(
            name="MF_Test",
            path="/Game/MaterialFunctions/",
            description="Test function",
        )

    @patch("unreal_backend_tcp.tools.send_command")
    def test_backend_create_material_function_uses_raw_command(
        self, mock_send_command
    ) -> None:
        mock_send_command.return_value = {"status": "success", "result": {"success": True}}

        backend_tools.create_material_function(
            name="MF_Test",
            path="/Game/MaterialFunctions/",
            description="Test function",
        )

        mock_send_command.assert_called_once_with(
            "create_material_function",
            {
                "name": "MF_Test",
                "path": "/Game/MaterialFunctions/",
                "description": "Test function",
            },
        )

    def test_unreal_connection_receives_raw_json_response_in_chunks(self) -> None:
        from unreal_backend_tcp.connection import UnrealConnection

        class FakeSocket:
            def __init__(self) -> None:
                self.chunks = [
                    b'{"status":"success",',
                    b'"result":{"message":"pong"}}',
                ]

            def settimeout(self, timeout: float) -> None:
                self.timeout = timeout

            def recv(self, size: int) -> bytes:
                return self.chunks.pop(0)

        connection = UnrealConnection()
        connection.socket = FakeSocket()

        response = connection._receive_raw_json_response("ping", timeout_override=1)

        self.assertEqual(response["status"], "success")
        self.assertEqual(response["result"]["message"], "pong")


class MaterialGraphContractTests(unittest.TestCase):
    @patch("unreal_material_graph.tools._load_full_graph")
    def test_get_material_graph_returns_full_graph_and_repairs_truncated_types(
        self, mock_load_full_graph
    ) -> None:
        mock_load_full_graph.return_value = {
            "status": "success",
            "result": {
                "success": True,
                "path": "/Game/Materials/M_Test",
                "asset_type": "Material",
                "nodes": [
                    {
                        "node_id": "Expr_ultiply_17",
                        "type": "ultiply",
                        "name": "MaterialExpressionMultiply_17",
                    }
                ],
                "connections": [],
                "property_connections": {},
            },
        }

        result = material_graph_tools.get_material_graph("/Game/Materials/M_Test")

        self.assertTrue(result["success"])
        self.assertEqual(result["nodes"][0]["type"], "Multiply")
        self.assertEqual(result["nodes"][0]["raw_type"], "ultiply")
        self.assertEqual(result["node_type_counts"], {"Multiply": 1})

    @patch("unreal_material_graph.tools._load_full_graph")
    def test_analyze_material_graph_can_return_full_graph_with_normalized_connections(
        self, mock_load_full_graph
    ) -> None:
        mock_load_full_graph.return_value = {
            "status": "success",
            "result": {
                "success": True,
                "path": "/Game/Materials/M_Test",
                "asset_type": "Material",
                "nodes": [{"node_id": "Expr_Constant_1", "type": "Constant"}],
                "connections": [
                    {
                        "from": "Expr_Constant_1",
                        "to": "Expr_Add_2",
                        "from_output": "Output_0",
                        "to_input": "A",
                    }
                ],
                "property_connections": {
                    "EmissiveColor": {"node_id": "Expr_Add_2", "output_index": 0}
                },
            },
        }

        result = material_graph_tools.analyze_material_graph(
            "/Game/Materials/M_Test",
            include_full_graph=True,
        )

        self.assertTrue(result["success"])
        self.assertEqual(result["connections"][0]["source"], "Expr_Constant_1")
        self.assertEqual(result["connections"][0]["target_input"], "A")
        self.assertEqual(
            result["property_connections"]["EmissiveColor"]["target"], "Material"
        )
        self.assertEqual(
            result["graph"]["property_connections"]["EmissiveColor"]["source"],
            "Expr_Add_2",
        )

    @patch("unreal_material_graph.tools._load_full_graph")
    def test_analyze_material_graph_verifies_backend_counts(self, mock_load_full_graph) -> None:
        mock_load_full_graph.return_value = {
            "status": "success",
            "result": {
                "success": True,
                "path": "/Game/Materials/M_Test",
                "asset_type": "Material",
                "node_count": 3,
                "connection_count": 2,
                "nodes": [{"type": "Constant"}, {"type": "Multiply"}],
                "connections": [{"source": "A", "target": "B"}],
                "property_connections": {},
            },
        }

        result = material_graph_tools.analyze_material_graph("/Game/Materials/M_Test")

        self.assertTrue(result["success"])
        self.assertFalse(result["verification"]["verified"])
        check_fields = {check["field"] for check in result["verification"]["checks"]}
        self.assertIn("node_count", check_fields)
        self.assertIn("connection_count", check_fields)

    @patch("unreal_material_graph.tools._load_full_graph")
    def test_analyze_material_graph_detects_mismatched_asset_path(self, mock_load_full_graph) -> None:
        mock_load_full_graph.return_value = {
            "status": "success",
            "result": {
                "success": True,
                "path": "/Game/Materials/M_Other",
                "asset_type": "Material",
                "nodes": [],
                "connections": [],
                "property_connections": {},
            },
        }

        result = material_graph_tools.analyze_material_graph("/Game/Materials/M_Test")

        self.assertTrue(result["success"])
        self.assertFalse(result["verification"]["verified"])
        asset_path_checks = [
            check
            for check in result["verification"]["checks"]
            if check["field"] == "asset_path"
        ]
        self.assertEqual(asset_path_checks[0]["actual"], "/Game/Materials/M_Other")

    @patch("unreal_material_graph.tools.analyze_material_graph")
    @patch("unreal_material_graph.tools.build_material_graph")
    def test_create_material_graph_recipe_uses_delta_validation_for_append(
        self, mock_build_material_graph, mock_analyze_material_graph
    ) -> None:
        mock_analyze_material_graph.side_effect = [
            {
                "success": True,
                "node_count": 5,
                "connection_count": 4,
                "property_connections": {"EmissiveColor": {"source": "Expr_1"}},
                "asset_path": "/Game/Materials/M_Test",
            },
            {
                "success": True,
                "node_count": 7,
                "connection_count": 5,
                "property_connections": {"EmissiveColor": {"source": "Expr_1"}},
                "asset_path": "/Game/Materials/M_Test",
            },
        ]
        mock_build_material_graph.return_value = {
            "status": "success",
            "result": {
                "success": True,
                "node_count": 2,
                "connection_count": 1,
            },
        }

        result = material_graph_tools.create_material_graph_recipe(
            material_name="/Game/Materials/M_Test",
            nodes=[{"id": "NodeA", "type": "Constant"}, {"id": "NodeB", "type": "Add"}],
            connections=[
                {
                    "source": "NodeA",
                    "target": "NodeB",
                    "source_output": "Output_0",
                    "target_input": "A",
                }
            ],
        )

        self.assertTrue(result["success"])
        post_count_checks = [
            check
            for check in result["verification"]["checks"]
            if check["field"] == "post_node_count"
        ]
        self.assertEqual(post_count_checks[0]["expected"], 7)

    @patch("unreal_material_graph.tools.analyze_material_graph")
    @patch("unreal_material_graph.tools.build_material_graph")
    def test_create_material_graph_recipe_passes_custom_additional_outputs(
        self, mock_build_material_graph, mock_analyze_material_graph
    ) -> None:
        mock_analyze_material_graph.side_effect = [
            {
                "success": True,
                "node_count": 0,
                "connection_count": 0,
                "property_connections": {},
                "asset_path": "/Game/Materials/M_Test",
            },
            {
                "success": True,
                "node_count": 1,
                "connection_count": 0,
                "property_connections": {},
                "asset_path": "/Game/Materials/M_Test",
            },
        ]
        mock_build_material_graph.return_value = {
            "status": "success",
            "result": {
                "success": True,
                "node_count": 1,
                "connection_count": 0,
            },
        }
        additional_outputs = [
            {"output_name": "Opacity", "output_type": "Float1"},
            {"name": "PackedNormal", "type": "Float3"},
        ]

        result = material_graph_tools.create_material_graph_recipe(
            material_name="/Game/Materials/M_Test",
            nodes=[
                {
                    "id": "CustomExample",
                    "type": "Custom",
                    "code": "return 0;",
                    "additional_outputs": additional_outputs,
                }
            ],
        )

        self.assertTrue(result["success"])
        backend_kwargs = mock_build_material_graph.call_args.kwargs
        self.assertEqual(backend_kwargs["nodes"][0]["additional_outputs"], additional_outputs)

    @patch("unreal_material_graph.tools.analyze_material_graph")
    @patch("unreal_material_graph.tools.build_material_graph")
    def test_patch_material_graph_passes_delete_and_disconnect_to_backend(
        self, mock_build_material_graph, mock_analyze_material_graph
    ) -> None:
        mock_analyze_material_graph.side_effect = [
            {
                "success": True,
                "node_count": 4,
                "connection_count": 3,
                "property_connections": {
                    "EmissiveColor": {"source": "Expr_Old", "target_input": "EmissiveColor"}
                },
                "asset_path": "/Game/Materials/M_Test",
            },
            {
                "success": True,
                "node_count": 3,
                "connection_count": 2,
                "property_connections": {},
                "asset_path": "/Game/Materials/M_Test",
            },
        ]
        mock_build_material_graph.return_value = {
            "status": "success",
            "result": {"success": True, "node_count": 0, "connection_count": 0},
        }

        result = material_graph_tools.patch_material_graph(
            material_name="/Game/Materials/M_Test",
            delete_nodes=["Expr_Dead_7"],
            disconnect_connections=[
                {"source": "Expr_A", "target": "Expr_B", "target_input": "A"}
            ],
            disconnect_properties=["EmissiveColor"],
        )

        self.assertTrue(result["success"])
        backend_kwargs = mock_build_material_graph.call_args.kwargs
        self.assertEqual(backend_kwargs["delete_nodes"], ["Expr_Dead_7"])
        self.assertEqual(
            backend_kwargs["disconnect_connections"][0]["target_input"], "A"
        )
        self.assertEqual(backend_kwargs["disconnect_properties"], ["EmissiveColor"])

    @patch("unreal_material_graph.tools.analyze_material_graph")
    @patch("unreal_material_graph.tools.build_material_graph")
    def test_patch_material_graph_updates_existing_node_properties(
        self, mock_build_material_graph, mock_analyze_material_graph
    ) -> None:
        mock_analyze_material_graph.side_effect = [
            {
                "success": True,
                "node_count": 1,
                "connection_count": 0,
                "property_connections": {},
                "asset_path": "/Game/Materials/M_Test",
            },
            {
                "success": True,
                "node_count": 1,
                "connection_count": 0,
                "property_connections": {},
                "asset_path": "/Game/Materials/M_Test",
                "nodes": [
                    {
                        "node_id": "Expr_TextureCoordinate_42",
                        "name": "MaterialExpressionTextureCoordinate_1",
                        "type": "TextureCoordinate",
                        "coordinate_index": 2,
                    }
                ],
            },
        ]
        mock_build_material_graph.return_value = {
            "status": "success",
            "result": {"success": True, "updated_node_count": 1},
        }

        result = material_graph_tools.patch_material_graph(
            material_name="/Game/Materials/M_Test",
            update_nodes=[
                {
                    "node_name": "MaterialExpressionTextureCoordinate_1",
                    "properties": {"coordinate_index": 2},
                }
            ],
        )

        self.assertTrue(result["success"])
        backend_kwargs = mock_build_material_graph.call_args.kwargs
        self.assertEqual(
            backend_kwargs["update_nodes"][0]["node_name"],
            "MaterialExpressionTextureCoordinate_1",
        )
        self.assertEqual(
            backend_kwargs["update_nodes"][0]["properties"]["coordinate_index"],
            2,
        )
        readback_checks = [
            check
            for check in result["verification"]["checks"]
            if check["field"].endswith(".coordinate_index")
        ]
        self.assertEqual(readback_checks[0]["actual"], 2)


class SceneToolContractTests(unittest.TestCase):
    @patch("unreal_scene.tools._run_editor_python")
    def test_set_actor_component_material_runs_live_override_with_readback(
        self, mock_run_editor_python
    ) -> None:
        mock_run_editor_python.return_value = {
            "success": True,
            "operation_id": "scene:set_actor_component_material:test",
            "domain": "scene",
            "targets": ["CubeActor"],
            "applied_changes": [],
            "failed_changes": [],
            "post_state": {},
            "verification": {"verified": True, "checks": []},
        }

        result = scene_tools.set_actor_component_material(
            actor_name_or_label="CubeActor",
            component_name="StaticMeshComponent0",
            material_slot=0,
            material_asset_path="/Game/Materials/MI_Test",
        )

        self.assertTrue(result["success"])
        script = mock_run_editor_python.call_args.args[0]
        self.assertIn("selected_component.set_material(material_slot, material)", script)
        self.assertIn("selected_component.get_material(material_slot)", script)

    @patch("unreal_scene.tools.set_actor_component_material")
    def test_apply_scene_actor_batch_supports_material_overrides(
        self, mock_set_actor_component_material
    ) -> None:
        mock_set_actor_component_material.return_value = {
            "success": True,
            "operation_id": "scene:set_actor_component_material:test",
            "domain": "scene",
            "targets": ["CubeActor"],
            "applied_changes": [
                {
                    "target": "CubeActor.StaticMeshComponent0",
                    "field": "material_override",
                    "value": "/Game/Materials/MI_Test",
                }
            ],
            "failed_changes": [],
            "post_state": {"CubeActor": {"material": "/Game/Materials/MI_Test.MI_Test"}},
            "verification": {"verified": True, "checks": [{"ok": True}]},
        }

        result = scene_tools.apply_scene_actor_batch(
            [
                {
                    "actor_name": "CubeActor",
                    "material_overrides": [
                        {
                            "component_name": "StaticMeshComponent0",
                            "material_slot": 0,
                            "material_asset_path": "/Game/Materials/MI_Test",
                        }
                    ],
                }
            ]
        )

        self.assertTrue(result["success"])
        mock_set_actor_component_material.assert_called_once_with(
            actor_name_or_label="CubeActor",
            material_asset_path="/Game/Materials/MI_Test",
            material_slot=0,
            component_name="StaticMeshComponent0",
            save_level=False,
        )


class DiagnosticsContractTests(unittest.TestCase):
    @patch.dict("os.environ", {}, clear=True)
    def test_get_project_path_requires_explicit_env(self) -> None:
        with self.assertRaises(RuntimeError):
            runtime_config.get_project_path()

    @patch.dict("os.environ", {}, clear=True)
    def test_runtime_paths_marks_project_path_unconfigured(self) -> None:
        runtime_paths = runtime_config.get_runtime_paths()

        self.assertEqual(runtime_paths["project_path"], "")
        self.assertEqual(runtime_paths["project_path_configured"], "false")

    @patch.dict("os.environ", {}, clear=True)
    def test_runtime_paths_resolves_engine_root_from_explicit_env(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            engine_root = Path(temp_dir) / "UE" / "Engine"
            (engine_root / "Source").mkdir(parents=True)
            (engine_root / "Binaries").mkdir(parents=True)

            with patch.dict("os.environ", {"UE_ENGINE_ROOT": str(engine_root)}, clear=True):
                runtime_paths = runtime_config.get_runtime_paths()

        self.assertEqual(Path(runtime_paths["engine_root"]), engine_root)
        self.assertEqual(Path(runtime_paths["engine_source"]), engine_root / "Source")
        self.assertEqual(runtime_paths["engine_root_source_available"], "true")

    @patch.dict("os.environ", {}, clear=True)
    def test_engine_root_resolves_from_editor_exe(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            engine_root = Path(temp_dir) / "UE" / "Engine"
            editor_exe = engine_root / "Binaries" / "Win64" / "UnrealEditor.exe"
            (engine_root / "Source").mkdir(parents=True)
            editor_exe.parent.mkdir(parents=True)
            editor_exe.write_text("", encoding="utf-8")

            with patch.dict("os.environ", {"UE_EDITOR_EXE": str(editor_exe)}, clear=True):
                resolved = runtime_config.get_engine_root_path()

        self.assertEqual(resolved, engine_root)

    @patch.dict("os.environ", {}, clear=True)
    def test_engine_root_resolves_from_project_engine_association_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            engine_parent = temp_root / "UE"
            engine_root = engine_parent / "Engine"
            project_path = temp_root / "Project" / "Project.uproject"
            (engine_root / "Source").mkdir(parents=True)
            (engine_root / "Binaries").mkdir(parents=True)
            project_path.parent.mkdir(parents=True)
            project_path.write_text(
                json.dumps({"EngineAssociation": str(engine_parent)}),
                encoding="utf-8",
            )

            with patch.dict("os.environ", {"UE_PROJECT_PATH": str(project_path)}, clear=True):
                resolved = runtime_config.get_engine_root_path()

        self.assertEqual(resolved, engine_root)

    @patch("unreal_diagnostics.tools.get_project_path_optional")
    @patch("unreal_diagnostics.tools.get_editor_exe_path")
    @patch("unreal_diagnostics.tools.get_editor_ready_state")
    def test_dev_launch_returns_structured_failure_for_missing_paths(
        self,
        mock_ready_state,
        mock_editor_exe_path,
        mock_project_path_optional,
    ) -> None:
        mock_ready_state.return_value = {"ready": False}
        mock_editor_exe_path.return_value = Path("D:/missing/UnrealEditor.exe")
        mock_project_path_optional.return_value = Path("D:/missing/Project.uproject")

        result = diagnostics_tools.dev_launch_editor_and_wait_ready()

        self.assertFalse(result["success"])
        failed_fields = {item["field"] for item in result["failed_changes"]}
        self.assertIn("editor_exe", failed_fields)
        self.assertIn("project_path", failed_fields)

    @patch("unreal_diagnostics.tools.wait_for_editor_ready")
    @patch("unreal_diagnostics.tools.subprocess.Popen")
    @patch("unreal_diagnostics.tools.get_project_path_optional")
    @patch("unreal_diagnostics.tools.get_editor_exe_path")
    @patch("unreal_diagnostics.tools.get_editor_ready_state")
    def test_dev_launch_success_payload_is_json_serializable(
        self,
        mock_ready_state,
        mock_editor_exe_path,
        mock_project_path_optional,
        mock_popen,
        mock_wait_for_ready,
    ) -> None:
        mock_ready_state.return_value = {"ready": False}
        mock_editor_exe_path.return_value = Path(__file__)
        mock_project_path_optional.return_value = Path(__file__)
        mock_wait_for_ready.return_value = {"ready": True}

        result = diagnostics_tools.dev_launch_editor_and_wait_ready()

        json.dumps(result, ensure_ascii=False)
        self.assertEqual(result["targets"], [str(Path(__file__))])
        mock_popen.assert_called_once()


class RenderDocContractTests(unittest.TestCase):
    def test_reverse_lookup_renderdoc_symbols_scans_provided_roots(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            shader_dir = Path(tmpdir) / "Saved" / "ShaderDebugInfo"
            source_dir = Path(tmpdir) / "Source"
            shader_dir.mkdir(parents=True, exist_ok=True)
            source_dir.mkdir(parents=True, exist_ok=True)
            (shader_dir / "MyShader.usf").write_text(
                "// DebugName: FancyLightPixelShader\n", encoding="utf-8"
            )
            (source_dir / "LightComponent.cpp").write_text(
                "Params.LightColor = FVector3f::ZeroVector;\n", encoding="utf-8"
            )

            with patch(
                "unreal_renderdoc.tools._renderdoc_lookup_roots",
                return_value=[shader_dir, source_dir],
            ):
                result = renderdoc_tools.reverse_lookup_renderdoc_symbols(
                    shader_hints=["FancyLightPixelShader"],
                    parameter_hints=["LightColor"],
                    limit=10,
                )

            self.assertTrue(result["success"])
            self.assertTrue(result["shader_debug_matches"])
            self.assertTrue(result["cpp_symbol_matches"])

    def test_normalize_renderdoc_debug_labels_produces_stable_ids(self) -> None:
        result = renderdoc_tools.normalize_renderdoc_debug_labels(
            ["BasePass/Main View", "Nanite::Emit GBuffer"]
        )

        self.assertTrue(result["success"])
        stable_ids = [item["stable_id"] for item in result["normalized_labels"]]
        self.assertEqual(stable_ids, ["basepass_main_view", "nanite_emit_gbuffer"])

    @patch("unreal_renderdoc.tools._extract_selection_context")
    @patch("unreal_renderdoc.tools._parse_log_render_context")
    @patch("unreal_renderdoc.tools._latest_project_log")
    @patch("unreal_renderdoc.tools.send_command")
    @patch("unreal_renderdoc.tools.get_current_level")
    @patch("unreal_renderdoc.tools._run_live_python")
    @patch("unreal_renderdoc.tools.get_project_path")
    def test_get_renderdoc_capture_context_combines_live_and_log_state(
        self,
        mock_get_project_path,
        mock_run_live_python,
        mock_get_current_level,
        mock_send_command,
        mock_latest_project_log,
        mock_parse_log_context,
        mock_extract_selection_context,
    ) -> None:
        mock_run_live_python.return_value = {
            "success": True,
            "world_name": "MyWorld",
            "world_path": "/Game/TestMap.TestMap",
            "camera": {
                "location": {"x": 1, "y": 2, "z": 3},
                "rotation": {"pitch": 4, "yaw": 5, "roll": 6},
            },
            "projection": {
                "is_in_pie": False,
                "build_configuration": "Development",
                "build_version": "UE5-CL-0",
            },
            "cvars": {
                "r.ScreenPercentage": {"string": "100"},
                "r.SecondaryScreenPercentage.GameViewport": {"string": "100"},
                "r.DynamicRes.OperationMode": {"string": "0"},
                "r.Nanite": {"string": "1"},
            },
        }
        mock_get_current_level.return_value = {
            "status": "success",
            "result": {"level_name": "PersistentLevel", "level_path": "/Game/TestMap"},
        }
        mock_send_command.side_effect = [
            {
                "status": "success",
                "result": {
                    "success": True,
                    "perspective": True,
                    "fov": 90.0,
                    "ortho_zoom": 2048.0,
                },
            },
            {
                "status": "success",
                "result": {
                    "success": True,
                    "viewport_type": "Editor",
                    "width": 1920,
                    "height": 1080,
                },
            },
        ]
        mock_latest_project_log.return_value = Path("D:/Logs/ExampleProject.log")
        mock_parse_log_context.return_value = {
            "log_path": "D:/Logs/ExampleProject.log",
            "rhi_name": "D3D12",
            "shader_platform": "PCD3D_SM6",
            "feature_level": "SM6",
        }
        mock_get_project_path.return_value = Path("D:/Projects/ExampleProject/ExampleProject.uproject")
        mock_extract_selection_context.return_value = {
            "success": True,
            "selected_actors": [],
            "selected_assets": [],
            "materials": [],
            "semantic_mapping": {"marker_candidates": [], "likely_pass_families": []},
        }

        result = renderdoc_tools.get_renderdoc_capture_context(include_selection=True)

        self.assertTrue(result["success"])
        context = result["context"]
        rich_context = result["rich_context"]
        self.assertEqual(context["engine"]["project"], "ExampleProject")
        self.assertEqual(context["engine"]["rhi"], "D3D12")
        self.assertEqual(context["scene"]["world"], "MyWorld")
        self.assertEqual(context["view"]["size"], [1920, 1080])
        self.assertEqual(rich_context["selection_context"]["success"], True)

    @patch("unreal_renderdoc.tools.get_project_path")
    @patch("unreal_renderdoc.tools._wait_for_new_capture")
    @patch("unreal_renderdoc.tools._list_captures")
    @patch("unreal_renderdoc.tools._live_capture_command")
    @patch("unreal_renderdoc.tools.get_renderdoc_capture_context")
    def test_request_renderdoc_capture_persists_context_and_notes(
        self,
        mock_context,
        mock_live_capture_command,
        mock_list_captures,
        mock_wait_for_new_capture,
        mock_get_project_path,
    ) -> None:
        with unittest.mock.patch("pathlib.Path.write_text") as _unused:
            pass
        temp_root = Path(self.id().replace(".", "_")).resolve()
        project_dir = temp_root / "Project"
        saved_dir = project_dir / "Saved" / "RenderDocCaptures"
        saved_dir.mkdir(parents=True, exist_ok=True)
        capture_file = saved_dir / "auto_capture.rdc"
        capture_file.write_bytes(b"rdc")

        mock_get_project_path.return_value = project_dir / "Proj.uproject"
        mock_context.return_value = {"success": True, "context": {"debug_cvars": {}}}
        mock_live_capture_command.return_value = {"success": True}
        mock_list_captures.return_value = {}
        mock_wait_for_new_capture.return_value = capture_file

        result = renderdoc_tools.request_renderdoc_capture(
            workflow="editor",
            capture_name="Named Capture",
            notes="Repro notes",
        )

        try:
            self.assertTrue(result["success"])
            self.assertTrue(result["capture_path"].endswith("Named_Capture.rdc"))
            self.assertTrue(Path(result["capture_path"]).exists())
            self.assertTrue(Path(result["context_path"]).exists())
            self.assertTrue(str(result["context_path"]).endswith(".rdc.context.json"))
            self.assertTrue(Path(result["rich_context"]["notes_path"]).exists())
            payload = json.loads(Path(result["context_path"]).read_text(encoding="utf-8"))
            self.assertIn("engine", payload)
            self.assertIn("capture", payload)
        finally:
            if temp_root.exists():
                import shutil

                shutil.rmtree(temp_root, ignore_errors=True)

    def test_capture_renderdoc_diff_pair_emits_changed_cvars(self) -> None:
        with patch("unreal_renderdoc.tools.get_renderdoc_capture_context") as mock_context, patch(
            "unreal_renderdoc.tools._apply_live_configuration"
        ) as mock_apply, patch(
            "unreal_renderdoc.tools.request_renderdoc_capture"
        ) as mock_capture:
            mock_context.return_value = {
                "context": {
                    "debug_cvars": {
                        "r.ScreenPercentage": {"string": "100"},
                        "r.Nanite": {"string": "1"},
                    }
                }
            }
            mock_apply.return_value = {
                "success": True,
                "applied_changes": [],
                "failed_changes": [],
                "checks": [],
            }
            mock_capture.side_effect = [
                {
                    "success": True,
                    "capture_path": "D:/base.rdc",
                    "context_path": "D:/base.context.json",
                    "context": {"cvars": {"r.ScreenPercentage": 100}},
                    "failed_changes": [],
                },
                {
                    "success": True,
                    "capture_path": "D:/variant.rdc",
                    "context_path": "D:/variant.context.json",
                    "context": {"cvars": {"r.ScreenPercentage": 50}},
                    "failed_changes": [],
                },
            ]

            result = renderdoc_tools.capture_renderdoc_diff_pair(
                {"cvars": {"r.ScreenPercentage": "100"}},
                {"cvars": {"r.ScreenPercentage": "50"}},
            )

            self.assertTrue(result["success"])
            changed = result["comparison_metadata"]["structured_inputs"]["cvars"]
            self.assertEqual(changed[0]["name"], "r.ScreenPercentage")


class PackagingAndExposureContractTests(unittest.TestCase):
    def test_pyproject_includes_unreal_renderdoc_package(self) -> None:
        pyproject = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
        includes = pyproject["tool"]["setuptools"]["packages"]["find"]["include"]
        self.assertIn("unreal_renderdoc*", includes)

    def test_orchestrator_exposes_only_routing_tools(self) -> None:
        importlib.reload(orchestrator_server)

        self.assertTrue(callable(orchestrator_server.get_harness_domains))
        self.assertTrue(callable(orchestrator_server.get_domain_design))
        self.assertTrue(callable(orchestrator_server.route_harness_task))
        self.assertFalse(hasattr(orchestrator_server, "DEFAULT_TOOLS"))
        # Verify orchestrator does NOT import domain TOOLS
        self.assertFalse(hasattr(orchestrator_server, "SCENE_TOOLS"))
        self.assertFalse(hasattr(orchestrator_server, "ASSET_TOOLS"))

    def test_default_mcp_config_exposes_unified_tool_surface(self) -> None:
        config = json.loads(Path("config/mcp_config.example.json").read_text(encoding="utf-8"))
        servers = config["mcpServers"]

        self.assertIn("unreal-mcp", servers)
        self.assertEqual(servers["unreal-mcp"]["args"], ["-m", "unreal_mcp.slim_server"])
        for server in servers.values():
            self.assertNotEqual(server.get("args"), ["-m", "unreal_orchestrator.server"])

    def test_domain_design_includes_recommended_connection(self) -> None:
        result = orchestrator_server.get_domain_design("scene")

        self.assertTrue(result["success"])
        connection = result["design"]["recommended_connection"]
        self.assertEqual(connection["command"], "python")
        self.assertEqual(connection["args"], ["-m", "unreal_scene.server"])
        self.assertTrue(connection["requires_editor_ready"])

    def test_material_graph_design_marks_direct_read_as_unguarded(self) -> None:
        result = orchestrator_server.get_domain_design("material_graph")

        self.assertTrue(result["success"])
        connection = result["design"]["recommended_connection"]
        self.assertTrue(connection["requires_editor_ready"])
        self.assertFalse(connection["read_only_tools_require_editor_ready"])
        self.assertIn("get_material_graph", connection["unguarded_read_tools"])

    def test_make_guarded_tool_preserves_signature(self) -> None:
        import inspect
        from unreal_harness_runtime.editor_guard import make_guarded_tool
        from unreal_scene.tools import create_spot_light_ring

        guarded = make_guarded_tool("scene.create_spot_light_ring", create_spot_light_ring)
        sig = inspect.signature(guarded)
        params = list(sig.parameters.keys())

        self.assertEqual(guarded.__name__, "create_spot_light_ring")
        self.assertIn("center", params)
        self.assertIn("wait_for_ready", params)
        self.assertIn("ready_timeout_seconds", params)
        self.assertIn("ready_poll_seconds", params)
        self.assertTrue(params.index("wait_for_ready") > params.index("replace_existing"))

    def test_domain_servers_export_tools_list(self) -> None:
        from unreal_scene import server as scene_server
        from unreal_asset import server as asset_server
        from unreal_blueprint import server as blueprint_server
        from unreal_material import server as material_server
        from unreal_material_graph import server as material_graph_server
        from unreal_renderdoc import server as renderdoc_server
        from unreal_diagnostics import server as diagnostics_server

        self.assertEqual(len(scene_server.TOOLS), 12)
        self.assertEqual(len(asset_server.TOOLS), 19)
        self.assertEqual(len(blueprint_server.TOOLS), 10)
        self.assertEqual(len(material_server.TOOLS), 10)
        self.assertEqual(len(material_graph_server.TOOLS), 7)
        self.assertEqual(len(renderdoc_server.TOOLS), 12)
        self.assertEqual(len(diagnostics_server.TOOLS), 10)

    def test_unified_mcp_server_includes_all_domain_tools(self) -> None:
        from unreal_mcp import server as mcp_server

        domain_names = {
            t.__name__ for t in mcp_server.TOOLS
        }
        self.assertIn("create_asset_with_properties", domain_names)
        self.assertIn("create_material_asset", domain_names)
        self.assertIn("set_scene_light_intensity", domain_names)
        self.assertIn("add_blueprint_node", domain_names)
        self.assertIn("get_material_graph", domain_names)
        self.assertIn("patch_material_graph", domain_names)
        self.assertIn("request_renderdoc_capture", domain_names)
        self.assertIn("get_editor_ready_state", domain_names)
        self.assertEqual(len(mcp_server.TOOLS), 79)

    def test_slim_mcp_server_exposes_small_discovery_surface(self) -> None:
        from unreal_mcp import slim_server

        tool_names = {tool.__name__ for tool in slim_server.TOOLS}

        self.assertLessEqual(len(slim_server.TOOLS), 12)
        self.assertIn("get_harness_domains", tool_names)
        self.assertIn("get_domain_design", tool_names)
        self.assertIn("route_harness_task", tool_names)
        self.assertIn("get_editor_ready_state", tool_names)
        self.assertIn("get_token_usage_summary", tool_names)
        self.assertNotIn("create_asset_with_properties", tool_names)

    def test_read_result_handle_pages_nested_list_with_fields(self) -> None:
        from unreal_orchestrator.result_store import store_result

        stored = store_result(
            {
                "status": "success",
                "result": {
                    "nodes": [
                        {"name": "N0", "type": "Constant", "extra": 0},
                        {"name": "N1", "type": "Multiply", "extra": 1},
                        {"name": "N2", "type": "Lerp", "extra": 2},
                    ]
                },
            }
        )

        result = backend_tools.read_result_handle(
            stored["result_handle"],
            path="result.nodes",
            offset=1,
            limit=2,
            fields=["name"],
        )

        self.assertTrue(result["success"])
        self.assertEqual(result["path"], "result.nodes")
        self.assertEqual(result["total_count"], 3)
        self.assertEqual(result["returned_count"], 2)
        self.assertEqual(result["result"], [{"name": "N1"}, {"name": "N2"}])


if __name__ == "__main__":
    unittest.main()
