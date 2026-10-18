"""Geometría y medias geométricas de haces regulares. Sin interfaz."""

from dataclasses import dataclass
import math

import numpy as np

from .models import Conductor, InputError, PHASES, finite_number


@dataclass(frozen=True)
class BundleSpec:
    center: Conductor
    count: int
    radius_m: float
    spacing_m: float | None = None
    rotation_deg: float = 0.0


@dataclass(frozen=True)
class BundleGeometry:
    specs: tuple[BundleSpec, ...]
    positions_m: np.ndarray
    radii_m: np.ndarray
    phase_index: np.ndarray
    incidence: np.ndarray
    current_weights: np.ndarray
    real_distances_m: np.ndarray
    image_distances_m: np.ndarray
    capacitive_radius_m: np.ndarray
    equivalent_distances_m: np.ndarray
    equivalent_images_m: np.ndarray
    polygon_radii_m: np.ndarray

    @property
    def labels(self):
        return tuple(f"{PHASES[p]}{i+1}" for p in range(3) for i in range(self.specs[p].count))


def own_geometric_mean(geometry: BundleGeometry, self_lengths_m) -> np.ndarray:
    """Media de n² distancias; diagonal propia especificada por fase."""
    if len(self_lengths_m) != 3:
        raise InputError("Se requiere una distancia propia por fase.")
    lengths = np.array([finite_number(v, "Distancia propia [m]") for v in self_lengths_m])
    if np.any(lengths <= 0):
        raise InputError("Las distancias propias deben ser positivas.")
    own = geometry.real_distances_m.copy()
    np.fill_diagonal(own, lengths[geometry.phase_index])
    return np.array([np.exp(np.mean(np.log(own[np.ix_(geometry.phase_index == p, geometry.phase_index == p)]))) for p in range(3)])


def build_bundles(specs: tuple[BundleSpec, ...]) -> BundleGeometry:
    if len(specs) != 3 or {(s.center.circuit,s.center.phase) for s in specs} != {(1,p) for p in PHASES}:
        raise InputError("Los haces requieren un único circuito con fases A, B y C.")
    specs = tuple(sorted(specs,key=lambda s: PHASES.index(s.center.phase)))
    normalized, points, phase_ids, radii, polygon_radii = [], [], [], [], []
    for phase, spec in enumerate(specs):
        if isinstance(spec.count,bool) or not isinstance(spec.count,int) or spec.count not in (1,2,3,4):
            raise InputError("Cada haz admite 1, 2, 3 o 4 subconductores.")
        x = finite_number(spec.center.x_m,"X del centro [m]")
        y = finite_number(spec.center.y_m,"Altura del centro [m]")
        radius = finite_number(spec.radius_m,"Radio exterior del subconductor [m]")
        rotation = finite_number(spec.rotation_deg,"Rotación [grados]")
        if radius <= 0:
            raise InputError("El radio exterior del subconductor debe ser positivo.")
        spacing = None if spec.count == 1 else finite_number(spec.spacing_m,"Separación entre vecinos [m]")
        if spacing is not None and spacing <= 2*radius:
            raise InputError("La separación debe superar el diámetro: los subconductores no pueden tocarse.")
        a = 0.0 if spec.count == 1 else spacing/(2*math.sin(math.pi/spec.count))
        base = {1:0.0,2:0.0,3:math.pi/2,4:math.pi/4}[spec.count]
        angles = base + math.radians(rotation % 360) + np.arange(spec.count)*2*math.pi/spec.count
        positions = np.array([x,y]) + a*np.column_stack((np.cos(angles),np.sin(angles)))
        points.extend(positions)
        phase_ids.extend([phase]*spec.count)
        radii.extend([radius]*spec.count)
        polygon_radii.append(a)
        normalized.append(BundleSpec(Conductor(1,PHASES[phase],x,y),spec.count,radius,spacing,rotation))
    points, ids, radii = np.asarray(points), np.asarray(phase_ids), np.asarray(radii)
    if not np.all(np.isfinite(points)) or np.any(points[:,1] <= radii):
        raise InputError("Cada subconductor debe quedar por encima del suelo, sin tocarlo; revisa centros y separación.")
    with np.errstate(over="ignore",invalid="ignore"):
        dx = points[:,0,None]-points[None,:,0]
        real = np.hypot(dx,points[:,1,None]-points[None,:,1])
        images = np.hypot(dx,points[:,1,None]+points[None,:,1])
        radius_sum = radii[:,None]+radii[None,:]
    if not all(np.all(np.isfinite(v)) for v in (real,images,radius_sum)):
        raise InputError("La magnitud de las entradas produce distancias no representables.")
    off = ~np.eye(len(points),dtype=bool)
    if np.any(real[off] <= radius_sum[off]):
        raise InputError("No se permite contacto ni solapamiento entre subconductores de ninguna fase.")
    incidence = np.eye(3)[ids]
    weights = incidence/np.array([s.count for s in specs])[None,:]
    deq, seq, req = np.zeros((3,3)), np.empty((3,3)), np.empty(3)
    own = real.copy()
    np.fill_diagonal(own,radii)
    for i in range(3):
        idx = ids == i
        req[i] = np.exp(np.mean(np.log(own[np.ix_(idx,idx)])))
        for j in range(3):
            block = np.ix_(idx,ids == j)
            seq[i,j] = np.exp(np.mean(np.log(images[block])))
            if i != j:
                deq[i,j] = np.exp(np.mean(np.log(real[block])))
    return BundleGeometry(tuple(normalized),points,radii,ids,incidence,weights,real,images,
                          req,deq,seq,np.asarray(polygon_radii))
