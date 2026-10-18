from pathlib import Path
from io import BytesIO
import json
import numpy as np
import pytest
from pypdf import PdfReader

from ste_calculator.sequence_discrepancy import (analyze_dove,unequal_current_equivalent,
                                                scalar_transposed_sequences)
from ste_calculator.sequence_discrepancy_report import discrepancy_pdf,discrepancy_record
from ste_calculator.pscad_series import load_dove_case,find_dove_folder
from ste_calculator.models import InputError


@pytest.fixture(scope='module')
def analysis():
    return analyze_dove()


def test_base_scenario_remains_exactly_stage_7d(analysis):
    from ste_calculator.series_transposition import transpose_series
    case=load_dove_case()
    original=case.z_ohm_per_m.copy()
    expected=transpose_series(original,case.labels).average_ohm_per_m
    np.testing.assert_array_equal(analysis['scenarios'][0].transposed_phase_ohm_per_m,expected)
    np.testing.assert_array_equal(case.z_ohm_per_m,original)
    assert analysis['case'].phase_result.primitive.method=='kersting_pq_finite'


def test_sequences_match_scalar_formula_and_pscad_publication_without_zeroing(analysis):
    for scenario in analysis['scenarios']:
        z=scenario.transposed_phase_ohm_per_m
        # Independiente de scalar_transposed_sequences y de A: primera propia y mutua.
        expected=np.array([z[0,0]+2*z[0,1],z[0,0]-z[0,1],z[0,0]-z[0,1]])
        np.testing.assert_allclose(np.diag(scenario.sequence_ohm_per_m),expected,rtol=1e-14,atol=1e-18)
        assert scenario.scalar_residual_ohm_per_m<1e-18
        off=scenario.sequence_ohm_per_m-np.diag(np.diag(scenario.sequence_ohm_per_m))
        assert np.max(np.abs(off))<1e-18
    assert analysis['pscad_publication_residual_ohm_km']<2.1e-9
    np.testing.assert_allclose(np.diag(analysis['pscad_sequence_ohm_m'])*1000,
                                [.199967488+1.424319802j,.0262542031+.254854708j,.0262542031+.254854708j],rtol=0,atol=1e-14)


def test_ten_percent_error_is_exact_signed_difference_amplification(analysis):
    c=analysis['cancellation']
    assert c['signed_error_R1_pct']==pytest.approx(10.0145324688,abs=1e-9)
    assert c['signed_error_Rs_pct']>0 and c['signed_error_Rm_pct']<0
    assert c['delta_R1_ohm_km']==pytest.approx(c['delta_Rs_ohm_km']-c['delta_Rm_ohm_km'],abs=1e-17)
    assert c['contribution_own_percentage_points']+c['contribution_mutual_percentage_points']==pytest.approx(c['signed_error_R1_pct'],abs=1e-12)
    assert c['cancellation_factor']==pytest.approx(5.41105967524,abs=1e-10)


def test_dc_sensitivity_changes_only_copy_of_input_diagonal_and_exact_phase_shift(analysis):
    ac,dc=analysis['scenarios'][:2]
    delta=(.102-.1859/1.609344)/4/1000
    np.testing.assert_allclose(dc.primitive_ohm_per_m-ac.primitive_ohm_per_m,
        np.diag((dc.resistance_input_ohm_km-ac.resistance_input_ohm_km)/1000),rtol=1e-14,atol=1e-18)
    np.testing.assert_array_equal(ac.primitive_ohm_per_m.imag,dc.primitive_ohm_per_m.imag)
    np.testing.assert_allclose(dc.transposed_phase_ohm_per_m-ac.transposed_phase_ohm_per_m,delta*np.eye(3),rtol=1e-12,atol=1e-18)
    np.testing.assert_allclose(dc.sequence_ohm_per_m-ac.sequence_ohm_per_m,delta*np.eye(3),rtol=1e-12,atol=1e-18)
    assert all(c.resistance_ac_ohm_per_km==pytest.approx(.1859/1.609344) for c in analysis['case'].phase_result.primitive.conductors)
    ref=analysis['pscad_sequence_ohm_m'][1,1].real
    assert ac.sequence_ohm_per_m[1,1].real>ref>dc.sequence_ohm_per_m[1,1].real
    budget=analysis['positive_resistance_budget']
    assert budget['R1_externo_STE_ohm_km']==pytest.approx(.000005212634644,abs=1e-14)
    assert budget['R1_PSCAD_menos_RDC_sobre_4_ohm_km']==pytest.approx(.0007542031,abs=1e-14)


def test_comparison_r_and_x_are_independent_and_dc_does_not_reproduce_pscad(analysis):
    table=analysis['comparison']
    assert len(table)==12
    for row in table.to_dict(orient='records'):
        assert row['Error_R_pct']==pytest.approx(100*abs(row['STE_R_ohm_km']-row['PSCAD_R_ohm_km'])/abs(row['PSCAD_R_ohm_km']))
        assert row['Error_X_pct']==pytest.approx(100*abs(row['STE_X_ohm_km']-row['PSCAD_X_ohm_km'])/abs(row['PSCAD_X_ohm_km']))
    positive=table[table.Secuencia==1]
    np.testing.assert_allclose(positive.Error_R_pct,[10.01453247,2.85284022,10.26599063,2.62495546],rtol=0,atol=1e-8)
    assert np.min(positive.Error_X_pct)>1


def test_unequal_model_matches_independent_bordered_system_and_power_identity(analysis):
    e=analysis['incidence']
    for scenario in analysis['scenarios'][2:]:
        z=scenario.primitive_ohm_per_m
        # Sistema completo independiente; no usa la inversa reducida de admitancia.
        k=np.block([[z,-e],[e.T,np.zeros((3,3))]])
        rhs=np.vstack((np.zeros((len(z),3)),np.eye(3)))
        solution=np.linalg.solve(k,rhs)
        np.testing.assert_allclose(solution[:len(z)],scenario.response,rtol=1e-12,atol=1e-15)
        np.testing.assert_allclose(solution[len(z):],scenario.original_phase_ohm_per_m,rtol=1e-12,atol=1e-18)
        assert scenario.current_sharing.current_residual<1e-13
        assert scenario.current_sharing.voltage_residual<1e-13
        np.testing.assert_allclose(scenario.original_phase_ohm_per_m,scenario.original_phase_ohm_per_m.T,atol=1e-18)
        ip=np.array([1+2j,-2+.7j,3-.4j])
        sub=scenario.response@ip
        voltage=scenario.original_phase_ohm_per_m@ip
        np.testing.assert_allclose(np.vdot(ip,voltage),np.vdot(sub,z@sub),rtol=1e-12,atol=1e-17)


def test_symmetric_subconductors_reduce_to_equal_current_analytical_case():
    e=np.kron(np.eye(3),np.ones((4,1)))
    self_impedance=.3+.8j
    common=.1+.2j
    z=np.eye(12)*self_impedance+np.full((12,12),common)
    result=unequal_current_equivalent(z,e)
    expected=np.eye(3)*self_impedance/4+np.full((3,3),common)
    np.testing.assert_allclose(result.phase_ohm_per_m,expected,rtol=1e-13)
    np.testing.assert_allclose(result.response,e/4,rtol=1e-13,atol=1e-15)


def test_unequal_current_influence_is_quantified_not_claimed_as_pscad_correction(analysis):
    ac_equal,dc_equal,ac_unequal,dc_unequal=analysis['scenarios']
    change=100*(ac_unequal.sequence_ohm_per_m[1,1].real/ac_equal.sequence_ohm_per_m[1,1].real-1)
    assert 0.22<change<.24
    data=analysis['currents']
    assert len(data)==96
    equal=data[data.Escenario==ac_equal.name]
    np.testing.assert_allclose(equal.Modulo_A,.25,atol=1e-15)
    different=data[(data.Escenario==ac_unequal.name)&data.Excitacion.str.startswith('Positiva')]
    assert 5<different.Desviacion_modulo_pct.abs().max()<5.2
    assert 3<different.Desfase_grados.abs().max()<3.1


@pytest.mark.parametrize('z,e',[(np.zeros((12,12)),np.kron(np.eye(3),np.ones((4,1)))),
    (np.eye(4),np.ones((4,3))),(np.eye(12),np.zeros((12,3))),
    (np.eye(12)*np.nan,np.kron(np.eye(3),np.ones((4,1)))),(np.eye(12),np.ones((10,3)))])
def test_invalid_current_sharing_inputs_are_rejected(z,e):
    with pytest.raises(InputError):
        unequal_current_equivalent(z,e)


def test_scalar_check_does_not_silently_discard_untransposed_couplings(analysis):
    with pytest.raises(InputError,match='no está idealmente transpuesta'):
        scalar_transposed_sequences(analysis['scenarios'][0].original_phase_ohm_per_m)


def test_analysis_preserves_original_inputs_and_previous_artifacts():
    paths=[*find_dove_folder().glob('*'),*Path('output').glob('*transposicion_dove*'),*Path('output/pdf').glob('*transposicion_dove*')]
    before={p:p.read_bytes() for p in paths if p.is_file()}
    analyze_dove()
    for path,original in before.items():
        assert path.read_bytes()==original


def test_json_and_pdf_preserve_matrices_sequences_errors_and_physical_caveats(analysis):
    record=discrepancy_record(analysis)
    parsed=json.loads(json.dumps(record,ensure_ascii=False,allow_nan=False))
    assert len(parsed['escenarios'])==4 and len(parsed['comparacion_secuencias'])==12
    assert parsed['entradas_originales']['metodo']=='kersting_pq_finite'
    reader=PdfReader(BytesIO(discrepancy_pdf(analysis)))
    text='\n'.join(p.extract_text() for p in reader.pages)
    for term in ('0.1859','0.102','R_AC','R_DC','Error R [%]','Error X [%]',
                 'Z0=Zpropio+2 Zmutuo','Z1=Z2=Zpropio-Zmutuo','10.014532','8.530158','1.484374',
                 'gradiente longitudinal','no reproduce PSCAD','Z012 completa'):
        assert term in text
    for value in analysis['pscad_sequence_ohm_m'].diagonal():
        assert f'{value.real*1000:.9e}' in text
    assert all(float(p.mediabox.width)>float(p.mediabox.height) for p in reader.pages)
