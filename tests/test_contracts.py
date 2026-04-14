import unittest
from pathlib import Path
from unittest.mock import patch
import importlib
import json
import tempfile
import tomllib

from unreal_asset import tools as asset_tools
from unreal_diagnostics import tools as diagnostics_tools
from unreal_harness_runtime import config as runtime_config
from unreal_material import tools as material_tools
from unreal_material_graph import tools as material_graph_tools
from unreal_orchestrator import server as orchestrator_server
from unreal_renderdoc import tools as renderdoc_tools


class AssetToolContractTests(unittest.TestCase):
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
                    }
                ],
                "total_count": 1,
                "returned_count": 1,
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
        texture = result["textures"][0]
        self.assertEqual(
            texture["properties"]["compression_settings"]["name"], "TC_NORMALMAP"
        )
        self.assertFalse(texture["properties"]["srgb"])

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


class MaterialGraphContractTests(unittest.TestCase):
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
        mock_latest_project_log.return_value = Path("D:/Logs/RenderingMCP.log")
        mock_parse_log_context.return_value = {
            "log_path": "D:/Logs/RenderingMCP.log",
            "rhi_name": "D3D12",
            "shader_platform": "PCD3D_SM6",
            "feature_level": "SM6",
        }
        mock_get_project_path.return_value = Path("D:/Projects/RenderingMCP/RenderingMCP.uproject")
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
        self.assertEqual(context["engine"]["project"], "RenderingMCP")
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

    def test_orchestrator_default_tools_include_asset_and_material_workflows(self) -> None:
        importlib.reload(orchestrator_server)
        tool_names = {tool.__name__ for tool in orchestrator_server.DEFAULT_TOOLS}

        self.assertIn("create_asset_with_properties", tool_names)
        self.assertIn("update_asset_properties", tool_names)
        self.assertIn("import_texture_asset", tool_names)
        self.assertIn("create_material_asset", tool_names)
        self.assertIn("query_textures", tool_names)
        self.assertIn("get_asset_properties", tool_names)


if __name__ == "__main__":
    unittest.main()
