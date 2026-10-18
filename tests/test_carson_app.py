import numpy as np
from streamlit.testing.v1 import AppTest

from tests.test_transposition_app import APP, widget, has_matrix
from ste_calculator.carson import calculate_carson, calculate_carson_layout, kersting_example, MODIFIED, PQ_TRUNCATED
from ste_calculator.double_circuit import reproducible_specs, build_circuit_geometry


def by_key(widgets,key):
    return next(w for w in widgets if w.key==key)


def loaded():
    app = AppTest.from_file(str(APP),default_timeout=45).run()
    widget(app.button,"Cargar fases del ejemplo 4.1 de Kersting · sin Kron").click().run()
    assert not app.exception
    return app


def test_kersting_primitive_units_contributions_and_pdf_in_interface():
    app = loaded()
    expected = calculate_carson(kersting_example(),60,100)
    assert has_matrix(app,expected.z_ohm_per_km.real,atol=1e-12)
    assert has_matrix(app,expected.z_ohm_per_km.imag,atol=1e-12)
    assert any("sin reducción de Kron" in item.value for item in app.success)
    widget(app.selectbox,"Unidad de impedancia Carson").set_value("Ω/m").run()
    assert not app.exception
    assert has_matrix(app,expected.z_ohm_per_m.real,atol=1e-15)
    assert has_matrix(app,expected.z_ohm_per_m.imag,atol=1e-15)
    widget(app.checkbox,"Preparar informe PDF Carson").check().run()
    assert not app.exception
    assert any(item.label=="Descargar informe PDF Carson" for item in app.get("download_button"))


def test_switch_method_and_change_resistivity_recompute_series_impedance():
    app = loaded()
    widget(app.selectbox,"Método de Carson").set_value(PQ_TRUNCATED).run()
    expected = calculate_carson(kersting_example(),60,100,PQ_TRUNCATED)
    assert not app.exception
    assert has_matrix(app,expected.z_ohm_per_km.real,atol=1e-12)
    assert has_matrix(app,expected.z_ohm_per_km.imag,atol=1e-12)
    widget(app.number_input,"Resistividad del terreno Carson [Ω·m]").set_value(1000).run()
    expected = calculate_carson(kersting_example(),60,1000,PQ_TRUNCATED)
    assert not app.exception
    assert has_matrix(app,expected.z_ohm_per_km.imag,atol=1e-12)


def test_source_gmr_and_domain_failures_are_specific():
    app = loaded()
    widget(app.text_input,"Fuente técnica de R_AC y RMG · Carson").set_value("").run()
    assert not app.exception
    assert not any("Carson calculado:" in item.value for item in app.success)
    assert any("fuente técnica" in item.value for item in app.info)
    widget(app.text_input,"Fuente técnica de R_AC y RMG · Carson").set_value("Ficha técnica de ensayo").run()
    by_key(app.number_input,"car_gmr_B").set_value(0).run()
    assert any("B:" in item.value and "RMG" in item.value for item in app.info)
    by_key(app.number_input,"car_gmr_B").set_value(.0244*.3048).run()
    widget(app.number_input,"Resistividad del terreno Carson [Ω·m]").set_value(0).run()
    assert not app.exception
    assert any("resistividad deben ser positivas" in item.value for item in app.info)


def test_carson_parameters_do_not_change_capacitance_or_general_frequency():
    app = AppTest.from_file(str(APP),default_timeout=45).run()
    widget(app.button,"Cargar caso obligatorio de capacitancia").click().run()
    expected = app.dataframe[3].value.to_numpy(dtype=float).copy()
    for p in "ABC":
        by_key(app.number_input,f"car_r_{p}").set_value(.2)
        by_key(app.number_input,f"car_gmr_{p}").set_value(.008)
    widget(app.text_input,"Fuente técnica de R_AC y RMG · Carson").set_value("Ensayo técnico documentado")
    widget(app.number_input,"Frecuencia Carson [Hz]").set_value(60)
    widget(app.number_input,"Resistividad del terreno Carson [Ω·m]").set_value(100)
    app.run()
    assert not app.exception
    np.testing.assert_array_equal(app.dataframe[3].value,expected)
    widget(app.selectbox,"Método de Carson").set_value(PQ_TRUNCATED).run()
    widget(app.number_input,"Resistividad del terreno Carson [Ω·m]").set_value(1000).run()
    widget(app.number_input,"Frecuencia Carson [Hz]").set_value(50).run()
    assert not app.exception
    np.testing.assert_array_equal(app.dataframe[3].value,expected)
    assert widget(app.number_input,"Frecuencia [Hz]").value is None


def test_double_circuit_and_bundle_mutuals_remain_six_by_six():
    app = AppTest.from_file(str(APP),default_timeout=45).run()
    widget(app.button,"Cargar caso reproducible de doble circuito").click().run()
    for p in ("A","B","C","A'","B'","C'"):
        by_key(app.number_input,f"car_r_{p}").set_value(.2)
        by_key(app.number_input,f"car_gmr_{p}").set_value(.008)
        by_key(app.number_input,f"dc_n_{p}").set_value(4)
    widget(app.text_input,"Fuente técnica de R_AC y RMG · Carson").set_value("Ficha técnica de ensayo de seis fases")
    widget(app.number_input,"Frecuencia Carson [Hz]").set_value(60)
    widget(app.number_input,"Resistividad del terreno Carson [Ω·m]").set_value(100)
    widget(app.radio,"Geometría para Carson").set_value("Subconductores configurados en Haces")
    app.run()
    assert not app.exception
    assert any("Carson calculado:" in item.value for item in app.success)
    assert any("I_sub=I_fase/n" in item.value for item in app.warning)
    assert any(f.value.shape==(24,24) for f in app.dataframe)
    expected = calculate_carson_layout(build_circuit_geometry(reproducible_specs(4)),(.2,)*6,(.008,)*6,
                                       ("Ficha técnica de ensayo de seis fases",)*6,60,100)
    assert has_matrix(app,expected.z_ohm_per_km.real,atol=1e-12)
    assert has_matrix(app,expected.z_ohm_per_km.imag,atol=1e-12)
