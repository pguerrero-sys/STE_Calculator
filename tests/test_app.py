# Regresión de adaptadores históricos; la interfaz principal se prueba en test_workspace_app.py.
from pathlib import Path

import numpy as np
import pytest
from streamlit.testing.v1 import AppTest

APP = Path(__file__).resolve().parent / "fixtures" / "validated_app.py"


def widget_with_label(widgets, label):
    return next(widget for widget in widgets if widget.label == label)


def configured_app(coordinates=None):
    app = AppTest.from_file(str(APP), default_timeout=30)
    app.session_state["coordinates"] = coordinates or {
        "C1-A": (-1.0, 2.0), "C1-B": (2.0, 6.0), "C1-C": (2.0, 2.0)
    }
    app.run()
    widget_with_label(app.number_input, "Frecuencia [Hz]").set_value(60.0)
    widget_with_label(app.number_input, "Longitud de la línea").set_value(1.0)
    app.run()
    return app


def test_empty_startup_has_no_results_and_all_sections():
    app = AppTest.from_file(str(APP), default_timeout=30).run()
    assert not app.exception
    assert len(app.tabs) == 7
    assert any(tab.label == "Haces" for tab in app.tabs)
    assert any(tab.label == "Inductancia" for tab in app.tabs)
    assert not app.metric
    assert any("Sin resultados" in message.value for message in app.info)


def test_known_geometry_and_pending_options_are_disabled():
    app = configured_app()
    assert not app.exception
    table = app.dataframe[1].value  # El editor de coordenadas es dataframe[0].
    np.testing.assert_allclose(table["Distancia [m]"], [5, 3, 4])
    assert widget_with_label(app.checkbox, "Considerar transposición (pendiente)").disabled
    assert widget_with_label(app.checkbox, "Suelo ideal por imágenes (capacitancia)").disabled
    assert widget_with_label(app.checkbox, "Carson / suelo no ideal (pendiente)").disabled
    assert widget_with_label(app.number_input, "Subconductores por fase (modelo individual)").disabled
    app.run()
    assert not app.exception
    np.testing.assert_allclose(app.dataframe[1].value["Distancia [m]"], [5, 3, 4])
    widget_with_label(app.number_input, "Frecuencia [Hz]").set_value(-1).run()
    assert not app.exception
    assert not app.metric
    assert any("mayor que cero" in message.value for message in app.info)


@pytest.mark.parametrize("coordinates", [
    {"C1-A": (0.0, 0.0), "C1-B": (2.0, 6.0), "C1-C": (2.0, 2.0)},
    {"C1-A": (2.0, 2.0), "C1-B": (2.0, 6.0), "C1-C": (2.0, 2.0)},
])
def test_invalid_geometry_suppresses_results(coordinates):
    app = configured_app(coordinates)
    assert not app.exception
    assert not app.metric
    assert any("Sin resultados" in message.value for message in app.info)


def test_example_is_explicitly_marked_and_circuit_change_requires_new_coordinates():
    app = AppTest.from_file(str(APP), default_timeout=30).run()
    widget_with_label(app.button, "Cargar ejemplo geométrico ilustrativo").click().run()
    widget_with_label(app.number_input, "Frecuencia [Hz]").set_value(60.0)
    widget_with_label(app.number_input, "Longitud de la línea").set_value(1.0)
    app.run()
    assert not app.exception
    assert any("no validados" in message.value for message in app.warning)
    assert app.metric[1].value == "3"
    widget_with_label(app.number_input, "Número de circuitos").set_value(2).run()
    assert not app.exception
    assert not app.metric
    assert len(app.dataframe[0].value) == 6
    assert app.dataframe[0].value.iloc[0]["Y [m]"] == 12.0


def test_capacitance_required_case_without_longitudinal_metadata():
    app = AppTest.from_file(str(APP), default_timeout=30).run()
    widget_with_label(app.button, "Cargar caso obligatorio de capacitancia").click().run()
    assert not app.exception
    assert widget_with_label(app.number_input, "Frecuencia [Hz]").value is None
    expected = [[7.719800, -1.240982, -1.317160], [-1.240982, 7.719800, -1.317160], [-1.317160, -1.317160, 8.122161]]
    # Sin geometría longitudinal completa: editor, P, C en F/m y C en nF/km.
    np.testing.assert_allclose(app.dataframe[3].value, expected, rtol=0, atol=0.5e-6)
    np.testing.assert_allclose(app.dataframe[2].value * 1e12, app.dataframe[3].value, rtol=1e-14)
    assert any("Identidad comprobada" in message.value for message in app.success)
    widget_with_label(app.number_input, "Radio exterior A [m]").set_value(0).run()
    assert not app.exception
    assert any("radios exteriores deben" in message.value for message in app.info)
    assert len(app.dataframe) == 1


def test_multiple_circuits_block_capacitance_and_keep_geometry():
    app = AppTest.from_file(str(APP), default_timeout=30).run()
    widget_with_label(app.button, "Cargar caso obligatorio de capacitancia").click().run()
    widget_with_label(app.number_input, "Número de circuitos").set_value(2).run()
    widget_with_label(app.button, "Cargar ejemplo geométrico ilustrativo").click().run()
    widget_with_label(app.number_input, "Frecuencia [Hz]").set_value(60.0)
    widget_with_label(app.number_input, "Longitud de la línea").set_value(1.0)
    app.run()
    assert not app.exception
    assert app.metric[1].value == "15"
    assert any("Solo se admite un circuito" in message.value for message in app.info)
    assert not any("Identidad comprobada" in message.value for message in app.success)
