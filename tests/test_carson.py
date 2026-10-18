from dataclasses import replace
import math

import numpy as np
import pytest
from scipy.linalg import null_space

from ste_calculator.carson import (CarsonConductor, calculate_carson, calculate_carson_layout,
    convert_impedance, kersting_example, FT_M, MILE_M, MODIFIED, PQ_TRUNCATED, G_SI_H_PER_M)
from ste_calculator.models import InputError
from ste_calculator.double_circuit import reproducible_specs, build_circuit_geometry, calculate_section
from ste_calculator.inductance import RMGInput, SOLID_UNIFORM, NO_GROUND


def test_kersting_example_4_1_full_primitive_without_kron():
    result = calculate_carson(kersting_example(True),60,100)
    published_r = np.full((4,4),.0953)
    np.fill_diagonal(published_r,[.4013,.4013,.4013,.6873])
    published_x = np.array([[1.4133,.8515,.7266,.7524],
                            [.8515,1.4133,.7802,.7865],
                            [.7266,.7802,1.4133,.7674],
                            [.7524,.7865,.7674,1.5465]])
    computed = convert_impedance(result.z_ohm_per_m,"Ω/m","Ω/mile")
    np.testing.assert_allclose(computed.real,published_r,rtol=0,atol=6e-5)
    np.testing.assert_allclose(computed.imag,published_x,rtol=0,atol=6e-5)
    assert result.z_ohm_per_m.shape==(4,4)  # No se ha eliminado el neutro.
    assert computed[0,0] != pytest.approx(.4576+1.078j,abs=1e-4)  # p.94 reducida NO es la primitiva.


def test_independent_us_units_closed_formula_for_all_self_and_mutual_terms():
    data = tuple(replace(c,height_m=c.height_m+2*i,x_m=c.x_m-i) for i,c in enumerate(kersting_example(True)))
    f,rho = 50.,250.
    result = calculate_carson(data,f,rho)
    expected = np.zeros((4,4),complex)
    # Ecs.4.37-4.38 en Ω/milla, independientes del ensamblaje SI con imágenes/P/Q.
    g_mile = .1609344e-3
    for i,a in enumerate(data):
        for j,b in enumerate(data):
            d_ft = a.gmr_m/FT_M if i==j else math.hypot(a.x_m-b.x_m,a.height_m-b.height_m)/FT_M
            r_mile = a.resistance_ac_ohm_per_km*1.609344 if i==j else 0
            expected[i,j] = r_mile+math.pi**2*f*g_mile+1j*4*math.pi*f*g_mile*(math.log(1/d_ft)+7.6786+.5*math.log(rho/f))
    np.testing.assert_allclose(convert_impedance(result.z_ohm_per_m,"Ω/m","Ω/mile"),expected,rtol=1e-14,atol=1e-15)


@pytest.mark.parametrize("method",[MODIFIED,PQ_TRUNCATED])
def test_reciprocity_contributions_passivity_and_units(method):
    result = calculate_carson(kersting_example(True),60,100,method)
    z = result.z_ohm_per_m
    np.testing.assert_allclose(z,z.T,rtol=0,atol=1e-18)
    assert not np.allclose(z,z.conj().T,atol=1e-8)
    assert np.min(np.linalg.eigvalsh(z.real))>0
    np.testing.assert_allclose(z,result.z_conductor_ohm_per_m+result.z_geometry_ohm_per_m+result.z_earth_ohm_per_m,atol=1e-19)
    np.testing.assert_allclose(result.z_ohm_per_km,z*1000,rtol=1e-15)
    np.testing.assert_allclose(convert_impedance(result.z_ohm_per_km,"Ω/km","Ω/m"),z,rtol=1e-15)
    np.testing.assert_allclose(result.z_conductor_ohm_per_m.real,np.diag([c.resistance_ac_ohm_per_km/1000 for c in result.conductors]))


def test_modified_resistivity_scaling_is_common_mode_not_capacitance():
    a = calculate_carson(kersting_example(),60,100)
    b = calculate_carson(kersting_example(),60,1000)
    expected = 1j*2*math.pi*60*G_SI_H_PER_M*math.log(10)*np.ones((3,3))
    np.testing.assert_allclose(b.z_ohm_per_m-a.z_ohm_per_m,expected,rtol=1e-13,atol=1e-19)
    assert np.max(np.abs(a.z_earth_ohm_per_m.real-np.pi**2*60*G_SI_H_PER_M))<1e-19


@pytest.mark.parametrize("method",[MODIFIED,PQ_TRUNCATED])
def test_joint_frequency_resistivity_scaling_keeps_k_and_scales_external_impedance(method):
    a = calculate_carson(kersting_example(),50,100,method)
    b = calculate_carson(kersting_example(),60,120,method)
    np.testing.assert_allclose(a.k,b.k,rtol=1e-14)
    np.testing.assert_allclose(b.z_ohm_per_m-b.z_conductor_ohm_per_m,
                               1.2*(a.z_ohm_per_m-a.z_conductor_ohm_per_m),rtol=1e-14,atol=1e-19)


def test_height_cancellation_is_only_a_modified_carson_property():
    data = kersting_example()
    raised = tuple(replace(c,height_m=c.height_m+20) for c in data)
    a,b = calculate_carson(data,60,100),calculate_carson(raised,60,100)
    np.testing.assert_allclose(a.z_ohm_per_m,b.z_ohm_per_m,rtol=1e-14)
    assert np.max(np.abs(a.z_geometry_ohm_per_m-b.z_geometry_ohm_per_m))>1e-5
    assert not np.allclose(calculate_carson(data,60,100,PQ_TRUNCATED).z_ohm_per_m,
                           calculate_carson(raised,60,100,PQ_TRUNCATED).z_ohm_per_m,atol=1e-7)


def test_pq_equations_with_nonzero_angle_against_scalar_book_evaluation():
    a = CarsonConductor("i",-3,13,.2,.008,"Ensayo técnico")
    b = CarsonConductor("j",3,9,.3,.006,"Ensayo técnico")
    result = calculate_carson((a,b),60,100,PQ_TRUNCATED)
    theta = math.atan2(6,22)
    s_ft = math.sqrt(520)/.3048
    k = .0008565*s_ft*math.sqrt(.6)
    p = math.pi/8-k*math.cos(theta)/(3*math.sqrt(2))+k*k/16*math.cos(2*theta)*(.6728+math.log(2/k))
    q = -.0386+.5*math.log(2/k)+k*math.cos(theta)/(3*math.sqrt(2))
    assert result.k[0,1]==pytest.approx(k,rel=1e-14)
    assert result.p[0,1]==pytest.approx(p,rel=1e-14)
    assert result.q[0,1]==pytest.approx(q,rel=1e-14)
    assert result.k[0,0]==pytest.approx(.0008565*(26/.3048)*math.sqrt(.6))
    # La diapositiva 6 con k²√2/3 NO coincide con (4.23).
    wrong = math.pi/8-k*k*math.sqrt(2)/3*math.cos(theta)+(2/3)*k*k*math.log(1/k)
    assert abs(p-wrong)>1e-3


@pytest.mark.parametrize("circuits",[1,2])
@pytest.mark.parametrize("n",[1,2,3,4])
@pytest.mark.parametrize("method",[MODIFIED,PQ_TRUNCATED])
def test_existing_geometries_bundle_aggregation_and_ideal_reference(circuits,n,method):
    specs = reproducible_specs(n)[:3*circuits]
    geometry = build_circuit_geometry(specs)
    gmr = (.011765*math.exp(-.25),)*(3*circuits)  # Ensayo explícito macizo, no conversión ACSR.
    resistances = tuple(.1+.02*i for i in range(3*circuits))
    result = calculate_carson_layout(geometry,resistances,gmr,("Ensayo macizo explícito",)*(3*circuits),60,100,method)
    assert result.primitive.z_ohm_per_m.shape==(3*circuits*n,)*2
    assert result.z_ohm_per_m.shape==(3*circuits,)*2
    t = geometry.current_weights
    np.testing.assert_allclose(result.z_ohm_per_m,t.T @ result.primitive.z_ohm_per_m @ t,rtol=1e-14)
    np.testing.assert_allclose(np.diag(result.z_conductor_ohm_per_m.real)*1000,np.array(resistances)/n,rtol=1e-14)
    old = calculate_section(specs,(RMGInput(.011765,SOLID_UNIFORM),)*(3*circuits))
    np.testing.assert_allclose(result.z_geometry_ohm_per_m.imag,2*np.pi*60*old.l_h_per_m,rtol=1e-13,atol=1e-19)
    if circuits==2:
        assert np.max(np.abs(result.z_ohm_per_m[:3,3:]))>1e-5


def test_modified_balanced_subspace_matches_verified_no_ground_restriction():
    specs = reproducible_specs()
    g = build_circuit_geometry(specs)
    rmg = (.011765*math.exp(-.25),)*6
    result = calculate_carson_layout(g,(.2,)*6,rmg,("Ensayo macizo",)*6,60,100)
    old = calculate_section(specs,(RMGInput(.011765,SOLID_UNIFORM),)*6,inductance_model=NO_GROUND)
    q = null_space(np.ones((1,6)))
    np.testing.assert_allclose(q.T @ result.z_ohm_per_m @ q,
        q.T @ (np.eye(6)*.0002+1j*2*np.pi*60*old.l_h_per_m) @ q,rtol=1e-13,atol=1e-18)


def test_manufacturer_rmg_used_without_macizo_factor():
    data = kersting_example()
    result = calculate_carson(data,60,100)
    expected = 2*2*np.pi*60*1e-7*math.log(2*data[0].height_m/data[0].gmr_m)
    assert result.z_geometry_ohm_per_m[0,0].imag==pytest.approx(expected,rel=1e-14)
    assert result.conductors[0].gmr_m==.0244*FT_M


def test_warning_and_blocking_thresholds_are_software_policy_not_full_solution():
    raised = tuple(replace(c,height_m=100) for c in kersting_example())
    result = calculate_carson(raised,60,100)
    assert .1<result.k.max()<1
    assert any("preventivo" in w for w in result.warnings)
    with pytest.raises(InputError,match="k máximo"):
        calculate_carson(tuple(replace(c,height_m=1000) for c in raised),60,100)
    outside = calculate_carson(kersting_example(),400,1000)
    assert any("50-60" in w for w in outside.warnings)
    with pytest.raises(InputError):
        calculate_carson(kersting_example(),60,0)


@pytest.mark.parametrize("f,rho",[(None,100),(0,100),(-1,100),(math.nan,100),(60,None),(60,-1),(60,math.inf),(1e-320,1e308)])
def test_invalid_frequency_resistivity_and_representability(f,rho):
    with pytest.raises(InputError):
        calculate_carson(kersting_example(),f,rho)


@pytest.mark.parametrize("change",[{"gmr_m":0},{"gmr_m":None},{"source":""},{"height_m":0},
                                    {"x_m":math.inf},{"resistance_ac_ohm_per_km":-1},{"radius_m":.0001}])
def test_invalid_technical_inputs_identify_conductor(change):
    data = list(kersting_example())
    data[1] = replace(data[1],**change)
    with pytest.raises(InputError,match="B"):
        calculate_carson(data,60,100)


def test_invalid_method_duplicates_geometry_and_units():
    data = kersting_example()
    for bad in ((),(data[0],data[0]),(data[0],replace(data[1],x_m=data[0].x_m))):
        with pytest.raises(InputError):
            calculate_carson(bad,60,100)
    with pytest.raises(InputError):
        calculate_carson(data,60,100,"full_carson")
    with pytest.raises(InputError):
        convert_impedance(1j,"Ω","Ω/km")
    with pytest.raises(InputError):
        convert_impedance(complex(math.nan,1),"Ω/m","Ω/km")
