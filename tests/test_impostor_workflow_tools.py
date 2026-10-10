"""Regressions exposed by a real layered-depth material/asset workflow."""
from types import SimpleNamespace
from unittest.mock import patch
import json

from unreal_material_graph import tools as graph
from unreal_asset import import_batch
from unreal_scene.preview import render_static_mesh_preview


def test_parameter_readback_defaults_can_be_reused_in_creation_recipe():
    scalar=graph._normalize_recipe_node_schema({'type':'ScalarParameter','default_value':512})
    vector=graph._normalize_recipe_node_schema({'type':'VectorParameter','default_value':[.1,.2,.3,1]})
    explicit=graph._normalize_recipe_node_schema({'type':'ScalarParameter','default_value':512,'value':8})
    assert scalar['value']==512
    assert vector['value']==[.1,.2,.3,1]
    assert explicit['value']==8
    assert graph._normalize_recipe_node_schema({'type':'MaterialExpressionCameraVectorWS'})['type']=='CameraVector'


def test_rebuild_removes_old_edges_and_preserves_summary_property_count():
    path='/Game/Test/M_Rebuild'
    before={'success':True,'asset_path':path,'node_count':2,'connection_count':1,
            'connections':[{'source':'old1','target':'old2','target_input':'A'}],
            'property_connections':{'EmissiveColor':{'node_id':'old2','output_index':0}}}
    after={'success':True,'asset_path':path,'node_count':2,'connection_count':1,
           'property_connections':['EmissiveColor'],'property_connection_count':1}
    built={'status':'success','result':{'success':True,'node_count':2,'connection_count':2}}
    with patch.object(graph,'analyze_material_graph',side_effect=[before,after]),patch.object(graph,'build_material_graph',return_value=built):
        result=graph.create_material_graph_recipe(path,
            nodes=[{'id':'new1','type':'Constant','value':1},{'id':'new2','type':'Multiply'}],
            delete_nodes=['old1','old2'],
            connections=[{'source':'new1','target':'new2','target_input':'A'}],
            property_connections={'EmissiveColor':{'node_id':'new2','output_index':0}})
    assert result['success'],result.get('verification')
    assert result['verification']['verified']


def test_commandlet_reads_log_when_python_print_is_absent_from_stdout(tmp_path):
    project=tmp_path/'Project.uproject'
    def run(*args,**kwargs):
        log=tmp_path/'Saved/MCPImports/import_batch.log'
        log.write_text('LogPython: __UNREAL_MCP_JSON__:'+json.dumps({'success':True,'items':[{'saved':True}]}))
        return SimpleNamespace(stdout='script executed successfully',stderr='',returncode=0)
    with patch.object(import_batch,'get_project_path',return_value=project),patch.object(import_batch,'get_engine_root_path',return_value=tmp_path/'Engine'),patch.object(import_batch.subprocess,'run',side_effect=run):
        result=import_batch._run_import_commandlet('print("test")')
    assert result['success'] and result['items'][0]['saved']


def test_invalid_import_and_capture_requests_do_not_touch_editor():
    with patch.object(import_batch,'_run_import_commandlet') as execute:
        assert not import_batch.import_assets_batch([], '/Game/Test')['success']
        assert not import_batch.import_assets_batch([{'name':'A','source_path':'missing.exr'}], '/Game/Test')['success']
        execute.assert_not_called()
    assert not render_static_mesh_preview('/Game/A','/Game/B','relative.png')['success']
