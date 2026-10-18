import math

import numpy as np
import pytest
from scipy.linalg import block_diag

from ste_calculator.models import Conductor,InputError
from ste_calculator.bundles import BundleSpec,build_bundles
from ste_calculator.bundle_electrical import calculate_bundle_capacitance,calculate_bundle_inductance
from ste_calculator.capacitance import VACUUM_PERMITTIVITY_F_PER_M
from ste_calculator.inductance import (RMGInput,SOLID_UNIFORM,IDEAL_GROUND,NO_GROUND,
                                      ZERO_SUM_PROJECTOR as H,convert_inductance,calculate_reactance)
from ste_calculator.transposition import (calculate_transposition,position_assignments,permutation_matrix,
                                         section_lengths_m,ZERO_SUM_BASIS)

CENTERS = (Conductor(1,"A",-3,13),Conductor(1,"B",3,13),Conductor(1,"C",0,9))
INPUTS = (RMGInput(.011765,SOLID_UNIFORM),)*3
FACTOR = 2*math.pi*VACUUM_PERMITTIVITY_F_PER_M
EXPECTED_L = np.array([[.961802,.298262,.298262],[.298262,.961802,.298262],[.298262,.298262,.961802]])
EXPECTED_C = np.array([[13.803851,-3.300067,-3.300067],[-3.300067,13.803851,-3.300067],[-3.300067,-3.300067,13.803851]])


def specs(n=4):
    return tuple(BundleSpec(c,n,.011765,.4572) for c in CENTERS)


def analytic_compound_inverse(a,b):
    # Inversa analítica de (a−b)I + b11ᵀ, independiente del solver del módulo.
    return np.eye(3)/(a-b) - b*np.ones((3,3))/((a-b)*(a+2*b))


def test_required_case_computed_matches_six_decimal_reference():
    r = calculate_transposition(specs(),INPUTS)
    np.testing.assert_allclose(convert_inductance(r.l_h_per_m,"H/m","mH/km"),EXPECTED_L,rtol=0,atol=.5e-6)
    np.testing.assert_allclose(r.c_f_per_m*1e12,EXPECTED_C,rtol=0,atol=.5e-6)
    assert r.inversion_residual < 1e-14


def test_independent_direct_charge_constraints_and_analytic_average():
    g = build_bundles(specs())
    distance = g.real_distances_m.copy()
    np.fill_diagonal(distance,g.radii_m)
    p = np.log(g.image_distances_m/distance)
    e = g.incidence
    # Resolver potenciales y cargas totales impuestos sin invertir la C calculada.
    # P q + E alpha = 0; Eᵀ q = Q. Entonces P_fase = −alpha/Q.
    saddle = np.block([[p,e],[e.T,np.zeros((3,3))]])
    rhs = np.vstack((np.zeros((len(p),3)),np.eye(3)))
    phase_p = -np.linalg.solve(saddle,rhs)[-3:]
    a,b = np.trace(phase_p)/3, (phase_p.sum()-np.trace(phase_p))/6
    expected = FACTOR*analytic_compound_inverse(a,b)
    r = calculate_transposition(specs(),INPUTS)
    np.testing.assert_allclose(r.c_f_per_m,expected,rtol=1e-13,atol=1e-25)
    # Distancias propias con RMG individual: término interno contado una vez.
    np.fill_diagonal(distance,.011765*math.exp(-.25))
    primitive_l = 2e-7*np.log(g.image_distances_m/distance)
    phase_l = g.current_weights.T @ primitive_l @ g.current_weights
    ls,lm = np.trace(phase_l)/3,(phase_l.sum()-np.trace(phase_l))/6
    expected_l = (ls-lm)*np.eye(3)+lm*np.ones((3,3))
    np.testing.assert_allclose(r.l_h_per_m,expected_l,rtol=1e-13,atol=1e-21)


def test_direct_capacitance_average_is_not_used():
    r = calculate_transposition(specs(),INPUTS)
    direct = sum(s.capacitance.phase_f_per_m for s in r.sections)/3
    np.testing.assert_allclose(r.direct_average_c_f_per_m,direct,rtol=1e-14)
    assert abs((r.direct_average_c_f_per_m[0,0]-r.c_f_per_m[0,0])*1e12) > .02
    np.testing.assert_allclose(r.average_phase_p @ r.c_f_per_m/FACTOR,np.eye(3),atol=1e-14,rtol=0)


@pytest.mark.parametrize("n",[1,2,3,4])
@pytest.mark.parametrize("model",[IDEAL_GROUND,NO_GROUND])
def test_tramos_symmetry_permutations_units_and_restrictions(n,model):
    r = calculate_transposition(specs(n),INPUTS,True,model,model)
    assert len(r.sections) == 3
    assignments = np.array([s.phase_to_position for s in r.sections])
    for col in assignments.T:
        assert set(col) == {0,1,2}
    first_l = r.sections[0].inductance.phase_h_per_m
    first_c = r.sections[0].capacitance.phase_f_per_m
    for s in r.sections:
        perm = permutation_matrix(s.phase_to_position)
        np.testing.assert_array_equal(perm.T@perm,np.eye(3))
        np.testing.assert_allclose(s.inductance.phase_h_per_m,perm.T@first_l@perm,rtol=1e-13,atol=1e-21)
        np.testing.assert_allclose(s.capacitance.phase_f_per_m,perm.T@first_c@perm,rtol=1e-13,atol=1e-25)
        assert s.weight == 1/3
    for matrix in (r.l_h_per_m,r.c_f_per_m,r.average_phase_p):
        np.testing.assert_allclose(matrix,matrix.T,rtol=0,atol=1e-20)
    np.testing.assert_allclose(convert_inductance(r.l_h_per_m,"H/m","mH/km"),r.l_h_per_m*1e6)
    x = calculate_reactance(r.l_h_per_m,60)
    np.testing.assert_allclose(x.x_ohm_per_km,2*np.pi*60*1000*r.l_h_per_m)
    target = np.eye(3) if model==IDEAL_GROUND else H
    np.testing.assert_allclose(r.average_phase_p@r.c_f_per_m/FACTOR,target,rtol=0,atol=1e-14)
    if model == NO_GROUND:
        for matrix in (r.l_h_per_m,r.c_f_per_m):
            np.testing.assert_allclose(matrix@np.ones(3),0,atol=1e-20)
            assert np.linalg.matrix_rank(matrix,tol=1e-22) == 2


@pytest.mark.parametrize("n",[1,2,3,4])
@pytest.mark.parametrize("model",[IDEAL_GROUND,NO_GROUND])
def test_no_transposition_conserves_previous_models(n,model):
    g = build_bundles(specs(n))
    original_l = calculate_bundle_inductance(g,INPUTS,model)
    original_c = calculate_bundle_capacitance(g,model)
    r = calculate_transposition(specs(n),INPUTS,False,model,model)
    assert len(r.sections) == 1 and r.sections[0].weight == 1
    expected_l = original_l.phase_h_per_m if model==IDEAL_GROUND else original_l.projected_h_per_m
    np.testing.assert_allclose(r.l_h_per_m,expected_l,rtol=1e-14,atol=1e-21)
    np.testing.assert_allclose(r.c_f_per_m,original_c.phase_f_per_m,rtol=1e-14,atol=1e-25)


def test_phase_properties_follow_phase_and_each_section_is_rebuilt():
    different = tuple(BundleSpec(c,n,r,.3,angle) for c,n,r,angle in zip(CENTERS,(1,2,4),(.01,.012,.015),(0,10,20)))
    data = tuple(RMGInput(s.radius_m,SOLID_UNIFORM) for s in different)
    result = calculate_transposition(different,data)
    for section in result.sections:
        for phase,location in enumerate(section.phase_to_position):
            spec = section.geometry.specs[phase]
            assert spec.count == different[phase].count
            assert spec.radius_m == different[phase].radius_m
            assert spec.rotation_deg == different[phase].rotation_deg
            assert spec.center.x_m == CENTERS[location].x_m
            assert spec.center.y_m == CENTERS[location].y_m
    assert np.ptp(np.diag(result.l_h_per_m)) > 1e-9  # No se impone igualdad artificial.


@pytest.mark.parametrize("ind_model,cap_model",[(IDEAL_GROUND,NO_GROUND),(NO_GROUND,IDEAL_GROUND)])
def test_independent_ground_models(ind_model,cap_model):
    r = calculate_transposition(specs(),INPUTS,True,ind_model,cap_model)
    assert r.inductance_model == ind_model and r.capacitance_model == cap_model
    assert r.inversion_residual < 1e-13


def test_capacitance_does_not_require_inductive_data():
    r = calculate_transposition(specs(),None)
    assert r.l_h_per_m is None
    np.testing.assert_allclose(r.c_f_per_m*1e12,EXPECTED_C,rtol=0,atol=.5e-6)


def test_lengths_and_normalized_fractions():
    assert section_lengths_m(90000,True) == (30000,30000,30000)
    assert section_lengths_m(90000,False) == (90000,)
    for invalid in (None,0,-1,float("nan")):
        with pytest.raises(InputError):
            section_lengths_m(invalid,True)


def test_invalid_modes_circuits_and_permutations():
    for assignment in ((0,0,2),(0,1),(True,1,2)):
        with pytest.raises(InputError):
            permutation_matrix(assignment)
    with pytest.raises(InputError):
        position_assignments("sí")
    with pytest.raises(InputError):
        calculate_transposition(specs(),INPUTS,capacitance_model="carson")
    with pytest.raises(InputError):
        calculate_transposition(specs()[:2],INPUTS)
