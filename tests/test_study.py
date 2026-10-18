from dataclasses import replace
import numpy as np
import pytest
from ste_calculator.conductor_library import conductor
from ste_calculator.study import StudyConfig,calculate_study,derived_matrices,positive_equivalents
from ste_calculator.bundles import BundleSpec
from ste_calculator.models import Conductor
from ste_calculator.inductance import IDEAL_GROUND,NO_GROUND
from ste_calculator.double_circuit import calculate_double_circuit
from ste_calculator.transposition import calculate_transposition
from ste_calculator.resistance import SPECIFIED


def config(circuits=2,count=2,historical=True,**kwargs):
    d=conductor('DOVE')
    if historical:d=replace(d,gmr_m=.00954024,sources=dict(d.sources,diameter_gmr='Ensayo DOVE histórico del usuario'))
    specs=tuple(BundleSpec(Conductor(c,p,x,h+12*(c-1)),count,.011765 if historical else d.radius_m,.4572)
        for c in range(1,circuits+1) for p,x,h in (('A',-3,13),('B',3,13),('C',0,9)))
    return StudyConfig(specs,(d,)*(3*circuits),voltage_kv=220,power=250,power_factor=.9,complete=True,**kwargs)


@pytest.mark.parametrize('circuits,count',[(1,1),(1,4),(2,1),(2,2),(2,4)])
def test_workflow_reuses_existing_motors_and_all_variants(circuits,count):
    s=calculate_study(config(circuits,count))
    from ste_calculator.inductance import RMGInput,MANUFACTURER
    rmg=(RMGInput(.011765,MANUFACTURER,.00954024,'dato histórico'),)*(3*circuits)
    for model in (IDEAL_GROUND,NO_GROUND):
        for trans in (False,True):
            v=s.variants[model,trans]
            direct=calculate_double_circuit(s.config.specs,rmg,inductance_model=model,capacitance_model=model,complete=trans) if circuits==2 else calculate_transposition(s.config.specs,rmg,trans,model,model)
            np.testing.assert_array_equal(v.c_f_per_m,direct.c_f_per_m)
            np.testing.assert_array_equal(v.l_h_per_m,direct.l_h_per_m)
            assert v.c_f_per_m.shape==(3*circuits,3*circuits)
            if model==NO_GROUND:
                np.testing.assert_allclose(v.c_f_per_m@np.ones(3*circuits),0,atol=2e-24)


def test_required_c6_no_ground_coefficients_stay_verified():
    s=calculate_study(config())
    c=s.variants[NO_GROUND,True].c_f_per_m*1e12
    np.testing.assert_allclose([c[0,0],c[0,1],c[3,3],c[3,4],c[0,3]],
        [10.029643,-2.962967,10.029575,-2.962933,-1.367903],rtol=0,atol=5e-7)
    assert np.linalg.matrix_rank(c,tol=1e-9)==5
    assert np.max(np.abs(c-s.variants[NO_GROUND,False].c_f_per_m*1e12))>.7
    assert len(positive_equivalents(c,s.geometry.phase_labels))==2


def test_units_z_y_and_no_silent_parallel_reduction():
    s=calculate_study(config(parallel=True));d=derived_matrices(s,IDEAL_GROUND,NO_GROUND,True)
    np.testing.assert_allclose(d['Z_ohm_m'].real,np.eye(6)*.0515/1000)
    np.testing.assert_allclose(d['Z_ohm_m'].imag,2*np.pi*60*d['L_h_m'])
    np.testing.assert_allclose(d['Y_s_m'],1j*2*np.pi*60*d['C_f_m'])
    assert d['Z_ohm_m'].shape==(6,6)
    assert np.max(np.abs(d['Z_ohm_m'][:3,3:]))>1e-9


def test_missing_operating_or_rmg_data_do_not_block_capacitance():
    cfg=config();cfg=replace(cfg,conductor_data=tuple(replace(d,gmr_m=None) for d in cfg.conductor_data),voltage_kv=None,power=None)
    s=calculate_study(cfg)
    assert s.resistance is None and s.variants[NO_GROUND,True].l_h_per_m is None
    assert s.variants[NO_GROUND,True].c_f_per_m.shape==(6,6)
    assert 'inductance' in s.messages and 'resistance' in s.messages


def test_carson_independent_transposition_and_kron_conditions():
    from ste_calculator.kron import AuxiliaryConductor,ZERO_DROP,UNKNOWN
    from ste_calculator.carson import CarsonConductor
    cfg=config(carson_enabled=True)
    base=calculate_study(cfg)
    assert len(base.carson['sections'])==9
    z=base.carson['phase'];np.testing.assert_allclose(z,z.T,atol=1e-18)
    aux=AuxiliaryConductor(CarsonConductor('G1',0,30,.3,.004,'Datos de ensayo documentados'),connection=UNKNOWN)
    blocked=calculate_study(replace(cfg,auxiliaries=(aux,)))
    assert blocked.carson['phase'] is None
    assert blocked.carson['sections'][0]['augmented'].z_ohm_per_m.shape==(7,7)
    aux=replace(aux,connection=ZERO_DROP,justification='Ensayo algebraico, ΔV=0 declarado')
    reduced=calculate_study(replace(cfg,auxiliaries=(aux,),kron_confirmed=True))
    assert reduced.carson['phase'].shape==(6,6)
    assert len(reduced.carson['sections'])==9
    np.testing.assert_array_equal(reduced.variants[NO_GROUND,True].c_f_per_m,base.variants[NO_GROUND,True].c_f_per_m)


def test_confirmed_solid_custom_reuses_original_rmg_resolver():
    from ste_calculator.inductance import SOLID_UNIFORM
    from ste_calculator.study import rmg_values
    cfg=config(1,1)
    cfg=replace(cfg,conductor_data=tuple(replace(d,gmr_m=None,rmg_method=SOLID_UNIFORM) for d in cfg.conductor_data))
    s=calculate_study(cfg)
    np.testing.assert_allclose(rmg_values(s),.011765*np.exp(-.25),rtol=1e-15)


def test_equivalent_positive_is_not_offered_when_sequence_couplings_remain():
    s=calculate_study(config())
    assert positive_equivalents(s.variants[NO_GROUND,False].c_f_per_m,s.geometry.phase_labels)==()


def test_external_comparison_uses_separate_resistance_reactance_errors():
    from ste_calculator.study import external_comparisons
    s=calculate_study(config(1,4))
    z=derived_matrices(s,IDEAL_GROUND,IDEAL_GROUND,True)['Z_ohm_m']
    ref=z*1000
    ref=ref.real*1.1+1j*ref.imag*.9
    phase,seq=external_comparisons(z,ref,s.geometry.phase_labels)
    assert len(phase)==9 and len(seq)==3
    for row in phase:
        if row['R_PSCAD']!=0:assert row['Error_R_pct']==pytest.approx(100/11)
        if row['X_PSCAD']!=0:assert row['Error_X_pct']==pytest.approx(100/9)
