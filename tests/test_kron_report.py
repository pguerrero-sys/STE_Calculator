from dataclasses import replace
from io import BytesIO
import json
import numpy as np
from pypdf import PdfReader
from tests.test_kron import example
from ste_calculator.kron import reduce_augmented, augment_carson
from ste_calculator.kron_report import kron_record, kron_pdf
from ste_calculator.printing import render_pdf, PAGE_SIZE, MARGIN, font_name
from reportlab.pdfbase.pdfmetrics import stringWidth
from ste_calculator.carson import calculate_carson_layout
from ste_calculator.double_circuit import reproducible_specs, build_circuit_geometry


def test_record_preserves_complex_blocks_units_and_electrical_conditions():
    aug = example()
    red = reduce_augmented(aug,confirmed=True)
    record = json.loads(json.dumps(kron_record(aug,red)))
    z = record["Z_reducida_ohm_m"]
    np.testing.assert_allclose(np.array(z["real"])+1j*np.array(z["imag"]),red.z_ohm_per_m)
    assert record["reduccion_aplicada"] is True
    assert record["auxiliares"][0]["connection"]=="ideal_multigrounded"
    assert set(record["bloques_ohm_m"])=={"pp","pn","np","nn"}
    assert record["primitiva_Carson"]["orden_fases"]==["A","B","C","n"]
    raw = kron_record(aug)
    assert raw["reduccion_aplicada"] is False
    assert "Z_reducida_ohm_m" not in raw


def test_pdf_contains_full_equations_inputs_blocks_and_result_or_no_reduction():
    aug = example()
    red = reduce_augmented(aug,confirmed=True)
    reader = PdfReader(BytesIO(kron_pdf(aug,red)))
    text = "\n".join(p.extract_text() for p in reader.pages)
    for expected in ("Zreducida=Zpp-Zpn", "inversa(Znn)","Znp", "Znn", "In=-Y Ip", "Ω/km", "Ω/mile", "Ω/m", "4.45", "4.54", "RMG", "Multitierra ideal"):
        assert expected in text
    assert f"{red.z_ohm_per_km[0,0].real:.9e}" in text
    assert "HIPÓTESIS DECLARADA" in text
    raw = PdfReader(BytesIO(kron_pdf(aug)))
    raw_text = "\n".join(p.extract_text() for p in raw.pages)
    assert "REDUCCIÓN NO APLICADA" in raw_text
    assert "Zreducida de fases" not in raw_text


def test_pdf_wide_double_circuit_four_bundle_plus_two_guards_preserves_all_cells():
    base = calculate_carson_layout(build_circuit_geometry(reproducible_specs(4)),(.2,)*6,(.008,)*6,("Prueba numérica",)*6,60,100)
    a = example().auxiliaries[0]
    auxiliaries = tuple(replace(a,conductor=replace(a.conductor,label=f"G{i+1}",x_m=x,height_m=21),role="guard")
                        for i,x in enumerate((-4,4)))
    aug = augment_carson(base,auxiliaries)
    red = reduce_augmented(aug,confirmed=True)
    text = "\n".join(p.extract_text() for p in PdfReader(BytesIO(kron_pdf(aug,red))).pages)
    assert "columnas 25-26" in text
    assert "G1" in text and "G2" in text and "C'-4" in text
    for value in aug.primitive.z_ohm_per_m.flat:
        assert f"{value.real:.9e}" in text and f"{value.imag:.9e}" in text


def test_pdf_long_formula_wraps_with_tail_and_no_text_past_right_margin():
    # Reproduce una sustitución sin espacios que excede una línea de página.
    formula = "Zred="+"(0.123456789+j0.987654321)*"*45+"FIN_FORMULA"
    reader = PdfReader(BytesIO(render_pdf("Fórmula larga",[formula+"\nSegunda ecuación: ΔVn=0"],[])))
    text = "".join(p.extract_text() for p in reader.pages)
    assert "FIN_FORMULA" in text and "Segunda ecuación" in text
    fragments = []
    for p in reader.pages:
        def visitor(value,cm,tm,font,size):
            # ReportLab emite cada renglón envuelto por separado.
            if "0.123456789" in value or "FIN_FORMULA" in value:
                fragments.append(value.strip())
        p.extract_text(visitor_text=visitor)
    assert len(fragments)>1
    for line in fragments:
        for row in line.splitlines():
            assert stringWidth(row,font_name(),9)<=PAGE_SIZE[0]-2*MARGIN+1
