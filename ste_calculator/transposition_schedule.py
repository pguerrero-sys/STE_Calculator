"""Planificación combinatoria de circuitos trifásicos, sin ecuaciones físicas.

El plan admite N circuitos; los motores eléctricos existentes admiten solo 1/2.
Cada asignación indica la posición física ocupada por una fase completa.
"""
from dataclasses import dataclass
from itertools import product
import math

from .models import InputError

MODES = ('Sin transposición', 'Transposición ideal completa automática')


@dataclass(frozen=True)
class TranspositionSchedule:
    circuit_count: int
    complete: bool
    assignments: tuple
    weights: tuple


def automatic_schedule(circuit_count, complete=True):
    if type(circuit_count) is not int or circuit_count<1:
        raise InputError('El número de circuitos trifásicos debe ser un entero positivo.')
    if type(complete) is not bool:
        raise InputError('La selección de transposición debe ser booleana.')
    shifts=product(range(3),repeat=circuit_count) if complete else [(0,)*circuit_count]
    assignments=tuple(tuple(3*c+(phase+shift)%3 for c,shift in enumerate(row) for phase in range(3))
                      for row in shifts)
    count=len(assignments)
    # Normalización interna con suma compensada; nunca se relee texto redondeado.
    raw=(1.0/count,)*count
    total=math.fsum(raw)
    weights=tuple(w/total for w in raw)
    return TranspositionSchedule(circuit_count,complete,assignments,weights)


def migrate_mode(value):
    """Conservar activación de sesiones anteriores sin reutilizar planes manuales."""
    return MODES[0] if value is None or str(value).startswith('Sin transposición') else MODES[1]
