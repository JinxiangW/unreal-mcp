"""Exercise generated editor code with a texture object, not just a sample node."""
import json
import sys
from types import SimpleNamespace
from unittest.mock import patch
from unreal_material_graph.samplers import sync_material_texture_samplers


def test_sampler_repair_reads_native_object_property_and_is_idempotent(capsys):
    color=SimpleNamespace(name='SAMPLERTYPE_COLOR')
    linear=SimpleNamespace(name='SAMPLERTYPE_LINEAR_COLOR')
    class Texture:
        def get_editor_property(self, name):
            return {'compression_settings':SimpleNamespace(name='TC_HDR_COMPRESSED'),
                    'srgb':False,'lod_group':SimpleNamespace(name='TEXTUREGROUP_WORLD'),
                    'virtual_texture_streaming':False}[name]
        def get_path_name(self): return '/Game/Depth'
    class Node:
        sampler=color
        def get_editor_property(self, name): return Texture() if name=='texture' else self.sampler
        def set_editor_property(self, name, value): self.sampler=value
    class Material:
        def modify(self): pass
    node=Node();material=Material();compiled=[];saved=[]
    ue=SimpleNamespace(Material=Material,MaterialExpressionTextureBase=Node,
        MaterialSamplerType=SimpleNamespace(SAMPLERTYPE_COLOR=color,SAMPLERTYPE_LINEAR_COLOR=linear),
        load_asset=lambda p:material,find_object=lambda m,n:node,
        MaterialEditingLibrary=SimpleNamespace(recompile_material=lambda m:compiled.append(m)),
        EditorAssetLibrary=SimpleNamespace(save_loaded_asset=lambda m:saved.append(m) or True),
        SystemLibrary=SimpleNamespace(collect_garbage=lambda:None))
    def run(code):
        exec(code,{})
        return json.loads(capsys.readouterr().out.split('__UNREAL_MCP_JSON__:')[-1])
    graph={'success':True,'nodes':[{'name':'TextureObjectParameter_0','texture_path':'/Game/Depth'}]}
    with patch.dict(sys.modules,{'unreal':ue}),patch('unreal_material_graph.samplers.get_material_graph',return_value=graph),patch('unreal_material_graph.samplers.run_editor_python',side_effect=run):
        before=sync_material_texture_samplers('/Game/M')
        assert not before['success'] and not compiled and not saved
        after=sync_material_texture_samplers('/Game/M',repair=True)
        assert after['success'] and after['summary']['repaired']==1
        assert after['items'][0]['actual']=='SAMPLERTYPE_LINEAR_COLOR'
        again=sync_material_texture_samplers('/Game/M',repair=True)
        assert again['success'] and again['summary']['repaired']==0
        assert len(compiled)==len(saved)==1
