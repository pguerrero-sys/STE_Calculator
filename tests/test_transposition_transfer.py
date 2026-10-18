"""Regresiones del contrato entre Geometría, widgets de Haces y Transposición."""

import pytest
from streamlit.testing.v1 import AppTest

from tests.test_transposition_app import APP, L, C, widget, has_matrix, mapping
from ste_calculator import bundle_ui


def configured():
    app = AppTest.from_file(str(APP), default_timeout=30)
    app.session_state["coordinates"] = {
        "C1-A": (-3.0, 13.0), "C1-B": (3.0, 13.0), "C1-C": (0.0, 9.0),
    }
    for phase in "ABC":
        for name, value in (("n", 4), ("s", .4572), ("r", .011765), ("angle", 0.0)):
            app.session_state[f"haz_{name}_{phase}"] = value
    app.session_state["haz_material"] = bundle_ui.MATERIALS[1]
    app.session_state["haz_confirm"] = True
    app.session_state["haz_cap_ground"] = "Suelo ideal"
    app.session_state["haz_ind_ground"] = "Suelo ideal"
    app.session_state["trans_mode"] = "Transposición ideal completa"
    return app


def test_renderer_without_return_does_not_lose_valid_widget_inputs(monkeypatch):
    original = bundle_ui.render_bundle_tab

    def legacy_renderer(*args, **kwargs):
        original(*args, **kwargs)
        # Reproduce el módulo de etapa 4 conservado en memoria por el servidor.
        return None

    monkeypatch.setattr(bundle_ui, "render_bundle_tab", legacy_renderer)
    app = configured().run()
    widget(app.number_input, "Frecuencia [Hz]").set_value(60).run()
    assert not app.exception
    assert any("Equipotencialidad comprobada" in item.value for item in app.success)
    assert has_matrix(app, L)
    assert has_matrix(app, C)
    widget(app.radio, "Tratamiento de la línea").set_value("Sin transposición").run()
    assert not app.exception
    assert len(mapping(app)) == 1
    assert not has_matrix(app, L)
    widget(app.radio, "Tratamiento de la línea").set_value("Transposición ideal completa automática").run()
    assert not app.exception
    assert has_matrix(app, L) and has_matrix(app, C)


@pytest.mark.parametrize("frequency,length", [(None, None), (0, 0), (-1, -1), (60, None)])
def test_matrices_do_not_require_frequency_or_length(frequency, length):
    app = configured().run()
    widget(app.number_input, "Frecuencia [Hz]").set_value(frequency)
    widget(app.number_input, "Longitud de la línea").set_value(length)
    app.run()
    assert not app.exception
    assert has_matrix(app, L) and has_matrix(app, C)


def test_error_identifies_missing_phase_radius_and_recovers():
    app = configured().run()
    widget(app.number_input, "Radio exterior individual B [m]").set_value(None).run()
    assert not app.exception
    assert any("Transposición no calculada:" in item.value and "haz_r_B" in item.value for item in app.error)
    assert not has_matrix(app, C)
    widget(app.number_input, "Radio exterior individual B [m]").set_value(.011765).run()
    assert not app.exception
    assert has_matrix(app, L) and has_matrix(app, C)


def test_current_widgets_override_previous_geometry_and_model():
    app = configured().run()
    widget(app.number_input, "Separación entre vecinos A [m]").set_value(.5).run()
    assert not app.exception
    assert not has_matrix(app, L) and not has_matrix(app, C)
    widget(app.number_input, "Separación entre vecinos A [m]").set_value(.4572).run()
    assert has_matrix(app, L) and has_matrix(app, C)
    widget(app.number_input, "Número de circuitos").set_value(2).run()
    assert not app.exception
    assert not has_matrix(app, L) and not has_matrix(app, C)
    assert any("Transposición no calculada:" in item.value and "circuit" in item.value for item in app.error)
