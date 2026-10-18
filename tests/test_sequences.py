from dataclasses import replace
import math
import numpy as np
import pytest

from ste_calculator.sequences import phase_to_sequence, transformation_matrices
from ste_calculator.carson import calculate_carson, convert_impedance, PQ_TRUNCATED
from ste_calculator.kron import (augment_carson, reduce_augmented, reduce_kron, UNKNOWN, ISOLATED)
from ste_calculator.kron_validation import validate_two_guards
from ste_calculator.sequence_examples import two_guard_case
from ste_calculator.models import InputError
from ste_calculator.carson import calculate_carson_layout
from ste_calculator.double_circuit import build_circuit_geometry, reproducible_specs
from tests.test_kron import example


def test_kersting_full_published_sequence_matrix_including_nonzero_couplings():
    case = example()
    red = reduce_augmented(case,confirmed=True)
    seq = phase_to_sequence(red.z_ohm_per_m,case.phase_labels)
    z = convert_impedance(seq.z_ohm_per_m,"Ω/m","Ω/mile")
    published = np.array([[.7735+1.9373j,.0256+.0115j,-.0321+.0159j],
                          [-.0321+.0159j,.3061+.6270j,-.0723-.0060j],
                          [.0256+.0115j,.0723-.0059j,.3061+.6270j]])
    np.testing.assert_allclose(z.real,published.real,rtol=0,atol=6e-5)
    np.testing.assert_allclose(z.imag,published.imag,rtol=0,atol=6e-5)
    assert np.min(np.abs(z[~np.eye(3,dtype=bool)]))>.02
    assert not np.allclose(z,z.T)
    np.testing.assert_allclose(z[1,1],z[2,2],rtol=1e-14)
    assert seq.reconstruction_residual<1e-14


@pytest.mark.parametrize("count",[1,2])
def test_operator_positive_sequence_convention_and_inverse(count):
    a,b,inv = transformation_matrices(count)
    assert a.imag>0
    np.testing.assert_allclose(a**3,1,atol=1e-15)
    np.testing.assert_allclose(1+a+a*a,0,atol=1e-15)
    np.testing.assert_allclose(inv@b,np.eye(count*3),atol=1e-15)
    np.testing.assert_allclose(b[:3,1],[1,np.exp(-2j*np.pi/3),np.exp(2j*np.pi/3)],atol=1e-15)
    np.testing.assert_allclose(inv,b.conj().T/3,atol=1e-15)


def test_circulant_ideal_case_diagonalizes_naturally_without_zeroing_output():
    zs,zm = .4+1.3j,.1+.5j
    z = np.full((3,3),zm,dtype=complex)
    np.fill_diagonal(z,zs)
    out = phase_to_sequence(z,("A","B","C"))
    np.testing.assert_allclose(out.z_ohm_per_m,np.diag([zs+2*zm,zs-zm,zs-zm]),atol=1e-15)
    # Con perturbación asimétrica los términos pequeños se conservan, sin umbral.
    z[0,0]+=1e-9
    altered = phase_to_sequence(z,("A","B","C"))
    assert abs(altered.z_ohm_per_m[0,1])>1e-10


def test_round_trip_phase_drop_and_units_for_arbitrary_sequence_currents():
    case = example()
    z = reduce_augmented(case,confirmed=True).z_ohm_per_m
    seq = phase_to_sequence(z,case.phase_labels)
    currents = np.array([2+.3j,-1+8j,4-7j])
    expected = seq.inverse_transform @ (z @ (seq.transform@currents))
    np.testing.assert_allclose(seq.z_ohm_per_m@currents,expected,rtol=1e-14,atol=1e-17)
    for factor in (1000,1609.344):
        scaled = phase_to_sequence(z*factor,case.phase_labels)
        np.testing.assert_allclose(scaled.z_ohm_per_m,seq.z_ohm_per_m*factor,rtol=1e-13,atol=1e-15)


@pytest.mark.parametrize("count",[1,2])
@pytest.mark.parametrize("method",["modified_carson",PQ_TRUNCATED])
def test_two_guards_independent_constraint_system_and_double_circuit_couplings(count,method):
    case = two_guard_case(count)
    n = count*3
    case = augment_carson(calculate_carson(case.primitive.conductors[:n],60,100,method),case.auxiliaries)
    red = reduce_augmented(case,confirmed=True)
    check = validate_two_guards(case,red)
    assert check.relative_error<1e-14 and check.boundary_residual<1e-14
    np.testing.assert_allclose(check.independent_z_ohm_per_m,red.z_ohm_per_m,rtol=1e-14,atol=1e-18)
    seq = phase_to_sequence(red.z_ohm_per_m,case.phase_labels)
    np.testing.assert_allclose(seq.transform@seq.z_ohm_per_m@seq.inverse_transform,red.z_ohm_per_m,rtol=1e-13,atol=1e-18)
    if count==2:
        assert seq.z_ohm_per_m.shape==(6,6)
        assert np.linalg.norm(seq.z_ohm_per_m[:3,3:])>1e-5
        _,a,inv = transformation_matrices(1)
        np.testing.assert_allclose(seq.z_ohm_per_m[:3,3:],inv@red.z_ohm_per_m[:3,3:]@a,rtol=1e-13,atol=1e-18)


@pytest.mark.parametrize("count",[1,2])
def test_two_guards_closed_two_by_two_inverse_and_independent_us_carson(count):
    case = two_guard_case(count)
    conductors = case.primitive.conductors
    # Fórmula en pies/millas, no usa P/Q/S del cálculo del programa.
    reference = np.zeros((len(conductors),)*2,dtype=complex)
    f,rho,g_mile = 60.,100.,1e-7*1609.344
    for i,c in enumerate(conductors):
        for j,d in enumerate(conductors):
            distance_ft = c.gmr_m/.3048 if i==j else math.hypot(c.x_m-d.x_m,c.height_m-d.height_m)/.3048
            r = c.resistance_ac_ohm_per_km*1.609344 if i==j else 0.
            reference[i,j] = r+math.pi**2*f*g_mile+1j*4*math.pi*f*g_mile*(math.log(1/distance_ft)+7.6786+.5*math.log(rho/f))
    n = count*3
    nn = reference[n:,n:]
    determinant = nn[0,0]*nn[1,1]-nn[0,1]*nn[1,0]
    inverse = np.array([[nn[1,1],-nn[0,1]],[-nn[1,0],nn[0,0]]])/determinant
    independent = (reference[:n,:n]-reference[:n,n:]@inverse@reference[n:,:n])/1609.344
    red = reduce_augmented(case,confirmed=True)
    np.testing.assert_allclose(red.z_ohm_per_m,independent,rtol=1e-13,atol=1e-18)
    diagonal_only = case.blocks.pp-case.blocks.pn@np.diag(1/np.diag(case.blocks.nn))@case.blocks.np
    assert np.linalg.norm(diagonal_only-independent)>1e-5
    reverse = augment_carson(calculate_carson(conductors[:n],60,100),case.auxiliaries[::-1])
    np.testing.assert_allclose(reduce_augmented(reverse,confirmed=True).z_ohm_per_m,independent,rtol=1e-13,atol=1e-18)


@pytest.mark.parametrize("bundle_count",[1,4])
def test_double_circuit_subconductors_two_guards_and_sequence_mutuals(bundle_count):
    base = calculate_carson_layout(build_circuit_geometry(reproducible_specs(bundle_count)),
                                    (.2,)*6,(.008,)*6,("Ensayo algebraico",)*6,60,100)
    guards = two_guard_case(2).auxiliaries
    case = augment_carson(base,guards)
    red = reduce_augmented(case,confirmed=True)
    assert case.primitive.z_ohm_per_m.shape==(6*bundle_count+2,)*2
    assert case.z_ohm_per_m.shape==(8,8) and red.z_ohm_per_m.shape==(6,6)
    assert validate_two_guards(case,red).relative_error<1e-14
    seq = phase_to_sequence(red.z_ohm_per_m,case.phase_labels)
    assert np.linalg.norm(seq.z_ohm_per_m[:3,3:])>1e-5


@pytest.mark.parametrize("count",[1,2])
@pytest.mark.parametrize("connection",[UNKNOWN,ISOLATED])
def test_two_guard_unknown_or_isolated_condition_blocks_reduction_not_primitive(count,connection):
    case = two_guard_case(count)
    aux = (case.auxiliaries[0],replace(case.auxiliaries[1],connection=connection))
    raw = augment_carson(calculate_carson(case.primitive.conductors[:3*count],60,100),aux)
    assert raw.z_ohm_per_m.shape==(3*count+2,)*2
    with pytest.raises(InputError,match="G2:.*ΔV=0"):
        reduce_augmented(raw,confirmed=True)


@pytest.mark.parametrize("nn",[np.zeros((2,2)),np.ones((2,2)),np.diag([1,1e-14])])
def test_two_guard_singular_or_ill_conditioned_block_is_rejected(nn):
    case = two_guard_case()
    z = case.z_ohm_per_m.copy()
    z[3:,3:] = nn
    with pytest.raises(InputError,match="singular|condicionada"):
        reduce_kron(z,(0,1,2),case.auxiliaries,confirmed=True)


@pytest.mark.parametrize("value",[0,3,1.0,True,None])
def test_invalid_circuit_count(value):
    with pytest.raises(InputError):
        transformation_matrices(value)


@pytest.mark.parametrize("z,labels",[(np.eye(4),("A","B","C")),(np.eye(3)*np.nan,("A","B","C")),
    (np.eye(3),("B","A","C")),(np.eye(6),("A","B","C")),([["bad"]],())])
def test_invalid_matrix_shape_values_and_phase_order(z,labels):
    with pytest.raises(InputError):
        phase_to_sequence(z,labels)
