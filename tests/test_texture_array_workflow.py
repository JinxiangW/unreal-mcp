"""Raw DDS array layout and safety regressions for authored-mip import."""
import struct
import json
from pathlib import Path
from unittest.mock import patch
import pytest
from unreal_asset.texture_array import write_array_dds,read_dds_metadata,import_texture_arrays,inspect_texture_arrays


def test_dds_reorders_mip_major_input_into_slice_major_chains(tmp_path):
    mip0=tmp_path/'m0.bin';mip1=tmp_path/'m1.bin';target=tmp_path/'test.dds'
    mip0.write_bytes(bytes(range(32)));mip1.write_bytes(bytes(range(100,108)))
    info=write_array_dds(str(target),2,2,2,'RGBA8',[str(mip0),str(mip1)])
    assert info=={'width':2,'height':2,'mips':2,'slices':2,'dxgi_format':28,'dimension':3,'payload_bytes':40}
    assert target.read_bytes()[148:]==bytes(range(16))+bytes(range(100,104))+bytes(range(16,32))+bytes(range(104,108))


def test_dds_rejects_truncated_mip_before_writing_target(tmp_path):
    raw=tmp_path/'raw.bin';raw.write_bytes(b'123')
    target=tmp_path/'invalid.dds'
    with pytest.raises(ValueError,match='expected'):
        write_array_dds(str(target),4,4,3,'R32F',[str(raw)])
    assert not target.exists()


def test_single_slice_array_is_rejected_before_creating_wrong_ue_asset(tmp_path):
    manifest=tmp_path/'manifest.json'
    manifest.write_text(json.dumps({'destination_path':'/Game/Test','items':[{'name':'A','slices':1}]}))
    with patch('unreal_asset.texture_array.import_assets_batch') as importer:
        result=import_texture_arrays(str(manifest))
        assert not result['success'] and 'two slices' in result['error']
        importer.assert_not_called()


def test_array_inspection_never_calls_unsupported_native_dds_exporter(tmp_path):
    with patch('unreal_asset.texture_array.run_editor_python',return_value={'success':True,'items':[]}) as run:
        inspect_texture_arrays(['/Game/Test/Array'])
    code=run.call_args[0][0]
    assert 'TextureExporterDDS' not in code and 'run_asset_export_task' not in code
    assert 'Texture2DArray' in code


def test_texture_parameter_readback_compares_canonical_loaded_paths():
    from unreal_material.tools import update_material_instance_parameters_and_verify
    with patch('unreal_material.tools.run_editor_python',return_value={'success':True,'verification':[]}) as run:
        update_material_instance_parameters_and_verify('/Game/Test/MI',texture_parameters={'Array':'/Game/Test/Array'})
    code=run.call_args[0][0]
    assert 'actual_path == expected_path' in code
    assert 'expected_path = unreal.EditorAssetLibrary.get_path_name_for_loaded_asset(texture)' in code
