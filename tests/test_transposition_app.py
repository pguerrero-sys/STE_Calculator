# Regresión de adaptadores históricos; la interfaz principal se prueba en test_workspace_app.py.
from pathlib import Path

import numpy as np
from streamlit.testing.v1 import AppTest

APP = Path(__file__).resolve().parent / "fixtures" / "validated_app.py"
L = np.full((3, 3), .298262)
np.fill_diagonal(L, .961802)
C = np.full((3, 3), -3.300067)
np.fill_diagonal(C, 13.803851)


def widget(widgets, label):
    return next(item for item in widgets if item.label == label)


def loaded():
    app = AppTest.from_file(str(APP), default_timeout=30).run()
    widget(app.button, "Cargar caso obligatorio de transposición").click().run()
    assert not app.exception
    return app


def has_matrix(app, expected, atol=5e-7):
    for frame in app.dataframe:
        if frame.value.shape == expected.shape:
            try:
                if np.allclose(frame.value.to_numpy(dtype=float), expected, rtol=0, atol=atol):
                    return True
            except (ValueError, TypeError):
                pass
    return False


def mapping(app):
    return next(frame.value for frame in app.dataframe if "Tramo" in frame.value.columns)


def test_required_case_equal_sections_and_intermediate_views():
    app = loaded()
    assert has_matrix(app, L)
    assert has_matrix(app, C)
    rows = mapping(app)
    assert len(rows) == 3
    np.testing.assert_allclose(rows["Peso"], 1/3)
    for phase in "ABC":
        assert set(rows[phase]) == {"P1", "P2", "P3"}
    widget(app.number_input, "Longitud de la línea").set_value(90).run()
    assert not app.exception
    assert set(mapping(app)["Longitud"]) == {"30000 m"}
    widget(app.checkbox, "Mostrar geometría del tramo 2").check().run()
    widget(app.checkbox, "Mostrar sistema completo de subconductores del tramo 2").check().run()
    assert not app.exception
    assert any(frame.value.shape == (12, 12) for frame in app.dataframe)


def test_switch_to_untransposed_and_back_preserves_case():
    app = loaded()
    widget(app.radio, "Tratamiento de la línea").set_value("Sin transposición").run()
    assert not app.exception
    assert len(mapping(app)) == 1
    assert not has_matrix(app, L)
    assert not has_matrix(app, C)
    widget(app.radio, "Tratamiento de la línea").set_value("Transposición ideal completa automática").run()
    assert not app.exception
    assert has_matrix(app, L)
    assert has_matrix(app, C)


def test_no_ground_restrictions_and_independent_models():
    app = loaded()
    widget(app.selectbox, "Suelo para capacitancia del haz").set_value("Sin suelo · carga total cero").run()
    assert not app.exception
    assert has_matrix(app, L)
    assert any("Σq_fase = 0" in item.value for item in app.warning)
    widget(app.selectbox, "Suelo para inductancia del haz").set_value("Sin suelo · corrientes de suma cero").run()
    assert not app.exception
    assert any("IA + IB + IC = 0" in item.value for item in app.warning)
    assert not any("d₀" in item.label for item in app.number_input)


def test_missing_manufacturer_source_keeps_capacitance_available():
    app = loaded()
    widget(app.selectbox, "Modelo inductivo del subconductor").set_value("ACSR/trenzado: RMG del fabricante").run()
    assert not app.exception
    assert has_matrix(app, C)
    assert any("Inductancia no disponible" in item.value for item in app.info)
