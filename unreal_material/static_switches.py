"""Verified native static-switch overrides; these compile material permutations."""
from unreal_harness_runtime.python_exec import run_editor_python,wrap_editor_python,python_literal


def set_material_instance_static_switches(instance_path: str, switches: dict[str,bool]) -> dict:
    if not switches or not all(isinstance(k,str) and k and isinstance(v,bool) for k,v in switches.items()):
        return {'success':False,'error':'Expected nonempty name-to-bool switches'}
    body=f'''
instance=unreal.load_asset({python_literal(instance_path)})
if not isinstance(instance,unreal.MaterialInstanceConstant):raise RuntimeError('Expected MaterialInstanceConstant')
values={python_literal(switches)}
names={{str(n) for n in unreal.MaterialEditingLibrary.get_static_switch_parameter_names(instance)}}
if not set(values).issubset(names):raise RuntimeError('Unknown switches: '+str(set(values)-names))
items=[]
for name,value in values.items():
    # UE 5.6's implementation initializes bResult=false and never sets it true.
    # Validate native state instead of treating that return value as failure.
    unreal.MaterialEditingLibrary.set_material_instance_static_switch_parameter_value(instance,name,value,update_material_instance=False)
    if bool(unreal.MaterialEditingLibrary.get_material_instance_static_switch_parameter_value(instance,name)) != value:
        raise RuntimeError('Static switch write failed: '+name)
unreal.MaterialEditingLibrary.update_material_instance(instance)
if not unreal.EditorAssetLibrary.save_loaded_asset(instance,only_if_is_dirty=False):raise RuntimeError('Save failed')
for name,value in values.items():
    actual=bool(unreal.MaterialEditingLibrary.get_material_instance_static_switch_parameter_value(instance,name))
    items.append(dict(name=name,expected=value,actual=actual,success=value==actual))
ok=all(i['success'] for i in items)
_mcp_emit(dict(success=ok,summary=dict(requested=len(items),succeeded=sum(i['success'] for i in items)),items=items,
          post_state={{i['name']:i['actual'] for i in items}},verification=dict(verified=ok,mode='native_static_permutation_readback')))
'''
    return run_editor_python(wrap_editor_python(body))
