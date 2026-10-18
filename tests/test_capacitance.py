import math

import numpy as np
import pytest

from ste_calculator.capacitance import (
    VACUUM_PERMITTIVITY_F_PER_M, calculate_capacitance,
    capacitance_to_f_per_m, capacitance_to_nf_per_km,
)
from ste_calculator.models import Conductor, InputError


CASE = (Conductor(1, "A", -3, 13), Conductor(1, "B", 3, 13), Conductor(1, "C", 0, 9))
RADII = (.011765,) * 3
EXPECTED_NF_PER_KM = np.array([
    [7.719800, -1.240982, -1.317160],
    [-1.240982, 7.719800, -1.317160],
    [-1.317160, -1.317160, 8.122161],
])


def test_mandatory_case_matches_six_decimal_reference():
    result = calculate_capacitance(CASE, RADII)
    np.testing.assert_allclose(result.c_nf_per_km, EXPECTED_NF_PER_KM, atol=0.5e-6, rtol=0)
    np.testing.assert_allclose(result.real_distances_m, [[0, 6, 5], [6, 0, 5], [5, 5, 0]])
    np.testing.assert_allclose(result.image_distances_m,
        [[26, math.sqrt(712), math.sqrt(493)], [math.sqrt(712), 26, math.sqrt(493)], [math.sqrt(493), math.sqrt(493), 18]])
    assert result.p[0, 0] == pytest.approx(math.log(26 / .011765))
    assert result.p[0, 1] == pytest.approx(math.log(math.sqrt(712) / 6))


def test_symmetry_positive_definiteness_invertibility_and_identity_in_si():
    result = calculate_capacitance(CASE, RADII)
    for matrix in (result.p, result.p_inverse, result.c_f_per_m):
        np.testing.assert_allclose(matrix, matrix.T, rtol=1e-14, atol=0)
        assert np.all(np.linalg.eigvalsh(matrix) > 0)
        assert np.linalg.matrix_rank(matrix) == 3
    factor = 2 * math.pi * VACUUM_PERMITTIVITY_F_PER_M
    # La normalización evita que un atol grande acepte matrices pequeñas incorrectas.
    np.testing.assert_allclose((result.p @ result.c_f_per_m) / factor, np.eye(3), atol=1e-14, rtol=0)
    assert result.normalized_residual < 1e-14
    assert np.all(np.diag(result.c_f_per_m) > 0)
    assert np.all(result.c_f_per_m[~np.eye(3, dtype=bool)] < 0)


def test_known_symmetric_line_antisymmetric_mode():
    # Para centros (-d,h),(0,h),(d,h), [1,0,-1] es autovector de P.
    d, h, radius = 4.0, 12.0, .01
    conductors = tuple(Conductor(1, phase, x, h) for phase, x in zip("ABC", (-d, 0, d)))
    result = calculate_capacitance(conductors, (radius,) * 3)
    a = math.log(2 * h / radius)
    c = math.log(math.hypot(2 * d, 2 * h) / (2 * d))
    vector = np.array([1, 0, -1])
    expected = 2 * math.pi * VACUUM_PERMITTIVITY_F_PER_M / (a - c) * vector
    np.testing.assert_allclose(result.c_f_per_m @ vector, expected, atol=1e-26, rtol=1e-13)


def test_far_separated_limit_matches_isolated_line_charge_model():
    h, radius = 10.0, .01
    conductors = tuple(Conductor(1, phase, x, h) for phase, x in zip("ABC", (-1e8, 0, 1e8)))
    result = calculate_capacitance(conductors, (radius,) * 3)
    isolated = 2 * math.pi * VACUUM_PERMITTIVITY_F_PER_M / math.log(2 * h / radius)
    np.testing.assert_allclose(np.diag(result.c_f_per_m), isolated, rtol=1e-13)
    assert np.max(np.abs(result.c_f_per_m[~np.eye(3, dtype=bool)])) < isolated * 1e-12


def test_common_geometric_scale_and_horizontal_translation_do_not_change_c():
    baseline = calculate_capacitance(CASE, RADII)
    moved = tuple(Conductor(1, c.phase, c.x_m * 100 + 3000, c.y_m * 100) for c in CASE)
    result = calculate_capacitance(moved, tuple(r * 100 for r in RADII))
    np.testing.assert_allclose(result.c_f_per_m, baseline.c_f_per_m, atol=0, rtol=1e-13)


def test_input_order_preserves_radius_association_and_returns_abc():
    radii = (.01, .02, .03)
    first = calculate_capacitance(CASE, radii)
    reverse = calculate_capacitance(tuple(reversed(CASE)), tuple(reversed(radii)))
    assert reverse.labels == ("A", "B", "C")
    np.testing.assert_allclose(first.c_f_per_m, reverse.c_f_per_m)


def test_permittivity_scales_c_linearly_without_changing_p():
    first = calculate_capacitance(CASE, RADII)
    second = calculate_capacitance(CASE, RADII, epsilon0_f_per_m=2 * VACUUM_PERMITTIVITY_F_PER_M)
    np.testing.assert_array_equal(first.p, second.p)
    np.testing.assert_allclose(second.c_f_per_m, 2 * first.c_f_per_m)


def test_capacitance_units_preserve_negative_mutual_entries_and_round_trip():
    np.testing.assert_allclose(capacitance_to_nf_per_km([1e-12, -2e-12, 0]), [1, -2, 0])
    assert capacitance_to_nf_per_km(1) == 1e12
    result = calculate_capacitance(CASE, RADII)
    np.testing.assert_allclose(capacitance_to_f_per_m(result.c_nf_per_km), result.c_f_per_m, atol=0, rtol=1e-15)


@pytest.mark.parametrize("radius", [None, 0, -1, math.nan, math.inf, 13, 14])
def test_invalid_radius_rejected(radius):
    with pytest.raises(InputError):
        calculate_capacitance(CASE, (radius, .011765, .011765))


@pytest.mark.parametrize("epsilon", [None, 0, -1, math.nan, math.inf, 1e308])
def test_invalid_or_unrepresentable_permittivity_rejected(epsilon):
    with pytest.raises(InputError):
        calculate_capacitance(CASE, RADII, epsilon)


@pytest.mark.parametrize("x,y", [(math.nan, 13), (0, math.inf), (0, -1), (0, 0)])
def test_invalid_coordinates_rejected(x, y):
    with pytest.raises(InputError):
        calculate_capacitance((Conductor(1, "A", x, y), *CASE[1:]), RADII)


@pytest.mark.parametrize("separation", [0, .019, .02])
def test_coincidence_overlap_and_contact_rejected(separation):
    conductors = (Conductor(1, "A", 0, 13), Conductor(1, "B", separation, 13), CASE[2])
    with pytest.raises(InputError, match="solaparse"):
        calculate_capacitance(conductors, (.01,) * 3)


def test_unsupported_circuits_duplicate_phases_and_missing_radius():
    for conductors in (CASE[:2], (*CASE, Conductor(2, "A", 30, 13)), (CASE[0], CASE[0], CASE[2])):
        with pytest.raises(InputError, match="un circuito"):
            calculate_capacitance(conductors, RADII)
    with pytest.raises(InputError, match="radio exterior"):
        calculate_capacitance(CASE, RADII[:2])


def test_nonrepresentable_distances_rejected():
    with pytest.raises(InputError, match="representables"):
        calculate_capacitance((Conductor(1, "A", -1e308, 13), Conductor(1, "B", 1e308, 13), CASE[2]), RADII)


@pytest.mark.parametrize("convert", [capacitance_to_nf_per_km, capacitance_to_f_per_m])
def test_invalid_capacitance_conversion(convert):
    with pytest.raises(InputError):
        convert([math.nan, math.inf])
