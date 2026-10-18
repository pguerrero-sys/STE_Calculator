from io import BytesIO
import json
import numpy as np
from pypdf import PdfReader
from tests.test_kron import example
from ste_calculator.kron import reduce_augmented
from ste_calculator.kron_report import kron_record,kron_pdf
from ste_calculator.sequences import phase_to_sequence
from ste_calculator.sequence_examples import two_guard_case


def test_sequence_json_preserves_full_complex_matrix_all_units_and_convention():
    case = example()
    red = reduce_augmented(case,confirmed=True)
    seq = phase_to_sequence(red.z_ohm_per_m,case.phase_labels)
    record = json.loads(json.dumps(kron_record(case,red)))["componentes_simetricas"]
    assert record["orden_secuencias"]==["0","1","2"]
    assert "exp(jωt)" in record["convencion"]
    for unit,factor in (("Ω/m",1),("Ω/km",1000),("Ω/mile",1609.344)):
        z = record["Z012_por_unidad"][unit]
        np.testing.assert_allclose(np.array(z["real"])+1j*np.array(z["imag"]),seq.z_ohm_per_m*factor,rtol=1e-14)
    assert "componentes_simetricas" not in kron_record(case)


def test_sequence_pdf_equations_and_all_nondiagonal_cells_and_units():
    case = example()
    red = reduce_augmented(case,confirmed=True)
    seq = phase_to_sequence(red.z_ohm_per_m,case.phase_labels)
    text = "\n".join(p.extract_text() for p in PdfReader(BytesIO(kron_pdf(case,red))).pages)
    for expected in ("Z012=A^-1 Zabc A", "A^-1 = (1/3)","positiva", "negativa", "Secuencia/circuito", "4.59", "4.67"):
        assert expected in text
    for value in (seq.z_ohm_per_m*1609.344).flat:
        assert f"{value.real:.9e}" in text and f"{value.imag:.9e}" in text


def test_double_circuit_guard_report_includes_independent_check_and_six_sequences():
    case = two_guard_case(2)
    red = reduce_augmented(case,confirmed=True)
    record = kron_record(case,red)
    assert record["contraste_dos_guardas"]["error_relativo"]<1e-14
    text = "\n".join(p.extract_text() for p in PdfReader(BytesIO(kron_pdf(case,red))).pages)
    assert "0 C2" in text and "2 C2" in text
    assert "Z independiente dos guardas" in text
    assert "Error relativo=" in text
