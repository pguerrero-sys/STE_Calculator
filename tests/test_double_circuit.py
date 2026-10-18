import math

import numpy as np
import pytest
from scipy.linalg import null_space, block_diag

from ste_calculator.bundles import BundleSpec, build_bundles
from ste_calculator.bundle_electrical import calculate_bundle_capacitance, calculate_bundle_inductance
from ste_calculator.models import Conductor, InputError
from ste_calculator.inductance import (RMGInput, SOLID_UNIFORM, MANUFACTURER, IDEAL_GROUND,
                                      NO_GROUND, ZERO_SUM_PROJECTOR, convert_inductance)
from ste_calculator.double_circuit import (FACTOR, LABELS, calculate_section, calculate_double_circuit,
    reproducible_specs, default_assignments, build_circuit_geometry, reactance_six)

INPUTS = (RMGInput(.011765,SOLID_UNIFORM),)*6


@pytest.mark.parametrize("n",[1,2,3,4])
@pytest.mark.parametrize("model",[IDEAL_GROUND,NO_GROUND])
def test_six_phase_symmetry_energy_units_and_equipotentiality(n,model):
    result = calculate_double_circuit(reproducible_specs(n),INPUTS,inductance_model=model,capacitance_model=model)
    section = result.sections[0]
    g = section.geometry
    assert g.positions_m.shape == (6*n,2)
    assert section.potential_sub.shape == (6*n,6*n)
    assert result.l_h_per_m.shape == result.c_f_per_m.shape == (6,6)
    q = np.eye(6) if model==IDEAL_GROUND else null_space(np.ones((1,6)))
    for m in (result.l_h_per_m,result.c_f_per_m,result.average_phase_p):
        np.testing.assert_allclose(m,m.T,rtol=0,atol=1e-20)
        assert np.min(np.linalg.eigvalsh(q.T @ m @ q))>0
    delta = section.potential_sub @ (section.charge_response_f_per_m/FACTOR)-g.incidence
    if model==NO_GROUND:
        delta -= delta.mean(axis=0,keepdims=True)
        np.testing.assert_allclose(np.sum(section.charge_response_f_per_m,axis=0),0,atol=1e-25)
        for m in (result.l_h_per_m,result.c_f_per_m):
            np.testing.assert_allclose(m @ np.ones(6),0,atol=1e-20)
            assert np.linalg.matrix_rank(m,tol=1e-22)==5
        assert np.linalg.matrix_rank(result.l_circuit_balanced_h_per_m,tol=1e-21)==4
        assert result.l_loops_h_per_m.shape == (4,4)
    np.testing.assert_allclose(delta,0,atol=1e-13)
    np.testing.assert_allclose(result.average_phase_p @ result.c_f_per_m/FACTOR,q @ q.T,atol=1e-13)
    np.testing.assert_allclose(convert_inductance(result.l_h_per_m,"H/m","mH/km"),result.l_h_per_m*1e6)
    np.testing.assert_allclose(reactance_six(result.l_h_per_m,60),2*np.pi*60*1000*result.l_h_per_m)


def test_independent_analytic_six_single_conductors_with_images():
    specs = reproducible_specs()
    xy = np.array([(s.center.x_m,s.center.y_m) for s in specs])
    p,l = np.zeros((6,6)),np.zeros((6,6))
    for i in range(6):
        for j in range(6):
            d = math.hypot(xy[i,0]-xy[j,0],xy[i,1]-xy[j,1])
            s = math.hypot(xy[i,0]-xy[j,0],xy[i,1]+xy[j,1])
            p[i,j] = math.log(s/(.011765 if i==j else d))
            l[i,j] = 2e-7*math.log(s/(.011765*math.exp(-.25) if i==j else d))
    r = calculate_double_circuit(specs,INPUTS)
    np.testing.assert_allclose(r.l_h_per_m,l,rtol=1e-14)
    # Inversión independiente y comprobación dimensional de todos los elementos.
    np.testing.assert_allclose(r.c_f_per_m,FACTOR*np.linalg.solve(p,np.eye(6)),rtol=1e-13)
    assert r.l_h_per_m[0,3]>0 and r.c_f_per_m[0,3]<0
    assert not np.allclose(r.l_h_per_m[:3,3:],0,atol=1e-10)
    assert r.sections[0].geometry.real_distances_m[0,3] == 8
    assert r.sections[0].geometry.image_distances_m[0,0] == 30


@pytest.mark.parametrize("n",[1,2,3,4])
@pytest.mark.parametrize("model",[IDEAL_GROUND,NO_GROUND])
def test_comparison_with_verified_single_circuit_modules(n,model):
    specs = reproducible_specs(n)
    old_geometry = build_bundles(specs[:3])
    old_l = calculate_bundle_inductance(old_geometry,INPUTS[:3],model)
    old_c = calculate_bundle_capacitance(old_geometry,model)
    one = calculate_section(specs[:3],INPUTS[:3],model,model)
    expected_l = old_l.phase_h_per_m if model==IDEAL_GROUND else old_l.projected_h_per_m
    np.testing.assert_allclose(one.l_h_per_m,expected_l,rtol=1e-13,atol=1e-21)
    np.testing.assert_allclose(one.c_f_per_m,old_c.phase_f_per_m,rtol=1e-13,atol=1e-25)
    double = calculate_section(specs,INPUTS,model,model)
    np.testing.assert_allclose(double.potential_sub[:3*n,:3*n],old_c.potential_coefficients,atol=1e-14)
    if model==IDEAL_GROUND:
        np.testing.assert_allclose(double.l_h_per_m[:3,:3],old_l.phase_h_per_m,rtol=1e-13)
    else:
        h = ZERO_SUM_PROJECTOR
        np.testing.assert_allclose(h @ double.l_h_per_m[:3,:3] @ h,old_l.projected_h_per_m,rtol=1e-13,atol=1e-21)


def test_capacitance_block_is_not_isolated_circuit_and_floating_single_conductors():
    specs = reproducible_specs()
    r = calculate_double_circuit(specs,INPUTS)
    old = calculate_bundle_capacitance(build_bundles(specs[:3])).phase_f_per_m
    assert np.max(np.abs((r.c_f_per_m[:3,:3]-old)*1e12))>.01
    # Q2=0, conductores sencillos: eliminar potenciales flotantes recupera P11^-1.
    c = r.c_f_per_m
    floating = c[:3,:3]-c[:3,3:] @ np.linalg.solve(c[3:,3:],c[3:,:3])
    np.testing.assert_allclose(floating,old,rtol=1e-13,atol=1e-25)


@pytest.mark.parametrize("mode",["none","same","opposite"])
@pytest.mark.parametrize("model",[IDEAL_GROUND,NO_GROUND])
def test_transposition_assignments_potential_average_and_permutations(mode,model):
    assignments = default_assignments(mode)
    r = calculate_double_circuit(reproducible_specs(4),INPUTS,assignments,inductance_model=model,capacitance_model=model)
    first = r.sections[0]
    for row,section in zip(assignments,r.sections):
        rotation = np.eye(6)[:,row]
        np.testing.assert_allclose(section.l_h_per_m,rotation.T @ first.l_h_per_m @ rotation,rtol=1e-13,atol=1e-21)
        np.testing.assert_allclose(section.c_f_per_m,rotation.T @ first.c_f_per_m @ rotation,rtol=1e-13,atol=1e-25)
    expected_l = sum(w*s.l_h_per_m for w,s in zip(r.weights,r.sections))
    np.testing.assert_allclose(r.l_h_per_m,expected_l,atol=1e-21)
    p = sum(w*s.effective_phase_p for w,s in zip(r.weights,r.sections))
    q = np.eye(6) if model==IDEAL_GROUND else null_space(np.ones((1,6)))
    independent_c = FACTOR*q @ np.linalg.solve(q.T @ p @ q,q.T)
    np.testing.assert_allclose(r.c_f_per_m,independent_c,rtol=1e-13,atol=1e-25)
    if mode!="none":
        direct = sum(w*s.c_f_per_m for w,s in zip(r.weights,r.sections))
        assert np.max(np.abs((direct-r.c_f_per_m)*1e12))>.01


def test_relative_transposition_cycles_change_intercircuit_mutual_terms():
    specs = reproducible_specs()
    same = calculate_double_circuit(specs,INPUTS,default_assignments("same"))
    opposite = calculate_double_circuit(specs,INPUTS,default_assignments("opposite"))
    np.testing.assert_allclose(same.l_h_per_m[:3,:3],opposite.l_h_per_m[:3,:3])
    assert np.max(np.abs((same.l_h_per_m[:3,3:]-opposite.l_h_per_m[:3,3:])*1e6))>.01


def test_custom_weights_and_phase_construction_follow_phase():
    specs = tuple(BundleSpec(s.center,1+i%4,s.radius_m,.4,10*i) for i,s in enumerate(reproducible_specs()))
    rows = default_assignments("opposite")
    r = calculate_double_circuit(specs,INPUTS,rows,(.2,.3,.5))
    for row,section in zip(rows,r.sections):
        for i,s in enumerate(section.geometry.specs):
            assert s.count==specs[i].count and s.rotation_deg==specs[i].rotation_deg
            assert s.center.x_m==specs[row[i]].center.x_m and s.center.y_m==specs[row[i]].center.y_m
    np.testing.assert_allclose(r.l_h_per_m,sum(w*s.l_h_per_m for w,s in zip(r.weights,r.sections)),rtol=1e-13)


def test_manufacturer_rmg_is_used_directly_and_capacitance_independent():
    rmg = tuple(RMGInput(.011765,MANUFACTURER,.008,"Ficha de ensayo de prueba") for _ in LABELS)
    r = calculate_double_circuit(reproducible_specs(),rmg,capacitance_model=NO_GROUND)
    np.testing.assert_allclose(r.sections[0].rmg_m,.008)
    cap_only = calculate_double_circuit(reproducible_specs(),capacitance_model=NO_GROUND)
    np.testing.assert_allclose(cap_only.c_f_per_m,r.c_f_per_m,rtol=1e-13)
    assert cap_only.l_h_per_m is None


@pytest.mark.parametrize("reference",[10,1000,2000])
def test_no_ground_reference_invariance_and_individual_circuit_balance(reference):
    r = calculate_double_circuit(reproducible_specs(3),INPUTS,inductance_model=NO_GROUND,capacitance_model=NO_GROUND)
    s = r.sections[0]
    h = np.eye(6)-np.ones((6,6))/6
    raw = s.geometry.current_weights.T @ (s.l_sub_h_per_m+2e-7*math.log(reference)) @ s.geometry.current_weights
    np.testing.assert_allclose(h @ raw @ h,r.l_h_per_m,rtol=1e-13,atol=1e-21)
    hcc = block_diag(ZERO_SUM_PROJECTOR,ZERO_SUM_PROJECTOR)
    np.testing.assert_allclose(hcc @ r.l_h_per_m @ hcc,r.l_circuit_balanced_h_per_m,rtol=1e-13,atol=1e-21)


@pytest.mark.parametrize("bad_weights",[(0,.5,.5),(-1,1,1),(.2,.2,.2),(math.nan,.5,.5)])
def test_invalid_segment_weights(bad_weights):
    with pytest.raises(InputError):
        calculate_double_circuit(reproducible_specs(),INPUTS,default_assignments("same"),bad_weights)


def test_invalid_geometry_and_assignment_are_specific():
    specs = list(reproducible_specs())
    s = specs[3]
    specs[3] = BundleSpec(Conductor(2,"A",-4,15),1,s.radius_m)
    with pytest.raises(InputError,match="A-1.*A'-1"):
        build_circuit_geometry(specs)
    with pytest.raises(InputError,match="Tramo 1"):
        calculate_double_circuit(reproducible_specs(),INPUTS,((0,0,2,3,4,5),))
    with pytest.raises(InputError):
        calculate_double_circuit(reproducible_specs(),INPUTS,capacitance_model="carson")
    for frequency in (None,0,-1,math.nan):
        with pytest.raises(InputError):
            reactance_six(np.eye(6),frequency)
