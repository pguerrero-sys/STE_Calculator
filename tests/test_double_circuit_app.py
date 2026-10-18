import numpy as np
from streamlit.testing.v1 import AppTest

from tests.test_transposition_app import APP, widget, has_matrix
from ste_calculator.double_circuit import calculate_double_circuit, reproducible_specs, default_assignments
from ste_calculator.inductance import RMGInput, SOLID_UNIFORM, NO_GROUND
from ste_calculator.bundles import BundleSpec
from ste_calculator.models import Conductor

INPUTS = (RMGInput(.011765,SOLID_UNIFORM),)*6


def loaded():
    app = AppTest.from_file(str(APP),default_timeout=45).run()
    widget(app.button,"Cargar caso reproducible de doble circuito").click().run()
    assert not app.exception
    return app


def test_load_six_phases_matrices_and_pdf_without_longitudinal_metadata():
    app = loaded()
    assert widget(app.number_input,"Número de circuitos").value==2
    assert widget(app.number_input,"Frecuencia [Hz]").value is None
    assert widget(app.number_input,"Longitud de la línea").value is None
    r = calculate_double_circuit(reproducible_specs(),INPUTS)
    assert has_matrix(app,r.l_h_per_m*1e6,atol=1e-12)
    assert has_matrix(app,r.c_f_per_m*1e12,atol=1e-12)
    widget(app.checkbox,"Preparar informe PDF de doble circuito").check().run()
    assert not app.exception
    assert any(item.label=="Descargar informe PDF · doble circuito" for item in app.get("download_button"))
    widget(app.number_input,"Frecuencia [Hz]").set_value(60).run()
    assert not app.exception
    assert has_matrix(app,2*np.pi*60*r.l_h_per_m*1000,atol=1e-12)


def test_bundles_and_transposition_switch_rebuild_current_six_phase_state():
    app = loaded()
    for p in ("A","B","C","A'","B'","C'"):
        widget(app.number_input,f"Subconductores {p} · doble").set_value(4)
    app.run()
    assert not app.exception
    widget(app.radio,"Transposición de doble circuito").set_value("Transposición ideal completa automática").run()
    assert not app.exception
    r = calculate_double_circuit(reproducible_specs(4),INPUTS,complete=True)
    assert has_matrix(app,r.l_h_per_m*1e6,atol=1e-12)
    assert has_matrix(app,r.c_f_per_m*1e12,atol=1e-12)
    coordinates = [f.value for f in app.dataframe if "Subconductor" in f.value.columns and len(f.value)==24]
    assert len(coordinates)==1
    widget(app.radio,"Transposición de doble circuito").set_value("Sin transposición").run()
    assert not app.exception
    original = calculate_double_circuit(reproducible_specs(4),INPUTS)
    assert has_matrix(app,original.l_h_per_m*1e6,atol=1e-12)


def test_no_ground_constraints_and_manufacturer_independence():
    app = loaded()
    widget(app.selectbox,"Suelo para L · doble circuito").set_value("Sin suelo · suma global cero").run()
    widget(app.selectbox,"Suelo para C · doble circuito").set_value("Sin suelo · carga global cero").run()
    assert not app.exception
    r = calculate_double_circuit(reproducible_specs(),INPUTS,inductance_model=NO_GROUND,capacitance_model=NO_GROUND)
    assert has_matrix(app,r.l_h_per_m*1e6,atol=1e-12)
    assert any("Σq de las seis" in item.value for item in app.warning)
    assert any("rango 5" in item.value for item in app.warning)
    widget(app.selectbox,"Modelo de conductor · doble circuito").set_value("ACSR/trenzado · RMG del fabricante").run()
    assert not app.exception
    assert has_matrix(app,r.c_f_per_m*1e12,atol=1e-12)
    assert any("fuente técnica" in item.value for item in app.info)


def test_legacy_manual_state_is_ignored_and_invalid_radius_recovers():
    # Inyectar antes del primer render: AppTest no permite serializar un valor
    # antiguo que ya no figure en las opciones del widget actual.
    app = AppTest.from_file(str(APP),default_timeout=45)
    app.session_state['circuit_count']=2
    app.session_state['coordinates']={s.center.label:(s.center.x_m,s.center.y_m) for s in reproducible_specs()}
    app.session_state['dc_material']='Macizo no magnético uniforme'
    app.session_state['dc_confirm']=True
    for label in ("A","B","C","A'","B'","C'"):
        app.session_state[f'dc_n_{label}']=1
        app.session_state[f'dc_r_{label}']=.011765
        app.session_state[f'dc_s_{label}']=.4572
    app.session_state['dc_trans_mode']='Asignaciones y fracciones personalizadas'
    app.session_state['dc_sections']=9
    for t in range(9):
        app.session_state[f'dc_weight_{t}']=.111111111
        for i in range(6): app.session_state[f'dc_pos_{t}_{i}']=f'P{i+1}'
    app.run()
    assert not app.exception
    assert widget(app.radio,'Transposición de doble circuito').value=='Transposición ideal completa automática'
    plan=next(f.value for f in app.dataframe if 'Fracción L' in f.value.columns)
    assert len(plan)==9 and len(plan.drop(columns=['Tramo','Fracción L','Fracción exacta']).drop_duplicates())==9
    assert not any('Fracción L del tramo' in w.label or 'Número de tramos' in w.label for w in app.number_input)
    assert not any(w.label.startswith('Posición ') for w in app.selectbox)
    assert any("Doble circuito calculado" in item.value for item in app.success)
    widget(app.number_input,"Radio exterior A' · doble [m]").set_value(0).run()
    assert not app.exception
    assert any("Circuito 2" in item.value and "radio" in item.value for item in app.error)
    widget(app.number_input,"Radio exterior A' · doble [m]").set_value(.011765).run()
    assert not app.exception
    assert any("Doble circuito calculado" in item.value for item in app.success)


def test_required_dove_two_bundle_no_ground_auto_plan_and_switches():
    from tests.test_automatic_transposition import dove_specs
    import math
    app=loaded()
    specs=dove_specs()
    app.session_state['coordinates']={s.center.label:(s.center.x_m,s.center.y_m) for s in specs}
    app.session_state['editor_revision']+=1
    for label in ("A","B","C","A'","B'","C'"):
        app.session_state[f'dc_n_{label}']=2
    app.run()
    widget(app.selectbox,'Modelo de conductor · doble circuito').set_value('ACSR/trenzado · RMG del fabricante').run()
    widget(app.selectbox,'Suelo para C · doble circuito').set_value('Sin suelo · carga global cero').run()
    mode=widget(app.radio,'Transposición de doble circuito')
    assert mode.options==['Sin transposición','Transposición ideal completa automática']
    mode.set_value('Transposición ideal completa automática').run()
    assert not app.exception
    result=calculate_double_circuit(specs,capacitance_model=NO_GROUND,complete=True)
    assert has_matrix(app,result.c_f_per_m*1e12,atol=1e-10)
    plan=next(f.value for f in app.dataframe if 'Fracción L' in f.value.columns)
    assert len(plan)==9 and math.fsum(plan['Fracción L'])==1
    assert set(plan['Fracción exacta'])=={'1/9'}
    assert not any('Fracción L del tramo' in w.label or 'Número de tramos' in w.label for w in app.number_input)
    assert not any(w.label.startswith('Posición ') for w in app.selectbox)
    widget(app.selectbox,'Tramo para visualizar · doble circuito').set_value(8).run()
    widget(app.checkbox,'Preparar informe PDF de doble circuito').check().run()
    assert not app.exception
    assert any(w.label=='Descargar informe PDF · doble circuito' for w in app.get('download_button'))
    widget(app.radio,'Transposición de doble circuito').set_value('Sin transposición').run()
    assert not app.exception
    original=calculate_double_circuit(specs,capacitance_model=NO_GROUND,complete=False)
    assert has_matrix(app,original.c_f_per_m*1e12,atol=1e-10)
    assert len(next(f.value for f in app.dataframe if 'Fracción L' in f.value.columns))==1
    widget(app.radio,'Transposición de doble circuito').set_value('Transposición ideal completa automática').run()
    assert not app.exception and has_matrix(app,result.c_f_per_m*1e12,atol=1e-10)


def test_geometry_editor_changes_propagate_to_both_circuit_couplings():
    app = loaded()
    coords = dict(app.session_state["coordinates"])
    coords["C2-A"] = (5.0,15.0)
    app.session_state["coordinates"] = coords
    app.session_state["editor_revision"] += 1
    app.run()
    assert not app.exception
    specs = list(reproducible_specs())
    specs[3] = BundleSpec(Conductor(2,"A",5,15),1,.011765)
    expected = calculate_double_circuit(specs,INPUTS)
    assert has_matrix(app,expected.l_h_per_m*1e6,atol=1e-12)
    assert has_matrix(app,expected.c_f_per_m*1e12,atol=1e-12)
