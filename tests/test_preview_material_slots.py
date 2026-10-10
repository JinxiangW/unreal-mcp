from unittest.mock import patch
import ast
from unreal_scene.preview import render_static_mesh_preview


def test_default_material_slots_are_not_overridden(tmp_path):
    with patch('unreal_scene.preview.run_editor_python',return_value={'success':True}) as call:
        render_static_mesh_preview('/Game/Mesh',None,str(tmp_path/'capture.png'))
    code=call.call_args.args[0]
    assert 'override_path = None' in code
    tree=ast.parse(code)
    guarded=[n for n in ast.walk(tree) if isinstance(n,ast.If) and ast.unparse(n.test)=='material is not None']
    assert any(isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr=='set_material' for guard in guarded for n in ast.walk(guard))
    assert "'material_slots':" in code
    compile(code,'preview','exec')
