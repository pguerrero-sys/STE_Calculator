from io import BytesIO
import json

import numpy as np
from pypdf import PdfReader

from ste_calculator.carson import calculate_carson, kersting_example, calculate_carson_layout, PQ_TRUNCATED
from ste_calculator.carson_report import carson_record, carson_pdf
from ste_calculator.double_circuit import build_circuit_geometry, reproducible_specs
from ste_calculator.transposition import calculate_transposition
from ste_calculator.inductance import RMGInput, SOLID_UNIFORM


def test_json_preserves_complex_parts_sources_units_and_no_kron():
    result = calculate_carson(kersting_example(True),60,100)
    record = json.loads(json.dumps(carson_record(result)))
    matrix = np.array(record["Z_ohm_km"]["real"])+1j*np.array(record["Z_ohm_km"]["imag"])
    np.testing.assert_allclose(matrix,result.z_ohm_per_km)
    assert len(record["conductores"])==4
    assert record["conductores"][0]["gmr_m"]==.0244*.3048
    assert "PSCAD" in record["contexto"]
    assert "capacitancia" in record["nota_capacitancia"].lower() or "No se modifica C" in record["nota_capacitancia"]


def test_pdf_contains_complex_development_correct_footer_and_all_units():
    result = calculate_carson(kersting_example(),60,100,PQ_TRUNCATED)
    reader = PdfReader(BytesIO(carson_pdf(result)))
    text = "\n".join(p.extract_text() for p in reader.pages)
    for expected in ("P/Q finitos","Ω/km","Ω/m","R_AC","PSCAD","no hermíticas","retorno","4.23","Kron","P Carson","Q Carson"):
        assert expected in text
    assert f"{result.z_ohm_per_km[0,0].imag:.9e}" in text
    assert all(float(p.mediabox.width)>float(p.mediabox.height) for p in reader.pages)
    assert "Modelo ideal, sin validación" not in text


def test_bundle_pdf_contains_full_subconductor_system():
    g = build_circuit_geometry(reproducible_specs(4))
    r = calculate_carson_layout(g,(.2,)*6,(.008,)*6,("Ficha técnica de prueba",)*6,60,100)
    reader = PdfReader(BytesIO(carson_pdf(r)))
    text = "\n".join(p.extract_text() for p in reader.pages)
    assert "columnas 19-24" in text
    assert "C'-4" in text and "T, corrientes iguales" in text
    assert f"{r.z_ohm_per_km[-1,-1].real:.9e}" in text


def test_potential_and_capacitance_average_differ_without_changing_old_outputs():
    # Caso obligatorio histórico intacto y modelo a V común claramente distinto.
    from ste_calculator.bundles import BundleSpec
    from ste_calculator.models import Conductor
    centers = (Conductor(1,"A",-3,13),Conductor(1,"B",3,13),Conductor(1,"C",0,9))
    specs = tuple(BundleSpec(c,4,.011765,.4572) for c in centers)
    r = calculate_transposition(specs,(RMGInput(.011765,SOLID_UNIFORM),)*3)
    expected = np.full((3,3),-3.300067)
    np.fill_diagonal(expected,13.803851)
    np.testing.assert_allclose(r.c_f_per_m*1e12,expected,rtol=0,atol=.5e-6)
    direct = sum(s.weight*s.capacitance.phase_f_per_m for s in r.sections)
    np.testing.assert_allclose(direct,r.direct_average_c_f_per_m,rtol=1e-14)
    assert abs((direct[0,0]-r.c_f_per_m[0,0])*1e12)>.02
