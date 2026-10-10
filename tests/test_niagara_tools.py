from unittest.mock import patch

from unreal_niagara import tools


def native_ok():
    return {"success": True, "fail_count": 0, "results": [{"success": True}]}


def readback(bindings):
    return {"success": True, "renderers": [{"index": 0, "property_bindings": bindings}]}


def test_reject_invalid_index_without_transport():
    with patch.object(tools, "_native") as native:
        result = tools.set_niagara_component_binding('/Game/Test', 'Light', 'Param', 'Particles.Param', -1)
        assert not result['success']
        native.assert_not_called()


def test_aggregate_success_does_not_hide_native_operation_failure():
    response = {"success": True, "fail_count": 1, "results": [{"success": False, "error": "Wrong type"}]}
    with patch.object(tools, "_native", return_value=response), patch.object(tools, "run_editor_python") as save:
        result = tools.set_niagara_component_binding('/Game/Test', 'Light', 'Param', 'Particles.Param')
        assert not result['success'] and result['error'] == 'Wrong type'
        save.assert_not_called()


def test_save_failure_reports_applied_but_not_verified():
    with patch.object(tools, "_native", return_value=native_ok()), patch.object(tools, "run_editor_python", return_value={"success": False}):
        result = tools.set_niagara_component_binding('/Game/Test', 'Light', 'Param', 'Particles.Param')
        assert result['applied'] and not result['success']
        assert not result['verification']['verified']


def test_readback_requires_exactly_one_resolved_binding():
    binding = {"property": "Param", "attribute": "Particles.Param", "setter": "SetParam", "attribute_exists": True}
    for bindings, expected in [([binding], True), ([binding, binding], False), ([], False), ([dict(binding, attribute_exists=False)], False), ([dict(binding, setter='Wrong')], False)]:
        with patch.object(tools, "_native", return_value=native_ok()), patch.object(tools, "get_niagara_renderers", return_value=readback(bindings)):
            result = tools.set_niagara_component_binding('/Game/Test', 'Light', 'Param', 'Particles.Param', setter='SetParam', save=False)
            assert result['success'] is expected
            assert result['verification']['verified'] is expected


def test_missing_emitter_is_an_error():
    with patch.object(tools, "_native", return_value={"success": True, "emitters": []}):
        assert not tools.get_niagara_renderers('/Game/Test', 'Missing')['success']


def test_renderer_read_survives_server_response_compaction():
    from unreal_harness_runtime.editor_guard import _summarize_result
    native = {"success": True, "emitters": [{"name": "Light", "renderers": [{"type": "NiagaraComponentRenderer", "property_bindings": []}]}]}
    with patch.object(tools, "_native", return_value=native):
        result = _summarize_result(tools.get_niagara_renderers('/Game/Test', 'Light'))
        assert result['post_state']['renderers'][0]['type'] == 'NiagaraComponentRenderer'
