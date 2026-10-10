from unittest.mock import patch
import pytest
from unreal_scene.preview import render_static_mesh_preview


@pytest.mark.parametrize('origin,expected',[(None,[0,0,-100000]),([0,0,0],[0,0,0]),([3,4,-1000],[3,4,-1000])])
def test_mesh_and_camera_share_the_requested_origin(tmp_path,origin,expected):
    with patch('unreal_scene.preview.run_editor_python',return_value={'success':False}) as run:
        render_static_mesh_preview('/Game/Mesh','/Game/Mat',str(tmp_path/'capture.png'),world_origin=origin)
    code=run.call_args[0][0]
    assert 'origin = unreal.Vector(*'+repr(expected)+')' in code
    assert 'location = origin + direction*' in code
    assert "'world_origin':"+repr(expected) in code


def test_invalid_origin_does_not_spawn_actors(tmp_path):
    with patch('unreal_scene.preview.run_editor_python') as run:
        r=render_static_mesh_preview('/Game/Mesh','/Game/Mat',str(tmp_path/'capture.png'),world_origin=[0,float('nan'),0])
    assert not r['success'];run.assert_not_called()
