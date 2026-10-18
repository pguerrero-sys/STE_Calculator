"""Conversiones métricas exactas; no contiene constantes electromagnéticas."""

from .models import InputError, finite_number

METERS_PER_UNIT = {"mm": 0.001, "cm": 0.01, "m": 1.0, "km": 1000.0}


def convert_length(value: float, from_unit: str, to_unit: str) -> float:
    if from_unit not in METERS_PER_UNIT or to_unit not in METERS_PER_UNIT:
        raise InputError("Unidad no admitida. Usa mm, cm, m o km.")
    number = finite_number(value, "Longitud a convertir")
    result = number * (METERS_PER_UNIT[from_unit] / METERS_PER_UNIT[to_unit])
    return finite_number(result, "Resultado de la conversión")
