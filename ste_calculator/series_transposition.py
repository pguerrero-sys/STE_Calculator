"""Promedio de impedancias serie por permutaciones cíclicas, separado de L/C.

Kersting CRC 2002, pp.91 y 95, (4.68)-(4.72). Sección uniforme, tramos
iguales, corrientes de fase continuas, cruces sin longitud. No cascada exacta.
"""

from dataclasses import dataclass
import numpy as np
from .models import InputError
from .sequences import PHASE_ORDER


@dataclass(frozen=True)
class SeriesTransposition:
    labels: tuple
    original_ohm_per_m: np.ndarray
    permutations: tuple
    sections_ohm_per_m: tuple
    average_ohm_per_m: np.ndarray
    enabled: bool

    @property
    def selected_ohm_per_m(self):
        return self.average_ohm_per_m if self.enabled else self.original_ohm_per_m


def transpose_series(z_ohm_per_m,labels,*,enabled=True):
    """Zt=Stᵀ Zoriginal St; Zprom=(Z0+Z1+Z2)/3, sin redondeo ni ceros.

    Para dos circuitos St=diag(St3,St3): ciclos sincronizados, no reducción.
    Es un promedio de posiciones físicas fijas con fases equivalentes.
    """
    try:
        z = np.array(z_ohm_per_m,dtype=complex,copy=True)
        labels = tuple(labels)
    except (ValueError,TypeError) as exc:
        raise InputError("Matriz o etiquetas inválidas para transponer Z serie.") from exc
    if z.shape not in ((3,3),(6,6)) or not np.all(np.isfinite(z)):
        raise InputError("Transposición serie requiere matriz finita de 3×3 o 6×6.")
    if labels != PHASE_ORDER[:len(z)]:
        raise InputError("Orden requerido: A,B,C o A,B,C,A',B',C'.")
    if not isinstance(enabled,bool):
        raise InputError("La opción de transposición debe estar activada o desactivada.")
    scale = max(float(np.max(np.abs(z))),np.finfo(float).tiny)
    if np.max(np.abs(z-z.T))>scale*1e-10:
        raise InputError("Se requiere matriz serie recíproca Z=Zᵀ, sin conjugación.")
    permutations = tuple(tuple(c*3+(i+t)%3 for c in range(len(z)//3) for i in range(3)) for t in range(3))
    sections = tuple(z[np.ix_(p,p)].copy() for p in permutations)
    average = sum(section/3 for section in sections)
    if not np.all(np.isfinite(average)):
        raise InputError("El promedio de impedancias no es representable.")
    return SeriesTransposition(labels,z,permutations,sections,average,enabled)


def require_equivalent_phases(phase_result):
    """Evita promediar indebidamente R de conductores distintos por fase.

    Comprueba número de subconductores, R_AC, RMG, radio si conocido y
    distancias internas de haz. Cada circuito puede tener otro tipo de conductor.
    """
    base = getattr(phase_result,"primitive",phase_result)
    labels = getattr(phase_result,"phase_labels",base.labels)
    t = getattr(phase_result,"current_weights",np.eye(len(labels)))
    signatures = []
    for p in range(len(labels)):
        group = [base.conductors[i] for i in np.flatnonzero(t[:,p])]
        xy = np.array([[c.x_m,c.height_m] for c in group])
        distances = np.linalg.norm(xy[:,None,:]-xy[None,:,:],axis=2)
        radius = [np.nan if c.radius_m is None else c.radius_m for c in group]
        signatures.append(np.r_[len(group),sorted(c.resistance_ac_ohm_per_km for c in group),
                                 sorted(c.gmr_m for c in group),sorted(radius),np.sort(distances.ravel())])
    for start in range(0,len(labels),3):
        for p in (start+1,start+2):
            if signatures[p].shape!=signatures[start].shape or not np.allclose(signatures[p],signatures[start],rtol=1e-9,atol=1e-12,equal_nan=True):
                raise InputError(f"{labels[start]} y {labels[p]}: conductores/haces distintos. El promedio por permutación requiere fases equivalentes por circuito; no se promedia R_AC de conductores diferentes.")
