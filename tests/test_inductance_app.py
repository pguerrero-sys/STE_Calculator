# Regresión de adaptadores históricos; la interfaz principal se prueba en test_workspace_app.py.
from pathlib import Path

import numpy as np
from streamlit.testing.v1 import AppTest

APP = Path(__file__).resolve().parent / "fixtures" / "validated_app.py"
EXPECTED = np.array([[1.59014456,.29845590,.29816333],[.29845590,1.59014456,.29816333],[.29816333,.29816333,1.51659960]])


def widget(widgets, label):
    return next(item for item in widgets if item.label == label)


def loaded():
    app = AppTest.from_file(str(APP), default_timeout=30).run()
    widget(app.button,"Cargar caso obligatorio de inductancia").click().run()
    assert not app.exception
    return app


def contains_matrix(app, expected, atol=5e-9):
    for frame in app.dataframe:
        values = frame.value
        if values.shape == expected.shape:
            try:
                if np.allclose(values.to_numpy(dtype=float),expected,rtol=0,atol=atol):
                    return True
            except (ValueError,TypeError):
                pass
    return False


def test_load_inductance_case_and_frequency_changes_reactance_only():
    app = loaded()
    assert contains_matrix(app, EXPECTED)
    assert any("Reactancia no calculada" in info.value for info in app.info)
    widget(app.number_input,"Frecuencia [Hz]").set_value(60).run()
    assert not app.exception
    assert contains_matrix(app, EXPECTED)
    assert contains_matrix(app, 2*np.pi*60*EXPECTED*1e-3, atol=2e-9)
    widget(app.number_input,"Frecuencia [Hz]").set_value(0).run()
    assert contains_matrix(app, EXPECTED)
    assert any("Reactancia no calculada" in info.value for info in app.info)


def test_inductance_and_capacitance_controls_are_independent():
    app = loaded()
    assert widget(app.number_input,"Radio exterior A [m]").value is None
    widget(app.button,"Cargar caso obligatorio de capacitancia").click().run()
    capacitance = app.dataframe[3].value.to_numpy().copy()
    widget(app.radio,"Modelo de suelo (inductancia)").set_value("Sin efecto suelo · corrientes de suma cero").run()
    assert not app.exception
    np.testing.assert_allclose(app.dataframe[3].value,capacitance)
    assert any("Matriz proyectada" in header.value for header in app.subheader)
    assert not any(item.label == "Distancia de referencia d₀ [m]" for item in app.number_input)
    widget(app.number_input,"Radio exterior inductivo A [m]").set_value(.02).run()
    np.testing.assert_allclose(app.dataframe[3].value,capacitance)
    widget(app.number_input,"Radio exterior A [m]").set_value(0).run()
    assert any("Inductancia calculada" in info.value for info in app.success)
    assert any("Capacitancia no calculada" in info.value for info in app.info)


def test_solid_confirmation_and_invalid_radius_suppress_inductance():
    app = loaded()
    widget(app.checkbox,"Confirmo conductor circular macizo, no magnético y corriente uniforme").uncheck().run()
    assert not any("Inductancia calculada" in message.value for message in app.success)
    assert any("Confirma las hipótesis" in info.value for info in app.info)
    widget(app.checkbox,"Confirmo conductor circular macizo, no magnético y corriente uniforme").check()
    widget(app.number_input,"Radio exterior inductivo A [m]").set_value(0).run()
    assert not app.exception
    assert not any("Inductancia calculada" in message.value for message in app.success)


def test_manufacturer_mode_requires_source_and_uses_given_rmg():
    app = loaded()
    widget(app.selectbox,"Modelo del conductor (inductancia)").set_value("RMG conocido del fabricante").run()
    for phase in "ABC":
        widget(app.number_input,f"RMG fabricante {phase} [m]").set_value(.009)
    app.run()
    assert any("fuente técnica" in info.value for info in app.info)
    widget(app.text_input,"Fuente del RMG del fabricante").set_value("Ficha de prueba, RMG declarado en m").run()
    assert not app.exception
    assert any("Inductancia calculada" in info.value for info in app.success)
    assert any("sin recalcular" in item.value for item in app.latex)


def test_no_ground_reference_change_keeps_reduced_results():
    app = loaded()
    widget(app.radio,"Modelo de suelo (inductancia)").set_value("Sin efecto suelo · corrientes de suma cero").run()
    assert any("Inductancia calculada" in info.value for info in app.success)
    assert not any("L_ref" in header.value for header in app.subheader)
    assert any("I_A + I_B + I_C = 0" in item.value for item in app.warning)
    # Primer marco 2x2 es ahora L de lazos en H/m.
    loops = next(frame.value.to_numpy() for frame in app.dataframe if frame.value.shape == (2,2)).copy()
    widget(app.checkbox,"Mostrar deducción con referencia d₀").check().run()
    widget(app.number_input,"Distancia de referencia d₀ [m]").set_value(1000).run()
    assert not app.exception
    assert contains_matrix(app,loops,atol=1e-12)
    widget(app.number_input,"Número de circuitos").set_value(2).run()
    assert not any("Inductancia calculada" in info.value for info in app.success)
    assert any("Inductancia disponible solo" in info.value for info in app.info)


def test_advanced_reference_is_optional_and_never_changes_main_results():
    import pandas as pd

    app = loaded()
    widget(app.radio,"Modelo de suelo (inductancia)").set_value("Sin efecto suelo · corrientes de suma cero").run()
    widget(app.number_input,"Frecuencia [Hz]").set_value(60).run()
    baseline = [frame.value.copy() for frame in app.dataframe]
    assert not any(item.label == "Distancia de referencia d₀ [m]" for item in app.number_input)
    widget(app.checkbox,"Mostrar deducción con referencia d₀").check().run()
    assert any("Deducción avanzada no disponible" in item.value for item in app.info)
    references = []
    for distance in (10.0, 1000.0, 2000.0, 0.0):
        widget(app.number_input,"Distancia de referencia d₀ [m]").set_value(distance).run()
        assert not app.exception
        assert any("Inductancia calculada" in item.value for item in app.success)
        for original, frame in zip(baseline, app.dataframe):
            pd.testing.assert_frame_equal(original,frame.value)
        if distance > 0:
            references.append(app.dataframe[len(baseline)].value.to_numpy().copy())
        else:
            assert any("Deducción avanzada no disponible" in item.value for item in app.info)
    assert not np.allclose(references[0],references[1],rtol=0,atol=1e-12)
    widget(app.checkbox,"Mostrar deducción con referencia d₀").uncheck().run()
    assert not any(item.label == "Distancia de referencia d₀ [m]" for item in app.number_input)
    for original, frame in zip(baseline, app.dataframe):
        pd.testing.assert_frame_equal(original,frame.value)
