from streamlit.testing.v1 import AppTest
from tests.test_transposition_app import APP, widget, has_matrix
from tests.test_carson_app import by_key
from tests.test_kron_app import loaded
from tests.test_kron import example
from ste_calculator.kron import reduce_augmented, ISOLATED, UNKNOWN, ZERO_DROP
from ste_calculator.sequences import phase_to_sequence
from ste_calculator.sequence_examples import two_guard_case
from ste_calculator.carson import convert_impedance


def test_sequence_matrix_requires_valid_kron_and_updates_units():
    app = loaded()
    assert not any(s.value=="Componentes simétricas · etapa 7C" for s in app.subheader)
    widget(app.checkbox,"Declaro ΔVn = 0 en todos los auxiliares eliminados").check().run()
    case = example()
    seq = phase_to_sequence(reduce_augmented(case,confirmed=True).z_ohm_per_m,case.phase_labels)
    assert not app.exception
    assert has_matrix(app,seq.z_ohm_per_m.real*1000,atol=1e-13)
    assert has_matrix(app,seq.z_ohm_per_m.imag*1000,atol=1e-13)
    widget(app.selectbox,"Unidad de impedancia Kron").set_value("Ω/mile").run()
    assert has_matrix(app,convert_impedance(seq.z_ohm_per_m,"Ω/m","Ω/mile").imag,atol=1e-13)
    for condition in (ISOLATED,UNKNOWN):
        by_key(app.selectbox,"kron_0_connection").set_value(condition).run()
        assert not app.exception
        assert not any(s.value=="Componentes simétricas · etapa 7C" for s in app.subheader)
    by_key(app.selectbox,"kron_0_connection").set_value(ZERO_DROP).run()
    widget(app.checkbox,"Declaro ΔVn = 0 en todos los auxiliares eliminados").uncheck().run()
    assert not any(s.value=="Componentes simétricas · etapa 7C" for s in app.subheader)


def test_two_guard_preset_validation_pdf_and_six_phase_couplings():
    app = AppTest.from_file(str(APP),default_timeout=45).run()
    widget(app.number_input,"Número de circuitos").set_value(2).run()
    widget(app.button,"Cargar ensayo algebraico · dos guardas").click().run()
    assert not app.exception
    assert widget(app.number_input,"Número de circuitos").value==2
    assert not any("Kron calculado" in s.value for s in app.success)
    widget(app.checkbox,"Declaro ΔVn = 0 en todos los auxiliares eliminados").check().run()
    assert not app.exception
    assert any("Dos guardas: contraste independiente correcto" in s.value for s in app.success)
    case = two_guard_case(2)
    red = reduce_augmented(case,confirmed=True)
    seq = phase_to_sequence(red.z_ohm_per_m,case.phase_labels)
    assert has_matrix(app,red.z_ohm_per_km.real,atol=1e-13)
    assert has_matrix(app,seq.z_ohm_per_m.imag*1000,atol=1e-13)
    widget(app.checkbox,"Preparar informe PDF Kron").check().run()
    assert not app.exception
    assert any(b.label=="Descargar informe PDF Kron" for b in app.get("download_button"))
    by_key(app.selectbox,"kron_1_connection").set_value(ISOLATED).run()
    assert not app.exception
    assert not any("Dos guardas: contraste independiente correcto" in s.value for s in app.success)
    assert any("G2" in w.value and "no se elimina" in w.value for w in app.warning)
