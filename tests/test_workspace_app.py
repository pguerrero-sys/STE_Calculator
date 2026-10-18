"""Contrato real de app.py: cuatro secciones, entrada única y cálculo explícito."""
from pathlib import Path
import numpy as np
from streamlit.testing.v1 import AppTest
from ste_calculator.workspace_ui import NAV,PRESETS

APP=Path(__file__).resolve().parents[1]/'app.py'


def test_public_distribution_starts_without_private_reference_pdfs(monkeypatch,tmp_path):
    from ste_calculator import workspace_ui
    monkeypatch.setattr(workspace_ui,'ROOT',tmp_path)
    app=AppTest.from_file(str(APP),default_timeout=60).run()
    assert not app.exception
    assert any('no se distribuye' in m.value for m in app.info)


def widget(items,label):return next(w for w in items if w.label==label)


def loaded(preset=PRESETS[0]):
    app=AppTest.from_file(str(APP),default_timeout=60).run()
    widget(app.selectbox,'Caso de comprobación').set_value(preset).run()
    widget(app.button,'Cargar caso DOVE').click().run()
    assert not app.exception
    widget(app.button,'Calcular parámetros').click().run()
    assert not app.exception
    return app


def test_four_sections_empty_startup_and_no_internal_plan_in_configuration():
    app=AppTest.from_file(str(APP),default_timeout=60).run()
    assert not app.exception
    assert tuple(t.label for t in app.tabs)==NAV
    assert not app.metric
    assert not any('tramo' in w.label.lower() or w.label.startswith('Posición ') for w in app.number_input)
    assert widget(app.selectbox,'Circuitos trifásicos').options==['Sencillo','Doble']
    assert not any('Peso' in f.value.columns for f in app.tabs[0].dataframe)


def test_required_dove_scenario_resistance_and_explicit_calculation():
    app=loaded()
    widget(app.selectbox,'Apartado de resultados').set_value('Resistencia').run()
    assert not app.exception
    frame=next(f.value for f in app.dataframe if 'R fase [Ω/km]' in f.value.columns)
    np.testing.assert_allclose(frame['R fase [Ω/km]'],.02575)
    np.testing.assert_allclose(frame['Carga [%]'],22.62344315)
    assert widget(app.selectbox,'Transposición').options==['Sin transposición','Transposición ideal completa automática']
    widget(app.number_input,'Potencia total').set_value(500.).run()
    assert any('entradas cambiaron' in w.value.lower() for w in app.info)
    assert not any('R fase [Ω/km]' in f.value.columns for f in app.dataframe)
    widget(app.button,'Calcular parámetros').click().run()
    frame=next(f.value for f in app.dataframe if 'R fase [Ω/km]' in f.value.columns)
    np.testing.assert_allclose(frame['R conductor [Ω/km]'],.113)


def test_double_circuit_parallel_and_both_soil_models():
    app=loaded(PRESETS[1])
    widget(app.checkbox,'Declaro circuitos conectados en paralelo (solo equivalente resistivo)').check().run()
    widget(app.button,'Calcular parámetros').click().run()
    result=app.session_state['un_result']
    np.testing.assert_allclose(result.resistance.parallel_ohm_km,.02575)
    assert len(result.geometry.specs)==6
    assert len(result.variants['ideal_ground',True].sections)==9
    widget(app.selectbox,'Apartado de resultados').set_value('Capacitancia').run()
    assert not app.exception
    frames=[f.value for f in app.dataframe if f.value.shape==(6,6)]
    assert len(frames)>=2
    assert not any('Peso' in f.value.columns for f in app.tabs[0].dataframe)
    assert any('Peso' in f.value.columns and len(f.value)==9 for f in app.tabs[2].dataframe)


def test_historical_c6_and_summary_export_remain_available():
    app=loaded(PRESETS[2])
    result=app.session_state['un_result']
    c=result.variants['no_ground_balanced',True].c_f_per_m*1e12
    assert abs(c[0,0]-10.029643)<5e-7
    assert abs(c[0,3]+1.367903)<5e-7
    widget(app.button,'Preparar informe resumido').click().run()
    assert not app.exception
    assert any(w.label=='Descargar informe resumido PDF' for w in app.get('download_button'))
    widget(app.selectbox,'Transposición').set_value('Sin transposición').run()
    widget(app.button,'Calcular parámetros').click().run()
    assert not app.exception
    assert len(app.session_state['un_result'].variants['no_ground_balanced',False].sections)==1
    assert not any(w.label=='Descargar informe resumido PDF' for w in app.get('download_button'))


def test_impedance_equivalents_carson_and_unknown_auxiliary_are_separate():
    app=loaded()
    widget(app.checkbox,'Calcular también impedancia de Carson').check().run()
    widget(app.button,'Calcular parámetros').click().run()
    widget(app.selectbox,'Apartado de resultados').set_value('Impedancia y admitancia').run()
    assert not app.exception
    result=app.session_state['un_result']
    assert result.carson['phase'].shape==(3,3)
    assert any('Z Carson' in x.value for x in app.caption)
    assert any('Z geométrica' in x.value for x in app.caption)
    widget(app.number_input,'Conductores auxiliares de Carson').set_value(1).run()
    widget(app.button,'Calcular parámetros').click().run()
    assert not app.exception
    assert 'carson' in app.session_state['un_result'].messages
    assert app.session_state['un_result'].variants['ideal_ground',True].c_f_per_m.shape==(3,3)


def test_empty_bundle_count_does_not_silently_become_one():
    app=loaded()
    widget(app.number_input,'Subconductores por fase').set_value(None).run()
    widget(app.button,'Calcular parámetros').click().run()
    assert not app.exception
    assert any('no se puede calcular' in m.value.lower() for m in app.error)
