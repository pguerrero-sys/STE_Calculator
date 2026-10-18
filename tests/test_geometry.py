import math

import numpy as np
import pytest

from ste_calculator.geometry import calculate_geometry
from ste_calculator.models import Conductor, InputError, LineInput


def make_line(conductors=None, **kwargs):
    values = dict(circuit_count=1, frequency_hz=60.0, length_m=1000.0,
                  conductors=conductors or (Conductor(1, "A", -1, 2), Conductor(1, "B", 2, 6), Conductor(1, "C", 2, 2)))
    values.update(kwargs)
    return LineInput(**values)


def test_known_triangle_and_matrix():
    result = calculate_geometry(make_line())
    assert [p.distance_m for p in result.pairs] == pytest.approx([5, 3, 4])
    np.testing.assert_allclose(result.matrix_m, [[0, 5, 3], [5, 0, 4], [3, 4, 0]])
    assert result.pairs[0].dx_m == 3
    assert result.pairs[0].dy_m == 4


def test_two_circuits_include_cross_circuit_pairs():
    conductors = tuple(Conductor(c, p, float(c * 10 + i), 5.0)
                       for c in (1, 2) for i, p in enumerate(("A", "B", "C")))
    result = calculate_geometry(make_line(conductors, circuit_count=2))
    assert len(result.pairs) == 15
    assert result.matrix_m[0, 3] == 10


def test_translation_and_input_order_invariance():
    line = make_line()
    moved = tuple(Conductor(c.circuit, c.phase, c.x_m + 100, c.y_m + 20) for c in line.conductors)
    np.testing.assert_allclose(calculate_geometry(line).matrix_m, calculate_geometry(make_line(moved)).matrix_m)
    np.testing.assert_allclose(calculate_geometry(make_line(tuple(reversed(line.conductors)))).matrix_m,
                               calculate_geometry(line).matrix_m[::-1, ::-1])


@pytest.mark.parametrize("field,value", [("frequency_hz", 0), ("frequency_hz", -1), ("length_m", 0),
    ("length_m", math.inf), ("circuit_count", 0), ("circuit_count", 1.5), ("circuit_count", True)])
def test_invalid_line_values(field, value):
    with pytest.raises(InputError):
        calculate_geometry(make_line(**{field: value}))


@pytest.mark.parametrize("x,y", [(math.nan, 3), (math.inf, 3), (0, 0), (0, -1), (None, 3)])
def test_invalid_coordinates(x, y):
    line = make_line()
    conductors = (Conductor(1, "A", x, y), *line.conductors[1:])
    with pytest.raises(InputError):
        calculate_geometry(make_line(conductors))


def test_coincident_conductors_rejected():
    with pytest.raises(InputError, match="coincidir"):
        calculate_geometry(make_line((Conductor(1, "A", 2, 2), Conductor(1, "B", 2, 2), Conductor(1, "C", 4, 2))))


def test_missing_or_duplicate_phase_rejected():
    line = make_line()
    for conductors in (line.conductors[:2], (*line.conductors[:2], line.conductors[0])):
        with pytest.raises(InputError, match="exactamente"):
            calculate_geometry(make_line(conductors))


def test_extreme_coordinates_report_error():
    with pytest.raises(InputError, match="representable"):
        calculate_geometry(make_line((Conductor(1, "A", -1e308, 2), Conductor(1, "B", 1e308, 2), Conductor(1, "C", 0, 2))))
