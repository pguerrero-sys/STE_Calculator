from io import BytesIO
import json
import numpy as np
from pypdf import PdfReader
from ste_calculator.study import calculate_study
from ste_calculator.study_report import summary_pdf,annex_pdf,study_record
from ste_calculator.inductance import IDEAL_GROUND,NO_GROUND
from tests.test_study import config


def test_short_and_full_reports_have_distinct_content_and_preserve_values():
    study=calculate_study(config())
    summary=PdfReader(BytesIO(summary_pdf(study,IDEAL_GROUND,(IDEAL_GROUND,NO_GROUND))))
    annex=PdfReader(BytesIO(annex_pdf(study,IDEAL_GROUND,(NO_GROUND,))))
    text='\n'.join(p.extract_text() for p in summary.pages)
    full='\n'.join(p.extract_text() for p in annex.pages)
    assert len(summary.pages)<=8
    assert len(annex.pages)>len(summary.pages)
    assert 'Tramo 9' not in text
    assert 'Tramo 9' in full and 'Psub' in full and '0.103' in full
    assert 'R_DC20=0.1007' in text
    assert '0.102' in text
    record=study_record(study)
    json.dumps(record,ensure_ascii=False,allow_nan=False)
    c=record['study']['variants'][str((NO_GROUND,True))]['c_f_per_m']
    np.testing.assert_array_equal(c,study.variants[NO_GROUND,True].c_f_per_m)
