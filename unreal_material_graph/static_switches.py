"""Native StaticSwitchParameter inputs when the graph recipe lacks this type."""
from unreal_harness_runtime.python_exec import run_editor_python,wrap_editor_python,python_literal
from .tools import get_material_graph


def ensure_material_static_switch_inputs(material_path: str,target_node_name: str,
        true_node_name: str,false_node_name: str,switches: dict[str,bool]) -> dict:
    """Connect compile-time 1/0 selectors to named inputs of an existing node.

    The caller supplies existing true/false expressions. Existing parameters
    are reused by name. Compile, save and verify the resulting graph links.
    """
    if not switches or not all(isinstance(k,str) and k and isinstance(v,bool) for k,v in switches.items()):
        return {'success':False,'error':'Expected nonempty name-to-bool switches'}
    graph=get_material_graph(material_path)
    if not graph.get('success'):return graph
    names=[n['name'] for n in graph.get('nodes',[]) if n['type']=='StaticSwitchParameter']
    body=f'''
material=unreal.load_asset({python_literal(material_path)})
target=unreal.find_object(material,{python_literal(target_node_name)})
yes=unreal.find_object(material,{python_literal(true_node_name)})
no=unreal.find_object(material,{python_literal(false_node_name)})
if not all([material,target,yes,no]):raise RuntimeError('Missing material or expression')
values={python_literal(switches)}
available={{str(n) for n in unreal.MaterialEditingLibrary.get_material_expression_input_names(target)}}
if not set(values).issubset(available):raise RuntimeError('Unknown target inputs')
existing={{}}
for name in {python_literal(names)}:
    node=unreal.find_object(material,name)
    existing[str(node.get_editor_property('parameter_name'))]=node
items=[]
for i,(name,value) in enumerate(values.items()):
    node=existing.get(name)
    if node is None:
        node=unreal.MaterialEditingLibrary.create_material_expression(material,unreal.MaterialExpressionStaticSwitchParameter,400,2200+i*300)
    node.set_editor_property('parameter_name',name)
    node.set_editor_property('group','Compile Options')
    node.set_editor_property('default_value',value)
    for source,pin in [(yes,'True'),(no,'False')]:
        if not unreal.MaterialEditingLibrary.connect_material_expressions(source,'',node,pin):raise RuntimeError('Switch input failed')
    if not unreal.MaterialEditingLibrary.connect_material_expressions(node,'',target,name):raise RuntimeError('Switch output failed')
    items.append(dict(name=name,node_name=node.get_name(),default_value=bool(node.get_editor_property('default_value'))))
unreal.MaterialEditingLibrary.recompile_material(material)
if not unreal.EditorAssetLibrary.save_loaded_asset(material,only_if_is_dirty=False):raise RuntimeError('Save failed')
_mcp_emit(dict(success=True,items=items))
'''
    result=run_editor_python(wrap_editor_python(body))
    if not result.get('success'):return result
    after=get_material_graph(material_path)
    if not after.get('success'):return after
    ids={n['name']:n['node_id'] for n in after['nodes']};target_id=ids[target_node_name]
    checks=[]
    for item in result['items']:
        ok=any(c['source']==ids[item['node_name']] and c['target']==target_id and c['target_input']==item['name'] for c in after['connections'])
        checks.append(dict(name=item['name'],connected=ok,default_verified=item['default_value']==switches[item['name']]))
    ok=all(c['connected'] and c['default_verified'] for c in checks)
    result.update(success=ok,summary=dict(requested=len(checks),succeeded=sum(c['connected'] and c['default_verified'] for c in checks)),
                  post_state={i['name']:i for i in result['items']},verification=dict(verified=ok,checks=checks))
    return result
