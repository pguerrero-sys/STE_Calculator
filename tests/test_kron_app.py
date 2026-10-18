import numpy as np
from streamlit.testing.v1 import AppTest
from tests.test_transposition_app import APP, widget, has_matrix
from tests.test_carson_app import by_key
from tests.test_kron import example
from ste_calculator.kron import ZERO_DROP, ISOLATED, UNKNOWN, reduce_augmented
from ste_calculator.carson import convert_impedance, calculate_carson, kersting_example


def loaded():
    app = AppTest.from_file(str(APP),default_timeout=45).run()
    widget(app.button,"Cargar ejemplo 4.1 completo de Kersting · con neutro").click().run()
    assert not app.exception
    return app


def test_full_case_is_primitive_until_hypothesis_declared_then_units_and_pdf():
    app = loaded()
    aug = example()
    red = reduce_augmented(aug,confirmed=True)
    assert has_matrix(app,aug.z_ohm_per_m.real*1000,atol=1e-13)
    assert any("declarar explícitamente" in w.value for w in app.warning)
    assert not any("Kron calculado" in s.value for s in app.success)
    widget(app.checkbox,"Declaro ΔVn = 0 en todos los auxiliares eliminados").check().run()
    assert not app.exception
    assert any("Kron calculado: 3 fases" in s.value for s in app.success)
    assert has_matrix(app,red.z_ohm_per_km.real,atol=1e-13)
    assert has_matrix(app,red.z_ohm_per_km.imag,atol=1e-13)
    widget(app.selectbox,"Unidad de impedancia Kron").set_value("Ω/mile").run()
    expected = convert_impedance(red.z_ohm_per_m,"Ω/m","Ω/mile")
    assert has_matrix(app,expected.imag,atol=1e-13)
    widget(app.checkbox,"Preparar informe PDF Kron").check().run()
    assert not app.exception
    assert any(item.label=="Descargar informe PDF Kron" for item in app.get("download_button"))
    # Frecuencia general y longitud no son prerrequisitos para matrices serie.
    assert widget(app.number_input,"Frecuencia [Hz]").value is None
    assert widget(app.number_input,"Longitud de la línea").value is None


def test_connection_switch_blocks_only_reduction_and_can_restore_without_stale_results():
    app = loaded()
    widget(app.checkbox,"Declaro ΔVn = 0 en todos los auxiliares eliminados").check().run()
    assert any("Kron calculado" in s.value for s in app.success)
    for connection in (ISOLATED,UNKNOWN):
        by_key(app.selectbox,"kron_0_connection").set_value(connection).run()
        assert not app.exception
        assert not any("Kron calculado" in s.value for s in app.success)
        assert any("n:" in w.value and "no se elimina" in w.value for w in app.warning)
        assert has_matrix(app,example().z_ohm_per_m.imag*1000,atol=1e-13)
    by_key(app.selectbox,"kron_0_connection").set_value(ZERO_DROP).run()
    assert any("Kron calculado" in s.value for s in app.success)
    by_key(app.number_input,"kron_0_r").set_value(.8).run()
    old = reduce_augmented(example(),confirmed=True).z_ohm_per_km.real
    assert not has_matrix(app,old,atol=1e-13)
    # La fase Carson anterior permanece exactamente igual.
    assert has_matrix(app,calculate_carson(kersting_example(),60,100).z_ohm_per_km.real,atol=1e-13)


def test_missing_auxiliary_value_and_source_are_explicit_and_do_not_break_carson():
    app = loaded()
    by_key(app.text_input,"kron_0_source").set_value("").run()
    assert not app.exception
    assert any("n" in e.value and "fuente técnica" in e.value for e in app.error)
    by_key(app.text_input,"kron_0_source").set_value("Kersting").run()
    by_key(app.number_input,"kron_0_gmr").set_value(None).run()
    assert not app.exception
    assert any("RMG" in w.value and "auxiliar 1" in w.value for w in app.warning)
    assert any("Carson calculado" in s.value for s in app.success)
