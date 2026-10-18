from dataclasses import replace
import math
import pytest
import numpy as np
from ste_calculator.conductor_library import conductor,load_catalog
from ste_calculator.resistance import calculate_resistance,academic_temperature,three_phase_current,ACADEMIC,SPECIFIED
from ste_calculator.models import InputError


def test_dove_table_transcription_and_separate_historical_sources():
    d=conductor('DOVE')
    assert (d.gauge,d.aluminium_strands,d.steel_strands,d.nominal_current_a)==('556,5',26,7,725)
    assert d.r_dc20_ohm_km==.1007 and d.r_dc20_ohm_km!=.102
    assert d.r_ac_ohm_km=={'25':.103,'50':.113,'75':.123}
    assert d.radius_m==pytest.approx(.011773)
    assert d.gmr_m==pytest.approx(.00957072)
    assert len(load_catalog())==67
    assert all(d.sources for d in load_catalog().values())


@pytest.mark.parametrize('value,temp',[(0,25),(24.9999999,25),(25,50),(25.0000001,50),(74.9999999,50),(75,50),(75.0000001,75),(100,75),(150,75)])
def test_exact_academic_boundaries(value,temp): assert academic_temperature(value)==temp


@pytest.mark.parametrize('circuits,count,phase',[(1,4,.02575),(2,2,.0515)])
def test_required_dove_current_load_and_resistances(circuits,count,phase):
    r=calculate_resistance((conductor('DOVE'),)*(3*circuits),(count,)*(3*circuits),circuits,
        voltage_kv=220,power=250,power_factor=.9,parallel=circuits==2)
    assert r.total_current_a==pytest.approx(656.0798513518475)
    np.testing.assert_allclose(r.subconductor_current_a,164.01996283796187)
    np.testing.assert_allclose(r.load_percent,22.6234431500637)
    assert set(r.temperatures_c)=={25}
    np.testing.assert_allclose(r.phase_ohm_km,phase)
    if circuits==2:np.testing.assert_allclose(r.parallel_ohm_km,.02575)
    else:assert r.parallel_ohm_km is None


def test_mw_uses_power_factor_and_mva_does_not_divide_twice():
    assert three_phase_current(220,225,'MW',.9)==pytest.approx(three_phase_current(220,250,'MVA',.9))
    assert three_phase_current(220,250,'MVA',1)==pytest.approx(656.0798513518475)


@pytest.mark.parametrize('t,expected',[(25,.103),(50,.113),(75,.123)])
def test_specified_temperature_does_not_require_load_or_interpolate(t,expected):
    d=replace(conductor('DOVE'),nominal_current_a=None)
    r=calculate_resistance((d,)*3,(1,)*3,1,mode=SPECIFIED,temperature_c=t)
    assert r.total_current_a is None
    np.testing.assert_allclose(r.conductor_ohm_km,expected)
    with pytest.raises(InputError,match='interpola'):calculate_resistance((d,)*3,(1,)*3,1,mode=SPECIFIED,temperature_c=30)


@pytest.mark.parametrize('params',[dict(voltage_kv=0,power=250),dict(voltage_kv=220,power=-1),dict(voltage_kv=220,power=250,power_factor=0),dict(voltage_kv=220,power=250,power_factor=1.1),dict(frequency_hz=50),dict(mode='unknown')])
def test_invalid_inputs_and_frequency_not_extrapolated(params):
    with pytest.raises(InputError):calculate_resistance((conductor('DOVE'),)*3,(4,)*3,1,**params)


def test_custom_missing_value_is_not_invented_and_parallel_requires_declaration():
    d=replace(conductor('DOVE'),r_ac_ohm_km={'25':None,'50':.113,'75':.123})
    with pytest.raises(InputError): calculate_resistance((d,)*3,(1,)*3,1,mode=SPECIFIED)
    r=calculate_resistance((conductor('DOVE'),)*6,(2,)*6,2,voltage_kv=220,power=250)
    assert r.parallel_ohm_km is None


def test_parallel_unequal_counts_uses_network_of_resistances_not_sum_of_currents():
    r=calculate_resistance((conductor('DOVE'),)*6,(1,2,3,4,3,2),2,mode=SPECIFIED,parallel=True)
    np.testing.assert_allclose(r.parallel_ohm_km,[.103/5,.103/5,.103/5])
