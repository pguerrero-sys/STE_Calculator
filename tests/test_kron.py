from dataclasses import replace
import numpy as np
import pytest

from ste_calculator.carson import (calculate_carson, calculate_carson_layout, kersting_example,
                                    convert_impedance, PQ_TRUNCATED)
from ste_calculator.kron import (AuxiliaryConductor, ZERO_DROP, UNKNOWN, ISOLATED,
    augment_carson, reduce_augmented, reduce_kron, partition_impedance)
from ste_calculator.double_circuit import reproducible_specs, build_circuit_geometry
from ste_calculator.models import InputError


def example():
    aux = AuxiliaryConductor(kersting_example(True)[-1],"neutral",ZERO_DROP,"Kersting p.87, multitierra ideal")
    return augment_carson(calculate_carson(kersting_example(),60,100),(aux,))


def test_kersting_full_example_independently_computed_and_published():
    aug = example()
    reduced = reduce_augmented(aug,confirmed=True)
    direct = calculate_carson(kersting_example(True),60,100)
    np.testing.assert_array_equal(aug.primitive.z_ohm_per_m,direct.z_ohm_per_m)
    published = np.array([[.4576+1.0780j,.1560+.5017j,.1535+.3849j],
                          [.1560+.5017j,.4666+1.0482j,.1580+.4236j],
                          [.1535+.3849j,.1580+.4236j,.4615+1.0651j]])
    computed = convert_impedance(reduced.z_ohm_per_m,"Ω/m","Ω/mile")
    np.testing.assert_allclose(computed.real,published.real,rtol=0,atol=6e-5)
    np.testing.assert_allclose(computed.imag,published.imag,rtol=0,atol=6e-5)
    # Independiente del solver: con un solo neutro es un producto exterior escalar.
    z = direct.z_ohm_per_m
    expected = z[:3,:3]-np.outer(z[:3,3],z[3,:3])/z[3,3]
    np.testing.assert_allclose(reduced.z_ohm_per_m,expected,rtol=1e-14,atol=1e-18)
    assert reduced.solve_residual<1e-14


@pytest.mark.parametrize("connection",[UNKNOWN,ISOLATED,"invalid"])
def test_unknown_or_isolated_neutral_is_never_eliminated(connection):
    aug = example()
    aux = replace(aug.auxiliaries[0],connection=connection)
    with pytest.raises(InputError,match="ΔV=0"):
        reduce_kron(aug.z_ohm_per_m,(0,1,2),(aux,),confirmed=True)


def test_justification_and_explicit_declaration_are_required():
    aug = example()
    with pytest.raises(InputError,match="declarar explícitamente"):
        reduce_augmented(aug)
    aux = replace(aug.auxiliaries[0],justification=" ")
    with pytest.raises(InputError,match="justificación"):
        reduce_kron(aug.z_ohm_per_m,(0,1,2),(aux,),confirmed=True)
    with pytest.raises(InputError,match="cada auxiliar"):
        reduce_kron(aug.z_ohm_per_m,(0,1,2),(),confirmed=True)


@pytest.mark.parametrize("method",["modified_carson",PQ_TRUNCATED])
def test_multiple_auxiliaries_preserve_couplings_and_recover_original_equations(method):
    a = example().auxiliaries[0]
    b = replace(a,conductor=replace(a.conductor,label="G",x_m=3.2,height_m=15),role="guard")
    aug = augment_carson(calculate_carson(kersting_example(),60,100,method),(a,b))
    red = reduce_augmented(aug,confirmed=True)
    assert aug.blocks.nn.shape==(2,2)
    assert abs(aug.blocks.nn[0,1])>0
    ip = np.array([2+3j,-1+.3j,7-2j])  # No exige equilibrio de fases.
    currents = np.r_[ip,red.auxiliary_current_response@ip]
    voltage = aug.z_ohm_per_m@currents
    np.testing.assert_allclose(voltage[3:],0,atol=1e-17)
    np.testing.assert_allclose(voltage[:3],red.z_ohm_per_m@ip,rtol=1e-13,atol=1e-17)
    np.testing.assert_allclose(red.z_ohm_per_m,red.z_ohm_per_m.T,atol=1e-18)
    assert np.min(np.linalg.eigvalsh(red.z_ohm_per_m.real))>0
    diagonal_shortcut = aug.blocks.pp-aug.blocks.pn@np.diag(1/np.diag(aug.blocks.nn))@aug.blocks.np
    assert np.max(np.abs(diagonal_shortcut-red.z_ohm_per_m))>1e-5


@pytest.mark.parametrize("count",[1,2,3,4])
def test_double_circuit_bundles_preserve_six_phases_and_all_auxiliary_couplings(count):
    layout = build_circuit_geometry(reproducible_specs(count))
    base = calculate_carson_layout(layout,(.2,)*6,(.008,)*6,("Datos de prueba",)*6,60,100)
    aux = example().auxiliaries[0]
    aux = replace(aux,conductor=replace(aux.conductor,height_m=20,label="G"),role="guard")
    aug = augment_carson(base,(aux,))
    red = reduce_augmented(aug,confirmed=True)
    assert aug.primitive.z_ohm_per_m.shape==(6*count+1,)*2
    assert aug.z_ohm_per_m.shape==(7,7)
    assert red.z_ohm_per_m.shape==(6,6)
    np.testing.assert_allclose(aug.blocks.pp,base.z_ohm_per_m,rtol=1e-14,atol=1e-18)
    np.testing.assert_allclose(red.z_ohm_per_m,red.z_ohm_per_m.T,rtol=1e-14,atol=1e-18)
    assert np.min(np.abs(red.z_ohm_per_m[:3,3:]))>0


def test_units_commute_with_schur_reduction_and_round_trip():
    aug = example()
    red = reduce_augmented(aug,confirmed=True)
    for factor in (1000,1609.344):
        scaled = reduce_kron(aug.z_ohm_per_m*factor,(0,1,2),aug.auxiliaries,confirmed=True)
        np.testing.assert_allclose(scaled.z_ohm_per_m,red.z_ohm_per_m*factor,rtol=1e-14)
        np.testing.assert_allclose(scaled.auxiliary_current_response,red.auxiliary_current_response,rtol=1e-14)
    np.testing.assert_allclose(red.z_ohm_per_km,red.z_ohm_per_m*1000,rtol=1e-15)
    np.testing.assert_allclose(convert_impedance(red.z_ohm_per_km,"Ω/km","Ω/m"),red.z_ohm_per_m,rtol=1e-15)


def test_permuted_noncontiguous_partition_preserves_phase_order():
    aug = example()
    order = [3,2,0,1]
    permuted = aug.z_ohm_per_m[np.ix_(order,order)]
    red = reduce_kron(permuted,(2,3,1),aug.auxiliaries,confirmed=True)
    np.testing.assert_allclose(red.z_ohm_per_m,reduce_augmented(aug,confirmed=True).z_ohm_per_m,atol=1e-18)


@pytest.mark.parametrize("z,phases",[(np.ones((2,3)),(0,)),(np.eye(2)*np.nan,(0,)),
    (np.eye(2),(0,0)),(np.eye(2),(4,)),(np.eye(2),(False,)),(np.eye(2),()),
    (np.eye(2),(0,1)),(np.array([[1,2],[3,1]]),(0,))])
def test_invalid_matrices_and_partitions(z,phases):
    with pytest.raises(InputError):
        partition_impedance(z,phases)


@pytest.mark.parametrize("nn",[np.zeros((1,1)),np.ones((2,2)),np.diag([1,1e-14])])
def test_singular_or_ill_conditioned_nn_is_rejected(nn):
    n = len(nn)
    z = np.eye(3+n,dtype=complex)
    z[3:,3:] = nn
    a = example().auxiliaries[0]
    with pytest.raises(InputError,match="singular|condicionada"):
        reduce_kron(z,(0,1,2),(a,)*n,confirmed=True)


@pytest.mark.parametrize("changes",[{"gmr_m":0},{"resistance_ac_ohm_per_km":-1},{"height_m":0},
                                     {"source":""},{"label":"A"},{"x_m":0,"height_m":29*.3048}])
def test_invalid_auxiliary_properties_are_named(changes):
    aux = example().auxiliaries[0]
    aux = replace(aux,conductor=replace(aux.conductor,**changes))
    with pytest.raises(InputError):
        augment_carson(calculate_carson(kersting_example(),60,100),(aux,))


def test_adding_unknown_auxiliary_still_produces_full_primitive():
    aux = replace(example().auxiliaries[0],connection=UNKNOWN,justification="")
    aug = augment_carson(calculate_carson(kersting_example(),60,100),(aux,))
    assert aug.z_ohm_per_m.shape==(4,4)
    with pytest.raises(InputError):
        reduce_augmented(aug,confirmed=True)
