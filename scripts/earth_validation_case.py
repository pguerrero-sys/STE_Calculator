"""Reproducir 7F conservando entradas y artefactos anteriores."""
from pathlib import Path
import json
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from ste_calculator.earth_validation import analyze_earth_return, validation_record
from ste_calculator.earth_validation_report import earth_validation_pdf


def main():
    analysis=analyze_earth_return()
    output=ROOT/'output'
    (output/'pdf').mkdir(parents=True,exist_ok=True)
    (output/'ste_validacion_tierra_acsr_dove.json').write_text(
        json.dumps(validation_record(analysis),ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')
    for key,suffix in (('comparison','pscad'),('controlled','metodos')):
        (output/f'ste_validacion_tierra_acsr_{suffix}.csv').write_bytes(
            analysis[key].to_csv(index=False,lineterminator='\n').encode('utf-8-sig'))
    (output/'ste_validacion_tierra_acsr_pscad_numerica.csv').write_bytes(
        analysis['numerical_comparison'].to_csv(index=False,lineterminator='\n').encode('utf-8-sig'))
    (output/'pdf'/'ste_validacion_tierra_acsr_dove.pdf').write_bytes(earth_validation_pdf(analysis))
    df=analysis['comparison']
    print(df[(df.Dominio=='secuencia')&(df.Fila==df.Columna)&(df.Estado=='con_transposicion')].to_string(index=False))
    print('PSCAD 0=Deri-Semlyen; 2=integracion numerica: confirmados por usuario en interfaz. No equivalencia ACSR demostrada.')


if __name__=='__main__':
    main()
