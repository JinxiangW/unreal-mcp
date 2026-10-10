"""Read native compiled material statistics for automated shader validation."""
from typing import Any
from unreal_harness_runtime.python_exec import run_editor_python,wrap_editor_python,python_literal


def get_material_statistics(asset_paths: list[str]) -> dict[str, Any]:
    """Read UE shader instruction/sample counts. Zero instructions are not a compile pass.

    This does not recompile or claim to enumerate shader errors; use alongside
    material graph readback, log checks and an actual render.
    """
    if not 1<=len(asset_paths)<=32:
        return {'success':False,'error':'Expected 1-32 material paths'}
    body=f'''
items=[]
for path in {python_literal(asset_paths)}:
    material=unreal.EditorAssetLibrary.load_asset(path)
    if not isinstance(material,unreal.MaterialInterface):
        items.append({{'path':path,'success':False,'error':'Expected MaterialInterface'}})
        continue
    stats=unreal.MaterialEditingLibrary.get_statistics(material)
    fields=['num_vertex_shader_instructions','num_pixel_shader_instructions','num_samplers','num_vertex_texture_samples','num_pixel_texture_samples','num_uv_scalars','num_interpolator_scalars']
    values={{f:stats.get_editor_property(f) for f in fields}}
    items.append({{'path':path,'success':True,'statistics':values,'compiled_pixel_shader_present':values['num_pixel_shader_instructions']>0}})
_mcp_emit({{'success':all(i['success'] for i in items),'items':items}})
'''
    return run_editor_python(wrap_editor_python(body))
