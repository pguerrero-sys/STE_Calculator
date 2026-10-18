"""Inductancia de tres conductores; sin interfaz ni dependencia de capacitancia.

Ecuaciones y límites documentados en referencias/inductancia.md.
"""

from dataclasses import dataclass
import math

import numpy as np

from .models import Conductor, InputError, PHASES, finite_number

MU0_H_PER_M = 4 * math.pi * 1e-7  # Constante de modelo indicada por el usuario.
INDUCTANCE_FACTOR_H_PER_M = MU0_H_PER_M / (2 * math.pi)
SOLID_UNIFORM = "solid_uniform_nonmagnetic"
MANUFACTURER = "manufacturer"
IDEAL_GROUND = "ideal_ground"
NO_GROUND = "no_ground_balanced"
ZERO_SUM_PROJECTOR = np.eye(3) - np.ones((3, 3)) / 3
LOOP_BASIS = np.array([[1.0, 0.0], [0.0, 1.0], [-1.0, -1.0]])


@dataclass(frozen=True)
class RMGInput:
    radius_m: float
    method: str
    manufacturer_rmg_m: float | None = None
    source: str = ""


def resolve_rmg(data: RMGInput) -> float:
    radius = finite_number(data.radius_m, "Radio exterior [m]")
    if radius <= 0:
        raise InputError("El radio exterior debe ser mayor que cero.")
    if data.method == SOLID_UNIFORM:
        value = radius * math.exp(-1 / 4)
    elif data.method == MANUFACTURER:
        if not isinstance(data.source, str) or not data.source.strip():
            raise InputError("El RMG del fabricante requiere una fuente técnica identificada.")
        value = finite_number(data.manufacturer_rmg_m, "RMG del fabricante [m]")
    else:
        raise InputError("Selecciona el modelo macizo uniforme no magnético o un RMG del fabricante.")
    if not math.isfinite(value) or value <= 0 or value > radius:
        raise InputError("Para este modelo se requiere 0 < RMG ≤ radio exterior, en metros.")
    return value


def convert_inductance(value, from_unit: str, to_unit: str):
    """Conversión elemento a elemento; microH/m y mH/km tienen igual factor."""
    units = {"H/m": 1.0, "µH/m": 1e-6, "mH/km": 1e-6}
    if from_unit not in units or to_unit not in units:
        raise InputError("Unidad de inductancia no admitida: usa H/m, µH/m o mH/km.")
    try:
        values = np.asarray(value, dtype=float)
    except (TypeError, ValueError) as exc:
        raise InputError("La inductancia debe contener números finitos.") from exc
    with np.errstate(over="ignore", invalid="ignore"):
        result = values * (units[from_unit] / units[to_unit])
    if not np.all(np.isfinite(result)):
        raise InputError("La inductancia o su conversión no es finita.")
    return result


@dataclass(frozen=True)
class ReactanceResult:
    frequency_hz: float
    x_ohm_per_m: np.ndarray
    x_ohm_per_km: np.ndarray


def calculate_reactance(matrix_h_per_m, frequency_hz: float) -> ReactanceResult:
    frequency = finite_number(frequency_hz, "Frecuencia para reactancia [Hz]")
    if frequency <= 0:
        raise InputError("La frecuencia para reactancia debe ser mayor que cero.")
    matrix = convert_inductance(matrix_h_per_m, "H/m", "H/m")
    if matrix.ndim != 2 or matrix.shape[0] != matrix.shape[1] or matrix.shape[0] not in (2, 3):
        raise InputError("La reactancia requiere una matriz cuadrada de dos lazos o tres fases.")
    with np.errstate(over="ignore", invalid="ignore"):
        x = 2 * math.pi * frequency * matrix
        x_per_km = 1000 * x
    if not np.all(np.isfinite(x_per_km)):
        raise InputError("La reactancia calculada no es finita.")
    return ReactanceResult(frequency, x, x_per_km)


@dataclass(frozen=True)
class InductanceResult:
    conductors: tuple[Conductor, ...]
    rmg_inputs: tuple[RMGInput, ...]
    radii_m: np.ndarray
    rmg_m: np.ndarray
    ground_model: str
    reference_distance_m: float | None
    real_distances_m: np.ndarray
    image_positions_m: np.ndarray | None
    image_distances_m: np.ndarray | None
    logarithmic_coefficients: np.ndarray
    l_h_per_m: np.ndarray
    balanced_l_h_per_m: np.ndarray
    loop_l_h_per_m: np.ndarray
    condition_number: float

    @property
    def labels(self) -> tuple[str, ...]:
        return PHASES


def calculate_inductance(
    conductors: tuple[Conductor, ...],
    rmg_inputs: tuple[RMGInput, ...],
    ground_model: str = IDEAL_GROUND,
    reference_distance_m: float | None = None,
) -> InductanceResult:
    """Entradas alineadas con los conductores; salida siempre en orden A/B/C.

    Sin suelo, l_h_per_m es L_ref(d0), NO una inductancia absoluta única.
    balanced_l_h_per_m (3x3 de rango 2) y loop_l_h_per_m (2x2) no dependen de d0.
    """
    if len(conductors) != 3 or {(c.circuit, c.phase) for c in conductors} != {(1, p) for p in PHASES}:
        raise InputError("La inductancia admite solo un circuito con exactamente tres fases A, B y C.")
    if len(rmg_inputs) != 3:
        raise InputError("Ingresa radio y modelo de RMG para cada fase.")
    if ground_model not in (IDEAL_GROUND, NO_GROUND):
        raise InputError("Modelo de suelo no implementado. Elige suelo ideal o sin suelo con suma de corrientes cero.")
    paired = sorted(zip(conductors, rmg_inputs), key=lambda item: PHASES.index(item[0].phase))
    ordered = tuple(Conductor(1, c.phase, finite_number(c.x_m, f"X {c.phase}"),
                              finite_number(c.y_m, f"Altura {c.phase}")) for c, _ in paired)
    inputs = tuple(item[1] for item in paired)
    rmg = np.array([resolve_rmg(value) for value in inputs])
    radii = np.array([finite_number(value.radius_m, "Radio exterior") for value in inputs])
    coords = np.array([(c.x_m, c.y_m) for c in ordered])
    if np.any(coords[:, 1] <= radii):
        raise InputError("Los conductores deben estar por encima del suelo sin tocarlo: radio exterior < altura.")
    off = ~np.eye(3, dtype=bool)
    with np.errstate(over="ignore", invalid="ignore"):
        dx = coords[:, 0, None] - coords[None, :, 0]
        dy = coords[:, 1, None] - coords[None, :, 1]
        real = np.hypot(dx, dy)
        radii_sum = radii[:, None] + radii[None, :]
    if not np.all(np.isfinite(real)) or not np.all(np.isfinite(radii_sum)):
        raise InputError("Las distancias no son representables; revisa la magnitud de las entradas.")
    if np.any(real[off] <= radii_sum[off]):
        raise InputError("Los conductores no pueden coincidir, tocarse ni solaparse.")
    images = None
    image_positions = None
    if ground_model == IDEAL_GROUND:
        image_positions = coords * np.array([1.0, -1.0])
        with np.errstate(over="ignore", invalid="ignore"):
            images = np.hypot(dx, coords[:, 1, None] + coords[None, :, 1])
        if not np.all(np.isfinite(images)):
            raise InputError("Las distancias a las imágenes no son representables.")
        coefficients = np.empty((3, 3))
        coefficients[off] = np.log(images[off]) - np.log(real[off])
        np.fill_diagonal(coefficients, np.log(np.diag(images)) - np.log(rmg))
        physical_coefficients = coefficients
        reference = None
    else:
        reference = finite_number(reference_distance_m, "Distancia de referencia d₀ [m]")
        if reference <= 0:
            raise InputError("La distancia de referencia d₀ debe ser mayor que cero.")
        # Se explicita la unidad de referencia de 1 m en la representación canónica.
        # H*11^T*H y B^T*11^T*B son cero: las reducciones evitan cancelaciones
        # innecesarias de ln(d0) para referencias muy grandes o muy pequeñas.
        canonical = np.empty((3, 3))
        canonical[off] = -np.log(real[off] / 1.0)
        np.fill_diagonal(canonical, -np.log(rmg / 1.0))
        coefficients = canonical + math.log(reference / 1.0)
        physical_coefficients = canonical
    factor = INDUCTANCE_FACTOR_H_PER_M
    matrix = factor * coefficients
    balanced = factor * (ZERO_SUM_PROJECTOR @ physical_coefficients @ ZERO_SUM_PROJECTOR)
    loops = factor * (LOOP_BASIS.T @ physical_coefficients @ LOOP_BASIS)
    applicable = matrix if ground_model == IDEAL_GROUND else loops
    if not all(np.all(np.isfinite(m)) for m in (matrix, balanced, loops)):
        raise InputError("Los coeficientes inductivos no son finitos.")
    condition = float(np.linalg.cond(applicable))
    if np.min(np.linalg.eigvalsh(applicable)) <= 0 or not math.isfinite(condition) or condition > 1e12:
        raise InputError("La inductancia en el espacio físico no es definida positiva o está mal condicionada.")
    return InductanceResult(ordered, inputs, radii, rmg, ground_model, reference,
                            real, image_positions, images, coefficients, matrix, balanced, loops, condition)


@dataclass(frozen=True)
class BalancedFluxResult:
    currents_a: np.ndarray
    contributions_wb_turn_per_m: np.ndarray
    flux_wb_turn_per_m: np.ndarray
    zero_mean_flux_wb_turn_per_m: np.ndarray
    loop_flux_wb_turn_per_m: np.ndarray
    own_flux_wb_turn_per_m: np.ndarray
    mutual_flux_wb_turn_per_m: np.ndarray


def balanced_trial_currents(amplitude_a: float) -> np.ndarray:
    """Ensayo ABC de magnitudes iguales y desfases de 120 grados, suma cero."""
    amplitude = finite_number(amplitude_a, "Amplitud del ensayo [A]")
    if amplitude < 0:
        raise InputError("La amplitud del ensayo no puede ser negativa.")
    return amplitude * np.array([1, complex(-.5, -math.sqrt(3)/2), complex(-.5, math.sqrt(3)/2)])


def inductive_voltage_drop(flux_linkages_wb_turn_per_m, frequency_hz: float) -> np.ndarray:
    """Caída inductiva por longitud, j omega lambda, en V/m."""
    frequency = finite_number(frequency_hz, "Frecuencia para caída inductiva [Hz]")
    if frequency <= 0:
        raise InputError("La frecuencia para caída inductiva debe ser positiva.")
    try:
        flux = np.asarray(flux_linkages_wb_turn_per_m, dtype=complex)
    except (ValueError, TypeError) as exc:
        raise InputError("Los enlaces deben ser fasores finitos.") from exc
    with np.errstate(over="ignore", invalid="ignore"):
        voltage = 2j * math.pi * frequency * flux
    if not np.all(np.isfinite(voltage)):
        raise InputError("La caída inductiva no es finita.")
    return voltage


def balanced_flux_linkages(result: InductanceResult, currents_a) -> BalancedFluxResult:
    """Enlaces propios/mutuos y diferencias, exclusivamente para suma I=0."""
    try:
        currents = np.asarray(currents_a, dtype=complex)
    except (ValueError, TypeError) as exc:
        raise InputError("Ingresa tres corrientes fasoriales finitas.") from exc
    if currents.shape != (3,) or not np.all(np.isfinite(currents)):
        raise InputError("Se requieren tres corrientes fasoriales finitas.")
    scale = max(float(np.max(np.maximum(np.abs(currents.real), np.abs(currents.imag)))), np.finfo(float).tiny)
    if abs(np.sum(currents / scale)) > 1e-12:
        raise InputError("El análisis equilibrado requiere I_A + I_B + I_C = 0; no se admite secuencia cero.")
    with np.errstate(over="ignore", invalid="ignore"):
        contributions = result.l_h_per_m * currents[None, :]
        flux = np.sum(contributions, axis=1)
        projected = result.balanced_l_h_per_m @ currents
        loop_flux = result.loop_l_h_per_m @ currents[:2]
        own_flux = np.diag(contributions).copy()
        mutual_flux = np.sum(np.where(np.eye(3, dtype=bool), 0, contributions), axis=1)
    if not all(np.all(np.isfinite(v)) for v in (contributions, flux, projected, loop_flux, own_flux, mutual_flux)):
        raise InputError("Los enlaces de flujo no son representables con estas corrientes.")
    return BalancedFluxResult(currents, contributions, flux, projected, loop_flux, own_flux, mutual_flux)
