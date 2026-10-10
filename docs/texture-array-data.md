# 纹理数组与自定义 mip 数据工作流

真实验证：2026-09-14，`F:/GFFEngines/Main_Client`，UE 5.6.1 分支 `F:/GFFEngines/Develop_Maomi/Engine`。

## API

`unreal_asset.texture_array.import_texture_arrays(manifest_path, replace_existing=False)`：读取 manifest，生成原生 DX10 DDS，使用现有隔离 commandlet 批量导入。

```json
{
  "destination_path": "/Game/Example",
  "items": [{
    "name": "T_Array",
    "width": 256,
    "height": 256,
    "slices": 3,
    "format": "RGBA32F",
    "mip_files": ["mip0.bin", "mip1.bin"]
  }]
}
```

- 1–16 个数组；DDS 原生数组导入限定 2–512 个切片。单切片会被引擎识别为 Texture2D，因此提前拒绝，避免留下错误类型的资产。
- 格式：R32F、RGBA8、RGBA32F。raw 文件为小端、连续 `[slice,y,x,channels]`；每个文件对应一级 mip。
- writer 将 mip-major 文件改排成 DDS 的 slice-major mip chain，检查每级字节数后才写入。
- 数据纹理统一 sRGB=false、NeverStream、point filter、保留 Alpha；单 mip 使用 NoMipmaps，多 mip 使用 LeaveExistingMips。
- 原生导入后验证期望类为 Texture2DArray，应用设置、保存并回读。原型不存在也不需要新增 C++ 插件接口。

`inspect_texture_arrays(asset_paths)`：安全读取资产设置和注册表 Dimensions/Format。返回规范化 enum、summary、items、post_state、verification；GPU实际内容还需探针验证。

`unreal_scene.material_data.render_material_data(material_path, output_path, width, height)`：将材质绘制到线性RGBA8 RenderTarget并导出PNG，没有场景曝光或tonemapper。验证浮点数据时可将 `asuint` 位模式分到RGB字节，精确恢复。

`render_static_mesh_preview` 现支持 `.exr`，使用线性SceneColor HDR/RTF_RGBA16F，适合深度、法线和UV诊断；数值误差需计入half读回精度。返回实际摄像机旋转，便于对齐俯仰极点的CPU射线。

## 已验证

- 6/12表面层分别导入18/36个数组切片。Bounds为3切片、9级mip。
- GPU验证6张数组的全部切片、共22个数组/mip组合；R32F/RGBA32F逐位匹配，RGBA8所有UV字节匹配。
- 材质数组参数更换及保存回读正常。修复批量材质参数工具将短包路径和完整对象路径误判为不一致的问题。
- 数据材质渲染、浮点场景诊断、原图替换与GPU CSV测量均实际执行。
- 108项Python测试通过。

## 避免的引擎缺口

该分支 `FImageUtils::ExportTextureSourceToDDS` 没有处理 ETextureClass::Array，调用标准DDS导出器会断言。一次源数据检查触发此错误后，MCP已移除导出调用，改用注册表/属性和真正GPU回读；编辑器恢复完成。不再用DDS导出作为数组检查的前置条件。

首帧纹理资源可能仍在异步编译而返回默认32×32×1数组。GPU验证先查询实际维度，等待资源就绪后再逐值检查，不把占位资源当作资产数据。

证据目录：`Main_Client/Saved/GeneratedAssets/TrueImposter/LayerStudy/reports/`。没有修改用户已有的26个TrueImposter资产及默认外壳材质。
