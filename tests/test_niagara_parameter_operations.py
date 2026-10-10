from unittest.mock import patch
from unreal_niagara import tools

def row(name, links):
    return {"node": "Assignment0", "name": name, "input_links": links}

def test_dry_run_never_saves_or_reads_post_mutation():
    response={"success": True, "results": [{"success": True, "dry_run": True}]}
    with patch.object(tools,"_native",return_value=response) as native, patch.object(tools,"run_editor_python") as save:
        result=tools.rename_niagara_particle_parameter('/Game/Test','Emitter','Particles.Param','Particles.rad',replace_existing=True)
        assert result['summary']=={'dry_run':True,'applied':False}
        assert native.call_args.args[1]['operations'][0]['dry_run'] is True
        save.assert_not_called()

def test_case_only_rename_is_rejected_without_transport():
    with patch.object(tools,'_native') as native:
        assert not tools.rename_niagara_particle_parameter('/Game/Test','Emitter','Particles.rad','Particles.Rad')['success']
        native.assert_not_called()

def test_rename_checks_curve_links_not_only_names():
    before=row('Particles.Param',['FloatFromCurve.Value'])
    native={'success':True,'results':[{'success':True,'compiled':True,'before':{'assignments':[before]}}]}
    for links,ok in [(['FloatFromCurve.Value'],True),([],False),(['Other.Value'],False)]:
        with patch.object(tools,'_native',return_value=native),patch.object(tools,'get_niagara_assignments',return_value={'success':True,'post_state':{'assignments':[row('Particles.rad',links)]}}):
            result=tools.rename_niagara_particle_parameter('/Game/Test','Emitter','Particles.Param','Particles.rad',dry_run=False,save=False)
            assert result['verification']['verified'] is ok

def test_native_rejection_never_saves():
    native={'success':True,'fail_count':1,'results':[{'success':False,'error':'Destination has a connected input'}]}
    with patch.object(tools,'_native',return_value=native),patch.object(tools,'run_editor_python') as save:
        result=tools.rename_niagara_particle_parameter('/Game/Test','Emitter','Particles.Param','Particles.rad',dry_run=False)
        assert not result['success'] and 'connected' in result['error']
        save.assert_not_called()

def test_old_native_plugin_cannot_report_empty_inspection_as_success():
    with patch.object(tools,'_native',return_value={'success':True,'nodes':[]}):
        assert not tools.get_niagara_assignments('/Game/Test','Emitter')['success']

def test_position_readback_checks_spaces_and_scale():
    native={'success':True,'results':[{'success':True,'compiled':True}]}
    good={'Position':'Particles.Position','Source Space':'Simulation','Destination Space':'World','Apply Scale':'true'}
    for inputs,ok in [(good,True),({},False),(dict(good,**{'Source Space':'<invalid enum>'}),False),(dict(good,**{'Destination Space':'Local'}),False),(dict(good,**{'Apply Scale':'false'}),False)]:
        target=dict(row('Particles.Center',['Transform.TransformedPosition']),transform_inputs=inputs)
        with patch.object(tools,'_native',return_value=native),patch.object(tools,'get_niagara_assignments',return_value={'success':True,'post_state':{'assignments':[target]}}):
            result=tools.bind_niagara_particle_position('/Game/Test','Emitter','Assignment0','Particles.Center',dry_run=False,save=False)
            assert result['verification']['verified'] is ok
