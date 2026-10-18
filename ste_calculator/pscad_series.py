"""Lectura estricta de Z por longitud en salidas LCP, sin usar datos long-line."""

from dataclasses import replace
from pathlib import Path
import re
import numpy as np
from .models import InputError
from .series_inputs import exported_case

NUMBER = r"[+-]?(?:\d*\.\d+|\d+\.?)(?:[EeDd][+-]?\d+)?"
PAIR = re.compile(rf"({NUMBER})\s*,\s*({NUMBER})")
ROOT = Path(__file__).resolve().parents[1]
UNT = "DOVE_220kV_SinTransposicion_Prueba.txt"
TRN = "DOVE_220kV_ConTransposicion_Prueba.txt"


def phase_series_matrix(text,labels):
    lines = text.splitlines()
    starts = [i for i,line in enumerate(lines) if re.fullmatch(r"\s*SERIES IMPEDANCE MATRIX \(Z\) \[ohms/m\]:\s*",line)]
    if len(starts)!=1:
        raise InputError("PSCAD: se requiere un único bloque SERIES IMPEDANCE MATRIX (Z) [ohms/m]; no usar long-line, modos o secuencias.")
    phase_header = re.search(r"PHASE DOMAIN DATA\s*@\s*("+NUMBER+r")\s*Hz","\n".join(lines[:starts[0]]))
    if phase_header is None:
        raise InputError("PSCAD: falta frecuencia identificable de PHASE DOMAIN DATA.")
    rows = []
    for line in lines[starts[0]+1:]:
        if not line.strip() and not rows:
            continue
        matches = list(PAIR.finditer(line))
        if len(matches)!=len(labels) or PAIR.sub("",line).strip():
            break
        rows.append([complex(float(m[1].replace("D","E").replace("d","e")),float(m[2].replace("D","E").replace("d","e"))) for m in matches])
        if len(rows)==len(labels):
            break
    matrix = np.asarray(rows,dtype=complex)
    if matrix.shape!=(len(labels),)*2 or not np.all(np.isfinite(matrix)):
        raise InputError(f"PSCAD: matriz de fase incompleta; se esperan {len(labels)} filas y columnas.")
    frequency = float(phase_header[1].replace("D","E").replace("d","e"))
    if not np.isfinite(frequency) or frequency<=0:
        raise InputError("PSCAD: frecuencia de fase inválida.")
    return matrix,frequency


def find_dove_folder(root=ROOT):
    candidates = [p.parent for p in (Path(root)/"referencias").rglob("ste_carson.json")
                  if (p.parent/UNT).is_file() and (p.parent/TRN).is_file()]
    if len(candidates)!=1:
        raise InputError(f"Caso DOVE: se esperaba una carpeta con ste_carson.json y ambos TXT PSCAD; encontradas {len(candidates)} dentro de referencias.")
    return candidates[0]


def load_dove_case(root=ROOT):
    folder = find_dove_folder(root)
    case = exported_case((folder/"ste_carson.json").read_bytes())
    reference = {"source":"; ".join(str(folder/name) for name in (UNT,TRN)),"labels":case.labels,
                 "resistance_type":"DC","input_resistance_ohm_per_km":.102,
                 "resistance_source":"Dato declarado por el usuario y LEEME del caso: por subconductor",
                 "files":{},"frequencies_Hz":{}}
    for state,name in (("sin_transposicion",UNT),("con_transposicion",TRN)):
        z,f = phase_series_matrix((folder/name).read_text(encoding="utf-8-sig"),case.labels)
        reference[state] = {"real":z.real.tolist(),"imag":z.imag.tolist(),"unit":"Ω/m"}
        reference["files"][state] = str(folder/name)
        reference["frequencies_Hz"][state] = f
    metadata = dict(case.metadata,nombre="DOVE: entradas reales del JSON suministrado",
                    ruta_JSON=str(folder/"ste_carson.json"),resistencia_PSCAD="DC declarada: 0.102 Ω/km por subconductor")
    return replace(case,metadata=metadata,pscad=reference)
