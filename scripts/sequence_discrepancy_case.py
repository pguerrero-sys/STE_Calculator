"""Ejecutar análisis 7E sin editar entradas, módulos ni salidas 7D."""

from pathlib import Path
import json
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

from ste_calculator.sequence_discrepancy import analyze_dove
from ste_calculator.sequence_discrepancy_report import discrepancy_pdf,discrepancy_record


def main():
    analysis=analyze_dove()
    output=ROOT/'output'
    (output/'pdf').mkdir(parents=True,exist_ok=True)
    record=discrepancy_record(analysis)
    (output/'ste_secuencias_discrepancias_dove.json').write_text(json.dumps(record,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')
    for key,name in (('comparison','ste_secuencias_discrepancias_dove.csv'),('currents','ste_corrientes_subconductores_dove.csv')):
        (output/name).write_bytes(analysis[key].to_csv(index=False,lineterminator='\n').encode('utf-8-sig'))
    (output/'pdf'/'ste_secuencias_discrepancias_dove.pdf').write_bytes(discrepancy_pdf(analysis))
    print(analysis['comparison'].drop(columns=['PSCAD_R_ohm_km','PSCAD_X_ohm_km']).to_string(index=False))
    print('Cancelacion R1:',json.dumps(analysis['cancellation'],ensure_ascii=True))
    print('Diagnostico DC/reparto desigual; no equivalencia PSCAD ni ajuste de datos tecnicos originales.')


if __name__=='__main__':
    main()
