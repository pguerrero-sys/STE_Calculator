# Regresión de adaptadores históricos; la interfaz principal se prueba en test_workspace_app.py.
from pathlib import Path

import numpy as np
import pytest
from streamlit.testing.v1 import AppTest

from ste_calculator.bundles import BundleSpec,build_bundles
from ste_calculator.bundle_electrical import calculate_bundle_capacitance
from ste_calculator.inductance import NO_GROUND
from ste_calculator.models import Conductor

APP = Path(__file__).resolve().parent / "fixtures" / "validated_app.py"


def widget(widgets,label):
    return next(w for w in widgets if w.label == label)


def loaded():
    app = AppTest.from_file(str(APP),default_timeout=30).run()
    widget(app.button,"Cargar comparación sin haz (n=1)").click().run()
    assert not app.exception
    return app


def has_matrix(app,expected,atol=1e-23):
    for f in app.dataframe:
        if f.value.shape == expected.shape:
            try:
                if np.allclose(f.value.to_numpy(dtype=float),expected,rtol=1e-12,atol=atol):
                    return True
            except (ValueError,TypeError):
                pass
    return False


@pytest.mark.parametrize("n",[1,2,3,4])
def test_subconductor_positions_and_capacitance_in_interface(n):
    app = loaded()
    if n > 1:
        for p in "ABC":
            widget(app.number_input,f"Subconductores {p}").set_value(n)
        app.run()
        for p in "ABC":
            widget(app.number_input,f"Separación entre vecinos {p} [m]").set_value(.4)
        app.run()
    assert not app.exception
    positions = next(f.value for f in app.dataframe if "Subconductor" in f.value.columns)
    assert len(positions) == 3*n
    centers = (Conductor(1,"A",-3,13),Conductor(1,"B",3,13),Conductor(1,"C",0,9))
    g = build_bundles(tuple(BundleSpec(c,n,.011765,.4) for c in centers))
    expected = calculate_bundle_capacitance(g).phase_f_per_m
    assert has_matrix(app,expected)
    assert any("Equipotencialidad comprobada" in item.value for item in app.success)
    widget(app.selectbox,"Vista de subconductores").set_value("A").run()
    assert not app.exception


def test_acsr_requires_documented_rmg_without_blocking_capacitance():
    app = loaded()
    widget(app.selectbox,"Modelo inductivo del subconductor").set_value("ACSR/trenzado: RMG del fabricante").run()
    for p in "ABC":
        widget(app.number_input,f"RMG individual fabricante {p} [m]").set_value(.008)
    app.run()
    assert not app.exception
    assert any("fuente técnica" in item.value for item in app.info)
    assert any("Equipotencialidad comprobada" in item.value for item in app.success)
    widget(app.text_input,"Fuente del RMG individual ACSR/fabricante").set_value("Ficha de ensayo; valor de RMG en metros").run()
    assert not app.exception
    radii = next(f.value for f in app.dataframe if "RMG inductivo equivalente [m]" in f.value.columns)
    np.testing.assert_allclose(radii["RMG individual [m]"],.008)
    np.testing.assert_allclose(radii["Radio capacitivo equivalente [m]"],.011765)


def test_free_space_and_independent_ground_controls():
    app = loaded()
    widget(app.selectbox,"Suelo para capacitancia del haz").set_value("Sin suelo · carga total cero").run()
    assert not app.exception
    assert any("Σq_sub = 0" in item.value for item in app.warning)
    widget(app.selectbox,"Suelo para inductancia del haz").set_value("Sin suelo · corrientes de suma cero").run()
    assert not app.exception
    assert any("IA + IB + IC = 0" in item.value for item in app.warning)
    assert not any("d₀" in w.label for w in app.number_input)
    widget(app.number_input,"Frecuencia [Hz]").set_value(60).run()
    assert not app.exception
    assert any("Equipotencialidad comprobada" in item.value for item in app.success)


def test_invalid_spacing_and_multiple_circuits_block_bundle_results():
    app = loaded()
    widget(app.number_input,"Subconductores A").set_value(2).run()
    widget(app.number_input,"Separación entre vecinos A [m]").set_value(.001).run()
    assert not app.exception
    assert any("Haces no calculados" in item.value for item in app.info)
    assert not any("Equipotencialidad comprobada" in item.value for item in app.success)
    widget(app.number_input,"Número de circuitos").set_value(2).run()
    assert not app.exception
    assert any("un circuito" in item.value for item in app.info)
