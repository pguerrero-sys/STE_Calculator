import math

import numpy as np
import pytest

from ste_calculator.inductance import (
    MU0_H_PER_M, INDUCTANCE_FACTOR_H_PER_M as K, IDEAL_GROUND, NO_GROUND,
    SOLID_UNIFORM, MANUFACTURER, RMGInput, ZERO_SUM_PROJECTOR as H, LOOP_BASIS as B,
    resolve_rmg, calculate_inductance, calculate_reactance, convert_inductance,
    balanced_flux_linkages,
    balanced_trial_currents, inductive_voltage_drop,
)
from ste_calculator.models import Conductor, InputError

CASE = (Conductor(1, "A", -3, 13), Conductor(1, "B", 3, 13), Conductor(1, "C", 0, 9))
PARAMETERS = (RMGInput(.011765, SOLID_UNIFORM),) * 3
EXPECTED = np.array([[1.59014456, .29845590, .29816333],
                     [.29845590, 1.59014456, .29816333],
                     [.29816333, .29816333, 1.51659960]])
CURRENTS = np.array([1, complex(-.5, -math.sqrt(3)/2), complex(-.5, math.sqrt(3)/2)])


def test_mandatory_case_and_rmg_to_supplied_precision():
    result = calculate_inductance(CASE, PARAMETERS)
    np.testing.assert_allclose(result.rmg_m, .00916259121, atol=5e-12, rtol=0)
    np.testing.assert_allclose(convert_inductance(result.l_h_per_m, "H/m", "mH/km"), EXPECTED, atol=5e-9, rtol=0)
    assert MU0_H_PER_M == 4 * math.pi * 1e-7
    assert K == pytest.approx(2e-7, rel=1e-15)


def test_internal_flux_is_included_exactly_once():
    result = calculate_inductance(CASE, PARAMETERS)
    expected = K * np.log(2*np.array([13, 13, 9])/.011765) + MU0_H_PER_M/(8*math.pi)
    np.testing.assert_allclose(np.diag(result.l_h_per_m), expected, atol=0, rtol=1e-14)


def test_real_image_and_image_to_image_distances_at_different_heights():
    result = calculate_inductance(CASE, PARAMETERS)
    np.testing.assert_allclose(result.real_distances_m, [[0,6,5],[6,0,5],[5,5,0]])
    np.testing.assert_array_equal(result.image_positions_m, [[-3,-13],[3,-13],[0,-9]])
    expected_s = [[26, math.sqrt(712), math.sqrt(493)],
                  [math.sqrt(712),26,math.sqrt(493)],[math.sqrt(493),math.sqrt(493),18]]
    np.testing.assert_allclose(result.image_distances_m, expected_s)
    points = result.image_positions_m
    image_to_image = np.hypot(points[:,0,None]-points[None,:,0], points[:,1,None]-points[None,:,1])
    np.testing.assert_allclose(image_to_image, result.real_distances_m)


def test_symmetry_positive_energy_and_flux_decomposition():
    result = calculate_inductance(CASE, PARAMETERS)
    np.testing.assert_allclose(result.l_h_per_m, result.l_h_per_m.T, atol=1e-22, rtol=0)
    assert np.all(np.linalg.eigvalsh(result.l_h_per_m) > 0)
    flux = balanced_flux_linkages(result, CURRENTS)
    np.testing.assert_allclose(np.sum(flux.contributions_wb_turn_per_m, axis=1), result.l_h_per_m @ CURRENTS)
    np.testing.assert_allclose(flux.loop_flux_wb_turn_per_m, B.T @ flux.flux_wb_turn_per_m, atol=1e-21, rtol=1e-14)
    np.testing.assert_allclose(flux.zero_mean_flux_wb_turn_per_m, H @ flux.flux_wb_turn_per_m, atol=1e-21, rtol=1e-14)


@pytest.mark.parametrize("unit", ["µH/m", "mH/km"])
def test_units_have_full_factor_of_one_million(unit):
    np.testing.assert_allclose(convert_inductance([1, -2, 0], "H/m", unit), [1e6,-2e6,0])
    np.testing.assert_allclose(convert_inductance(convert_inductance(EXPECTED,"mH/km", "H/m"), "H/m", unit), EXPECTED)


def test_manufacturer_rmg_used_directly_not_corrected_again():
    data = RMGInput(.011765, MANUFACTURER, .009, "Ficha suministrada, RMG en m")
    assert resolve_rmg(data) == .009
    result = calculate_inductance(CASE, (data,)*3)
    assert result.l_h_per_m[0,0] == pytest.approx(K * math.log(26/.009))


def test_input_reordering_keeps_distinct_radii_and_rmg_association():
    data = tuple(RMGInput(r, SOLID_UNIFORM) for r in (.01,.015,.02))
    first = calculate_inductance(CASE, data)
    reverse = calculate_inductance(tuple(reversed(CASE)), tuple(reversed(data)))
    np.testing.assert_array_equal(first.rmg_m, reverse.rmg_m)
    np.testing.assert_array_equal(first.l_h_per_m, reverse.l_h_per_m)


def test_reference_dependence_and_physical_invariance_without_ground():
    first = calculate_inductance(CASE, PARAMETERS, NO_GROUND, 1)
    second = calculate_inductance(CASE, PARAMETERS, NO_GROUND, 1e8)
    np.testing.assert_allclose(second.l_h_per_m-first.l_h_per_m, K*math.log(1e8)*np.ones((3,3)), atol=1e-21, rtol=1e-14)
    assert first.image_distances_m is None and first.image_positions_m is None
    np.testing.assert_allclose(first.balanced_l_h_per_m, second.balanced_l_h_per_m, atol=1e-21, rtol=1e-14)
    np.testing.assert_allclose(first.loop_l_h_per_m, B.T @ second.l_h_per_m @ B, atol=5e-21, rtol=1e-14)
    np.testing.assert_allclose(first.balanced_l_h_per_m, H @ second.l_h_per_m @ H, atol=5e-21, rtol=1e-14)
    np.testing.assert_allclose(first.l_h_per_m @ CURRENTS, second.l_h_per_m @ CURRENTS, atol=5e-21, rtol=1e-14)
    for matrix in (first.balanced_l_h_per_m, first.loop_l_h_per_m):
        np.testing.assert_allclose(matrix, matrix.T, atol=1e-21, rtol=0)
    assert np.linalg.matrix_rank(first.balanced_l_h_per_m, tol=1e-18) == 2
    np.testing.assert_allclose(first.balanced_l_h_per_m @ np.ones(3), 0, atol=1e-21)
    assert np.all(np.linalg.eigvalsh(first.loop_l_h_per_m) > 0)


@pytest.mark.parametrize("reference", [10.0, 1000.0, 2000.0])
def test_requested_references_match_direct_loop_and_projected_formulas(reference):
    result = calculate_inductance(CASE, PARAMETERS, NO_GROUND, reference)
    ga, gb, gc = result.rmg_m
    # Derivación independiente por cocientes de distancias, sin d0.
    dac, dbc, dab = 5.0, 5.0, 6.0
    direct_loops = K*np.array([
        [math.log(dac*dac/(ga*gc)), math.log(dac*dbc/(dab*gc))],
        [math.log(dac*dbc/(dab*gc)), math.log(dbc*dbc/(gb*gc))],
    ])
    t = np.array([[2,-1],[-1,2],[-1,-1]])/3
    direct_projected = t @ direct_loops @ t.T
    np.testing.assert_allclose(result.loop_l_h_per_m,direct_loops,rtol=1e-14,atol=1e-21)
    np.testing.assert_allclose(result.balanced_l_h_per_m,direct_projected,rtol=1e-14,atol=1e-21)
    # Comprueba también la deducción con la matriz referida de cada d0.
    np.testing.assert_allclose(B.T @ result.l_h_per_m @ B,direct_loops,rtol=1e-14,atol=1e-21)
    np.testing.assert_allclose(H @ result.l_h_per_m @ H,direct_projected,rtol=1e-14,atol=1e-21)
    flux = balanced_flux_linkages(result,CURRENTS)
    np.testing.assert_allclose(flux.zero_mean_flux_wb_turn_per_m,direct_projected@CURRENTS,rtol=1e-14,atol=1e-21)
    np.testing.assert_allclose(flux.loop_flux_wb_turn_per_m,direct_loops@CURRENTS[:2],rtol=1e-14,atol=1e-21)
    x = calculate_reactance(result.balanced_l_h_per_m,60)
    np.testing.assert_allclose(x.x_ohm_per_m,2*math.pi*60*direct_projected,rtol=1e-14,atol=1e-18)


def test_equilateral_balanced_case_has_known_scalar_action_without_transposition():
    distance, height, radius = 6.0, 15.0, .01
    conductors = (Conductor(1,"A",-3,height),Conductor(1,"B",3,height),Conductor(1,"C",0,height+math.sqrt(27)))
    params = (RMGInput(radius, SOLID_UNIFORM),)*3
    result = calculate_inductance(conductors, params, NO_GROUND, 100)
    scalar = K * math.log(distance/(radius*math.exp(-.25)))
    np.testing.assert_allclose(result.l_h_per_m @ CURRENTS, scalar*CURRENTS, atol=2e-21, rtol=1e-14)


def test_common_height_translation_only_affects_model_with_ground():
    raised = tuple(Conductor(c.circuit,c.phase,c.x_m,c.y_m+100) for c in CASE)
    for model in (IDEAL_GROUND, NO_GROUND):
        a = calculate_inductance(CASE, PARAMETERS, model, 10)
        b = calculate_inductance(raised, PARAMETERS, model, 10)
        if model == NO_GROUND:
            np.testing.assert_array_equal(a.l_h_per_m, b.l_h_per_m)
        else:
            assert np.all(np.diag(b.l_h_per_m) > np.diag(a.l_h_per_m))


@pytest.mark.parametrize("model", [IDEAL_GROUND, NO_GROUND])
def test_geometric_scale_invariance_in_physical_space(model):
    scale = 100
    large = tuple(Conductor(1,c.phase,c.x_m*scale,c.y_m*scale) for c in CASE)
    params = tuple(RMGInput(p.radius_m*scale,p.method) for p in PARAMETERS)
    first = calculate_inductance(CASE, PARAMETERS, model, 10)
    second = calculate_inductance(large, params, model, 10)
    np.testing.assert_allclose(first.loop_l_h_per_m, second.loop_l_h_per_m, atol=3e-21, rtol=1e-14)


def test_reactance_uses_si_and_converts_to_ohm_per_km():
    result = calculate_inductance(CASE, PARAMETERS)
    x = calculate_reactance(result.l_h_per_m, 60)
    np.testing.assert_allclose(x.x_ohm_per_m, 2*math.pi*60*result.l_h_per_m, atol=0, rtol=1e-15)
    np.testing.assert_allclose(x.x_ohm_per_km, 2*math.pi*60*EXPECTED*1e-3, atol=2e-9, rtol=0)
    twice = calculate_reactance(result.l_h_per_m, 120)
    np.testing.assert_allclose(twice.x_ohm_per_m, 2*x.x_ohm_per_m)


def test_trial_current_flux_and_inductive_voltage_are_consistent():
    current = balanced_trial_currents(120)
    np.testing.assert_allclose(np.abs(current),120)
    assert abs(np.sum(current)) < 1e-12
    result = calculate_inductance(CASE, PARAMETERS, NO_GROUND, 100)
    flux = balanced_flux_linkages(result,current)
    np.testing.assert_allclose(flux.own_flux_wb_turn_per_m+flux.mutual_flux_wb_turn_per_m,flux.flux_wb_turn_per_m)
    voltage = inductive_voltage_drop(flux.loop_flux_wb_turn_per_m,60)
    x = calculate_reactance(result.loop_l_h_per_m,60)
    np.testing.assert_allclose(voltage,1j*x.x_ohm_per_m@current[:2],atol=1e-16,rtol=1e-14)


def test_invalid_trial_current_and_voltage_inputs():
    for amplitude in (-1,math.nan,math.inf,None):
        with pytest.raises(InputError):
            balanced_trial_currents(amplitude)
    for value,frequency in (([math.nan],60),([1],0),([1],None)):
        with pytest.raises(InputError):
            inductive_voltage_drop(value,frequency)


@pytest.mark.parametrize("frequency", [None, True, 0, -60, math.nan, math.inf, 1e308])
def test_invalid_frequency_or_overflow(frequency):
    with pytest.raises(InputError):
        calculate_reactance(np.eye(3), frequency)


@pytest.mark.parametrize("radius", [None, True, 0, -1, math.nan, math.inf, 13])
def test_invalid_or_ground_touching_radius(radius):
    with pytest.raises(InputError):
        calculate_inductance(CASE, (RMGInput(radius,SOLID_UNIFORM), *PARAMETERS[1:]))


@pytest.mark.parametrize("rmg", [None, True, 0, -1, math.nan, math.inf, .02])
def test_invalid_manufacturer_rmg(rmg):
    with pytest.raises(InputError):
        resolve_rmg(RMGInput(.011765, MANUFACTURER, rmg, "Catálogo"))


@pytest.mark.parametrize("source", ["", "   ", None])
def test_manufacturer_source_required(source):
    with pytest.raises(InputError, match="fuente"):
        resolve_rmg(RMGInput(.011765, MANUFACTURER, .009, source))


@pytest.mark.parametrize("reference", [None, True, 0, -1, math.nan, math.inf])
def test_invalid_distance_reference(reference):
    with pytest.raises(InputError):
        calculate_inductance(CASE, PARAMETERS, NO_GROUND, reference)


@pytest.mark.parametrize("x,y", [(math.nan,13),(math.inf,13),(0,0),(0,-1),(None,13)])
def test_invalid_coordinates(x,y):
    with pytest.raises(InputError):
        calculate_inductance((Conductor(1,"A",x,y),*CASE[1:]), PARAMETERS)


@pytest.mark.parametrize("distance", [0,.019,.02])
def test_conductors_coincident_touching_or_overlapping(distance):
    conductors = (Conductor(1,"A",0,13), Conductor(1,"B",distance,13), CASE[2])
    with pytest.raises(InputError, match="solaparse"):
        calculate_inductance(conductors, (RMGInput(.01,SOLID_UNIFORM),)*3)


def test_unsupported_circuits_duplicate_phases_and_models():
    for conductors in (CASE[:2],(*CASE,Conductor(2,"A",20,13)),(CASE[0],CASE[0],CASE[2])):
        with pytest.raises(InputError, match="un circuito"):
            calculate_inductance(conductors, PARAMETERS)
    with pytest.raises(InputError):
        calculate_inductance(CASE, PARAMETERS[:2])
    with pytest.raises(InputError, match="no implementado"):
        calculate_inductance(CASE, PARAMETERS, "carson")
    with pytest.raises(InputError, match="modelo"):
        resolve_rmg(RMGInput(.01,"ACSR_inventado"))


def test_unrepresentable_distances():
    conductors = (Conductor(1,"A",-1e308,13),Conductor(1,"B",1e308,13),CASE[2])
    with pytest.raises(InputError, match="representables"):
        calculate_inductance(conductors, PARAMETERS)


@pytest.mark.parametrize("currents", [[1,1,1],[1,2],[math.nan,0,0],[math.inf,0,0]])
def test_flux_rejects_nonzero_sum_and_invalid_currents(currents):
    result = calculate_inductance(CASE, PARAMETERS, NO_GROUND, 10)
    with pytest.raises(InputError):
        balanced_flux_linkages(result, currents)


def test_invalid_units_and_nonfinite_matrix():
    with pytest.raises(InputError):
        convert_inductance(1,"H/km","mH/km")
    with pytest.raises(InputError):
        convert_inductance(math.nan,"H/m","mH/km")
    with pytest.raises(InputError):
        calculate_reactance([[1,2,3]],60)
