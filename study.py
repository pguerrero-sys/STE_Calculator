"""Orquestación común: entradas -> motores existentes -> resultados, sin Streamlit.

No cambia ecuaciones de geometría, L, C, Carson, Kron ni secuencias.
"""
from dataclasses import dataclass, replace
import math
import numpy as np
from .models import Conductor, InputError
from .bundles import BundleSpec
from .double_circuit import build_circuit_geometry, calculate_double_circuit
from .transposition import calculate_transposition
from .transposition_schedule import automatic_schedule
from .inductance import RMGInput, MANUFACTURER, IDEAL_GROUND, NO_GROUND, resolve_rmg
from .resistance import calculate_resistance, ACADEMIC
from .carson import calculate_carson_layout, MODIFIED
from .kron import augment_carson, reduce_augmented
from .sequences import phase_to_sequence
from .series_comparison import percent_error


@dataclass(frozen=True)
class StudyConfig:
    specs: tuple
    conductor_data: tuple
    frequency_hz: float | None = 60
    length_km: float | None = None
    voltage_kv: float | None = None
    power: float | None = None
    power_kind: str = 'MVA'
    power_factor: float = 1
    load_type: str = 'Inductiva'
    complete: bool = False
    resistance_mode: str = ACADEMIC
    temperature_c: int = 25
    parallel: bool = False
    carson_enabled: bool = False
    carson_method: str = MODIFIED
    resistivity_ohm_m: float = 100
    auxiliaries: tuple = ()
    kron_confirmed: bool = False
    case_name: str = 'Configuración del usuario'


@dataclass(frozen=True)
class StudyResult:
    config: StudyConfig
    geometry: object
    variants: dict
    resistance: object | None
    messages: dict
    carson: dict | None
    circuit_comparison: dict | None


def variants_for(specs,rmgs):
    results={}
    for model in (IDEAL_GROUND,NO_GROUND):
        for trans in (False,True):
            if len(specs)==3:
                result=calculate_transposition(specs,rmgs,trans,model,model)
            else:
                result=calculate_double_circuit(specs,rmgs,inductance_model=model,capacitance_model=model,complete=trans)
            results[model,trans]=result
    return results


def moved_specs(specs,row):
    return tuple(BundleSpec(Conductor(s.center.circuit,s.center.phase,specs[pos].center.x_m,specs[pos].center.y_m),
                            s.count,s.radius_m,s.spacing_m,s.rotation_deg) for s,pos in zip(specs,row))


def calculate_study(config):
    geometry=build_circuit_geometry(config.specs)
    specs=geometry.specs
    n=len(specs)
    if len(config.conductor_data)!=n: raise InputError('Falta un conductor documentado por cada fase.')
    if config.length_km is not None and (not math.isfinite(config.length_km) or config.length_km<=0):
        raise InputError('La longitud debe ser positiva cuando se proporciona.')
    messages={}
    try:
        rmgs=tuple(RMGInput(s.radius_m,d.rmg_method,d.gmr_m,d.sources.get('diameter_gmr',''))
                   for s,d in zip(specs,config.conductor_data))
        for r in rmgs: resolve_rmg(r)
        if any(any('RMG' in w for w in d.warnings) for d in config.conductor_data):
            raise InputError('RMG con unidades discordantes en la fuente; introducir un dato personalizado verificado para calcular L.')
    except InputError as exc:
        rmgs=None; messages['inductance']=str(exc)
    variants=variants_for(specs,rmgs)
    try:
        resistance=calculate_resistance(config.conductor_data,tuple(s.count for s in specs),n//3,
            frequency_hz=config.frequency_hz,voltage_kv=config.voltage_kv,power=config.power,
            power_kind=config.power_kind,power_factor=config.power_factor,mode=config.resistance_mode,
            temperature_c=config.temperature_c,parallel=config.parallel)
    except InputError as exc:
        resistance=None;messages['resistance']=str(exc)
    carson=None
    if config.carson_enabled:
        if resistance is None or rmgs is None:
            messages['carson']='Carson requiere R_AC y RMG documentados: '+messages.get('resistance',messages.get('inductance',''))
        else:
            carson=calculate_series(config,specs,rmgs,resistance)
            if carson.get('error'): messages['carson']=carson['error']
    comparison=None
    if n==6:
        # Circuito 1 aislado, conserva su geometría/haz; no equivale al bloque C11.
        comparison=variants_for(specs[:3],None if rmgs is None else rmgs[:3])
    return StudyResult(config,geometry,variants,resistance,messages,carson,comparison)


def calculate_series(config,specs,rmgs,resistance):
    plan=automatic_schedule(len(specs)//3,config.complete)
    sections=[];phases=[]
    try:
        for row in plan.assignments:
            geom=build_circuit_geometry(moved_specs(specs,row))
            p=calculate_carson_layout(geom,resistance.conductor_ohm_km,tuple(resolve_rmg(r) for r in rmgs),
                tuple(d.sources['resistance_capacity'] for d in config.conductor_data),config.frequency_hz,
                config.resistivity_ohm_m,config.carson_method,'Resistencia AC seleccionada; no DC PSCAD')
            augmented=reduced=None
            if config.auxiliaries:
                augmented=augment_carson(p,config.auxiliaries)
                try:
                    reduced=reduce_augmented(augmented,confirmed=config.kron_confirmed)
                except InputError as exc:
                    sections.append(dict(phase=p,augmented=augmented,reduced=None))
                    return dict(sections=sections,error=str(exc),phase=None,sequence=None,assignments=plan.assignments)
            phases.append(p.z_ohm_per_m if reduced is None else reduced.z_ohm_per_m)
            sections.append(dict(phase=p,augmented=augmented,reduced=reduced))
        z=sum(w*p for w,p in zip(plan.weights,phases))
        seq=phase_to_sequence(z,sections[0]['phase'].phase_labels)
        return dict(sections=sections,phase=z,original_phase=phases[0],sequence=seq,
                    assignments=plan.assignments,weights=plan.weights,error='')
    except InputError as exc:
        return dict(sections=sections,phase=None,sequence=None,error=str(exc))


def derived_matrices(study,l_model,c_model,complete):
    l=study.variants[l_model,complete].l_h_per_m
    c=study.variants[c_model,complete].c_f_per_m
    f=study.config.frequency_hz
    omega=2*math.pi*f if f is not None and math.isfinite(f) and f>0 else None
    r=None if study.resistance is None else np.diag(study.resistance.phase_ohm_km)/1000
    z=None if r is None or l is None or omega is None else r+1j*omega*l
    y=None if omega is None else 1j*omega*c
    return dict(R_ohm_m=r,L_h_m=l,C_f_m=c,Z_ohm_m=z,Y_s_m=y,
                sequences=None if z is None else phase_to_sequence(z,study.geometry.phase_labels))


def positive_equivalents(matrix,labels):
    """Modos positivos por circuito, solo si están desacoplados del resto."""
    if matrix is None:return ()
    seq=phase_to_sequence(np.asarray(matrix,dtype=complex),labels).z_ohm_per_m
    scale=max(float(np.max(np.abs(seq))),np.finfo(float).tiny)
    result=[]
    for circuit,index in enumerate(range(1,len(seq),3),1):
        others=np.delete(seq[index,:],index)
        if np.max(np.abs(others))<=1e-10*scale:
            result.append((circuit,seq[index,index]))
    return tuple(result)


def rmg_values(study):
    section=study.variants[IDEAL_GROUND,False].sections[0]
    if hasattr(section,'rmg_m'):return section.rmg_m
    return None if section.inductance is None else section.inductance.individual_rmg_m


def external_comparisons(matrix_z,reference_ohm_km,labels):
    """Filas de fase/secuencia para contrastes externos, R/X por separado."""
    z=np.asarray(matrix_z,dtype=complex)*1000;ref=np.asarray(reference_ohm_km,dtype=complex)
    if z.shape!=ref.shape or z.shape!=(len(labels),len(labels)):
        raise InputError('Dimensiones incompatibles para comparación externa.')
    def row(name,a,b):
        return dict(Elemento=name,R_STE=float(a.real),X_STE=float(a.imag),R_PSCAD=float(b.real),X_PSCAD=float(b.imag),
                    Delta_R=float(a.real-b.real),Delta_X=float(a.imag-b.imag),
                    Error_R_pct=percent_error(a.real,b.real),Error_X_pct=percent_error(a.imag,b.imag))
    rows=[row(p+'/'+q,z[i,j],ref[i,j]) for i,p in enumerate(labels) for j,q in enumerate(labels)]
    a=phase_to_sequence(z/1000,labels).z_ohm_per_m*1000
    b=phase_to_sequence(ref/1000,labels).z_ohm_per_m*1000
    seq=[row(str(k),a[k,k],b[k,k]) for k in range(len(a))]
    return rows,seq


def section_arrays(result,index):
    s=result.sections[index]
    g=s.geometry
    if hasattr(s,'potential_sub'):
        return dict(geometry=g,P=s.potential_sub,C=s.c_f_per_m,Pphase=s.effective_phase_p,
                    Lsub=s.l_sub_h_per_m,L=s.l_h_per_m,response=s.charge_response_f_per_m,
                    D=g.real_distances_m,S=g.image_distances_m)
    cap=s.capacitance;ind=s.inductance
    return dict(geometry=g,P=cap.potential_coefficients,C=cap.phase_f_per_m,Pphase=s.effective_phase_p,
        Lsub=None if ind is None else ind.primitive_h_per_m,
        L=None if ind is None else ind.phase_h_per_m if result.inductance_model==IDEAL_GROUND else ind.projected_h_per_m,
        response=cap.charge_response_f_per_m,D=g.real_distances_m,S=g.image_distances_m)
