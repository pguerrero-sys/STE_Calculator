"""Distancias euclidianas en metros; independiente de Streamlit y Plotly."""

from dataclasses import dataclass
import math

import numpy as np
from scipy.spatial.distance import squareform

from .models import Conductor, InputError, LineInput


@dataclass(frozen=True)
class PairDistance:
    first: Conductor
    second: Conductor
    dx_m: float
    dy_m: float
    distance_m: float


@dataclass(frozen=True)
class GeometryResult:
    labels: tuple[str, ...]
    pairs: tuple[PairDistance, ...]
    matrix_m: np.ndarray


def calculate_geometry(data: LineInput) -> GeometryResult:
    data.validate()
    pairs = []
    for i, first in enumerate(data.conductors):
        for second in data.conductors[i + 1:]:
            dx = second.x_m - first.x_m
            dy = second.y_m - first.y_m
            # hypot evalúa Pitágoras sin elevar valores grandes al cuadrado.
            with np.errstate(over="ignore", invalid="ignore"):
                distance = float(np.hypot(dx, dy))
            if not all(math.isfinite(v) for v in (dx, dy, distance)) or distance <= 0:
                raise InputError("Las coordenadas producen una distancia no representable; revisa su magnitud.")
            pairs.append(PairDistance(first, second, dx, dy, distance))
    matrix = squareform(np.array([p.distance_m for p in pairs], dtype=float))
    return GeometryResult(tuple(c.label for c in data.conductors), tuple(pairs), matrix)
