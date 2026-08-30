import argparse
import json
from pathlib import Path
import sys

import unreal


MARKER = "__UNREAL_MCP_JSON__:"
RESULT_FILE = None


def parse_bool(value):
    if isinstance(value, bool):
        return value
    normalized = str(value).strip().lower()
    if normalized in {"1", "true", "yes", "y", "on"}:
        return True
    if normalized in {"0", "false", "no", "n", "off"}:
        return False
    raise argparse.ArgumentTypeError("expected a boolean value")


def try_set_prop(obj, prop, value, warnings):
    try:
        obj.set_editor_property(prop, value)
        return True
    except Exception as exc:
        warnings.append(
            "Could not set %s.%s: %s" % (obj.__class__.__name__, prop, exc)
        )
        return False


def try_get_prop(obj, prop, default=None):
    try:
        return obj.get_editor_property(prop)
    except Exception:
        return default


def resolve_enum(enum_type, value):
    if not value:
        return None
    candidates = [str(value), str(value).split(".")[-1]]
    candidates.extend(candidate.upper() for candidate in list(candidates))
    for candidate in candidates:
        if hasattr(enum_type, candidate):
            return getattr(enum_type, candidate)
    valid = [name for name in dir(enum_type) if name.isupper()]
    enum_name = getattr(enum_type, "__name__", str(enum_type))
    raise ValueError(
        "Unknown %s value %r. Valid values include: %s"
        % (enum_name, value, ", ".join(valid[:12]))
    )


def emit(payload):
    text = MARKER + json.dumps(payload, ensure_ascii=False)
    print(text)
    unreal.log(text)
    if RESULT_FILE:
        Path(RESULT_FILE).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )


def import_texture(source_path, name, destination_path):
    task = unreal.AssetImportTask()
    task.set_editor_property("filename", source_path)
    task.set_editor_property("destination_path", destination_path.rstrip("/"))
    task.set_editor_property("destination_name", name)
    task.set_editor_property("automated", True)
    task.set_editor_property("replace_existing", True)
    task.set_editor_property("save", True)

    # UE 5.6 routes PNG imports through Interchange when no explicit factory is
    # supplied. That path can assert in TaskGraph during unattended Python
    # imports. Supplying TextureFactory keeps texture commandlets on the legacy
    # importer and matches the explicit -factoryname=/Script/UnrealEd.TextureFactory
    # commandlet workaround.
    task.set_editor_property("factory", unreal.TextureFactory())

    asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
    asset_tools.import_asset_tasks([task])
    imported_paths = list(task.get_editor_property("imported_object_paths"))

    emit(
        {
            "success": len(imported_paths) > 0,
            "mode": "texture",
            "source_path": source_path,
            "factory": "/Script/UnrealEd.TextureFactory",
            "imported_object_paths": imported_paths,
        }
    )


def import_fbx(args):
    warnings = []
    source_path = args.source
    destination_path = args.destination
    if not Path(source_path).exists():
        raise FileNotFoundError("FBX source does not exist: %s" % source_path)

    task = unreal.AssetImportTask()
    task.set_editor_property("filename", source_path)
    task.set_editor_property("destination_path", destination_path.rstrip("/"))
    if args.name:
        task.set_editor_property("destination_name", args.name)
    task.set_editor_property("automated", True)
    task.set_editor_property("replace_existing", args.replace_existing)
    task.set_editor_property("replace_existing_settings", args.replace_existing_settings)
    task.set_editor_property("save", args.save)

    options = unreal.FbxImportUI()
    try_set_prop(options, "automated_import_should_detect_type", False, warnings)
    try_set_prop(options, "import_as_skeletal", args.import_as_skeletal, warnings)
    try_set_prop(options, "import_mesh", True, warnings)
    try_set_prop(options, "import_animations", args.import_animations, warnings)
    try_set_prop(options, "import_materials", args.import_materials, warnings)
    try_set_prop(options, "import_textures", args.import_textures, warnings)
    mesh_type = (
        unreal.FBXImportType.FBXIT_SKELETAL_MESH
        if args.import_as_skeletal
        else unreal.FBXImportType.FBXIT_STATIC_MESH
    )
    try_set_prop(options, "mesh_type_to_import", mesh_type, warnings)
    if args.import_as_skeletal:
        try_set_prop(options, "create_physics_asset", args.create_physics_asset, warnings)
        if args.skeleton:
            skeleton = unreal.load_asset(args.skeleton)
            if skeleton is None:
                raise ValueError("Could not load skeleton asset: %s" % args.skeleton)
            try_set_prop(options, "skeleton", skeleton, warnings)

    import_data = try_get_prop(
        options,
        "skeletal_mesh_import_data"
        if args.import_as_skeletal
        else "static_mesh_import_data",
    )
    if import_data is not None:
        if args.import_rotation:
            try_set_prop(
                import_data,
                "import_rotation",
                unreal.Rotator(
                    pitch=args.import_rotation[0],
                    yaw=args.import_rotation[1],
                    roll=args.import_rotation[2],
                ),
                warnings,
            )
        for prop, value in (
            ("convert_scene", args.convert_scene),
            ("convert_scene_unit", args.convert_scene_unit),
            ("force_front_x_axis", args.force_front_x_axis),
            ("update_skeleton_reference_pose", args.update_skeleton_reference_pose),
            ("use_t0_as_ref_pose", args.use_t0_as_ref_pose),
        ):
            if value is not None:
                try_set_prop(import_data, prop, value, warnings)
        if args.import_as_skeletal and args.import_meshes_in_bone_hierarchy is not None:
            try_set_prop(
                import_data,
                "import_meshes_in_bone_hierarchy",
                args.import_meshes_in_bone_hierarchy,
                warnings,
            )
        if not args.import_as_skeletal and args.combine_meshes is not None:
            try_set_prop(import_data, "combine_meshes", args.combine_meshes, warnings)
        if args.normal_import_method:
            method = resolve_enum(unreal.FBXNormalImportMethod, args.normal_import_method)
            try_set_prop(import_data, "normal_import_method", method, warnings)
    else:
        warnings.append("Could not read FBX import data object")

    task.set_editor_property("options", options)

    asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
    asset_tools.import_asset_tasks([task])
    imported_paths = list(task.get_editor_property("imported_object_paths"))

    emit(
        {
            "success": len(imported_paths) > 0,
            "mode": "fbx",
            "source_path": source_path,
            "destination_path": destination_path.rstrip("/"),
            "destination_name": args.name,
            "imported_object_paths": imported_paths,
            "import_options": {
                "import_as_skeletal": args.import_as_skeletal,
                "import_materials": args.import_materials,
                "import_textures": args.import_textures,
                "import_animations": args.import_animations,
                "import_rotation": args.import_rotation,
                "combine_meshes": args.combine_meshes,
                "import_meshes_in_bone_hierarchy": args.import_meshes_in_bone_hierarchy,
                "create_physics_asset": args.create_physics_asset,
                "normal_import_method": args.normal_import_method,
                "skeleton": args.skeleton,
                "convert_scene": args.convert_scene,
                "convert_scene_unit": args.convert_scene_unit,
                "force_front_x_axis": args.force_front_x_axis,
                "update_skeleton_reference_pose": args.update_skeleton_reference_pose,
                "use_t0_as_ref_pose": args.use_t0_as_ref_pose,
                "replace_existing": args.replace_existing,
                "replace_existing_settings": args.replace_existing_settings,
                "save": args.save,
            },
            "warnings": warnings,
        }
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", required=True, choices=["texture", "fbx"])
    parser.add_argument("--source", required=True)
    parser.add_argument("--name", default="")
    parser.add_argument("--destination", required=True)
    parser.add_argument("--replace-existing", type=parse_bool, default=True)
    parser.add_argument("--replace-existing-settings", type=parse_bool, default=False)
    parser.add_argument("--save", type=parse_bool, default=True)
    parser.add_argument("--import-as-skeletal", type=parse_bool, default=False)
    parser.add_argument("--import-materials", type=parse_bool, default=False)
    parser.add_argument("--import-textures", type=parse_bool, default=False)
    parser.add_argument("--import-animations", type=parse_bool, default=False)
    parser.add_argument("--import-rotation", nargs=3, type=float, default=None)
    parser.add_argument("--combine-meshes", type=parse_bool, default=None)
    parser.add_argument("--import-meshes-in-bone-hierarchy", type=parse_bool, default=None)
    parser.add_argument("--create-physics-asset", type=parse_bool, default=False)
    parser.add_argument("--normal-import-method", default="")
    parser.add_argument("--skeleton", default="")
    parser.add_argument("--convert-scene", type=parse_bool, default=None)
    parser.add_argument("--convert-scene-unit", type=parse_bool, default=None)
    parser.add_argument("--force-front-x-axis", type=parse_bool, default=None)
    parser.add_argument("--update-skeleton-reference-pose", type=parse_bool, default=None)
    parser.add_argument("--use-t0-as-ref-pose", type=parse_bool, default=None)
    parser.add_argument("--result-file", default="")
    args = parser.parse_args()

    global RESULT_FILE
    RESULT_FILE = args.result_file or None

    try:
        if args.mode == "texture":
            if not args.name:
                raise ValueError("--name is required for texture imports")
            import_texture(args.source, args.name, args.destination)
        else:
            import_fbx(args)
    except Exception as exc:
        emit({"success": False, "error": str(exc)})
        raise


if __name__ == "__main__":
    main()
