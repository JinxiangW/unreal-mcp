"""Verify or repair samplers on texture objects as well as texture sample nodes."""
from unreal_harness_runtime.python_exec import run_editor_python, wrap_editor_python, python_literal
from .tools import get_material_graph


def sync_material_texture_samplers(material_path: str, repair: bool = False) -> dict:
    """Match graph texture samplers to UE compression/sRGB/data-group settings.

    Includes TextureObject/TextureObjectParameter, which the native graph reader
    currently omits sampler_type for. Reports native property readback. A repair
    recompiles and saves the material. Instance texture overrides are not changed.
    """
    graph = get_material_graph(material_path)
    if not graph.get('success'):
        return graph
    names = [n['name'] for n in graph.get('nodes', []) if n.get('texture_path')]
    body = f'''
material = unreal.load_asset({python_literal(material_path)})
if not isinstance(material, unreal.Material):
    raise RuntimeError('Expected Material')
items = []
pending = []
for name in {python_literal(names)}:
    node = unreal.find_object(material, name)
    if not isinstance(node, unreal.MaterialExpressionTextureBase):
        raise RuntimeError('Expected texture expression: ' + name)
    texture = node.get_editor_property('texture')
    if texture is None:
        raise RuntimeError('Missing texture: ' + name)
    compression = texture.get_editor_property('compression_settings').name
    srgb = texture.get_editor_property('srgb')
    group = texture.get_editor_property('lod_group').name
    virtual = texture.get_editor_property('virtual_texture_streaming')
    kind = {{'TC_NORMALMAP':'NORMAL', 'TC_ALPHA':'ALPHA', 'TC_MASKS':'MASKS',
             'TC_DISTANCE_FIELD_FONT':'DISTANCE_FIELD_FONT'}}.get(compression)
    if compression == 'TC_GRAYSCALE': kind = 'GRAYSCALE' if srgb else 'LINEAR_GRAYSCALE'
    if kind is None: kind = 'COLOR' if srgb else 'LINEAR_COLOR'
    if virtual and kind != 'DISTANCE_FIELD_FONT': kind = 'VIRTUAL_' + kind
    if group in ('TEXTUREGROUP_8BIT_DATA', 'TEXTUREGROUP_16BIT_DATA'): kind = 'DATA'
    expected = getattr(unreal.MaterialSamplerType, 'SAMPLERTYPE_' + kind)
    before = node.get_editor_property('sampler_type')
    pending.append((node, expected))
    items.append(dict(node=name, texture=texture.get_path_name(), compression=compression,
                      srgb=srgb, before=before.name, expected=expected.name))
changed = sum(node.get_editor_property('sampler_type') != expected for node, expected in pending)
if {repair!r} and changed:
    material.modify()
    for node, expected in pending:
        node.set_editor_property('sampler_type', expected)
    unreal.MaterialEditingLibrary.recompile_material(material)
    if not unreal.EditorAssetLibrary.save_loaded_asset(material):
        raise RuntimeError('Material save failed')
for item, (node, expected) in zip(items, pending):
    actual = node.get_editor_property('sampler_type')
    item.update(actual=actual.name, success=actual == expected)
ok = all(item['success'] for item in items)
_mcp_emit(dict(success=ok, summary=dict(requested=len(items), mismatches_before=changed,
          repaired=changed if {repair!r} else 0), items=items,
          post_state={{item['node']:item['actual'] for item in items}},
          verification=dict(verified=ok, mode='native_sampler_property_readback')))
'''
    return run_editor_python(wrap_editor_python(body))
