from io import BytesIO
import json
import numpy as np
from pypdf import PdfReader
from ste_calculator.pscad_series import load_dove_case
from ste_calculator.series_transposition import transpose_series
from ste_calculator.series_comparison import comparison_table,comparison_csv
from ste_calculator.series_report import series_pdf,series_record
from ste_calculator.sequence_examples import two_guard_case
from ste_calculator.series_inputs import SeriesInput
from ste_calculator.kron import reduce_augmented
import pandas as pd


def test_pdf_has_original_sections_average_all_comparisons_ac_dc_and_correct_units():
    case = load_dove_case()
    result = transpose_series(case.z_ohm_per_m,case.labels)
    table = comparison_table(result,case.pscad)
    reader = PdfReader(BytesIO(series_pdf(case,result,table,case.pscad)))
    text = '\n'.join(p.extract_text() for p in reader.pages)
    for token in ('kersting_pq_finite','0.1859','0.102','R_AC','R_DC','Original sin transposición',
                  'Promedio transpuesto','Tramo 3','Error R [%]','Error X [%]','Ω/km','Ω/m','4.68'):
        assert token in text
    for column in ('Error_R_pct','Error_X_pct','PSCAD_R_ohm_km','PSCAD_X_ohm_km'):
        for value in table[column]:
            assert f'{value:.10g}' in text
    assert all(float(p.mediabox.width)>float(p.mediabox.height) for p in reader.pages)


def test_csv_json_preserve_every_element_and_missing_values_without_nan_json():
    case = load_dove_case()
    result = transpose_series(case.z_ohm_per_m,case.labels,enabled=False)
    table = comparison_table(result,case.pscad)
    csv = pd.read_csv(BytesIO(comparison_csv(table)))
    assert len(csv)==18
    np.testing.assert_allclose(csv.Error_R_pct,table.Error_R_pct,rtol=1e-13)
    record = json.loads(json.dumps(series_record(case,result,table,case.pscad),allow_nan=False))
    assert record['transposicion_activada'] is False
    assert record['PSCAD']['resistance_type']=='DC'
    np.testing.assert_allclose(record['Z_seleccionada_ohm_m']['real'],case.z_ohm_per_m.real)
    no_reference = comparison_table(result)
    missing = series_record(case,result,no_reference)
    assert missing['comparacion_ohm_km'][0]['Error_R_pct'] is None
    assert 'NaN' not in json.dumps(missing,allow_nan=False)


def test_double_circuit_pdf_comparison_has_all_72_rows_and_six_phase_labels():
    augmented = two_guard_case(2)
    reduced = reduce_augmented(augmented,confirmed=True)
    from ste_calculator.carson import calculate_carson
    phase_result = calculate_carson(augmented.primitive.conductors[:6],60,100)
    case = SeriesInput(phase_result,reduced.z_ohm_per_m,augmented.phase_labels,'Ensayo algebraico con Kron',
                        {'metodo':'modified_carson','frecuencia_Hz':60,'resistividad_ohm_m':100})
    result = transpose_series(case.z_ohm_per_m,case.labels)
    table = comparison_table(result)
    assert len(table)==72
    reader = PdfReader(BytesIO(series_pdf(case,result,table)))
    text = '\n'.join(p.extract_text() for p in reader.pages)
    assert "A'" in text and "C'" in text and 'Sin resultados PSCAD' in text
    assert text.count('Error R [%]')>=2  # Encabezado repetido al paginar.
