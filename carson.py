"""Impedancias serie de Carson; independiente de Streamlit y capacitancia.

Solo aproximaciones identificadas. Fuentes y dominio: referencias/carson.md.
"""

from dataclasses import dataclass
import math

import numpy as np

from .models import InputError, finite_number
from .inductance import MU0_H_PER_M

FT_M = .3048
MILE_M = 1609.344
G_SI_H_PER_M = MU0_H_PER_M/(4*math.pi)
K_FEET = 8.565e-4
MODIFIED = "modified_carson"
PQ_TRUNCATED = "kersting_pq_finite"
METHODS = {MODIFIED:"Carson modificado · Kersting (4.37)-(4.40)",
           PQ_TRUNCATED:"P/Q finitos · Kersting (4.23)-(4.24), aproximación"}


@dataclass(frozen=True)
class CarsonConductor:
    label: str
    x_m: float
    height_m: float
    resistance_ac_ohm_per_km: float
    gmr_m: float
    source: str
    radius_m: float | None = None
    conditions: str = ""


def convert_impedance(values,from_unit,to_unit):
    """Valores por longitud; una entrada Ω/km equivale a 0.001 Ω/m."""
    metres = {"Ω/m":1.,"Ω/km":1000.,"Ω/mile":MILE_M}
    if from_unit not in metres or to_unit not in metres:
        raise InputError("Usa Ω/m, Ω/km o Ω/mile para impedancias por longitud.")
    try:
        with np.errstate(over="ignore",invalid="ignore"):
            result = np.asarray(values,dtype=complex)*metres[to_unit]/metres[from_unit]
    except (TypeError,ValueError,OverflowError) as exc:
        raise InputError("La impedancia debe contener números finitos.") from exc
    if not np.all(np.isfinite(result)):
        raise InputError("La impedancia o su conversión no es representable.")
    return result


@dataclass(frozen=True)
class CarsonResult:
    conductors: tuple
    frequency_hz: float
    resistivity_ohm_m: float
    method: str
    real_distances_m: np.ndarray
    image_distances_m: np.ndarray
    cos_theta: np.ndarray
    k: np.ndarray
    p: np.ndarray
    q: np.ndarray
    z_conductor_ohm_per_m: np.ndarray  # Diagonal resistiva suministrada.
    z_geometry_ohm_per_m: np.ndarray  # jωL con imágenes de suelo ideal.
    z_earth_ohm_per_m: np.ndarray     # Corrección respecto de esa referencia.
    z_ohm_per_m: np.ndarray
    warnings: tuple

    @property
    def labels(self):
        return tuple(c.label for c in self.conductors)

    @property
    def z_ohm_per_km(self):
        return convert_impedance(self.z_ohm_per_m,"Ω/m","Ω/km")


def calculate_carson(conductors,frequency_hz,resistivity_ohm_m,method=MODIFIED):
    """Primitiva sin eliminar conductores; permite contrastar el ejemplo de 4 hilos.

    La interfaz admite tres o seis fases. Aquí los nombres son arbitrarios
    para poder comprobar la primitiva bibliográfica SIN aplicar Kron.
    """
    if method not in METHODS:
        raise InputError("Método de Carson no implementado. No hay método completo ni reducción de Kron en esta etapa.")
    frequency = finite_number(frequency_hz,"Frecuencia Carson [Hz]")
    rho = finite_number(resistivity_ohm_m,"Resistividad del terreno [Ω·m]")
    if frequency<=0 or rho<=0:
        raise InputError("Frecuencia Carson y resistividad deben ser positivas.")
    conductors = tuple(conductors)
    if not conductors or len({c.label for c in conductors})!=len(conductors):
        raise InputError("Se requieren conductores con identificadores únicos.")
    normalized = []
    for c in conductors:
        if not isinstance(c.source,str) or not c.source.strip():
            raise InputError(f"{c.label}: identifica la fuente técnica de R_AC y RMG; ACSR requiere datos documentados, nunca radio macizo supuesto.")
        x = finite_number(c.x_m,f"X de {c.label} [m]")
        height = finite_number(c.height_m,f"Altura de {c.label} [m]")
        resistance = finite_number(c.resistance_ac_ohm_per_km,f"R_AC de {c.label} [Ω/km]")
        gmr = finite_number(c.gmr_m,f"RMG de {c.label} [m]")
        if height<=0 or resistance<0 or gmr<=0 or gmr>=height:
            raise InputError(f"{c.label}: requiere altura>0, R_AC≥0 y 0<RMG<altura.")
        radius = None if c.radius_m is None else finite_number(c.radius_m,f"Radio exterior de {c.label} [m]")
        if radius is not None and not (0<gmr<=radius<height):
            raise InputError(f"{c.label}: requiere 0<RMG≤radio exterior<altura cuando se proporciona radio físico.")
        normalized.append(CarsonConductor(c.label,x,height,resistance,gmr,c.source,radius,c.conditions))
    conductors = tuple(normalized)
    x = np.array([c.x_m for c in conductors])
    h = np.array([c.height_m for c in conductors])
    with np.errstate(over="ignore",invalid="ignore"):
        dx = x[:,None]-x[None,:]
        real = np.hypot(dx,h[:,None]-h[None,:])
        images = np.hypot(dx,h[:,None]+h[None,:])
    if not np.all(np.isfinite(real)) or not np.all(np.isfinite(images)) or np.any(images<=0):
        raise InputError("Las distancias de Carson no son representables.")
    off = ~np.eye(len(conductors),dtype=bool)
    for i,j in np.argwhere(off):
        ci,cj = conductors[i],conductors[j]
        if real[i,j]==0 or (ci.radius_m is not None and cj.radius_m is not None and real[i,j]<=ci.radius_m+cj.radius_m):
            raise InputError(f"Contacto o coincidencia entre {ci.label} y {cj.label}.")
    # Logaritmos separados evitan desbordar f/rho o S/ft al validar k.
    log_k = math.log(K_FEET)+np.log(images)-math.log(FT_M)+.5*(math.log(frequency)-math.log(rho))
    if np.max(log_k)>=0:
        raise InputError("k máximo ≥ 1: fuera del dominio preventivo de pequeño k admitido por estas aproximaciones. Se requiere un desarrollo completo no implementado; este umbral es de software, no una cota de error bibliográfica.")
    if np.min(log_k)<math.log(np.finfo(float).tiny):
        raise InputError("k es demasiado pequeño para representarlo con precisión; revisa f y ρ.")
    k = np.exp(log_k)
    cos_theta = (h[:,None]+h[None,:])/images
    if method==MODIFIED:
        p = np.full(images.shape,math.pi/8)
        q = .5*(7.6786-(np.log(images)-math.log(FT_M))+.5*(math.log(rho)-math.log(frequency)))
    else:
        log_two_over_k = math.log(2)-log_k
        first = k*cos_theta/(3*math.sqrt(2))
        p = math.pi/8-first+(k*k/16)*(2*cos_theta*cos_theta-1)*(.6728+log_two_over_k)
        q = -.0386+.5*log_two_over_k+first
    distances = real.copy()
    np.fill_diagonal(distances,[c.gmr_m for c in conductors])
    omega = 2*math.pi*frequency
    with np.errstate(over="ignore",invalid="ignore"):
        z_conductor = np.diag([c.resistance_ac_ohm_per_km/1000 for c in conductors]).astype(complex)
        z_geometry = 1j*(2*omega*G_SI_H_PER_M)*(np.log(images)-np.log(distances))
        z_earth = (4*omega*G_SI_H_PER_M)*(p+1j*q)
        z = z_conductor+z_geometry+z_earth
    if not all(np.all(np.isfinite(m)) for m in (p,q,z_geometry,z_earth,z)):
        raise InputError("La impedancia de Carson no es representable con estas entradas.")
    warnings = []
    if np.max(k)>.1:
        warnings.append(f"k máximo={np.max(k):.6g}>0.1: aviso preventivo de software; los términos omitidos pueden ser importantes. No hay garantía de error ni evaluación completa.")
    if not 50<=frequency<=60:
        warnings.append("Frecuencia fuera de 50-60 Hz: esta implementación no ha validado la precisión de la aproximación a esa frecuencia.")
    return CarsonResult(conductors,frequency,rho,method,real,images,cos_theta,k,p,q,
                        z_conductor,z_geometry,z_earth,z,tuple(warnings))


@dataclass(frozen=True)
class CarsonPhaseResult:
    primitive: CarsonResult
    phase_labels: tuple
    current_weights: np.ndarray
    z_conductor_ohm_per_m: np.ndarray
    z_geometry_ohm_per_m: np.ndarray
    z_earth_ohm_per_m: np.ndarray
    z_ohm_per_m: np.ndarray

    @property
    def z_ohm_per_km(self):
        return convert_impedance(self.z_ohm_per_m,"Ω/m","Ω/km")


def calculate_carson_layout(geometry,resistances_ohm_per_km,gmr_m,sources,frequency_hz,
                            resistivity_ohm_m,method=MODIFIED,conditions=""):
    """Geometría de haces de etapas 4/6; corrientes I/n, sin Kron ni transposición."""
    count = len(geometry.specs)
    if count not in (3,6) or any(len(values)!=count for values in (resistances_ohm_per_km,gmr_m,sources)):
        raise InputError("Ingresa R_AC, RMG y fuente por cada una de las tres o seis fases.")
    phase_labels = tuple(s.center.phase+("'" if s.center.circuit==2 else "") for s in geometry.specs)
    data = tuple(CarsonConductor(geometry.labels[u],xy[0],xy[1],resistances_ohm_per_km[p],gmr_m[p],sources[p],geometry.radii_m[u],conditions)
                 for u,(xy,p) in enumerate(zip(geometry.positions_m,geometry.phase_index)))
    primitive = calculate_carson(data,frequency_hz,resistivity_ohm_m,method)
    t = geometry.current_weights
    def aggregate(m):
        return t.T @ m @ t
    r,x,e,z = [aggregate(m) for m in (primitive.z_conductor_ohm_per_m,primitive.z_geometry_ohm_per_m,
                                     primitive.z_earth_ohm_per_m,primitive.z_ohm_per_m)]
    return CarsonPhaseResult(primitive,phase_labels,t,r,x,e,z)


def kersting_example(include_neutral=False):
    """Datos bibliográficos, no ficha vigente ni resultados fijados en código."""
    source = "Kersting CRC 2002, ejemplo 4.1 pp.92-93; diámetro ejemplo 5.1 p.114"
    phases = tuple(CarsonConductor(label,x*FT_M,29*FT_M,.306/(MILE_M/1000),.0244*FT_M,source,.721*.0254/2,
                                   "Datos AC del ejemplo bibliográfico a 60 Hz")
                   for label,x in zip(("A","B","C"),(0,2.5,7)))
    neutral = CarsonConductor("n",4*FT_M,25*FT_M,.592/(MILE_M/1000),.00814*FT_M,source,.563*.0254/2)
    return phases+(neutral,) if include_neutral else phases
