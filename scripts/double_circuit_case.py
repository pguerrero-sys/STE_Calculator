"""Generar las matrices calculadas y el informe del caso sintético de etapa 6."""

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

import numpy as np
from ste_calculator.double_circuit import calculate_double_circuit, reproducible_specs, LABELS
from ste_calculator.inductance import RMGInput, SOLID_UNIFORM
from ste_calculator.printing import double_circuit_pdf


def main():
    specs = reproducible_specs()
    result = calculate_double_circuit(specs,(RMGInput(.011765,SOLID_UNIFORM),)*6)
    output = ROOT/"output"
    (output/"pdf").mkdir(parents=True,exist_ok=True)
    (output/"pdf"/"ste_doble_circuito.pdf").write_bytes(double_circuit_pdf(result,60))
    record = {
        "contexto":"Caso sintético de comprobación, no diseño validado",
        "orden_fases":LABELS,
        "posiciones_m":[[s.center.x_m,s.center.y_m] for s in specs],
        "subconductores_por_fase":1,"radio_individual_m":.011765,
        "modelo":"Macizo no magnético uniforme; suelo ideal; sin transposición",
        "mu0_H_m":float(4*np.pi*1e-7),"epsilon0_F_m":8.8541878128e-12,
        "L_mH_km":(result.l_h_per_m*1e6).tolist(),
        "C_nF_km":(result.c_f_per_m*1e12).tolist(),
        "P_promedio_adimensional":result.average_phase_p.tolist(),
        "residuo_normalizado":result.inversion_residual,
    }
    (output/"ste_doble_circuito.json").write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding="utf-8")
    np.set_printoptions(precision=6,suppress=True,linewidth=120)
    print("Orden: A B C A' B' C'")
    print("L [mH/km]\n",result.l_h_per_m*1e6)
    print("C [nF/km]\n",result.c_f_per_m*1e12)
    print("PDF y JSON calculados en output/; residuo normalizado",result.inversion_residual)


if __name__=="__main__":
    main()
