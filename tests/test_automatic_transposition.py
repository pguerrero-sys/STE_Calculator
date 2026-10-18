"""Regresiones del plan automático: ciclos independientes y haces completos."""
import math
from itertools import product
import numpy as np
import pytest
from scipy.linalg import null_space

from ste_calculator.transposition_schedule import automatic_schedule
from ste_calculator.double_circuit import calculate_double_circuit, FACTOR, build_circuit_geometry
from ste_calculator.bundles import BundleSpec
from ste_calculator.models import Conductor, InputError
from ste_calculator.inductance import NO_GROUND, IDEAL_GROUND, RMGInput, MANUFACTURER


def dove_specs():
    return tuple(BundleSpec(Conductor(c,p,x,h),2,.011765,.4572)
                 for c,offset in ((1,0),(2,12))
                 for p,x,h in (('A',-3,13+offset),('B',3,13+offset),('C',0,9+offset)))


@pytest.mark.parametrize('circuits',[1,2,3,4])
@pytest.mark.parametrize('enabled',[False,True])
def test_general_generator_independent_cycles_and_normalized_weights(circuits,enabled):
    plan=automatic_schedule(circuits,enabled)
    count=3**circuits if enabled else 1
    assert len(plan.assignments)==len(set(plan.assignments))==count
    assert math.fsum(plan.weights)==1.0
    np.testing.assert_allclose(plan.weights,1/count,rtol=0,atol=1e-17)
    for row in plan.assignments:
        for c in range(circuits):
            assert set(row[3*c:3*c+3])==set(range(3*c,3*c+3))
    if enabled:
        shifts={tuple(row[3*c]-3*c for c in range(circuits)) for row in plan.assignments}
        assert shifts==set(product(range(3),repeat=circuits))
    else:
        assert plan.assignments==(tuple(range(3*circuits)),)


@pytest.mark.parametrize('bad',[0,-1,True,1.0,None])
def test_generator_invalid_circuit_count(bad):
    with pytest.raises(InputError): automatic_schedule(bad)


@pytest.mark.parametrize('model',[NO_GROUND,IDEAL_GROUND])
def test_dove_independent_average_matches_matrix_group_average(model):
    specs=dove_specs()
    rmg=(RMGInput(.011765,MANUFACTURER,.00954024,'Kersting Appendix A; dato DOVE existente del proyecto'),)*6
    original=calculate_double_circuit(specs,rmg,capacitance_model=model,inductance_model=model,complete=False)
    result=calculate_double_circuit(specs,rmg,capacitance_model=model,inductance_model=model,complete=True)
    assert len(result.sections)==9
    assert np.max(np.abs((result.c_f_per_m-original.c_f_per_m)*1e12))>.01
    # Oráculo independiente: promedio del grupo Z3×Z3 sobre el P original,
    # no promedio de C. Todos los haces de este caso tienen igual construcción.
    expected_p=np.zeros((6,6)); expected_l=np.zeros((6,6))
    for a,b in product(range(3),repeat=2):
        row=[(i+a)%3 for i in range(3)]+[3+(i+b)%3 for i in range(3)]
        expected_p+=original.average_phase_p[np.ix_(row,row)]/9
        expected_l+=original.l_h_per_m[np.ix_(row,row)]/9
    q=null_space(np.ones((1,6))) if model==NO_GROUND else np.eye(6)
    expected_c=FACTOR*q@np.linalg.solve(q.T@expected_p@q,q.T)
    np.testing.assert_allclose(result.average_phase_p,expected_p,atol=1e-13,rtol=1e-13)
    np.testing.assert_allclose(result.c_f_per_m,expected_c,atol=1e-24,rtol=1e-12)
    np.testing.assert_allclose(result.l_h_per_m,expected_l,atol=1e-20,rtol=1e-12)
    np.testing.assert_allclose(result.c_f_per_m,result.c_f_per_m.T,atol=1e-25)
    for start in (0,3):
        np.testing.assert_allclose(np.diag(result.c_f_per_m)[start:start+3],result.c_f_per_m[start,start],atol=1e-24)
        block=result.c_f_per_m[start:start+3,start:start+3]
        np.testing.assert_allclose(block[~np.eye(3,dtype=bool)],block[0,1],atol=1e-24)
    np.testing.assert_allclose(result.c_f_per_m[:3,3:],result.c_f_per_m[0,3],atol=1e-24)
    assert np.max(np.abs(result.c_f_per_m[:3,3:]))>1e-13
    for permutation in ([1,2,0,3,4,5],[0,1,2,4,5,3]):
        np.testing.assert_allclose(result.c_f_per_m,result.c_f_per_m[np.ix_(permutation,permutation)],atol=1e-24)
    if model==NO_GROUND:
        np.testing.assert_allclose(result.c_f_per_m@np.ones(6),0,atol=1e-24)
        assert np.linalg.matrix_rank(result.c_f_per_m,tol=1e-22)==5
        assert max(s.neutrality_residual for s in result.sections)<1e-10
        np.testing.assert_allclose(result.average_phase_p@result.c_f_per_m/FACTOR,np.eye(6)-np.ones((6,6))/6,atol=1e-13)


def test_whole_bundle_properties_and_relative_positions_travel_with_phase():
    specs=tuple(BundleSpec(s.center,1+i%4,s.radius_m,.4572,13*i) for i,s in enumerate(dove_specs()))
    original=build_circuit_geometry(specs)
    result=calculate_double_circuit(specs,complete=True)
    for row,section in zip(result.assignments,result.sections):
        g=section.geometry
        for i,s in enumerate(g.specs):
            before=original.specs[i]
            assert (s.count,s.radius_m,s.spacing_m,s.rotation_deg)==(before.count,before.radius_m,before.spacing_m,before.rotation_deg)
            assert (s.center.x_m,s.center.y_m)==(specs[row[i]].center.x_m,specs[row[i]].center.y_m)
            offsets=g.positions_m[g.phase_index==i]-[s.center.x_m,s.center.y_m]
            before_offsets=original.positions_m[original.phase_index==i]-[before.center.x_m,before.center.y_m]
            np.testing.assert_allclose(offsets,before_offsets,atol=4e-15)


def test_automatic_engine_rejects_manual_overrides_and_retains_two_circuit_limit():
    with pytest.raises(InputError,match='manuales'):
        calculate_double_circuit(dove_specs(),complete=True,weights=(.111111111,)*9)
    specs=tuple(BundleSpec(Conductor(c,p,x,h+12*(c-1)),1,.011765)
                for c in range(1,4) for p,x,h in (('A',-3,13),('B',3,13),('C',0,9)))
    with pytest.raises(InputError,match='uno o dos'):
        calculate_double_circuit(specs,complete=True)
