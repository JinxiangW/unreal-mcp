"""Isolated, bounded asset imports with explicit settings and saved-state readback."""
from pathlib import Path
import json
import re
import subprocess
import tempfile
from typing import Any
from unreal_harness_runtime.python_exec import run_editor_python, wrap_editor_python, python_literal
from .tools import _ASSET_COERCE_PYTHON_HELPERS
from unreal_harness_runtime.config import get_engine_root_path, get_project_path
from unreal_harness_runtime.commandlet_exec import _extract_marker_payload


def _run_import_commandlet(code: str) -> dict[str, Any]:
    # Interchange's synchronous wait pumps TaskGraph. Running it from the live
    # MCP game-thread task can assert RecursionGuard; keep imports isolated.
    project = get_project_path()
    logs = project.parent / 'Saved/MCPImports'
    logs.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='ue_import_') as directory:
        script = Path(directory) / 'import_batch.py'
        script.write_text(code, encoding='utf-8')
        editor = get_engine_root_path() / 'Binaries/Win64/UnrealEditor-Cmd.exe'
        command = [str(editor), str(project), '-run=PythonScript', '-Script='+script.as_posix(),
                   '-unattended', '-nop4', '-nosplash', '-nosound', '-NullRHI',
                   '-abslog='+str(logs/'import_batch.log')]
        completed = subprocess.run(command, capture_output=True, text=True, encoding='utf-8',
                                   errors='replace', timeout=1800, shell=False,
                                   creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        output = completed.stdout + '\n' + completed.stderr
        (logs/'import_batch_stdout.log').write_text(output, encoding='utf-8')
        log_path = logs/'import_batch.log'
        log_output = log_path.read_text(encoding='utf-8',errors='replace') if log_path.exists() else ''
        result = _extract_marker_payload(output+'\n'+log_output)
        result['exit_code'] = completed.returncode
        result['log_path'] = str(logs/'import_batch.log')
        if completed.returncode != 0:
            result['success'] = False
            result.setdefault('error', f'Commandlet exited with {completed.returncode}')
        return result


def import_assets_batch(items: list[dict[str, Any]], destination_path: str, replace_existing: bool = False) -> dict[str, Any]:
    """Import 1-16 texture/FBX files in an isolated commandlet and verify properties.

    Each item has source_path, name, optional properties. FBX uses static-mesh
    import with textures/materials/collision generation disabled. Existing assets
    are rejected unless replace_existing is explicitly true.
    """
    if not 1 <= len(items) <= 16:
        return {'success': False, 'error': 'Expected 1-16 items'}
    if not re.fullmatch(r'/Game(?:/[A-Za-z0-9_]+)+', destination_path):
        return {'success': False, 'error': 'Expected a /Game package directory'}
    names = set()
    for item in items:
        p = Path(item.get('source_path', ''))
        name = item.get('name', '')
        if not p.is_file() or p.suffix.lower() not in ('.fbx','.png','.exr','.tga','.hdr','.tif','.tiff','.dds'):
            return {'success': False, 'error': f'Unsupported or missing source: {p}'}
        if not re.fullmatch(r'[A-Za-z0-9_]+', name) or name in names:
            return {'success': False, 'error': f'Invalid or duplicate name: {name}'}
        names.add(name)
    body = _ASSET_COERCE_PYTHON_HELPERS + f'''
_base_simple = _mcp_to_simple
def _mcp_to_simple(value):
    raw = _base_simple(value)
    if isinstance(raw,str) and raw.startswith('<') and ':' in raw and '.' in raw:
        head, number = raw.strip('<>').split(':',1)
        try: return {{'name':head.rsplit('.',1)[-1], 'value':int(number.strip())}}
        except ValueError: pass
    return raw
items = {python_literal(items)}
destination = {python_literal(destination_path)}
replace = {replace_existing!r}
for item in items:
    target = destination + '/' + item['name']
    if unreal.EditorAssetLibrary.does_asset_exist(target) and not replace:
        raise RuntimeError('Asset already exists: ' + target)
results = []
for item in items:
    task = unreal.AssetImportTask()
    task.set_editor_property('filename', item['source_path'])
    task.set_editor_property('destination_path', destination)
    task.set_editor_property('destination_name', item['name'])
    task.set_editor_property('automated', True)
    task.set_editor_property('replace_existing', replace)
    task.set_editor_property('save', False)
    if item['source_path'].lower().endswith('.dds'):
        task.set_editor_property('factory',unreal.TextureFactory())
    if item['source_path'].lower().endswith('.fbx'):
        options = unreal.FbxImportUI()
        options.set_editor_property('import_mesh', True)
        options.set_editor_property('import_as_skeletal', False)
        options.set_editor_property('import_materials', False)
        options.set_editor_property('import_textures', False)
        options.set_editor_property('import_animations', False)
        options.set_editor_property('automated_import_should_detect_type', False)
        options.set_editor_property('mesh_type_to_import', unreal.FBXImportType.FBXIT_STATIC_MESH)
        data = options.get_editor_property('static_mesh_import_data')
        data.set_editor_property('combine_meshes', True)
        data.set_editor_property('auto_generate_collision', False)
        data.set_editor_property('generate_lightmap_u_vs', False)
        data.set_editor_property('normal_import_method', unreal.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS)
        task.set_editor_property('options', options)
    try:
        unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
        path = destination + '/' + item['name']
        asset = unreal.EditorAssetLibrary.load_asset(path)
        if asset is None:
            raise RuntimeError('No asset at requested path; imported=' + str(task.get_editor_property('imported_object_paths')))
        if item.get('expected_class') and asset.get_class().get_name()!=item['expected_class']:
            raise RuntimeError('Imported unexpected class: '+asset.get_class().get_name())
        actual = {{}}
        checks = []
        asset.modify()
        for field, expected in item.get('properties', {{}}).items():
            current = asset.get_editor_property(field)
            value = _mcp_coerce_like(current, expected)
            asset.set_editor_property(field, value)
            got = _mcp_to_simple(asset.get_editor_property(field))
            want = _mcp_to_simple(value)
            actual[field] = got
            checks.append({{'field': field, 'expected': want, 'actual': got, 'ok': got == want}})
        saved = bool(unreal.EditorAssetLibrary.save_loaded_asset(asset, only_if_is_dirty=False))
        checks.append({{'field': 'saved', 'expected': True, 'actual': saved, 'ok': saved}})
        ok = all(c['ok'] for c in checks)
        results.append({{'target': path, 'success': ok, 'class': asset.get_class().get_name(), 'post_state': actual, 'verification': {{'verified': ok, 'checks': checks}}}})
    except Exception as exc:
        results.append({{'target': destination+'/'+item['name'], 'success': False, 'error': str(exc)}})
good = sum(r['success'] for r in results)
_mcp_emit({{'success': good == len(results), 'domain': 'asset', 'summary': {{'requested': len(items), 'succeeded': good, 'failed': len(results)-good}}, 'items': results, 'post_state': {{r['target']: r.get('post_state',{{}}) for r in results}}, 'verification': {{'verified': good == len(results)}}}})
'''
    return _run_import_commandlet(wrap_editor_python(body))


def inspect_static_mesh(asset_path: str) -> dict[str, Any]:
    """Read bounds, LOD section/material counts and import sources for a StaticMesh."""
    body = f'''
asset = unreal.EditorAssetLibrary.load_asset({python_literal(asset_path)})
if not isinstance(asset, unreal.StaticMesh):
    raise RuntimeError('Expected StaticMesh')
b = asset.get_bounding_box()
vec = lambda v: [v.x,v.y,v.z]
lods = []
for i in range(asset.get_num_lods()):
    lods.append({{'lod':i,'sections':asset.get_num_sections(i),'triangles':asset.get_num_triangles(i)}})
materials = [{{'slot': str(s.material_slot_name), 'material': s.material_interface.get_path_name() if s.material_interface else None}} for s in asset.get_editor_property('static_materials')]
_mcp_emit({{'success': True, 'asset_path':asset.get_path_name(), 'bounds_min':vec(b.min), 'bounds_max':vec(b.max), 'lods':lods, 'materials':materials}})
'''
    return run_editor_python(wrap_editor_python(body))


def set_static_mesh_material(asset_path: str, material_path: str, slot: int = 0) -> dict[str, Any]:
    """Set a StaticMesh default material slot, save it, and verify the reference."""
    if slot < 0:
        return {'success':False,'error':'slot must be nonnegative'}
    body=f'''
mesh=unreal.EditorAssetLibrary.load_asset({python_literal(asset_path)})
material=unreal.EditorAssetLibrary.load_asset({python_literal(material_path)})
if not isinstance(mesh,unreal.StaticMesh) or not isinstance(material,unreal.MaterialInterface):
    raise RuntimeError('Expected StaticMesh and MaterialInterface')
if {slot}>=len(mesh.get_editor_property('static_materials')): raise RuntimeError('Invalid slot')
mesh.modify()
mesh.set_material({slot},material)
saved=unreal.EditorAssetLibrary.save_loaded_asset(mesh,only_if_is_dirty=False)
actual=mesh.get_material({slot}).get_path_name()
ok=bool(saved) and actual==material.get_path_name()
_mcp_emit({{'success':ok,'post_state':{{'material_path':actual,'slot':{slot}}},'verification':{{'verified':ok,'saved':bool(saved)}}}})
'''
    return run_editor_python(wrap_editor_python(body))
