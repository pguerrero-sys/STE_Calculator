"""Eliminación de auxiliares con caída de tensión nula; matrices SI, sin UI.

Kersting (CRC 2002), §4.1.5-4.1.6, pp.86-87, ecs.4.45-4.54.
No calcula conexiones, impedancias de electrodos ni condiciones de frontera.
"""

from dataclasses import dataclass
import numpy as np

from .carson import CarsonConductor, CarsonResult, calculate_carson, convert_impedance
from .models import InputError

UNKNOWN = "unknown"
ISOLATED = "isolated"
ZERO_DROP = "ideal_multigrounded"
CONNECTIONS = {UNKNOWN: "Conexión desconocida", ISOLATED: "Aislado / sin retorno cerrado",
               ZERO_DROP: "Multitierra ideal: ΔV auxiliar = 0"}


@dataclass(frozen=True)
class AuxiliaryConductor:
    conductor: CarsonConductor
    role: str = "neutral"
    connection: str = UNKNOWN
    justification: str = ""


@dataclass(frozen=True)
class ImpedanceBlocks:
    pp: np.ndarray
    pn: np.ndarray
    np: np.ndarray
    nn: np.ndarray
    phase_indices: tuple
    auxiliary_indices: tuple


@dataclass(frozen=True)
class AugmentedCarson:
    primitive: CarsonResult
    phase_labels: tuple
    auxiliaries: tuple
    current_weights: np.ndarray
    z_ohm_per_m: np.ndarray
    blocks: ImpedanceBlocks

    @property
    def labels(self):
        return self.phase_labels + tuple(a.conductor.label for a in self.auxiliaries)


@dataclass(frozen=True)
class KronResult:
    blocks: ImpedanceBlocks
    z_ohm_per_m: np.ndarray
    correction_ohm_per_m: np.ndarray
    auxiliary_current_response: np.ndarray
    condition_number: float
    solve_residual: float

    @property
    def z_ohm_per_km(self):
        return convert_impedance(self.z_ohm_per_m, "Ω/m", "Ω/km")


def partition_impedance(z_ohm_per_m, phase_indices):
    """Partición completa; el complemento de fases son los auxiliares."""
    try:
        z = np.asarray(z_ohm_per_m, dtype=complex)
        phases = tuple(phase_indices)
    except (TypeError, ValueError) as exc:
        raise InputError("Matriz de impedancias o índices inválidos.") from exc
    if z.ndim != 2 or z.shape[0] != z.shape[1] or not np.all(np.isfinite(z)):
        raise InputError("La impedancia debe ser una matriz cuadrada finita.")
    if (not phases or any(isinstance(i, (bool, np.bool_)) or not isinstance(i, (int, np.integer))
                          or i < 0 or i >= len(z) for i in phases)
            or len(set(phases)) != len(phases)):
        raise InputError("Índices de fases vacíos, repetidos o fuera de rango.")
    scale = max(float(np.max(np.abs(z))), np.finfo(float).tiny)
    if np.max(np.abs(z-z.T)) > 1e-10*scale:
        raise InputError("Se requiere impedancia recíproca: Z=Zᵀ (sin conjugación).")
    auxiliary = tuple(i for i in range(len(z)) if i not in phases)
    if not auxiliary:
        raise InputError("Agrega al menos un conductor auxiliar para particionar Kron.")
    return ImpedanceBlocks(z[np.ix_(phases, phases)], z[np.ix_(phases, auxiliary)],
                           z[np.ix_(auxiliary, phases)], z[np.ix_(auxiliary, auxiliary)],
                           phases, auxiliary)


def augment_carson(phase_result, auxiliaries):
    """Conserva todos los acoplamientos de Carson, incluidos los subconductores.

    Si hay haces, A=diag(T,Iaux), Zterminal=Aᵀ Zsub A, con I_sub=I_fase/n.
    La primitiva completa permanece disponible; esta agregación no es Kron.
    """
    auxiliary = tuple(auxiliaries)
    if not auxiliary:
        raise InputError("Agrega al menos un neutro o cable de guarda.")
    for a in auxiliary:
        if not isinstance(a, AuxiliaryConductor) or a.role not in ("neutral", "guard"):
            raise InputError("Tipo de auxiliar inválido: usa neutral o guard.")
        if a.connection not in CONNECTIONS:
            raise InputError(f"{a.conductor.label}: condición eléctrica desconocida.")
    base = getattr(phase_result, "primitive", phase_result)
    labels = tuple(getattr(phase_result, "phase_labels", base.labels))
    if len(labels) not in (3, 6):
        raise InputError("Kron admite tres o seis fases conservadas.")
    all_labels = labels + tuple(a.conductor.label for a in auxiliary)
    if len(set(all_labels)) != len(all_labels):
        raise InputError("Las etiquetas de fases y auxiliares deben ser únicas.")
    primitive = calculate_carson(base.conductors + tuple(a.conductor for a in auxiliary),
                                base.frequency_hz, base.resistivity_ohm_m, base.method)
    t = getattr(phase_result, "current_weights", np.eye(len(labels)))
    a = np.zeros((len(primitive.labels), len(all_labels)))
    a[:len(base.labels), :len(labels)] = t
    a[len(base.labels):, len(labels):] = np.eye(len(auxiliary))
    z = a.T @ primitive.z_ohm_per_m @ a
    blocks = partition_impedance(z, range(len(labels)))
    return AugmentedCarson(primitive, labels, auxiliary, a, z, blocks)


def reduce_kron(z_ohm_per_m, phase_indices, auxiliaries, *, confirmed=False):
    """Complemento de Schur solo bajo la hipótesis declarada ΔVn=0.

    Resuelve Znn Y=Znp, sin formar la inversa numérica. No elimina aislados.
    Umbral cond>1e12: política numérica del software, no límite físico.
    """
    blocks = partition_impedance(z_ohm_per_m, phase_indices)
    auxiliary = tuple(auxiliaries)
    if len(auxiliary) != len(blocks.auxiliary_indices):
        raise InputError("Falta una condición eléctrica por cada auxiliar de Znn.")
    for a in auxiliary:
        if not isinstance(a, AuxiliaryConductor) or a.connection != ZERO_DROP:
            name = a.conductor.label if isinstance(a, AuxiliaryConductor) else "Auxiliar"
            raise InputError(f"{name}: Kron requiere ΔV=0; un auxiliar aislado o de conexión desconocida no se elimina.")
        if not isinstance(a.justification, str) or not a.justification.strip():
            raise InputError(f"{a.conductor.label}: falta la justificación de la conexión multitierra ideal.")
    if confirmed is not True:
        raise InputError("Falta declarar explícitamente ΔV=0 para todos los auxiliares eliminados.")
    condition = float(np.linalg.cond(blocks.nn))
    if not np.isfinite(condition) or condition > 1e12:
        raise InputError("Znn singular o mal condicionada (cond>1e12); no se aplica Kron ni pseudoinversa.")
    try:
        y = np.linalg.solve(blocks.nn, blocks.np)
    except np.linalg.LinAlgError as exc:
        raise InputError("Znn no invertible; no se puede eliminar el bloque auxiliar.") from exc
    correction = blocks.pn @ y
    reduced = blocks.pp-correction
    if not np.all(np.isfinite(reduced)):
        raise InputError("Reducción no representable con estas entradas.")
    denominator = np.linalg.norm(blocks.nn)*np.linalg.norm(y)+np.linalg.norm(blocks.np)
    residual = float(np.linalg.norm(blocks.nn@y-blocks.np)/max(denominator, np.finfo(float).tiny))
    return KronResult(blocks, reduced, correction, -y, condition, residual)


def reduce_augmented(result, *, confirmed=False):
    return reduce_kron(result.z_ohm_per_m, result.blocks.phase_indices, result.auxiliaries,
                       confirmed=confirmed)
