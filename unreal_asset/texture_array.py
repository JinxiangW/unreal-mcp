"""Native DDS Texture2DArray creation, authored mip import and source inspection."""
from pathlib import Path
import json
import math
import struct
from typing import Any
from .import_batch import import_assets_batch
from unreal_harness_runtime.python_exec import run_editor_python, wrap_editor_python, python_literal

FORMATS = {'R32F': (41,4,'TC_SINGLE_FLOAT'),
           'RGBA8': (28,4,'TC_VECTOR_DISPLACEMENTMAP'),
           'RGBA32F': (2,16,'TC_HDR_F32')}


def read_dds_metadata(path: str) -> dict[str, Any]:
    p=Path(path)
    with p.open('rb') as f: header=f.read(148)
    if len(header)!=148 or header[:4]!=b'DDS ' or header[84:88]!=b'DX10':
        raise ValueError('Expected a DDS with DX10 header')
    h=struct.unpack_from('<31I',header,4)
    dxgi,dimension,misc,slices,alpha=struct.unpack_from('<5I',header,128)
    return {'width':h[3],'height':h[2],'mips':max(1,h[6]),'slices':slices,
            'dxgi_format':dxgi,'dimension':dimension,'payload_bytes':p.stat().st_size-148}


def write_array_dds(path: str, width: int, height: int, slices: int,
                    format: str, mip_files: list[str]) -> dict[str, Any]:
    """Input files are mip-major, each containing contiguous [slice,y,x,channels]."""
    if format not in FORMATS or not (1<=slices<=512 and 1<=width<=8192 and 1<=height<=8192):
        raise ValueError('Unsupported format or dimensions')
    if not 1<=len(mip_files)<=1+int(math.log2(max(width,height))):
        raise ValueError('Invalid mip count')
    dxgi,bpp,_=FORMATS[format]
    data=[]
    for mip,file in enumerate(mip_files):
        raw=Path(file).read_bytes();size=max(1,width>>mip)*max(1,height>>mip)*bpp
        if len(raw)!=size*slices: raise ValueError(f'Mip {mip}: expected {size*slices} bytes, got {len(raw)}')
        data.append((raw,size))
    flags=0x100F | (0x20000 if len(data)>1 else 0)
    caps=0x1000 | (0x8 if slices>1 or len(data)>1 else 0) | (0x400000 if len(data)>1 else 0)
    h=[124,flags,height,width,width*bpp,0,len(data)]+[0]*11
    h += [32,4,int.from_bytes(b'DX10','little'),0,0,0,0,0]
    h += [caps,0,0,0,0]
    target=Path(path);target.parent.mkdir(parents=True,exist_ok=True)
    with target.open('wb') as f:
        f.write(b'DDS '+struct.pack('<31I',*h)+struct.pack('<5I',dxgi,3,0,slices,0))
        # DDS stores one complete mip chain for each array slice.
        for s in range(slices):
            for raw,size in data:f.write(raw[s*size:(s+1)*size])
    return read_dds_metadata(str(target))


def import_texture_arrays(manifest_path: str, replace_existing: bool = False) -> dict[str, Any]:
    """Create native arrays with exact raw mips, import in one isolated process.

    Manifest: destination_path and items[{name,width,height,slices,format,mip_files}].
    Supported formats R32F/RGBA8/RGBA32F are uncompressed linear data, never streamed.
    DDS native array import requires 2-512 slices; a single slice imports as Texture2D.
    """
    try:
        manifest=Path(manifest_path);spec=json.loads(manifest.read_text(encoding='utf-8-sig'))
        if not 1<=len(spec['items'])<=16:raise ValueError('Expected 1-16 arrays')
        items=[];metadata={}
        for item in spec['items']:
            if item['slices']<2:raise ValueError('DDS array import requires at least two slices; use a Texture2D import for one slice')
            name=item['name']
            if not name.replace('_','').isalnum():raise ValueError('Invalid name')
            files=[str((manifest.parent/p).resolve()) for p in item['mip_files']]
            dds=manifest.parent/(name+'.dds')
            metadata[name]=write_array_dds(str(dds),item['width'],item['height'],item['slices'],item['format'],files)
            items.append({'name':name,'source_path':str(dds),'expected_class':'Texture2DArray',
                          'properties':{'compression_settings':FORMATS[item['format']][2], 'srgb':False,
                                        'mip_gen_settings':'TMGS_LEAVE_EXISTING_MIPS' if len(files)>1 else 'TMGS_NO_MIPMAPS',
                                        'filter':'TF_NEAREST','never_stream':True,'compression_no_alpha':False,
                                        'address_x':'TA_CLAMP','address_y':'TA_CLAMP','address_z':'TA_CLAMP'}})
        result=import_assets_batch(items,spec['destination_path'],replace_existing)
        result['source_arrays']=metadata
        return result
    except (OSError,ValueError,KeyError,TypeError) as exc:
        return {'success':False,'error':str(exc)}


def inspect_texture_arrays(asset_paths: list[str]) -> dict[str, Any]:
    """Read array settings and registry dimensions without using the DDS exporter.

    UE 5.6 FImageUtils::ExportTextureSourceToDDS asserts on Texture2DArray.
    Actual GPU dimensions, mip contents and formats require a shader probe/listtextures.
    """
    if not 1<=len(asset_paths)<=16:return {'success':False,'error':'Expected 1-16 arrays'}
    body=f'''
def simple(value):
    if isinstance(value,(str,int,float,bool)) or value is None:return value
    text=str(value)
    if text.startswith('<') and ':' in text:
        head,number=text.strip('<>').split(':',1)
        try:return {{'name':head.rsplit('.',1)[-1],'value':int(number.strip())}}
        except ValueError:pass
    return text
items=[]
for path in {python_literal(asset_paths)}:
    asset=unreal.EditorAssetLibrary.load_asset(path)
    if not isinstance(asset,unreal.Texture2DArray): raise RuntimeError('Expected Texture2DArray: '+path)
    props={{f:simple(asset.get_editor_property(f)) for f in ['compression_settings','srgb','mip_gen_settings','filter','never_stream','compression_no_alpha']}}
    data=unreal.EditorAssetLibrary.find_asset_data(path)
    tags={{}}
    for key in ['Dimensions','Format','NumSlices']:
        try: tags[key]=unreal.AssetRegistryHelpers.get_tag_value(data,key)
        except Exception: tags[key]=None
    items.append({{'path':path,'success':True,'class':asset.get_class().get_name(),'properties':props,'registry_tags':tags}})
ok=all(i['success'] for i in items)
_mcp_emit({{'success':ok,'summary':{{'requested':len(items),'succeeded':sum(i['success'] for i in items),'failed':sum(not i['success'] for i in items)}},'items':items,'post_state':{{i['path']:i['properties'] for i in items}},'verification':{{'verified':ok,'mode':'asset_properties_readback','gpu_probe_required':True}}}})
'''
    result=run_editor_python(wrap_editor_python(body))
    return result
