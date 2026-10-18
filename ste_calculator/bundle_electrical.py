"""Modelos eléctricos de haces. Ver fuentes y supuestos en referencias/haces.md."""

from dataclasses import dataclass
import math

import numpy as np
from scipy.linalg import cho_factor, cho_solve, null_space

from .bundles import BundleGeometry, BundleSpec, build_bundles, own_geometric_mean
from .capacitance import VACUUM_PERMITTIVITY_F_PER_M
from .inductance import (
    IDEAL_GROUND, NO_GROUND, RMGInput, resolve_rmg,
    INDUCTANCE_FACTOR_H_PER_M, ZERO_SUM_PROJECTOR, LOOP_BASIS,
)
from .models import InputError, finite_number


def _validate_model(model):
    if model not in (IDEAL_GROUND,NO_GROUND):
        raise InputError("Solo se admite suelo ideal o el modelo restringido sin suelo. Carson no está implementado.")


def _check_positive(matrix):
    if not np.all(np.isfinite(matrix)):
        raise InputError("La matriz no es finita.")
    condition = float(np.linalg.cond(matrix))
    if not math.isfinite(condition) or condition > 1e12 or np.min(np.linalg.eigvalsh(matrix)) <= 0:
        raise InputError("El sistema físico no es definido positivo o está mal condicionado.")
    return condition


def _coefficients(geometry, self_radii, model):
    _validate_model(model)
    distances = geometry.real_distances_m.copy()
    np.fill_diagonal(distances,self_radii)
    if model == IDEAL_GROUND:
        return np.log(geometry.image_distances_m)-np.log(distances)
    return -np.log(distances/1.0)  # Normalización por 1 m; no es un retorno físico.


@dataclass(frozen=True)
class BundleInductanceResult:
    individual_rmg_m: np.ndarray
    equivalent_rmg_m: np.ndarray
    primitive_h_per_m: np.ndarray
    phase_h_per_m: np.ndarray
    projected_h_per_m: np.ndarray
    loops_h_per_m: np.ndarray
    ground_model: str
    condition_number: float


def calculate_bundle_inductance(geometry: BundleGeometry, rmg_inputs: tuple[RMGInput,...],
                                ground_model: str = IDEAL_GROUND) -> BundleInductanceResult:
    if len(rmg_inputs) != 3:
        raise InputError("Se requiere un modelo de RMG individual por fase.")
    for spec, data in zip(geometry.specs,rmg_inputs):
        if not math.isclose(spec.radius_m,finite_number(data.radius_m,"Radio exterior del modelo de RMG"),rel_tol=1e-12,abs_tol=0):
            raise InputError("El radio del modelo de RMG debe coincidir con el radio exterior ingresado.")
    individual = np.array([resolve_rmg(data) for data in rmg_inputs])
    equivalent = own_geometric_mean(geometry,individual)
    coefficients = _coefficients(geometry,individual[geometry.phase_index],ground_model)
    primitive = INDUCTANCE_FACTOR_H_PER_M*coefficients
    phase = geometry.current_weights.T @ primitive @ geometry.current_weights
    projected = ZERO_SUM_PROJECTOR @ phase @ ZERO_SUM_PROJECTOR
    loops = LOOP_BASIS.T @ phase @ LOOP_BASIS
    condition = _check_positive(phase if ground_model == IDEAL_GROUND else loops)
    return BundleInductanceResult(individual,equivalent,primitive,phase,projected,loops,ground_model,condition)


@dataclass(frozen=True)
class BundleCapacitanceResult:
    phase_f_per_m: np.ndarray
    charge_response_f_per_m: np.ndarray
    potential_coefficients: np.ndarray
    equipotential_residual: float
    neutrality_residual: float | None
    condition_number: float
    ground_model: str


def calculate_bundle_capacitance(geometry: BundleGeometry,
                                ground_model: str = IDEAL_GROUND) -> BundleCapacitanceResult:
    """Resuelve las cargas individuales imponiendo potencial común por fase.

    Sin suelo: carga total cero y potencial común indeterminado; C tiene rango 2.
    No utiliza el RMG ni el radio equivalente capacitivo en la matriz primitiva.
    """
    p = _coefficients(geometry,geometry.radii_m,ground_model)
    e = geometry.incidence
    factor = 2*math.pi*VACUUM_PERMITTIVITY_F_PER_M
    neutrality = None
    if ground_model == IDEAL_GROUND:
        condition = _check_positive(p)
        response = cho_solve(cho_factor(p,lower=True),e)
        residual = float(np.max(np.abs(p @ response-e)))
    else:
        z = null_space(np.ones((1,len(geometry.positions_m))))
        reduced = z.T @ p @ z
        condition = _check_positive(reduced)
        response = z @ cho_solve(cho_factor(reduced,lower=True),z.T @ e)
        difference = p @ response-e
        residual = float(np.max(np.abs(difference-difference.mean(axis=0,keepdims=True))))
        neutrality = float(np.max(np.abs(np.sum(response,axis=0))))
    if residual > 1e-10 or (neutrality is not None and neutrality > 1e-10):
        raise InputError("No se pudo comprobar equipotencialidad o neutralidad con precisión suficiente.")
    charges = factor*response
    phase = e.T @ charges
    _check_positive(phase if ground_model == IDEAL_GROUND else LOOP_BASIS.T @ phase @ LOOP_BASIS)
    return BundleCapacitanceResult(phase,charges,p,residual,neutrality,condition,ground_model)


def calculate_center_capacitance_approximation(geometry, ground_model=IDEAL_GROUND):
    """Tres círculos equivalentes en los centros: aproximación, no cargas explícitas."""
    centers = build_bundles(tuple(BundleSpec(spec.center,1,radius) for spec,radius
                                  in zip(geometry.specs,geometry.capacitive_radius_m)))
    return calculate_bundle_capacitance(centers,ground_model)
