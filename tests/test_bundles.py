import math

import numpy as np
import pytest

from ste_calculator.bundles import BundleSpec, build_bundles
from ste_calculator.bundle_electrical import (calculate_bundle_capacitance,calculate_bundle_inductance,
                                              calculate_center_capacitance_approximation)
from ste_calculator.capacitance import calculate_capacitance, VACUUM_PERMITTIVITY_F_PER_M
from ste_calculator.inductance import (calculate_inductance,RMGInput,SOLID_UNIFORM,MANUFACTURER,
                                      IDEAL_GROUND,NO_GROUND,INDUCTANCE_FACTOR_H_PER_M as K,
                                      ZERO_SUM_PROJECTOR as H)
from ste_calculator.models import Conductor,InputError

CENTERS = (Conductor(1,"A",-3,13),Conductor(1,"B",3,13),Conductor(1,"C",0,9))
RADIUS = .011765
INPUTS = (RMGInput(RADIUS,SOLID_UNIFORM),)*3


def geometry(n=1,spacing=.4,centers=CENTERS):
    return build_bundles(tuple(BundleSpec(c,n,RADIUS,spacing) for c in centers))


def closed_form(n,t,s):
    return {1: t,2: math.sqrt(t*s),3:(t*s*s)**(1/3),4:(t*math.sqrt(2)*s**3)**.25}[n]


@pytest.mark.parametrize("n",[1,2,3,4])
def test_regular_bundle_geometry_and_verified_closed_forms(n):
    g = geometry(n)
    l = calculate_bundle_inductance(g,INPUTS)
    assert len(g.positions_m) == 3*n
    for p in range(3):
        pts = g.positions_m[g.phase_index == p]
        np.testing.assert_allclose(pts.mean(axis=0),[CENTERS[p].x_m,CENTERS[p].y_m],atol=1e-14)
        if n > 1:
            block = g.real_distances_m[np.ix_(g.phase_index==p,g.phase_index==p)]
            assert np.min(block[~np.eye(n,dtype=bool)]) == pytest.approx(.4)
        assert g.capacitive_radius_m[p] == pytest.approx(closed_form(n,RADIUS,.4),rel=1e-13)
        assert l.equivalent_rmg_m[p] == pytest.approx(closed_form(n,RADIUS*math.exp(-.25),.4),rel=1e-13)
        assert l.equivalent_rmg_m[p]/g.capacitive_radius_m[p] == pytest.approx(math.exp(-.25/n),rel=1e-13)


@pytest.mark.parametrize("n",[1,2,3,4])
@pytest.mark.parametrize("model",[IDEAL_GROUND,NO_GROUND])
def test_capacitance_equipotential_reduction_symmetry_energy_and_neutrality(n,model):
    g = geometry(n)
    c = calculate_bundle_capacitance(g,model)
    factor = 2*math.pi*VACUUM_PERMITTIVITY_F_PER_M
    w = c.charge_response_f_per_m/factor
    difference = c.potential_coefficients @ w-g.incidence
    if model == IDEAL_GROUND:
        np.testing.assert_allclose(difference,0,atol=1e-13)
        assert np.all(np.linalg.eigvalsh(c.phase_f_per_m) > 0)
    else:
        np.testing.assert_allclose(difference-difference.mean(axis=0),0,atol=1e-13)
        np.testing.assert_allclose(np.sum(w,axis=0),0,atol=1e-13)
        np.testing.assert_allclose(c.phase_f_per_m @ np.ones(3)/factor,0,atol=1e-13)
        assert np.linalg.matrix_rank(c.phase_f_per_m,tol=1e-22) == 2
    np.testing.assert_allclose(c.phase_f_per_m,c.phase_f_per_m.T,rtol=1e-13,atol=1e-25)
    np.testing.assert_allclose(g.incidence.T @ c.charge_response_f_per_m,c.phase_f_per_m,rtol=1e-14)
    assert c.equipotential_residual < 1e-12
    energy = np.array([1.,-.5,-.5]) @ c.phase_f_per_m @ np.array([1.,-.5,-.5])
    assert energy > 0


@pytest.mark.parametrize("n",[1,2,3,4])
@pytest.mark.parametrize("model",[IDEAL_GROUND,NO_GROUND])
def test_inductance_equals_uniform_current_primitive_aggregation_and_gm(n,model):
    g = geometry(n)
    result = calculate_bundle_inductance(g,INPUTS,model)
    np.testing.assert_allclose(result.phase_h_per_m,g.current_weights.T @ result.primitive_h_per_m @ g.current_weights,atol=1e-21)
    np.testing.assert_allclose(result.phase_h_per_m,result.phase_h_per_m.T,atol=1e-21,rtol=1e-14)
    if model == IDEAL_GROUND:
        expected = np.empty((3,3))
        for i in range(3):
            expected[i,i] = K*math.log(g.equivalent_images_m[i,i]/result.equivalent_rmg_m[i])
            for j in range(3):
                if i != j:
                    expected[i,j] = K*math.log(g.equivalent_images_m[i,j]/g.equivalent_distances_m[i,j])
        np.testing.assert_allclose(result.phase_h_per_m,expected,rtol=1e-13,atol=1e-21)
    else:
        assert np.linalg.matrix_rank(result.projected_h_per_m,tol=1e-18) == 2
        np.testing.assert_allclose(result.projected_h_per_m @ np.ones(3),0,atol=1e-21)
        assert np.all(np.linalg.eigvalsh(result.loops_h_per_m) > 0)


@pytest.mark.parametrize("model",[IDEAL_GROUND,NO_GROUND])
def test_one_subconductor_reproduces_verified_modules(model):
    g = geometry(1)
    original_l = calculate_inductance(CENTERS,INPUTS,model,1)
    bundle_l = calculate_bundle_inductance(g,INPUTS,model)
    np.testing.assert_allclose(bundle_l.phase_h_per_m,original_l.l_h_per_m,atol=1e-21,rtol=1e-14)
    np.testing.assert_allclose(bundle_l.projected_h_per_m,original_l.balanced_l_h_per_m,atol=1e-21,rtol=1e-14)
    c = calculate_bundle_capacitance(g,model)
    if model == IDEAL_GROUND:
        original_c = calculate_capacitance(CENTERS,(RADIUS,)*3)
        np.testing.assert_allclose(c.phase_f_per_m,original_c.c_f_per_m,rtol=1e-14,atol=1e-25)
    approx = calculate_center_capacitance_approximation(g,model)
    np.testing.assert_allclose(c.phase_f_per_m,approx.phase_f_per_m,rtol=1e-14,atol=1e-25)


def test_free_space_equilateral_single_conductor_analytic_case():
    centers = (Conductor(1,"A",-3,13),Conductor(1,"B",3,13),Conductor(1,"C",0,13+math.sqrt(27)))
    g = geometry(1,centers=centers)
    expected_c = 2*math.pi*VACUUM_PERMITTIVITY_F_PER_M/math.log(6/RADIUS)*H
    np.testing.assert_allclose(calculate_bundle_capacitance(g,NO_GROUND).phase_f_per_m,expected_c,rtol=1e-13,atol=1e-25)


def test_explicit_charges_are_not_forced_equal_and_center_is_an_approximation():
    g = geometry(4)
    c = calculate_bundle_capacitance(g)
    a_charges = c.charge_response_f_per_m[g.phase_index==0,0]
    assert np.ptp(a_charges) > 1e-16
    approx = calculate_center_capacitance_approximation(g)
    assert np.max(np.abs(c.phase_f_per_m-approx.phase_f_per_m)) > 1e-17


def test_manufacturer_rmg_does_not_change_capacitive_radius_or_capacitance():
    g = geometry(3)
    cap = calculate_bundle_capacitance(g)
    data = (RMGInput(RADIUS,MANUFACTURER,.008,"Ficha de ensayo en metros"),)*3
    result = calculate_bundle_inductance(g,data)
    np.testing.assert_allclose(result.individual_rmg_m,.008)
    assert result.equivalent_rmg_m[0] == pytest.approx(closed_form(3,.008,.4))
    np.testing.assert_array_equal(cap.phase_f_per_m,calculate_bundle_capacitance(g).phase_f_per_m)
    with pytest.raises(InputError,match="fuente"):
        calculate_bundle_inductance(g,(RMGInput(RADIUS,MANUFACTURER,.008),)*3)


def test_mixed_counts_sizes_order_and_rotation():
    specs = tuple(BundleSpec(c,n,RADIUS,.4,17*p) for p,(c,n) in enumerate(zip(CENTERS,(2,3,4))))
    a,b = build_bundles(specs),build_bundles(tuple(reversed(specs)))
    assert len(a.positions_m) == 9
    np.testing.assert_array_equal(a.positions_m,b.positions_m)
    np.testing.assert_allclose(a.current_weights.sum(axis=0),1)
    np.testing.assert_allclose(calculate_bundle_capacitance(a).phase_f_per_m,calculate_bundle_capacitance(b).phase_f_per_m)


def test_two_conductor_mutual_gm_and_own_image_gm_are_not_center_distances():
    g = geometry(2)
    # Cuatro distancias entre los haces A y B: 6, 6−s, 6+s, 6 m.
    expected_d = (6*6*(6-.4)*(6+.4))**.25
    expected_saa = math.sqrt(26*math.hypot(26,.4))
    assert g.equivalent_distances_m[0,1] == pytest.approx(expected_d,rel=1e-14)
    assert g.equivalent_images_m[0,0] == pytest.approx(expected_saa,rel=1e-14)
    assert abs(g.equivalent_distances_m[0,1]-6) > .001
    assert abs(g.equivalent_images_m[0,0]-26) > .001


@pytest.mark.parametrize("n",[2,3,4])
def test_no_ground_common_scale_translation_invariance(n):
    original = geometry(n)
    moved = build_bundles(tuple(BundleSpec(Conductor(1,c.phase,c.x_m*10+50,c.y_m*10+30),n,RADIUS*10,4) for c in CENTERS))
    a = calculate_bundle_capacitance(original,NO_GROUND)
    b = calculate_bundle_capacitance(moved,NO_GROUND)
    np.testing.assert_allclose(a.phase_f_per_m,b.phase_f_per_m,rtol=1e-12,atol=1e-24)


@pytest.mark.parametrize("count",[0,5,1.5,True])
def test_invalid_count(count):
    with pytest.raises(InputError):
        build_bundles(tuple(BundleSpec(c,count,RADIUS,.4) for c in CENTERS))


@pytest.mark.parametrize("radius,spacing",[(0,.4),(-1,.4),(math.nan,.4),(.01,None),(.01,0),(.01,.02),(.01,math.inf)])
def test_invalid_radius_spacing_and_touching(radius,spacing):
    with pytest.raises(InputError):
        build_bundles(tuple(BundleSpec(c,2,radius,spacing) for c in CENTERS))


def test_ground_contact_cross_phase_overlap_and_unsupported_circuit():
    for centers in (
        (Conductor(1,"A",-3,.1),*CENTERS[1:]),
        (CENTERS[1],Conductor(1,"A",3,13),CENTERS[2]),
        (Conductor(2,"A",-3,13),*CENTERS[1:]),
    ):
        with pytest.raises(InputError):
            geometry(4,centers=centers)
    with pytest.raises(InputError):
        calculate_bundle_capacitance(geometry(1),"carson")


def test_inductive_radius_must_match_geometry_and_models_validate():
    with pytest.raises(InputError,match="coincidir"):
        calculate_bundle_inductance(geometry(),(RMGInput(.02,SOLID_UNIFORM),)*3)
    with pytest.raises(InputError):
        calculate_bundle_inductance(geometry(),INPUTS[:2])
    with pytest.raises(InputError):
        calculate_bundle_inductance(geometry(),(RMGInput(None,SOLID_UNIFORM),)*3)
