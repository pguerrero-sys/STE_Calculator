import math

import pytest

from ste_calculator.models import InputError
from ste_calculator.units import convert_length


@pytest.mark.parametrize("value,source,target,expected", [
    (1, "km", "m", 1000), (1500, "m", "km", 1.5), (1, "m", "mm", 1000),
    (10, "mm", "cm", 1), (3, "cm", "m", .03), (0, "m", "km", 0), (-2, "m", "cm", -200),
])
def test_metric_conversions(value, source, target, expected):
    assert convert_length(value, source, target) == pytest.approx(expected)


@pytest.mark.parametrize("unit", ["mm", "cm", "m", "km"])
def test_round_trip(unit):
    assert convert_length(convert_length(1.23456, unit, "m"), "m", unit) == pytest.approx(1.23456)


@pytest.mark.parametrize("value", [None, True, "incorrecto", math.nan, math.inf, -math.inf])
def test_invalid_values(value):
    with pytest.raises(InputError):
        convert_length(value, "m", "km")


def test_unknown_unit():
    with pytest.raises(InputError, match="Unidad"):
        convert_length(1, "ft", "m")


def test_conversion_overflow():
    with pytest.raises(InputError):
        convert_length(1e308, "km", "mm")
