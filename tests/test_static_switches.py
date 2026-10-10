import json,sys
from types import SimpleNamespace
from unittest.mock import patch
from unreal_material.static_switches import set_material_instance_static_switches
from unreal_material_graph.static_switches import ensure_material_static_switch_inputs


def test_static_overrides_use_native_permutation_update_and_readback(capsys):
    class Instance: pass
    instance=Instance();values={'UseHierarchy':False,'UseBilinear':False};writes=[];updates=[];saves=[]
    def setter(obj,name,value,update_material_instance):
        assert obj is instance and update_material_instance is False
        values[name]=value;writes.append(name);return False  # UE 5.6 return-value defect
    ue=SimpleNamespace(MaterialInstanceConstant=Instance,load_asset=lambda p:instance,
        MaterialEditingLibrary=SimpleNamespace(get_static_switch_parameter_names=lambda i:list(values),
            set_material_instance_static_switch_parameter_value=setter,update_material_instance=lambda i:updates.append(i),
            get_material_instance_static_switch_parameter_value=lambda i,n:values[n]),
        EditorAssetLibrary=SimpleNamespace(save_loaded_asset=lambda i,only_if_is_dirty:saves.append(i) or True),
        SystemLibrary=SimpleNamespace(collect_garbage=lambda:None))
    def run(code):
        exec(code,{})
        return json.loads(capsys.readouterr().out.split('__UNREAL_MCP_JSON__:')[-1])
    with patch.dict(sys.modules,{'unreal':ue}),patch('unreal_material.static_switches.run_editor_python',side_effect=run):
        r=set_material_instance_static_switches('/Game/MI',{'UseHierarchy':True,'UseBilinear':True})
        assert r['success'] and r['post_state']==values
        assert len(writes)==2 and len(updates)==len(saves)==1
        bad=set_material_instance_static_switches('/Game/MI',{'Unknown':True})
        assert not bad['success'] and len(writes)==2


def test_non_bool_static_values_are_rejected_before_editor_execution():
    with patch('unreal_material.static_switches.run_editor_python') as run:
        assert not set_material_instance_static_switches('/Game/MI',{'Switch':'false'})['success']
        run.assert_not_called()


def test_static_graph_inputs_require_boolean_defaults():
    with patch('unreal_material_graph.static_switches.get_material_graph') as read:
        assert not ensure_material_static_switch_inputs('/Game/M','Trace','One','Zero',{'UseHierarchy':1})['success']
        read.assert_not_called()


def test_static_graph_repair_requires_correct_readback_connection():
    before={'success':True,'nodes':[]}
    after={'success':True,'nodes':[{'name':'Trace','node_id':'t'},{'name':'Switch','node_id':'s'}],
           'connections':[{'source':'s','target':'t','target_input':'WrongInput'}]}
    with patch('unreal_material_graph.static_switches.get_material_graph',side_effect=[before,after]),patch(
        'unreal_material_graph.static_switches.run_editor_python',return_value={'success':True,'items':[{'name':'UseHierarchy','node_name':'Switch','default_value':True}]}) as run:
        result=ensure_material_static_switch_inputs('/Game/M','Trace','One','Zero',{'UseHierarchy':True})
    assert not result['success'] and not result['verification']['verified']
    assert "[(yes,'True'),(no,'False')]" in run.call_args[0][0]
