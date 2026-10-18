"""Valida primero el JSON DOVE sin transposición y luego el promedio y PSCAD."""

from pathlib import Path
import json
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

import numpy as np
from ste_calculator.pscad_series import load_dove_case
from ste_calculator.series_transposition import transpose_series,require_equivalent_phases
from ste_calculator.series_comparison import comparison_table,comparison_csv
from ste_calculator.series_report import series_pdf,series_record


def main():
    case = load_dove_case()
    residual = case.metadata.get("residuo_JSON_original_ohm_m")
    if residual is None or residual>1e-12:
        raise ValueError(f"No se valida el caso original sin transposicion: residuo={residual}")
    print("Primero: caso SIN transposicion recalculado y contrastado con JSON. Residuo [ohm/m]:",residual)
    require_equivalent_phases(case.phase_result)
    result = transpose_series(case.z_ohm_per_m,case.labels,enabled=True)
    table = comparison_table(result,case.pscad)
    np.set_printoptions(precision=12,suppress=True)
    print("Original [ohm/km]:\n",result.original_ohm_per_m*1000)
    print("Despues: transpuesta desde tres permutaciones [ohm/km]:\n",result.average_ohm_per_m*1000)
    print(table.drop(columns="Base_R").to_string(index=False))
    output = ROOT/"output"
    (output/"pdf").mkdir(parents=True,exist_ok=True)
    (output/"ste_carson_transposicion_dove.csv").write_bytes(comparison_csv(table))
    (output/"ste_carson_transposicion_dove.json").write_text(json.dumps(series_record(case,result,table,case.pscad),ensure_ascii=False,indent=2,allow_nan=False),encoding="utf-8")
    (output/"pdf"/"ste_carson_transposicion_dove.pdf").write_bytes(series_pdf(case,result,table,case.pscad))
    print("R_AC bibliografica STE=.1859 ohm/milla; R_DC PSCAD=.102 ohm/km, por subconductor. Modelos no identicos.")


if __name__=="__main__":
    main()
