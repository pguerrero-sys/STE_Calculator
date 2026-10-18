"""Recalcula el ejemplo aéreo 4.1 completo, sin resultados fijados en código."""

import json
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

import numpy as np
from ste_calculator.carson import calculate_carson, kersting_example, convert_impedance
from ste_calculator.kron import AuxiliaryConductor, ZERO_DROP, augment_carson, reduce_augmented
from ste_calculator.kron_report import kron_record, kron_pdf


def main():
    phases = calculate_carson(kersting_example(),60,100)
    neutral = AuxiliaryConductor(kersting_example(True)[-1],"neutral",ZERO_DROP,
                                  "Kersting §4.1.6 p.87 y ejemplo 4.1 pp.92-94: neutro multitierra ideal")
    augmented = augment_carson(phases,(neutral,))
    reduced = reduce_augmented(augmented,confirmed=True)
    output = ROOT/"output"
    (output/"pdf").mkdir(parents=True,exist_ok=True)
    (output/"ste_kron_kersting.json").write_text(json.dumps(kron_record(augmented,reduced),ensure_ascii=False,indent=2),encoding="utf-8")
    (output/"pdf"/"ste_kron_kersting.pdf").write_bytes(kron_pdf(augmented,reduced))
    np.set_printoptions(precision=9,suppress=True,linewidth=130)
    for unit in ("Ω/mile","Ω/km","Ω/m"):
        print("Primitiva completa",unit.replace("Ω","ohm"))
        print(convert_impedance(augmented.z_ohm_per_m,"Ω/m",unit))
        print("Reducida",unit.replace("Ω","ohm"))
        print(convert_impedance(reduced.z_ohm_per_m,"Ω/m",unit))
    print("cond(Znn):",reduced.condition_number,"residuo:",reduced.solve_residual)
    print("Hipotesis declarada: caida de tension auxiliar nula. No validacion de instalacion ni PSCAD.")


if __name__=="__main__":
    main()
