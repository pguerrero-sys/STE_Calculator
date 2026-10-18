"""Datos de entrada y validación, sin dependencias de la interfaz."""

from dataclasses import dataclass, field
import math

PHASES = ("A", "B", "C")


class InputError(ValueError):
    """Entrada que no cumple las condiciones de la etapa geométrica."""


def finite_number(value: object, name: str) -> float:
    if value is None or isinstance(value, bool):
        raise InputError(f"{name}: ingresa un número finito.")
    try:
        number = float(value)
    except (ValueError, TypeError, OverflowError) as exc:
        raise InputError(f"{name}: ingresa un número finito (usa punto decimal).") from exc
    if not math.isfinite(number):
        raise InputError(f"{name}: no se permiten NaN ni infinito.")
    return number


@dataclass(frozen=True)
class Conductor:
    circuit: int
    phase: str
    x_m: float
    y_m: float

    @property
    def label(self) -> str:
        return f"C{self.circuit}-{self.phase}"


@dataclass(frozen=True)
class FutureOptions:
    """Metadatos reservados: no participan en ningún cálculo de esta etapa."""

    transposition: bool = False
    ground_effect: bool = False
    conductor_reference: str = ""
    material_notes: str = ""
    bundle_count: int = 1
    bundle_spacing_notes: str = ""


@dataclass(frozen=True)
class LineInput:
    circuit_count: int
    frequency_hz: float
    length_m: float
    conductors: tuple[Conductor, ...]
    future: FutureOptions = field(default_factory=FutureOptions)

    def validate(self) -> None:
        if isinstance(self.circuit_count, bool) or not isinstance(self.circuit_count, int):
            raise InputError("El número de circuitos debe ser un entero.")
        if not 1 <= self.circuit_count <= 12:
            raise InputError("Se admiten entre 1 y 12 circuitos trifásicos en esta interfaz.")
        if finite_number(self.frequency_hz, "Frecuencia") <= 0:
            raise InputError("La frecuencia debe ser mayor que cero.")
        if finite_number(self.length_m, "Longitud") <= 0:
            raise InputError("La longitud debe ser mayor que cero.")
        expected = {(c, p) for c in range(1, self.circuit_count + 1) for p in PHASES}
        identities = [(c.circuit, c.phase) for c in self.conductors]
        if len(identities) != len(set(identities)) or set(identities) != expected:
            raise InputError("Debe existir exactamente una posición para cada fase A, B y C de cada circuito.")
        positions = set()
        for c in self.conductors:
            x = finite_number(c.x_m, f"{c.label}, X")
            y = finite_number(c.y_m, f"{c.label}, Y")
            if y <= 0:
                raise InputError(f"{c.label}: Y debe ser mayor que 0 m, por encima del terreno de referencia.")
            if (x, y) in positions:
                raise InputError(f"{c.label}: dos posiciones de fase no pueden coincidir.")
            positions.add((x, y))
