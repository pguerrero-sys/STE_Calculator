"""Ejemplo 4.1 y dos guardas de uno/dos circuitos, con matrices completas."""

import json
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

import numpy as np
from ste_calculator.carson import calculate_carson, kersting_example, convert_impedance
from ste_calculator.kron import AuxiliaryConductor, ZERO_DROP, augment_carson, reduce_augmented
from ste_calculator.sequences import phase_to_sequence
from ste_calculator.sequence_examples import two_guard_case
from ste_calculator.kron_report import kron_record, kron_pdf


def main():
    neutral = AuxiliaryConductor(kersting_example(True)[-1],"neutral",ZERO_DROP,"Kersting p.87: neutro multitierra ideal")
    book = augment_carson(calculate_carson(kersting_example(),60,100),(neutral,))
    cases = {"kersting_4_1":book,"dos_guardas_C1_ensayo":two_guard_case(1),"dos_guardas_C2_ensayo":two_guard_case(2)}
    records = {}
    np.set_printoptions(precision=9,suppress=True,linewidth=150)
    output = ROOT/"output"
    (output/"pdf").mkdir(parents=True,exist_ok=True)
    for name,case in cases.items():
        red = reduce_augmented(case,confirmed=True)
        seq = phase_to_sequence(red.z_ohm_per_m,case.phase_labels)
        records[name] = kron_record(case,red)
        print(name,"Z012 [ohm/mile], orden",seq.labels)
        print(convert_impedance(seq.z_ohm_per_m,"Ω/m","Ω/mile"))
        if name=="kersting_4_1":
            (output/"pdf"/"ste_secuencias_kersting.pdf").write_bytes(kron_pdf(case,red))
        else:
            validation = records[name]["contraste_dos_guardas"]
            print("Error relativo independiente:",validation["error_relativo"],"Residuo frontera:",validation["residuo_frontera"])
    (output/"ste_secuencias_validacion.json").write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding="utf-8")
    print("Geometrias de dos guardas sinteticas: ensayo algebraico, no datos comerciales ni validacion fisica de tierras.")


if __name__=="__main__":
    main()
