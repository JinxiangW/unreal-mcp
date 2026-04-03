import argparse
import json
from pathlib import Path
import sys

import unreal


MARKER = "__UNREAL_MCP_JSON__:"
RESULT_FILE = None


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

    asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
    asset_tools.import_asset_tasks([task])
    imported_paths = list(task.get_editor_property("imported_object_paths"))

    emit(
        {
            "success": len(imported_paths) > 0,
            "mode": "texture",
            "source_path": source_path,
            "imported_object_paths": imported_paths,
        }
    )


def import_fbx(source_path, destination_path):
    task = unreal.AssetImportTask()
    task.set_editor_property("filename", source_path)
    task.set_editor_property("destination_path", destination_path.rstrip("/"))
    task.set_editor_property("automated", True)
    task.set_editor_property("replace_existing", True)
    task.set_editor_property("save", True)

    options = unreal.FbxImportUI()
    options.set_editor_property("import_as_skeletal", False)
    options.set_editor_property("import_materials", False)
    options.set_editor_property("import_textures", False)
    task.set_editor_property("options", options)

    asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
    asset_tools.import_asset_tasks([task])
    imported_paths = list(task.get_editor_property("imported_object_paths"))

    emit(
        {
            "success": len(imported_paths) > 0,
            "mode": "fbx",
            "source_path": source_path,
            "imported_object_paths": imported_paths,
        }
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", required=True, choices=["texture", "fbx"])
    parser.add_argument("--source", required=True)
    parser.add_argument("--name", default="")
    parser.add_argument("--destination", required=True)
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
            import_fbx(args.source, args.destination)
    except Exception as exc:
        emit({"success": False, "error": str(exc)})
        raise


if __name__ == "__main__":
    main()
