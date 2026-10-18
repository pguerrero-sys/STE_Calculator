from io import BytesIO

import numpy as np
import pytest
from pypdf import PdfReader
from reportlab.pdfbase.pdfmetrics import stringWidth

from ste_calculator.printing import (MatrixBlock, matrix_tables, TABLE_WIDTH, PAGE_SIZE,
                                     font_name, render_pdf, double_circuit_pdf)
from ste_calculator.double_circuit import calculate_double_circuit, reproducible_specs, default_assignments
from ste_calculator.inductance import RMGInput, SOLID_UNIFORM, NO_GROUND
from ste_calculator.transposition import calculate_transposition
from ste_calculator.printing import transposition_pdf


def test_24_column_matrix_splits_without_losing_cells_and_repeats_labels():
    labels = tuple(f"A'-{i+1}" for i in range(24))
    values = np.arange(576,dtype=float).reshape(24,24)+.123456789
    block = MatrixBlock("Matriz ancha",values,labels,labels,"SI")
    tables = matrix_tables(block)
    assert len(tables)==4
    for start,end,table in tables:
        assert sum(table._argW)<=TABLE_WIDTH+1e-10
        assert table.repeatRows==1
        assert len(table._cellvalues)==25
        assert table._cellvalues[0][1:]==list(labels[start:end])
        for row in table._cellvalues:
            for width,value in zip(table._argW,row):
                assert stringWidth(value,font_name(),7.5)+12<=width
    content = render_pdf("Prueba de tablas",["24 columnas sin superposición."],[block])
    reader = PdfReader(BytesIO(content))
    text = "\n".join(page.extract_text() for page in reader.pages)
    for v in values.flat:
        assert f"{v:.9e}" in text
    assert text.count("Fase / posición")>=4  # También se repite al partir filas entre páginas.
    assert all(float(p.mediabox.width)>float(p.mediabox.height) for p in reader.pages)


@pytest.mark.parametrize("model",["ideal_ground",NO_GROUND])
def test_double_report_contains_all_phases_stages_units_and_formulas(model):
    result = calculate_double_circuit(reproducible_specs(4),(RMGInput(.011765,SOLID_UNIFORM),)*6,
                                      default_assignments("opposite"),inductance_model=model,capacitance_model=model)
    pdf = double_circuit_pdf(result,60)
    reader = PdfReader(BytesIO(pdf))
    text = "\n".join(page.extract_text() for page in reader.pages)
    for expected in ("Psub","Lsub","C6 principal","mH/km","nF/km","Tramo 3","A'-4","B'-4","C'-4","sin validación"):
        assert expected in text
    assert f"{result.c_f_per_m[-1,-1]*1e12:.9e}" in text
    assert "RMG=R exp(-1/4)" in text
    assert len(reader.pages)>4


def test_existing_stage_five_report_uses_shared_wide_table_layout():
    result = calculate_transposition(reproducible_specs(4)[:3],(RMGInput(.011765,SOLID_UNIFORM),)*3)
    reader = PdfReader(BytesIO(transposition_pdf(result)))
    text = "\n".join(p.extract_text() for p in reader.pages)
    assert "columnas 7-12" in text
    assert f"{result.c_f_per_m[-1,-1]*1e12:.9e}" in text
    assert "Tramo 3" in text
