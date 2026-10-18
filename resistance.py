"""Selección académica de R tabulada. No calcula temperatura ni efecto piel.

Notas STE pp.PDF109-111; Tablas_ACSR pp.PDF1-2. Corrientes RMS equilibradas.
"""
from dataclasses import dataclass
import math
import numpy as np
from .models import InputError, finite_number

ACADEMIC='Selección automática según criterio académico de carga'
SPECIFIED='Temperatura tabulada especificada'


def positive(value,name):
    v=finite_number(value,name)
    if v<=0: raise InputError(name+' debe ser mayor que cero.')
    return v


def academic_temperature(load_pct):
    load=finite_number(load_pct,'Porcentaje de carga')
    if load<0: raise InputError('El porcentaje de carga no puede ser negativo.')
    return 25 if load<25 else 50 if load<=75 else 75


def three_phase_current(voltage_kv,power,kind='MVA',power_factor=1):
    voltage=positive(voltage_kv,'Tensión línea-línea [kV]')
    value=finite_number(power,'Potencia total')
    if value<0: raise InputError('La potencia no puede ser negativa.')
    if kind not in ('MVA','MW'): raise InputError('La potencia debe expresarse en MVA o MW.')
    pf=positive(power_factor,'Factor de potencia')
    if pf>1: raise InputError('El factor de potencia debe ser ≤1.')
    apparent=value if kind=='MVA' else value/pf
    return apparent*1000/(math.sqrt(3)*voltage)


@dataclass(frozen=True)
class ResistanceResult:
    total_current_a: float | None
    circuit_current_a: float | None
    subconductor_current_a: np.ndarray | None
    load_percent: np.ndarray | None
    temperatures_c: tuple
    conductor_ohm_km: np.ndarray
    phase_ohm_km: np.ndarray
    parallel_ohm_km: np.ndarray | None
    dc20_ohm_km: tuple
    mode: str
    sources: tuple
    warnings: tuple


def calculate_resistance(data,counts,circuit_count,*,frequency_hz=60,voltage_kv=None,power=None,
                         power_kind='MVA',power_factor=1,mode=ACADEMIC,temperature_c=25,parallel=False):
    if type(circuit_count) is not int or circuit_count not in (1,2):
        raise InputError('Resistencia: solo uno o dos circuitos validados.')
    data,counts=tuple(data),tuple(counts)
    if len(data)!=3*circuit_count or len(counts)!=len(data) or any(type(n) is not int or not 1<=n<=4 for n in counts):
        raise InputError('Se requieren datos y cantidades de 1 a 4 subconductores por cada fase.')
    if mode not in (ACADEMIC,SPECIFIED): raise InputError('Modo de selección de resistencia no implementado.')
    f=positive(frequency_hz,'Frecuencia de resistencia [Hz]')
    for d in data:
        if not math.isclose(f,d.resistance_frequency_hz,rel_tol=0,abs_tol=1e-9):
            raise InputError(f'{d.designation}: R_AC documentada a {d.resistance_frequency_hz:g} Hz; no se extrapola a {f:g} Hz.')
    total=None if voltage_kv is None or power is None else three_phase_current(voltage_kv,power,power_kind,power_factor)
    current=None if total is None else total/circuit_count
    sub=None if total is None else current/np.asarray(counts)
    capacity_missing=any(d.nominal_current_a is None for d in data)
    loads=None if sub is None or (capacity_missing and mode==SPECIFIED) else np.array([100*i/positive(d.nominal_current_a,'Capacidad nominal tabulada [A]') for i,d in zip(sub,data)])
    if mode==ACADEMIC and loads is None:
        raise InputError('El criterio académico requiere tensión, potencia total y capacidad nominal documentada.')
    temps=tuple(academic_temperature(v) for v in loads) if mode==ACADEMIC else (temperature_c,)*len(data)
    resistances=[]
    for d,temp in zip(data,temps):
        if str(temp) not in d.r_ac_ohm_km:
            raise InputError(f'{d.designation}: no hay resistencia tabulada a {temp} °C. No se interpola por defecto.')
        resistances.append(positive(d.r_ac_ohm_km[str(temp)],'R_AC tabulada [Ω/km]'))
        if not d.sources.get('resistance_capacity','').strip():
            raise InputError('La resistencia requiere una fuente técnica identificada.')
    r=np.array(resistances);phase=r/np.asarray(counts)
    equivalent=1/np.sum(1/phase.reshape(circuit_count,3),axis=0) if parallel else None
    warnings=['Reparto uniforme de corriente entre circuitos y subconductores. El criterio académico no determina la temperatura física del conductor.']
    if loads is not None and np.any(loads>100): warnings.append('La corriente supera la capacidad tabulada: no constituye una evaluación térmica de diseño.')
    if len(set(counts))>1: warnings.append('Haces distintos: se mantiene la hipótesis de reparto uniforme por circuito; no se resuelve reparto real.')
    return ResistanceResult(total,current,sub,loads,temps,r,phase,equivalent,tuple(d.r_dc20_ohm_km for d in data),
                            mode,tuple(d.sources['resistance_capacity'] for d in data),tuple(warnings))
