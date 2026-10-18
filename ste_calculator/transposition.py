"""Transposición ideal por tramos; reutiliza los cálculos completos de haces.

Sin Streamlit. Procedimiento y restricciones en referencias/transposicion.md.
"""

from dataclasses import dataclass

import numpy as np
from scipy.linalg import cho_factor, cho_solve

from .bundles import BundleSpec, BundleGeometry, build_bundles
from .bundle_electrical import (BundleCapacitanceResult, BundleInductanceResult,
                                calculate_bundle_capacitance, calculate_bundle_inductance)
from .capacitance import VACUUM_PERMITTIVITY_F_PER_M
from .inductance import IDEAL_GROUND, NO_GROUND, RMGInput, ZERO_SUM_PROJECTOR, LOOP_BASIS
from .models import Conductor, InputError, PHASES, finite_number
from .transposition_schedule import automatic_schedule

ZERO_SUM_BASIS = np.array([[1/np.sqrt(2),1/np.sqrt(6)],[-1/np.sqrt(2),1/np.sqrt(6)],[0,-2/np.sqrt(6)]])


def position_assignments(complete: bool) -> tuple[tuple[int,...],...]:
    return automatic_schedule(1,complete).assignments


def permutation_matrix(assignment: tuple[int,...]) -> np.ndarray:
    """R[posición,fase]=1; por tanto una matriz fija se transforma como R^T M R."""
    if len(assignment) != 3 or any(type(i) is not int for i in assignment) or set(assignment) != {0,1,2}:
        raise InputError("La asignación debe permutar las tres posiciones 0, 1 y 2.")
    return np.eye(3)[:,assignment]


def section_lengths_m(total_length_m: float, complete: bool) -> tuple[float,...]:
    count = len(position_assignments(complete))
    length = finite_number(total_length_m,"Longitud total [m]")
    if length <= 0:
        raise InputError("La longitud total debe ser positiva.")
    return (length/count,)*count


def _symmetric(matrix):
    return (matrix+matrix.T)/2  # Solo elimina redondeo; no impone forma circulante.


def _inverse_positive(matrix):
    matrix = _symmetric(matrix)
    if not np.all(np.isfinite(matrix)):
        raise InputError("La matriz de coeficientes no es finita.")
    condition = np.linalg.cond(matrix)
    if not np.isfinite(condition) or condition > 1e12:
        raise InputError("La matriz de coeficientes está mal condicionada.")
    try:
        return _symmetric(cho_solve(cho_factor(matrix,lower=True),np.eye(len(matrix))))
    except np.linalg.LinAlgError as exc:
        raise InputError("La matriz de coeficientes no es definida positiva en el espacio aplicable.") from exc


def effective_phase_p(capacitance: BundleCapacitanceResult) -> np.ndarray:
    """Coeficientes adimensionales de potencial, después de imponer equipotencialidad."""
    factor = 2*np.pi*VACUUM_PERMITTIVITY_F_PER_M
    normalized_c = capacitance.phase_f_per_m/factor
    if capacitance.ground_model == IDEAL_GROUND:
        return _inverse_positive(normalized_c)
    if capacitance.ground_model != NO_GROUND:
        raise InputError("Modelo de suelo no implementado.")
    q = ZERO_SUM_BASIS
    return _symmetric(q @ _inverse_positive(q.T @ normalized_c @ q) @ q.T)


@dataclass(frozen=True)
class TranspositionSection:
    phase_to_position: tuple[int,...]
    weight: float
    geometry: BundleGeometry
    inductance: BundleInductanceResult | None
    capacitance: BundleCapacitanceResult
    effective_phase_p: np.ndarray


@dataclass(frozen=True)
class TranspositionResult:
    complete: bool
    sections: tuple[TranspositionSection,...]
    average_phase_p: np.ndarray
    c_f_per_m: np.ndarray
    direct_average_c_f_per_m: np.ndarray
    l_h_per_m: np.ndarray | None
    l_loops_h_per_m: np.ndarray | None
    inductance_model: str
    capacitance_model: str
    inversion_residual: float


def calculate_transposition(
    specs: tuple[BundleSpec,...], rmg_inputs: tuple[RMGInput,...] | None = None,
    complete: bool = True, inductance_model: str = IDEAL_GROUND,
    capacitance_model: str = IDEAL_GROUND,
) -> TranspositionResult:
    """Las construcciones y los RMG viajan con las fases; rmg_inputs en orden A/B/C.

    Con None se obtiene capacitancia sin requerir un modelo inductivo.
    Sin transposición se usa el primer tramo, conservando el modelo anterior.
    Sin suelo, L y P de salida representan solamente el subespacio de suma cero.
    """
    assignments = position_assignments(complete)
    if inductance_model not in (IDEAL_GROUND,NO_GROUND) or capacitance_model not in (IDEAL_GROUND,NO_GROUND):
        raise InputError("Solo se admite suelo ideal o el modelo restringido sin suelo; Carson no está implementado.")
    original = build_bundles(specs).specs
    positions = tuple(spec.center for spec in original)
    sections = []
    for number,assignment in enumerate(assignments,1):
        moved = tuple(BundleSpec(Conductor(1,PHASES[phase],positions[location].x_m,positions[location].y_m),
                                 original[phase].count,original[phase].radius_m,
                                 original[phase].spacing_m,original[phase].rotation_deg)
                      for phase,location in enumerate(assignment))
        try:
            geometry = build_bundles(moved)
            cap = calculate_bundle_capacitance(geometry,capacitance_model)
            ind = calculate_bundle_inductance(geometry,rmg_inputs,inductance_model) if rmg_inputs is not None else None
            phase_p = effective_phase_p(cap)
        except InputError as exc:
            raise InputError(f"Tramo {number}: {exc}") from exc
        sections.append(TranspositionSection(assignment,1/len(assignments),geometry,ind,cap,phase_p))
    average_p = _symmetric(sum(s.weight*s.effective_phase_p for s in sections))
    factor = 2*np.pi*VACUUM_PERMITTIVITY_F_PER_M
    target = np.eye(3)
    if capacitance_model == IDEAL_GROUND:
        c = factor*_inverse_positive(average_p)
    else:
        q = ZERO_SUM_BASIS
        c = factor*_symmetric(q @ _inverse_positive(q.T @ average_p @ q) @ q.T)
        target = ZERO_SUM_PROJECTOR
    residual = float(np.max(np.abs(average_p @ c/factor-target)))
    if not np.isfinite(residual) or residual > 1e-10:
        raise InputError("No se pudo comprobar la inversión de los coeficientes promedio.")
    l,loops = None,None
    if rmg_inputs is not None:
        l = _symmetric(sum(s.weight*(s.inductance.phase_h_per_m if inductance_model==IDEAL_GROUND
                                   else s.inductance.projected_h_per_m) for s in sections))
        loops = _symmetric(sum(s.weight*s.inductance.loops_h_per_m for s in sections))
    direct_c = _symmetric(sum(s.weight*s.capacitance.phase_f_per_m for s in sections))
    return TranspositionResult(complete,tuple(sections),average_p,c,direct_c,l,loops,
                               inductance_model,capacitance_model,residual)
