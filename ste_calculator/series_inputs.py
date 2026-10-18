"""Entrada de etapa 7D: estado actual o JSON exportado; nunca usa Z guardada como salida."""

from dataclasses import dataclass,asdict
import json
import re
import numpy as np
from .carson import (CarsonConductor, CarsonPhaseResult, calculate_carson, calculate_carson_layout,
                      convert_impedance, MODIFIED)
from .kron import AuxiliaryConductor, augment_carson, reduce_augmented, UNKNOWN
from .models import InputError, PHASES, finite_number
from .bundles import BundleSpec
from .double_circuit import build_circuit_geometry


@dataclass(frozen=True)
class SeriesInput:
    phase_result: object
    z_ohm_per_m: np.ndarray
    labels: tuple
    description: str
    metadata: dict
    pscad: dict | None = None


def state_case(conductors,circuit_count,state,*,with_kron=False,coordinate_error=""):
    if circuit_count not in (1,2):
        raise InputError("Carson transpuesto admite uno o dos circuitos.")
    if conductors is None:
        raise InputError("Coordenadas actuales: "+coordinate_error)
    ordered = tuple(sorted(conductors,key=lambda c:(c.circuit,PHASES.index(c.phase))))
    labels = tuple(c.phase+("'" if c.circuit==2 else "") for c in ordered)
    if len(labels)!=circuit_count*3:
        raise InputError("Faltan coordenadas de fases para transponer Carson.")
    unit = state.get("car_r_unit","Ω/km")
    resistances = tuple(float(convert_impedance(finite_number(state.get(f"car_r_{p}"),f"R_AC de {p}"),unit,"Ω/km").real) for p in labels)
    gmr = tuple(state.get(f"car_gmr_{p}") for p in labels)
    source,conditions = state.get("car_source",""),state.get("car_conditions","")
    f,rho,method = state.get("car_f"),state.get("car_rho"),state.get("car_method",MODIFIED)
    if state.get("car_geometry_choice","").startswith("Subconductores"):
        prefix = "haz" if circuit_count==1 else "dc"
        specs = tuple(BundleSpec(c,state.get(f"{prefix}_n_{p}",1),state.get(f"{prefix}_r_{p}"),
                                  state.get(f"{prefix}_s_{p}"),state.get(f"{prefix}_angle_{p}",0.)) for c,p in zip(ordered,labels))
        geometry = build_circuit_geometry(specs)
        result = calculate_carson_layout(geometry,resistances,gmr,(source,)*len(labels),f,rho,method,conditions)
    else:
        result = calculate_carson(tuple(CarsonConductor(p,c.x_m,c.y_m,r,g,source,conditions=conditions)
                                        for p,c,r,g in zip(labels,ordered,resistances,gmr)),f,rho,method)
    z = result.z_ohm_per_m
    description = "Fases Carson sin eliminación de auxiliares"
    if with_kron:
        auxiliaries = []
        for i in range(state.get("kron_count",0)):
            prefix = f"kron_{i}_"
            c = CarsonConductor(state.get(prefix+"label",f"N{i+1}"),state.get(prefix+"x"),state.get(prefix+"h"),
                                 state.get(prefix+"r"),state.get(prefix+"gmr"),state.get(prefix+"source",""))
            auxiliaries.append(AuxiliaryConductor(c,state.get(prefix+"role","neutral"),
                                  state.get(prefix+"connection",UNKNOWN),state.get(prefix+"basis","")))
        augmented = augment_carson(result,auxiliaries)
        z = reduce_augmented(augmented,confirmed=state.get("kron_confirm",False)).z_ohm_per_m
        description = "Kron por tramo: auxiliares fijos, ΔVn=0 declarado"
    primitive = getattr(result,"primitive",result)
    return SeriesInput(result,z,labels,description,{"frecuencia_Hz":f,"resistividad_ohm_m":rho,
                        "metodo":method,"fuente_R_AC":source,"condiciones":conditions,"resistencia_STE":"AC",
                        "conductores":[vars(c) for c in primitive.conductors],
                        "auxiliares":[asdict(a) for a in auxiliaries] if with_kron else [],
                        "kron_DeltaVn0_declarado":bool(with_kron and state.get("kron_confirm",False))})


def exported_case(payload):
    """Importa carson_record de 7A, incluido haz con grupos explícitos en etiquetas.

    Acepta envoltorio {carson: registro, case_name: nombre, pscad: referencia}.
    Para Kron se usa el estado de los controles anteriores, sin inferir conexiones
    de un archivo que no las declare. No carga fórmulas ni ejecuta código del JSON.
    """
    try:
        data = json.loads(payload) if isinstance(payload,(str,bytes,bytearray)) else payload
        record = data.get("carson",data)
        raw = record["conductores"]
        if not isinstance(raw,list) or not 3<=len(raw)<=24:
            raise InputError("JSON: se admiten hasta 24 subconductores de tres o seis fases; sin auxiliares implícitos.")
        labels = tuple(record["orden_fases"])
        conductors = tuple(CarsonConductor(**row) for row in raw)
        frequency = record["frecuencia_Hz"]
        rho = record["resistividad_ohm_m"]
        method = record["metodo"]
    except (ValueError,TypeError,KeyError,AttributeError) as exc:
        if isinstance(exc,InputError):
            raise
        raise InputError("JSON Carson inválido: se requieren conductores, orden_fases, frecuencia_Hz, resistividad_ohm_m y metodo del exportador 7A.") from exc
    if record.get("resistance_type","AC")!="AC":
        raise InputError("El JSON debe aportar R_AC documentada; no se convierte R_DC automáticamente.")
    if len(labels) not in (3,6):
        raise InputError("El JSON debe conservar tres o seis fases, sin auxiliares sin declarar.")
    primitive = calculate_carson(conductors,frequency,rho,method)
    if primitive.labels==labels:
        result = primitive
    else:
        t = np.zeros((len(conductors),len(labels)))
        for p,label in enumerate(labels):
            indices = [i for i,c in enumerate(conductors) if re.fullmatch(re.escape(label)+r"-[1-4]",c.label)]
            if not 1<=len(indices)<=4:
                raise InputError(f"JSON: no hay agrupación inequívoca de subconductores de {label}.")
            t[indices,p] = 1/len(indices)
        if not np.all(np.count_nonzero(t,axis=1)==1):
            raise InputError("JSON: hay auxiliares o subconductores sin asignación explícita de fase.")
        r,x,e,z = [t.T@m@t for m in (primitive.z_conductor_ohm_per_m,primitive.z_geometry_ohm_per_m,
                                     primitive.z_earth_ohm_per_m,primitive.z_ohm_per_m)]
        result = CarsonPhaseResult(primitive,labels,t,r,x,e,z)
    metadata = {"nombre":data.get("case_name","JSON Carson importado"),"frecuencia_Hz":frequency,
                "resistividad_ohm_m":rho,"metodo":method,"resistencia_STE":"AC",
                "fuentes_R_AC":list(dict.fromkeys(c.source for c in conductors)),
                "conductores":[vars(c) for c in conductors]}
    for key,unit in (("Z_ohm_m","Ω/m"),("Z_ohm_km","Ω/km")):
        if key in record:
            try:
                saved = np.asarray(record[key]["real"],float)+1j*np.asarray(record[key]["imag"],float)
                if saved.shape!=result.z_ohm_per_m.shape or not np.all(np.isfinite(saved)):
                    raise ValueError("Dimensiones o valores de Z almacenada inválidos")
                metadata["residuo_JSON_original_ohm_m"] = float(np.max(np.abs(result.z_ohm_per_m-convert_impedance(saved,unit,"Ω/m"))))
            except (ValueError,TypeError,KeyError) as exc:
                raise InputError("JSON: matriz almacenada con dimensiones o valores inválidos.") from exc
            break
    return SeriesInput(result,result.z_ohm_per_m,labels,"Recalculado desde entradas del JSON; sin Kron implícito",metadata,data.get("pscad"))
