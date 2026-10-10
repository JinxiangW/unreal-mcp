"""Linear material render-target output for GPU data probes (no scene/tonemapper)."""
from pathlib import Path
from typing import Any
from unreal_harness_runtime.python_exec import run_editor_python,wrap_editor_python,python_literal


def render_material_data(material_path: str, output_path: str, width: int = 256, height: int = 256) -> dict[str, Any]:
    """Draw a material to linear RGBA8 PNG. Encode float bits in RGB for exact probes."""
    output=Path(output_path)
    if not output.is_absolute() or output.suffix.lower()!='.png' or not (1<=width<=4096 and 1<=height<=4096):
        return {'success':False,'error':'Expected absolute PNG and dimensions 1-4096'}
    output.parent.mkdir(parents=True,exist_ok=True)
    output.unlink(missing_ok=True)
    body=f'''
material=unreal.EditorAssetLibrary.load_asset({python_literal(material_path)})
if not isinstance(material,unreal.MaterialInterface):raise RuntimeError('Expected material')
world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
rt=unreal.RenderingLibrary.create_render_target2d(world,{width},{height},unreal.TextureRenderTargetFormat.RTF_RGBA8)
try:
    rt.set_editor_property('target_gamma',1.0)
    unreal.RenderingLibrary.draw_material_to_render_target(world,rt,material)
    unreal.RenderingLibrary.export_render_target(world,rt,{python_literal(str(output.parent))},{python_literal(output.name)})
    _mcp_emit({{'success':True,'output_path':{python_literal(str(output))},'width':{width},'height':{height}}})
finally:
    unreal.RenderingLibrary.release_render_target2d(rt)
'''
    result=run_editor_python(wrap_editor_python(body))
    if result.get('success'):
        result['success']=output.exists() and output.stat().st_size>0
    return result
