"""Deterministic offscreen StaticMesh material previews, without desktop control."""
from pathlib import Path
import math
import re
from typing import Any
from unreal_harness_runtime.python_exec import run_editor_python, wrap_editor_python, python_literal


def render_static_mesh_preview(asset_path: str, material_path: str | None, output_path: str,
                               camera_direction: list[float] = [1,-2,1], distance: float = 80,
                               resolution: int = 512, fov: float = 36,
                               rotation: list[float] = [0,0,0], scale: float = 1,
                               profile_frames: int = 0,
                               world_origin: list[float] | None = None) -> dict[str, Any]:
    """Capture one mesh/material to PNG, cleaning up all transient actors/RTs.

    camera_direction is relative to the mesh bounds centre in world space.
    rotation is pitch/yaw/roll. Captures use manual exposure and show-only actors.
    No level is saved or existing actor modified.
    Pass material_path=None to preserve every slot's default mesh material.
    world_origin defaults to [0,0,-100000]. Override it for coordinate-precision
    tests; the same offset is applied to both the mesh and the capture camera.
    With profile_frames=30..300, return immediately and retain only the preview
    actors until a bounded GPU CSV capture completes. A .profile.json sidecar
    reports cleanup/completion; the adjacent CSV contains actual GPU timers.
    """
    if not (32<=resolution<=2048 and distance>0 and scale>0 and 1<fov<170):
        return {'success': False, 'error':'Invalid capture dimensions or camera'}
    if len(camera_direction)!=3 or sum(x*x for x in camera_direction)<1e-10 or len(rotation)!=3:
        return {'success':False,'error':'Expected nonzero direction and 3 rotation components'}
    if profile_frames and not 30<=profile_frames<=300:
        return {'success':False,'error':'profile_frames must be zero or 30-300'}
    origin_values = [0,0,-100000] if world_origin is None else world_origin
    if len(origin_values)!=3 or not all(isinstance(v,(int,float)) and math.isfinite(v) for v in origin_values):
        return {'success':False,'error':'world_origin must contain three finite numbers'}
    target=Path(output_path)
    if not target.is_absolute() or target.suffix.lower() not in ('.png','.exr'):
        return {'success':False,'error':'output_path must be an absolute PNG or EXR path'}
    target.parent.mkdir(parents=True,exist_ok=True)
    if profile_frames:
        target.with_suffix('.profile.json').unlink(missing_ok=True)
        target.with_suffix('.csv').unlink(missing_ok=True)
    body=f'''
mesh = unreal.EditorAssetLibrary.load_asset({python_literal(asset_path)})
override_path = {python_literal(material_path)}
material = unreal.EditorAssetLibrary.load_asset(override_path) if override_path is not None else None
if not isinstance(mesh,unreal.StaticMesh) or (override_path is not None and not isinstance(material,unreal.MaterialInterface)):
    raise RuntimeError('Expected StaticMesh and MaterialInterface')
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
origin = unreal.Vector(*{python_literal(origin_values)})
actor = None
capture = None
rt = None
profiling = False
try:
    actor = actors.spawn_actor_from_class(unreal.StaticMeshActor,origin,transient=True)
    component = actor.static_mesh_component
    component.set_static_mesh(mesh)
    if material is not None:
        for i in range(component.get_num_materials()): component.set_material(i,material)
    actor.set_actor_scale3d(unreal.Vector({scale},{scale},{scale}))
    rot = {python_literal(rotation)}
    actor.set_actor_rotation(unreal.Rotator(pitch=rot[0],yaw=rot[1],roll=rot[2]),False)
    direction = unreal.Vector(*{python_literal(camera_direction)}).normal()
    location = origin + direction*{distance}
    capture = actors.spawn_actor_from_class(unreal.SceneCapture2D,location,transient=True)
    capture.set_actor_rotation(unreal.MathLibrary.find_look_at_rotation(location,origin),False)
    cc = capture.get_component_by_class(unreal.SceneCaptureComponent2D)
    cc.set_editor_property('capture_every_frame',False)
    cc.set_editor_property('capture_on_movement',False)
    cc.set_editor_property('fov_angle',{fov})
    cc.set_editor_property('primitive_render_mode',unreal.SceneCapturePrimitiveRenderMode.PRM_USE_SHOW_ONLY_LIST)
    cc.show_only_actor_components(actor)
    cc.set_editor_property('capture_source',unreal.SceneCaptureSource.{'SCS_SCENE_COLOR_HDR' if target.suffix.lower()=='.exr' else 'SCS_FINAL_COLOR_LDR'})
    cc.set_editor_property('show_flag_settings',[unreal.EngineShowFlagsSetting(show_flag_name=n,enabled=False) for n in ['Atmosphere','Fog','VolumetricFog','SkyLighting','MotionBlur']])
    pp = cc.get_editor_property('post_process_settings')
    pp.set_editor_property('override_auto_exposure_method',True)
    pp.set_editor_property('auto_exposure_method',unreal.AutoExposureMethod.AEM_MANUAL)
    pp.set_editor_property('override_auto_exposure_bias',True)
    pp.set_editor_property('auto_exposure_bias',0)
    pp.set_editor_property('override_auto_exposure_apply_physical_camera_exposure',True)
    pp.set_editor_property('auto_exposure_apply_physical_camera_exposure',False)
    pp.set_editor_property('override_bloom_intensity',True)
    pp.set_editor_property('bloom_intensity',0)
    cc.set_editor_property('post_process_settings',pp)
    cc.set_editor_property('post_process_blend_weight',1)
    rt = unreal.RenderingLibrary.create_render_target2d(world,{resolution},{resolution},unreal.TextureRenderTargetFormat.{'RTF_RGBA16F' if target.suffix.lower()=='.exr' else 'RTF_RGBA8'})
    cc.set_editor_property('texture_target',rt)
    cc.capture_scene()
    unreal.RenderingLibrary.export_render_target(world,rt,{python_literal(str(target.parent))},{python_literal(target.name)})
    if {profile_frames}>0:
        import pathlib
        if getattr(unreal,'_mcp_preview_profile',None):
            raise RuntimeError('A preview profile is already active')
        old_gpu=unreal.SystemLibrary.get_console_variable_int_value('r.GPUStatsEnabled')
        old_csv=unreal.SystemLibrary.get_console_variable_int_value('r.GPUCsvStatsEnabled')
        for cmd in ['r.GPUStatsEnabled 1','r.GPUCsvStatsEnabled 1']:
            unreal.SystemLibrary.execute_console_command(world,cmd)
        frame=[0]
        last_engine_frame=[-1]
        handle=[None]
        csv_source=pathlib.Path(unreal.Paths.project_saved_dir())/'Profiling/CSV'/{python_literal(target.with_suffix('.csv').name)}
        if csv_source.exists(): csv_source.unlink()
        profile_started=__import__('time').monotonic()
        def tick(delta):
            engine_frame=unreal.SystemLibrary.get_frame_count()
            if engine_frame==last_engine_frame[0]: return
            last_engine_frame[0]=engine_frame
            frame[0]+=1
            try:
                # Editor components do not necessarily tick while the app is
                # unfocused. Explicit captures make the benchmark independent
                # of viewport realtime and bTickInEditor settings.
                cc.capture_scene()
                if frame[0]==10:
                    unreal.SystemLibrary.execute_console_command(world,{python_literal('CSVProfile STARTFILE='+target.with_suffix('.csv').name)})
                    unreal.SystemLibrary.execute_console_command(world,'CSVProfile FRAMES={profile_frames}')
                ready=csv_source.is_file() and csv_source.stat().st_size>0
                timed_out=__import__('time').monotonic()-profile_started>180
                if ready or timed_out:
                    unreal.unregister_slate_post_tick_callback(handle[0])
                    actors.destroy_actor(capture)
                    actors.destroy_actor(actor)
                    unreal.RenderingLibrary.release_render_target2d(rt)
                    unreal.SystemLibrary.execute_console_command(world,'r.GPUStatsEnabled '+str(old_gpu))
                    unreal.SystemLibrary.execute_console_command(world,'r.GPUCsvStatsEnabled '+str(old_csv))
                    if ready:
                        __import__('shutil').copyfile(csv_source,{python_literal(str(target.with_suffix('.csv')))})
                    else:
                        unreal.SystemLibrary.execute_console_command(world,'CSVProfile STOP')
                    pathlib.Path({python_literal(str(target.with_suffix('.profile.json')))}).write_text(json.dumps({{'success':ready,'frames':{profile_frames},'cleanup':True,'csv_path':{python_literal(str(target.with_suffix('.csv')))},'error':None if ready else 'CSV capture timed out'}}),encoding='utf-8')
                    unreal._mcp_preview_profile=None
            except Exception as exc:
                unreal.unregister_slate_post_tick_callback(handle[0])
                actors.destroy_actor(capture);actors.destroy_actor(actor)
                unreal.RenderingLibrary.release_render_target2d(rt)
                unreal.SystemLibrary.execute_console_command(world,'CSVProfile STOP')
                unreal.SystemLibrary.execute_console_command(world,'r.GPUStatsEnabled '+str(old_gpu))
                unreal.SystemLibrary.execute_console_command(world,'r.GPUCsvStatsEnabled '+str(old_csv))
                unreal._mcp_preview_profile=None
                pathlib.Path({python_literal(str(target.with_suffix('.profile.json')))}).write_text(json.dumps({{'success':False,'error':str(exc),'cleanup':True}}),encoding='utf-8')
        handle[0]=unreal.register_slate_post_tick_callback(tick)
        unreal._mcp_preview_profile={{'tick':tick,'handle':handle[0]}}
        profiling=True
    camera_rot=capture.get_actor_rotation()
    _mcp_emit({{'success':True,'asset_path':mesh.get_path_name(),'material_path':material.get_path_name() if material else None,'material_slots':[component.get_material(i).get_path_name() if component.get_material(i) else None for i in range(component.get_num_materials())],'output_path':{python_literal(str(target))},'resolution':{resolution},'camera_direction':{python_literal(camera_direction)},'camera_rotation':{{'pitch':camera_rot.pitch,'yaw':camera_rot.yaw,'roll':camera_rot.roll}},'world_origin':{python_literal(origin_values)},'distance':{distance},'fov':{fov},'profile_frames':{profile_frames},'profile_status':'started' if profiling else 'disabled'}})
finally:
    if not profiling:
        if capture: actors.destroy_actor(capture)
        if actor: actors.destroy_actor(actor)
        if rt: unreal.RenderingLibrary.release_render_target2d(rt)
'''
    result=run_editor_python(wrap_editor_python(body))
    if result.get('success'):
        result['success']=target.is_file() and target.stat().st_size>0
        result['verification']={'verified':result['success'],'file_bytes':target.stat().st_size if target.is_file() else 0}
    return result
