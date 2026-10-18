"""Seis terminales independientes, haces y tramos; sin Streamlit.

La extensión usa las mismas primitivas físicas de las etapas anteriores.
Convenciones y restricciones: referencias/doble_circuito.md.
"""

from dataclasses import dataclass
import math

import numpy as np
from scipy.linalg import null_space, block_diag

from .bundles import BundleSpec, build_bundles
from .models import Conductor, InputError, PHASES, finite_number
from .inductance import (IDEAL_GROUND, NO_GROUND, resolve_rmg,
                         INDUCTANCE_FACTOR_H_PER_M, LOOP_BASIS, ZERO_SUM_PROJECTOR)
from .capacitance import VACUUM_PERMITTIVITY_F_PER_M
from .transposition import _inverse_positive
from .transposition_schedule import automatic_schedule

LABELS = ("A", "B", "C", "A'", "B'", "C'")
FACTOR = 2*math.pi*VACUUM_PERMITTIVITY_F_PER_M


def symmetric(matrix):
    return (matrix+matrix.T)/2


@dataclass(frozen=True)
class CircuitGeometry:
    specs: tuple
    positions_m: np.ndarray
    radii_m: np.ndarray
    phase_index: np.ndarray
    labels: tuple
    incidence: np.ndarray
    current_weights: np.ndarray
    real_distances_m: np.ndarray
    image_distances_m: np.ndarray

    @property
    def phase_labels(self):
        return LABELS[:len(self.specs)]


def build_circuit_geometry(specs):
    """Tres o seis fases; reutiliza build_bundles por circuito y valida cruces."""
    specs = tuple(specs)
    if any(s.center.phase not in PHASES for s in specs):
        raise InputError("Cada circuito debe usar las fases A, B y C.")
    specs = tuple(sorted(specs,key=lambda s: (s.center.circuit,PHASES.index(s.center.phase))))
    count = len(specs)
    if count not in (3,6) or {(s.center.circuit,s.center.phase) for s in specs} != {(c,p) for c in range(1,count//3+1) for p in PHASES}:
        raise InputError("Se requieren fases A/B/C completas de uno o dos circuitos.")
    groups = []
    for circuit in range(1,count//3+1):
        group = tuple(BundleSpec(Conductor(1,s.center.phase,s.center.x_m,s.center.y_m),s.count,s.radius_m,s.spacing_m,s.rotation_deg)
                      for s in specs if s.center.circuit==circuit)
        try:
            groups.append(build_bundles(group))
        except InputError as exc:
            raise InputError(f"Circuito {circuit}: {exc}") from exc
    positions = np.vstack([g.positions_m for g in groups])
    radii = np.concatenate([g.radii_m for g in groups])
    ids = np.concatenate([g.phase_index+3*i for i,g in enumerate(groups)])
    with np.errstate(over="ignore",invalid="ignore"):
        dx = positions[:,0,None]-positions[None,:,0]
        real = np.hypot(dx,positions[:,1,None]-positions[None,:,1])
        images = np.hypot(dx,positions[:,1,None]+positions[None,:,1])
    if not np.all(np.isfinite(real)) or not np.all(np.isfinite(images)):
        raise InputError("Las distancias entre circuitos no son representables.")
    off = ~np.eye(len(radii),dtype=bool)
    overlaps = np.argwhere(off & (real <= radii[:,None]+radii[None,:]))
    labels = tuple(f"{LABELS[p]}-{i+1}" for p,s in enumerate(specs) for i in range(s.count))
    if len(overlaps):
        i,j = overlaps[0]
        raise InputError(f"Contacto o solapamiento entre {labels[i]} y {labels[j]}, incluso entre circuitos.")
    e = np.eye(count)[ids]
    t = e/np.array([s.count for s in specs])
    # Conserva los valores normalizados por la geometría de etapa 4.
    normalized = tuple(BundleSpec(Conductor(c+1,s.center.phase,s.center.x_m,s.center.y_m),s.count,s.radius_m,s.spacing_m,s.rotation_deg)
                       for c,g in enumerate(groups) for s in g.specs)
    return CircuitGeometry(normalized,positions,radii,ids,labels,e,t,real,images)


def coefficients(geometry,self_radii,model):
    if model not in (IDEAL_GROUND,NO_GROUND):
        raise InputError("Modelo de suelo no implementado; Carson está pendiente.")
    distances = geometry.real_distances_m.copy()
    np.fill_diagonal(distances,self_radii)
    if model == IDEAL_GROUND:
        return np.log(geometry.image_distances_m)-np.log(distances)
    return -np.log(distances/1.0)  # Auxiliar: referencia 1 m, eliminada al proyectar.


@dataclass(frozen=True)
class CircuitSection:
    geometry: CircuitGeometry
    potential_sub: np.ndarray
    charge_response_f_per_m: np.ndarray
    effective_phase_p: np.ndarray
    c_f_per_m: np.ndarray
    l_sub_h_per_m: np.ndarray | None
    l_h_per_m: np.ndarray | None
    rmg_m: np.ndarray | None
    equipotential_residual: float
    neutrality_residual: float
    rmg_inputs: tuple | None


def calculate_section(specs,rmg_inputs=None,inductance_model=IDEAL_GROUND,capacitance_model=IDEAL_GROUND):
    """Modelo de fase completo; con tres fases permite contrastar etapas previas."""
    if inductance_model not in (IDEAL_GROUND,NO_GROUND):
        raise InputError("Modelo inductivo no implementado.")
    geometry = build_circuit_geometry(specs)
    n = len(geometry.specs)
    q = null_space(np.ones((1,n)))
    h = np.eye(n)-np.ones((n,n))/n
    p = coefficients(geometry,geometry.radii_m,capacitance_model)
    e = geometry.incidence
    neutrality = 0.0
    if capacitance_model == IDEAL_GROUND:
        response = _inverse_positive(p) @ e
        residual = float(np.max(np.abs(p @ response-e)))
    else:
        z = null_space(np.ones((1,len(p))))
        response = z @ _inverse_positive(z.T @ p @ z) @ z.T @ e
        delta = p @ response-e
        residual = float(np.max(np.abs(delta-delta.mean(axis=0,keepdims=True))))
        neutrality = float(np.max(np.abs(np.sum(response,axis=0))))
    if max(residual,neutrality) > 1e-10:
        raise InputError("No se pudo comprobar equipotencialidad/neutralidad de los seis terminales.")
    c = FACTOR*symmetric(e.T @ response)
    effective_p = (_inverse_positive(c/FACTOR) if capacitance_model==IDEAL_GROUND else
                   symmetric(q @ _inverse_positive(q.T @ (c/FACTOR) @ q) @ q.T))
    rmg,lsub,l = None,None,None
    if rmg_inputs is not None:
        if len(rmg_inputs) != n:
            raise InputError("Se requiere un modelo de RMG por fase, en orden A/B/C/A'/B'/C'.")
        for label,spec,data in zip(geometry.phase_labels,geometry.specs,rmg_inputs):
            if not math.isclose(spec.radius_m,finite_number(data.radius_m,"Radio de RMG"),rel_tol=1e-12):
                raise InputError(f"Fase {label}: el radio de RMG no coincide con el radio exterior.")
        rmg = np.array([resolve_rmg(data) for data in rmg_inputs])
        lsub = INDUCTANCE_FACTOR_H_PER_M*coefficients(geometry,rmg[geometry.phase_index],inductance_model)
        raw = symmetric(geometry.current_weights.T @ lsub @ geometry.current_weights)
        l = raw if inductance_model==IDEAL_GROUND else symmetric(h @ raw @ h)
        _inverse_positive(l if inductance_model==IDEAL_GROUND else q.T @ l @ q)
    return CircuitSection(geometry,p,FACTOR*response,effective_p,c,lsub,l,rmg,residual,neutrality,
                          tuple(rmg_inputs) if rmg_inputs is not None else None)


def default_assignments(mode):
    if mode == "none":
        return ((0,1,2,3,4,5),)
    if mode not in ("same","opposite"):
        raise InputError("Elige sin transposición, ciclos simultáneos u opuestos.")
    return tuple(tuple((i+t)%3 for i in range(3))+tuple(3+(i+(t if mode=="same" else -t))%3 for i in range(3)) for t in range(3))


def validate_sections(assignments,weights):
    if not assignments or len(assignments)>9 or len(assignments)!=len(weights):
        raise InputError("Define de 1 a 9 tramos con una fracción por tramo.")
    for t,row in enumerate(assignments,1):
        if len(row)!=6 or any(type(v) is not int for v in row) or set(row[:3])!={0,1,2} or set(row[3:])!={3,4,5}:
            raise InputError(f"Tramo {t}: cada fase debe ocupar una posición distinta dentro de su circuito (P1-P3 y P4-P6).")
    w = tuple(finite_number(v,f"Fracción de longitud del tramo {t}") for t,v in enumerate(weights,1))
    if any(v<=0 for v in w) or not math.isclose(sum(w),1,rel_tol=0,abs_tol=1e-10):
        raise InputError("Las fracciones de longitud deben ser positivas y sumar 1.")
    return w


@dataclass(frozen=True)
class DoubleCircuitResult:
    sections: tuple
    assignments: tuple
    weights: tuple
    inductance_model: str
    capacitance_model: str
    average_phase_p: np.ndarray
    c_f_per_m: np.ndarray
    l_h_per_m: np.ndarray | None
    l_circuit_balanced_h_per_m: np.ndarray | None
    l_loops_h_per_m: np.ndarray | None
    inversion_residual: float


def calculate_double_circuit(specs,rmg_inputs=None,assignments=None,weights=None,
                             inductance_model=IDEAL_GROUND,capacitance_model=IDEAL_GROUND,*,complete=None):
    base = build_circuit_geometry(specs)
    if len(base.specs)!=6:
        raise InputError("Doble circuito requiere exactamente seis fases independientes.")
    if complete is not None:
        if assignments is not None or weights is not None:
            raise InputError('El plan automático no admite asignaciones ni fracciones manuales.')
        plan=automatic_schedule(len(base.specs)//3,complete)
        assignments,weights=plan.assignments,plan.weights
    assignments = default_assignments("none") if assignments is None else tuple(tuple(row) for row in assignments)
    weights = (1/len(assignments),)*len(assignments) if weights is None and assignments else weights
    weights = validate_sections(assignments,weights)
    sections = []
    for t,row in enumerate(assignments,1):
        moved = tuple(BundleSpec(Conductor(s.center.circuit,s.center.phase,base.specs[pos].center.x_m,base.specs[pos].center.y_m),
                                 s.count,s.radius_m,s.spacing_m,s.rotation_deg) for s,pos in zip(base.specs,row))
        try:
            sections.append(calculate_section(moved,rmg_inputs,inductance_model,capacitance_model))
        except InputError as exc:
            raise InputError(f"Tramo {t}: {exc}") from exc
    average_p = symmetric(sum(w*s.effective_phase_p for w,s in zip(weights,sections)))
    h = np.eye(6)-np.ones((6,6))/6
    if capacitance_model==IDEAL_GROUND:
        c = FACTOR*_inverse_positive(average_p)
        target = np.eye(6)
    else:
        q = null_space(np.ones((1,6)))
        c = FACTOR*symmetric(q @ _inverse_positive(q.T @ average_p @ q) @ q.T)
        target = h
    residual = float(np.max(np.abs(average_p @ c/FACTOR-target)))
    if residual>1e-10:
        raise InputError("Falló la comprobación del promedio de potenciales de seis fases.")
    l,balanced,loops = None,None,None
    if rmg_inputs is not None:
        l = symmetric(sum(w*s.l_h_per_m for w,s in zip(weights,sections)))
        hcc = block_diag(ZERO_SUM_PROJECTOR,ZERO_SUM_PROJECTOR)
        bcc = block_diag(LOOP_BASIS,LOOP_BASIS)
        balanced = symmetric(hcc @ l @ hcc)
        loops = symmetric(bcc.T @ l @ bcc)
    return DoubleCircuitResult(tuple(sections),assignments,weights,inductance_model,capacitance_model,
                               average_p,c,l,balanced,loops,residual)


def reactance_six(matrix_h_per_m,frequency_hz):
    frequency = finite_number(frequency_hz,"Frecuencia para reactancia [Hz]")
    if frequency<=0:
        raise InputError("La frecuencia para reactancia debe ser positiva.")
    with np.errstate(over="ignore",invalid="ignore"):
        x = 2*math.pi*frequency*np.asarray(matrix_h_per_m,dtype=float)*1000
    if x.shape!=(6,6) or not np.all(np.isfinite(x)):
        raise InputError("La reactancia de seis fases debe ser finita y de 6×6.")
    return x  # Ω/km


def reproducible_specs(count=1):
    """Caso sintético: no son propiedades de un conductor comercial."""
    return tuple(BundleSpec(Conductor(c,p,x,y),count,.011765,.4572 if count>1 else None)
                 for c,x in ((1,-4),(2,4)) for p,y in zip(PHASES,(15,11,7)))
