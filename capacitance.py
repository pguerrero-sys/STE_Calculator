"""Capacitancia de Maxwell por imágenes, SI. Fuentes: referencias/capacitancia.md.

Un circuito A/B/C, un conductor circular por fase, aire y plano de suelo ideal.
No depende de Streamlit ni modifica las funciones de geometría existentes.
"""

from dataclasses import dataclass

import numpy as np
from scipy.linalg import cho_factor, cho_solve

from .models import Conductor, InputError, PHASES, finite_number

# Cifra indicada por el usuario, no una propiedad inferida de un conductor.
VACUUM_PERMITTIVITY_F_PER_M = 8.8541878128e-12
NF_PER_KM_PER_F_PER_M = 1e12
# Límite de estabilidad numérica de software, no una restricción normativa.
MAX_CONDITION_NUMBER = 1e12


@dataclass(frozen=True)
class CapacitanceResult:
    labels: tuple[str, ...]
    conductors: tuple[Conductor, ...]
    radii_m: np.ndarray
    epsilon0_f_per_m: float
    real_distances_m: np.ndarray
    image_distances_m: np.ndarray
    p: np.ndarray
    p_inverse: np.ndarray
    c_f_per_m: np.ndarray
    c_nf_per_km: np.ndarray
    condition_number: float
    identity_product_f_per_m: np.ndarray
    identity_target_f_per_m: np.ndarray
    normalized_residual: float


def capacitance_to_nf_per_km(value):
    """Convierte F/m a nF/km, elemento a elemento; conserva signos."""
    values = np.asarray(value, dtype=float)
    with np.errstate(over="ignore", invalid="ignore"):
        converted = values * NF_PER_KM_PER_F_PER_M
    if not np.all(np.isfinite(converted)):
        raise InputError("La capacitancia o su conversión no es finita.")
    return converted


def capacitance_to_f_per_m(value):
    """Conversión inversa de nF/km a F/m."""
    values = np.asarray(value, dtype=float)
    if not np.all(np.isfinite(values)):
        raise InputError("La capacitancia no es finita.")
    return values / NF_PER_KM_PER_F_PER_M


def calculate_capacitance(
    conductors: tuple[Conductor, ...],
    radii_m: tuple[float, ...],
    epsilon0_f_per_m: float = VACUUM_PERMITTIVITY_F_PER_M,
) -> CapacitanceResult:
    """Radios alineados con los conductores de entrada; salida ordenada A/B/C.

    Solo recibe coordenadas y radios exteriores: no acepta GMR, haces,
    transposición ni parámetros longitudinales o de suelo no ideal.
    """
    if len(conductors) != 3 or {(c.circuit, c.phase) for c in conductors} != {(1, p) for p in PHASES}:
        raise InputError("Capacitancia disponible solo para un circuito con tres conductores: A, B y C.")
    if len(radii_m) != 3:
        raise InputError("Ingresa un radio exterior para cada una de las tres fases.")
    epsilon = finite_number(epsilon0_f_per_m, "Permitividad [F/m]")
    if epsilon <= 0:
        raise InputError("La permitividad debe ser positiva.")
    paired = sorted(zip(conductors, radii_m), key=lambda item: PHASES.index(item[0].phase))
    ordered = tuple(item[0] for item in paired)
    radii = np.array([finite_number(item[1], f"Radio exterior {item[0].phase} [m]") for item in paired])
    coords = np.array([[finite_number(c.x_m, f"{c.label}, X"), finite_number(c.y_m, f"{c.label}, Y")] for c in ordered])
    if np.any(radii <= 0):
        raise InputError("Los radios exteriores deben ser mayores que cero.")
    if np.any(coords[:, 1] <= radii):
        raise InputError("El radio exterior de cada fase debe ser menor que su altura: el conductor no puede tocar el suelo.")
    with np.errstate(over="ignore", invalid="ignore"):
        dx = coords[:, 0, None] - coords[None, :, 0]
        dy = coords[:, 1, None] - coords[None, :, 1]
        height_sum = coords[:, 1, None] + coords[None, :, 1]
        real = np.hypot(dx, dy)
        images = np.hypot(dx, height_sum)
        radius_sum = radii[:, None] + radii[None, :]
    if not all(np.all(np.isfinite(a)) for a in (real, images, radius_sum)):
        raise InputError("Distancias no representables; revisa la magnitud de las coordenadas o radios.")
    off_diagonal = ~np.eye(3, dtype=bool)
    if np.any(real[off_diagonal] <= radius_sum[off_diagonal]):
        raise InputError("Los conductores no pueden coincidir, tocarse ni solaparse.")
    p = np.empty((3, 3))
    # Diferencia de logaritmos = logaritmo del cociente, sin desbordar S/r.
    p[off_diagonal] = np.log(images[off_diagonal]) - np.log(real[off_diagonal])
    np.fill_diagonal(p, np.log(np.diag(images)) - np.log(radii))
    if not np.all(np.isfinite(p)):
        raise InputError("La matriz P no es finita.")
    condition = float(np.linalg.cond(p))
    if not np.isfinite(condition) or condition > MAX_CONDITION_NUMBER:
        raise InputError("La matriz P es singular o está mal condicionada para una inversión fiable.")
    try:
        inverse = cho_solve(cho_factor(p, lower=True), np.eye(3))
    except np.linalg.LinAlgError as exc:
        raise InputError("La matriz P no es definida positiva; revisa la geometría y los radios.") from exc
    factor = 2 * np.pi * epsilon
    with np.errstate(over="ignore", invalid="ignore", divide="ignore"):
        c = factor * inverse
        product = p @ c
        target = factor * np.eye(3)
        residual = float(np.max(np.abs(product / factor - np.eye(3))))
    if not np.all(np.isfinite(c)) or not np.isfinite(residual) or residual > 1e-10:
        raise InputError("No se pudo comprobar P × C = 2πε₀ I con precisión numérica suficiente.")
    return CapacitanceResult(
        PHASES, ordered, radii, epsilon, real, images, p, inverse, c,
        capacitance_to_nf_per_km(c), condition, product, target, residual,
    )
