"""Comparación por componentes R y X, sin convertir ni equiparar R_DC y R_AC."""

import json
import numpy as np
import pandas as pd
from .carson import convert_impedance
from .models import InputError, finite_number

STATES = ("sin_transposicion","con_transposicion")


def pscad_reference(payload,labels):
    """Matrices de PSCAD suministradas, nunca derivadas de las salidas STE."""
    try:
        data = json.loads(payload) if isinstance(payload,(str,bytes,bytearray)) else payload
        if not isinstance(data,dict) or not isinstance(data.get("source"),str) or not data["source"].strip():
            raise InputError("PSCAD: indica source para identificar el origen de los resultados.")
        if data.get("resistance_type") not in ("AC","DC","unknown"):
            raise InputError("PSCAD: resistance_type debe ser AC, DC o unknown.")
        order = tuple(data["labels"])
        if len(order)!=len(labels) or set(order)!=set(labels):
            raise InputError("PSCAD: etiquetas de fases incompatibles; no se reduce doble circuito a tres.")
        indices = [order.index(p) for p in labels]
        matrices = {}
        for state in STATES:
            if state not in data:
                continue
            entry = data[state]
            r,x = np.asarray(entry["real"],float),np.asarray(entry["imag"],float)
            if r.shape!=(len(labels),)*2 or x.shape!=r.shape or not np.all(np.isfinite(r)) or not np.all(np.isfinite(x)):
                raise InputError(f"PSCAD {state}: R y X deben ser matrices finitas de {len(labels)}×{len(labels)}.")
            z = convert_impedance(r+1j*x,entry["unit"],"Ω/km")
            matrices[state] = z[np.ix_(indices,indices)]
        if not matrices:
            raise InputError("PSCAD: falta sin_transposicion o con_transposicion; no se genera una a partir de la otra.")
    except (ValueError,TypeError,KeyError,AttributeError) as exc:
        if isinstance(exc,InputError):
            raise
        raise InputError("JSON PSCAD inválido: requiere labels y matrices real/imag con unit explícita.") from exc
    return data,matrices


def percent_error(computed,reference):
    c = finite_number(computed,"Valor STE")
    r = finite_number(reference,"Valor PSCAD")
    return None if r==0 else 100*abs(c-r)/abs(r)


def comparison_table(result,reference=None):
    data,matrices = ({}, {}) if reference is None else pscad_reference(reference,result.labels)
    note = {"DC":"R_AC STE frente a R_DC PSCAD: diferencia de entradas/modelos",
            "AC":"R_AC en ambos; revisar temperatura, frecuencia y método",
            "unknown":"Base de resistencia PSCAD no especificada"}.get(data.get("resistance_type"),"Pendiente de datos PSCAD")
    rows = []
    for state,z in zip(STATES,(result.original_ohm_per_m,result.average_ohm_per_m)):
        z = convert_impedance(z,"Ω/m","Ω/km")
        reference_z = matrices.get(state)
        for i,p in enumerate(result.labels):
            for j,q in enumerate(result.labels):
                value = None if reference_z is None else reference_z[i,j]
                rows.append({"Estado":state,"Fila":p,"Columna":q,"STE_R_ohm_km":z[i,j].real,"STE_X_ohm_km":z[i,j].imag,
                    "PSCAD_R_ohm_km":None if value is None else value.real,"PSCAD_X_ohm_km":None if value is None else value.imag,
                    "Error_R_pct":None if value is None else percent_error(z[i,j].real,value.real),
                    "Error_X_pct":None if value is None else percent_error(z[i,j].imag,value.imag),"Base_R":note})
    return pd.DataFrame(rows)


def comparison_csv(table):
    return table.to_csv(index=False,na_rep="",lineterminator="\n").encode("utf-8-sig")
