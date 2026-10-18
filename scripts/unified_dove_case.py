"""Verificación reproducible de la nueva interfaz y sus dos exportaciones."""
from pathlib import Path
import sys,json
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from dataclasses import replace
from pypdf import PdfReader
from ste_calculator.conductor_library import conductor
from ste_calculator.models import Conductor
from ste_calculator.bundles import BundleSpec
from ste_calculator.study import StudyConfig,calculate_study
from ste_calculator.study_report import summary_pdf,annex_pdf,study_record
from ste_calculator.inductance import IDEAL_GROUND,NO_GROUND


def main():
    d=conductor('DOVE')
    historical=replace(d,gmr_m=.00954024,sources=dict(d.sources,diameter_gmr='Regresión C6: radio/RMG históricos del usuario; separados de Tablas_ACSR.pdf'))
    specs=tuple(BundleSpec(Conductor(c,p,x,h+12*(c-1)),2,.011765,.4572) for c in (1,2) for p,x,h in (('A',-3,13),('B',3,13),('C',0,9)))
    result=calculate_study(StudyConfig(specs,(historical,)*6,voltage_kv=220,power=250,power_factor=.9,length_km=100,complete=True,parallel=True,case_name='DOVE C6 histórico + resistencia académica de tabla, fuentes separadas'))
    output=ROOT/'output';(output/'pdf').mkdir(exist_ok=True)
    for name,data in (('ste_resumen_dove.pdf',summary_pdf(result,IDEAL_GROUND,(IDEAL_GROUND,NO_GROUND))),('ste_anexo_dove.pdf',annex_pdf(result,IDEAL_GROUND,(IDEAL_GROUND,NO_GROUND)))):
        path=output/'pdf'/name;path.write_bytes(data)
        print(name,len(PdfReader(path).pages),'pages')
    (output/'ste_estudio_unificado_dove.json').write_text(json.dumps(study_record(result),ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')
    print('I_total',result.resistance.total_current_a,'A')
    print('I_sub',result.resistance.subconductor_current_a.tolist(),'A')
    print('R_phase',result.resistance.phase_ohm_km.tolist(),'ohm/km')
    print('R_parallel',result.resistance.parallel_ohm_km.tolist(),'ohm/km')
    print('C6 no ground nF/km:',(result.variants[NO_GROUND,True].c_f_per_m*1e12).tolist())


if __name__=='__main__':main()
