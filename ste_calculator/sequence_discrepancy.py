"""Etapa 7E: diagnóstico reproducible de DOVE, sin alterar el modelo 7D.

Matrices SI. La sustitución DC es SOLO sensibilidad. El reparto desigual es
un modelo auxiliar con gradiente longitudinal común, no un modelo PSCAD.
"""

from dataclasses import dataclass
import numpy as np
import pandas as pd
from .models import InputError
from .pscad_series import load_dove_case,PAIR,find_dove_folder,TRN
from .series_comparison import pscad_reference,percent_error
from .series_transposition import transpose_series
from .sequences import phase_to_sequence

AC_EQUAL = "AC · I/n · referencia 7D"
DC_EQUAL = "DC temporal · I/n · sensibilidad"
AC_SHARED = "AC · reparto desigual · diagnóstico"
DC_SHARED = "DC temporal · reparto desigual · diagnóstico"


@dataclass(frozen=True)
class CurrentSharing:
    phase_ohm_per_m: np.ndarray
    response: np.ndarray
    current_residual: float
    voltage_residual: float
    condition_primitive: float
    condition_phase_admittance: float


def unequal_current_equivalent(z_ohm_per_m,incidence):
    """Zsub Isub=E V', Iphase=Eᵀ Isub ⇒ Zphase=(Eᵀ Zsub^-1 E)^-1.

    Gradiente longitudinal común por fase, sección uniforme, conexiones ideales,
    shunt omitido en esta eliminación serie. Sin inversión explícita, sin Kron
    de guardas ni propiedades adicionales de hebras/proximidad.
    """
    try:
        z = np.asarray(z_ohm_per_m,dtype=complex)
        e = np.asarray(incidence,dtype=float)
    except (TypeError,ValueError) as exc:
        raise InputError("Matrices inválidas para diagnóstico de reparto de corriente.") from exc
    if (z.ndim!=2 or z.shape[0]!=z.shape[1] or not np.all(np.isfinite(z))
            or e.ndim!=2 or e.shape[0]!=len(z) or e.shape[1] not in (3,6)
            or not np.all(np.isfinite(e)) or not np.all((e==0)|(e==1))
            or not np.all(e.sum(axis=1)==1) or np.any(e.sum(axis=0)==0)):
        raise InputError("Se requiere Zsub cuadrada finita y E binaria con una fase por subconductor y tres o seis fases no vacías.")
    scale = max(float(np.max(np.abs(z))),np.finfo(float).tiny)
    if np.max(np.abs(z-z.T))>1e-10*scale:
        raise InputError("Zsub debe ser recíproca: Zsub=Zsubᵀ.")
    condition = float(np.linalg.cond(z))
    if not np.isfinite(condition) or condition>1e12:
        raise InputError("Zsub singular o mal condicionada; no se usa pseudoinversa.")
    try:
        w = np.linalg.solve(z,e)
        y = e.T@w
        cond_y = float(np.linalg.cond(y))
        if not np.isfinite(cond_y) or cond_y>1e12:
            raise InputError("Admitancia equivalente singular o mal condicionada.")
        phase = np.linalg.solve(y,np.eye(e.shape[1]))
    except np.linalg.LinAlgError as exc:
        raise InputError("No se pudo resolver el modelo auxiliar de reparto de corriente.") from exc
    response = w@phase
    current_error = float(np.linalg.norm(e.T@response-np.eye(e.shape[1])))
    voltage_error = float(np.linalg.norm(z@response-e@phase)/max(np.linalg.norm(z)*np.linalg.norm(response)+np.linalg.norm(e@phase),np.finfo(float).tiny))
    return CurrentSharing(phase,response,current_error,voltage_error,condition,cond_y)


@dataclass(frozen=True)
class SensitivityScenario:
    name: str
    resistance_input_ohm_km: np.ndarray
    primitive_ohm_per_m: np.ndarray
    original_phase_ohm_per_m: np.ndarray
    transposed_phase_ohm_per_m: np.ndarray
    sequence_ohm_per_m: np.ndarray
    scalar_sequence_ohm_per_m: np.ndarray
    scalar_residual_ohm_per_m: float
    response: np.ndarray
    current_sharing: CurrentSharing | None


def scalar_transposed_sequences(z_ohm_per_m):
    """Verificación independiente solo de matriz 3×3 idealmente transpuesta."""
    z = np.asarray(z_ohm_per_m,dtype=complex)
    if z.shape!=(3,3) or not np.all(np.isfinite(z)):
        raise InputError("La verificación escalar requiere matriz trifásica finita de 3×3.")
    own = np.trace(z)/3
    mutual = (z.sum()-np.trace(z))/6
    expected = np.full((3,3),mutual,dtype=complex)
    np.fill_diagonal(expected,own)
    if not np.allclose(z,expected,rtol=1e-10,atol=1e-18):
        raise InputError("La matriz no está idealmente transpuesta: no aplicar fórmulas escalares descartando acoplamientos.")
    return np.array([own+2*mutual,own-mutual,own-mutual])


def make_scenario(name,zsub,e,weights,labels,resistance,*,unequal=False):
    sharing = unequal_current_equivalent(zsub,e) if unequal else None
    phase = sharing.phase_ohm_per_m if sharing is not None else weights.T@zsub@weights
    transposed = transpose_series(phase,labels).average_ohm_per_m
    seq = phase_to_sequence(transposed,labels).z_ohm_per_m
    scalar = scalar_transposed_sequences(transposed)
    residual = float(np.max(np.abs(np.diag(seq)-scalar)))
    return SensitivityScenario(name,resistance.copy(),zsub.copy(),phase,transposed,seq,scalar,residual,
                               sharing.response if sharing is not None else weights.copy(),sharing)


def cancellation_analysis(ste_phase_ohm_m,pscad_phase_ohm_m):
    # Las fórmulas escalares se validan primero, sin suponer desacoplamiento.
    scalar_transposed_sequences(ste_phase_ohm_m)
    scalar_transposed_sequences(pscad_phase_ohm_m)
    s,m = (ste_phase_ohm_m[0,0].real*1000,ste_phase_ohm_m[0,1].real*1000)
    sr,mr = (pscad_phase_ohm_m[0,0].real*1000,pscad_phase_ohm_m[0,1].real*1000)
    r1 = sr-mr
    if r1==0:
        raise InputError("R1 PSCAD es cero: amplificación y porcentaje de resistencia indefinidos.")
    return {"Rs_STE_ohm_km":s,"Rm_STE_ohm_km":m,"Rs_PSCAD_ohm_km":sr,"Rm_PSCAD_ohm_km":mr,
            "delta_Rs_ohm_km":s-sr,"delta_Rm_ohm_km":m-mr,"delta_R1_ohm_km":(s-sr)-(m-mr),
            "R1_STE_ohm_km":s-m,"R1_PSCAD_ohm_km":r1,
            "signed_error_Rs_pct":100*(s-sr)/sr,"signed_error_Rm_pct":100*(m-mr)/mr,
            "contribution_own_percentage_points":100*(s-sr)/r1,
            "contribution_mutual_percentage_points":-100*(m-mr)/r1,
            "signed_error_R1_pct":100*((s-m)-r1)/r1,
            "cancellation_factor":(abs(sr)+abs(mr))/abs(r1)}


def published_pscad_sequence(root=None):
    """Control adicional con Zsq publicada, no fuente del cálculo principal."""
    folder = find_dove_folder() if root is None else find_dove_folder(root)
    text = (folder/TRN).read_text(encoding="utf-8-sig")
    tag = "SEQUENCE IMPEDANCE MATRIX (Zsq) [ohms/m]:"
    if text.count(tag)!=1:
        raise InputError("PSCAD: no hay un único bloque Zsq para contraste adicional.")
    rows=[]
    for line in text.split(tag)[1].splitlines():
        if not line.strip() and not rows:
            continue
        matches=list(PAIR.finditer(line))
        if len(matches)!=3 or PAIR.sub("",line).strip():
            break
        rows.append([complex(float(p[1]),float(p[2])) for p in matches])
        if len(rows)==3:
            break
    z = np.asarray(rows,dtype=complex)
    if z.shape!=(3,3) or not np.all(np.isfinite(z)):
        raise InputError("Zsq PSCAD incompleta.")
    return z


def analyze_dove(root=None):
    case = load_dove_case() if root is None else load_dove_case(root)
    if case.labels!=("A","B","C"):
        raise InputError("El diagnóstico DOVE requiere tres fases ABC, sin reducción de circuitos.")
    base = case.phase_result.primitive
    t = case.phase_result.current_weights
    e = (t!=0).astype(float)
    n = e.sum(axis=0)
    if not np.all(n==4):
        raise InputError("Este análisis exige el caso DOVE con cuatro subconductores por fase.")
    r_ac = np.array([c.resistance_ac_ohm_per_km for c in base.conductors])
    r_dc = np.full(len(r_ac),case.pscad["input_resistance_ohm_per_km"])
    # Se modifica una COPIA de la diagonal real; GMR y términos externos intactos.
    dc = base.z_ohm_per_m+np.diag((r_dc-r_ac)/1000)
    scenarios = tuple(make_scenario(name,z,e,t,case.labels,r,unequal=unequal) for name,z,r,unequal in (
        (AC_EQUAL,base.z_ohm_per_m,r_ac,False),(DC_EQUAL,dc,r_dc,False),
        (AC_SHARED,base.z_ohm_per_m,r_ac,True),(DC_SHARED,dc,r_dc,True)))
    _,references = pscad_reference(case.pscad,case.labels)
    pscad_phase = references["con_transposicion"]/1000
    pscad_seq = phase_to_sequence(pscad_phase,case.labels).z_ohm_per_m
    pscad_scalar = scalar_transposed_sequences(pscad_phase)
    rows=[]
    for scenario in scenarios:
        for k in range(3):
            z,ref = scenario.sequence_ohm_per_m[k,k]*1000,pscad_seq[k,k]*1000
            rows.append({"Escenario":scenario.name,"Secuencia":k,"STE_R_ohm_km":z.real,"STE_X_ohm_km":z.imag,
                         "PSCAD_R_ohm_km":ref.real,"PSCAD_X_ohm_km":ref.imag,
                         "Error_R_pct":percent_error(z.real,ref.real),"Error_X_pct":percent_error(z.imag,ref.imag),
                         "Delta_R_ohm_km":z.real-ref.real,"Delta_X_ohm_km":z.imag-ref.imag})
    a = np.exp(2j*np.pi/3)
    currents=[]
    for scenario in scenarios:
        for mode,ip in (("Positiva: [1,a²,a] A",np.array([1,a*a,a])),("Cero: [1,1,1] A",np.ones(3))):
            isub = scenario.response@ip
            phase_index=np.argmax(e,axis=1)
            ratios = n[phase_index]*isub/ip[phase_index]
            for i,c in enumerate(base.conductors):
                currents.append({"Escenario":scenario.name,"Excitacion":mode,"Subconductor":c.label,
                    "I_real_A":isub[i].real,"I_imag_A":isub[i].imag,"Modulo_A":abs(isub[i]),
                    "Desviacion_modulo_pct":100*(abs(ratios[i])-1),"Desfase_grados":np.angle(ratios[i],deg=True)})
    published = published_pscad_sequence() if root is None else published_pscad_sequence(root)
    conductor_ac = float(r_ac.mean()/4)
    conductor_dc = float(r_dc.mean()/4)
    positive_budget = {"Rconductor_AC_sobre_4_ohm_km":conductor_ac,"Rconductor_DC_sobre_4_ohm_km":conductor_dc,
        "R1_externo_STE_ohm_km":float(scenarios[0].sequence_ohm_per_m[1,1].real*1000-conductor_ac),
        "R1_PSCAD_menos_RDC_sobre_4_ohm_km":float(pscad_seq[1,1].real*1000-conductor_dc),
        "desplazamiento_DC_menos_AC_ohm_km":conductor_dc-conductor_ac}
    return {"case":case,"incidence":e,"weights":t,"scenarios":scenarios,"pscad_phase_ohm_m":pscad_phase,
            "pscad_sequence_ohm_m":pscad_seq,"pscad_scalar_ohm_m":pscad_scalar,
            "pscad_scalar_residual_ohm_m":float(np.max(np.abs(np.diag(pscad_seq)-pscad_scalar))),
            "pscad_published_sequence_ohm_m":published,
            "pscad_publication_residual_ohm_km":float(np.max(np.abs(pscad_seq-published)))*1000,
            "comparison":pd.DataFrame(rows),"currents":pd.DataFrame(currents),
            "positive_resistance_budget":positive_budget,
            "cancellation":cancellation_analysis(scenarios[0].transposed_phase_ohm_per_m,pscad_phase)}
