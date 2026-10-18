"""Regenerar el ejemplo 4.1 de Kersting, sin Kron, con ambos métodos aproximados."""

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

import numpy as np
from ste_calculator.carson import calculate_carson, kersting_example, METHODS, MODIFIED, convert_impedance
from ste_calculator.carson_report import carson_record, carson_pdf


def main():
    output = ROOT/"output"
    (output/"pdf").mkdir(parents=True,exist_ok=True)
    methods = {}
    np.set_printoptions(precision=9,suppress=True,linewidth=130)
    for method in METHODS:
        result = calculate_carson(kersting_example(),60,100,method)
        methods[method] = carson_record(result)
        print(METHODS[method])
        print("R [ohm/km]\n",result.z_ohm_per_km.real)
        print("X [ohm/km]\n",result.z_ohm_per_km.imag)
        if method==MODIFIED:
            (output/"pdf"/"ste_carson_kersting.pdf").write_bytes(carson_pdf(result))
    raw = calculate_carson(kersting_example(True),60,100)
    primitive_mile = convert_impedance(raw.z_ohm_per_m,"Ω/m","Ω/mile")
    record = {"contexto":"Kersting ejemplo 4.1: bloque primitivo de fases, sin Kron; no validación PSCAD",
              "metodos":methods,"primitiva_4_hilos_sin_Kron":carson_record(raw),
              "primitiva_4_hilos_ohm_mile":{"real":primitive_mile.real.tolist(),"imag":primitive_mile.imag.tolist()}}
    (output/"ste_carson_kersting.json").write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding="utf-8")
    print("PDF y JSON calculados en output/. No se aplicó Kron.")


if __name__=="__main__":
    main()
