"""Componentes simétricas: Kersting CRC 2002 §4.1.7, ecs.4.59-4.67.

Convención fasorial exp(jωt), a=exp(j2π/3), fases ABC, secuencias 0/1/2.
Transformación lineal, sin promediar geometrías ni eliminar acoplamientos.
"""

from dataclasses import dataclass
import numpy as np
from .models import InputError

PHASE_ORDER = ("A", "B", "C", "A'", "B'", "C'")


def transformation_matrices(circuit_count=1):
    if isinstance(circuit_count,bool) or not isinstance(circuit_count,(int,np.integer)) or circuit_count not in (1,2):
        raise InputError("Componentes simétricas admite uno o dos circuitos completos ABC.")
    a = np.exp(2j*np.pi/3)
    single = np.array([[1,1,1],[1,a*a,a],[1,a,a*a]],dtype=complex)
    # A^-1 = A^H/3 para esta convención, no A^T/3.
    transform = np.kron(np.eye(circuit_count),single)
    return a,transform,transform.conj().T/3


@dataclass(frozen=True)
class SequenceResult:
    phase_labels: tuple
    labels: tuple
    operator_a: complex
    transform: np.ndarray
    inverse_transform: np.ndarray
    z_ohm_per_m: np.ndarray
    reconstruction_residual: float


def phase_to_sequence(z_ohm_per_m,phase_labels):
    """Zs=B^-1 Zphase B, B=A o diag(A,A). Entrada/salida en Ω/m.

    Para seis fases el orden de salida es 0C1/1C1/2C1/0C2/1C2/2C2.
    Zs en general NO es simétrica ni hermítica. No se redondea ni diagonaliza.
    """
    try:
        z = np.asarray(z_ohm_per_m,dtype=complex)
        labels = tuple(phase_labels)
    except (TypeError,ValueError) as exc:
        raise InputError("Impedancias de fase o etiquetas inválidas para secuencias.") from exc
    if z.shape not in ((3,3),(6,6)) or not np.all(np.isfinite(z)):
        raise InputError("Se requiere Zabc finita de 3×3 o 6×6 en Ω/m.")
    if labels != PHASE_ORDER[:len(z)]:
        raise InputError("Orden de fases requerido: A,B,C o A,B,C,A',B',C'. Reordena explícitamente la matriz.")
    count = len(z)//3
    a,b,inv = transformation_matrices(count)
    zs = inv @ z @ b
    if not np.all(np.isfinite(zs)):
        raise InputError("La transformación de secuencias no es representable.")
    names = tuple(str(i) if count==1 else f"{i} C{c}" for c in range(1,count+1) for i in range(3))
    residual = float(np.linalg.norm(b@zs@inv-z)/max(np.linalg.norm(z),np.finfo(float).tiny))
    return SequenceResult(labels,names,a,b,inv,zs,residual)
