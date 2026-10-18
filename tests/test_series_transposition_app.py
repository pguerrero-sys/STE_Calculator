import numpy as np
from streamlit.testing.v1 import AppTest
from tests.test_transposition_app import APP,widget,has_matrix
from tests.test_carson_app import by_key
from ste_calculator.pscad_series import load_dove_case
from ste_calculator.series_transposition import transpose_series
from ste_calculator.sequence_examples import two_guard_case
from ste_calculator.kron import reduce_augmented,ISOLATED


def selected_frame(app,title):
    elements = list(app)
    start = next(i for i,e in enumerate(elements) if e.type=='markdown' and e.value==title)
    kind = app.dataframe[0].type
    return next(e.value.to_numpy(dtype=float) for e in elements[start+1:] if e.type==kind)


def test_dove_off_on_off_recomputes_selected_matrix_and_preserves_prior_inputs():
    app = AppTest.from_file(str(APP),default_timeout=45).run()
    widget(app.button,"Cargar caso DOVE · JSON y PSCAD").click().run()
    assert not app.exception
    case = load_dove_case()
    result = transpose_series(case.z_ohm_per_m,case.labels)
    for enabled in (False,True,False):
        widget(app.checkbox,"Activar transposición ideal de Carson").set_value(enabled).run()
        assert not app.exception
        expected = result.average_ohm_per_m if enabled else result.original_ohm_per_m
        np.testing.assert_allclose(selected_frame(app,"Resultado seleccionado · R [Ω/km]"),expected.real*1000,rtol=1e-14)
        np.testing.assert_allclose(selected_frame(app,"Resultado seleccionado · X [Ω/km]"),expected.imag*1000,rtol=1e-14)
    assert widget(app.number_input,"Frecuencia [Hz]").value is None
    assert by_key(app.number_input,'car_f').value is None  # JSON solo afecta a 7D.
    assert any('residuo máximo contra JSON=0.000e+00' in s.value for s in app.success)
    assert any('PSCAD declara DC' in s.value for s in app.warning)
    frame = next(f.value for f in app.dataframe if 'Error_R_pct' in f.value.columns)
    assert len(frame)==18 and not frame.Error_R_pct.isna().any()
    widget(app.selectbox,"Unidad de impedancia serie · 7D").set_value('Ω/m').run()
    np.testing.assert_allclose(selected_frame(app,"Resultado seleccionado · R [Ω/m]"),case.z_ohm_per_m.real,rtol=1e-14)
    widget(app.checkbox,"Preparar informe PDF Carson transpuesto").check().run()
    assert not app.exception
    assert any(b.label=='Descargar comparación Carson transpuesto PDF' for b in app.get('download_button'))
    assert any(b.label=='Descargar comparación Carson transpuesto CSV' for b in app.get('download_button'))


def test_current_double_circuit_kron_per_section_and_isolated_guard_block():
    app = AppTest.from_file(str(APP),default_timeout=45).run()
    widget(app.number_input,'Número de circuitos').set_value(2).run()
    widget(app.button,'Cargar ensayo algebraico · dos guardas').click().run()
    widget(app.checkbox,'Declaro ΔVn = 0 en todos los auxiliares eliminados').check().run()
    widget(app.checkbox,'Usar fases reducidas por Kron en cada tramo · 7D').check()
    widget(app.checkbox,'Activar transposición ideal de Carson').check().run()
    assert not app.exception
    case = two_guard_case(2)
    z = reduce_augmented(case,confirmed=True).z_ohm_per_m
    expected = transpose_series(z,case.phase_labels)
    np.testing.assert_allclose(selected_frame(app,'Resultado seleccionado · X [Ω/km]'),expected.average_ohm_per_m.imag*1000,rtol=1e-13,atol=1e-15)
    assert any('Doble circuito: tres secciones' in i.value for i in app.info)
    by_key(app.selectbox,'kron_1_connection').set_value(ISOLATED).run()
    assert not app.exception
    assert any('Transposición serie no calculada:' in i.value and 'G2' in i.value for i in app.info)
