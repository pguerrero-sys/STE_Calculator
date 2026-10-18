"""Controles independientes de unidades, fórmulas y experimento 7F."""
from io import BytesIO
import json
import math
from dataclasses import replace
import numpy as np
import pytest
from pypdf import PdfReader
from ste_calculator.carson import calculate_carson, CarsonConductor, MODIFIED, PQ_TRUNCATED, convert_impedance
from ste_calculator.earth_validation import analyze_earth_return, validation_record, STATES
from ste_calculator.earth_validation_report import earth_validation_pdf


@pytest.fixture(scope='module')
def analysis():
    return analyze_earth_return()


@pytest.mark.parametrize('method',[MODIFIED,PQ_TRUNCATED])
def test_independent_scalar_us_formula_unequal_heights(method):
    # Sin usar constantes, matrices de distancias ni P/Q de la implementación.
    data=(CarsonConductor('A',-3,13,.1859/1.609344,.00954024,'Caso de control',.011765),
          CarsonConductor('B',3,17,.102,.008,'Control de alturas',.011),
          CarsonConductor('C',0,9,.12,.009,'Control de alturas',.012))
    f,rho=50,230
    actual=calculate_carson(data,f,rho,method)
    expected=np.empty((3,3),complex)
    for i,a in enumerate(data):
        for j,b in enumerate(data):
            distance_ft=(a.gmr_m if i==j else math.dist((a.x_m,a.height_m),(b.x_m,b.height_m)))/.3048
            image_ft=math.dist((a.x_m,a.height_m),(b.x_m,-b.height_m))/.3048
            if method==MODIFIED:
                # Forma cerrada (4.37)-(4.38), sin ensamblaje de imágenes.
                r=(a.resistance_ac_ohm_per_km*1.609344 if i==j else 0)+math.pi**2*f*.0001609344
                x=4*math.pi*f*.0001609344*(math.log(1/distance_ft)+7.6786+.5*math.log(rho/f))
            else:
                angle=math.atan2(abs(a.x_m-b.x_m),a.height_m+b.height_m)
                k=.0008565*image_ft*math.sqrt(f/rho)
                p=math.pi/8-k*math.cos(angle)/(3*math.sqrt(2))+k*k*math.cos(2*angle)/16*(.6728+math.log(2/k))
                q=-.0386+.5*math.log(2/k)+k*math.cos(angle)/(3*math.sqrt(2))
                r=(a.resistance_ac_ohm_per_km*1.609344 if i==j else 0)+4*(2*math.pi*f)*.0001609344*p
                x=2*(2*math.pi*f)*.0001609344*(math.log(image_ft/distance_ft)+2*q)
            expected[i,j]=(r+1j*x)/1609.344
    np.testing.assert_allclose(actual.z_ohm_per_m,expected,rtol=2e-14,atol=1e-18)


def test_identical_inputs_geometry_gmr_frequency_and_no_original_mutation(analysis):
    mod,pq=analysis['primitives'].values()
    assert mod.conductors==pq.conductors==analysis['case'].phase_result.primitive.conductors
    assert mod.frequency_hz==pq.frequency_hz==60
    assert mod.resistivity_ohm_m==pq.resistivity_ohm_m==100
    for name in ('real_distances_m','image_distances_m','z_conductor_ohm_per_m','z_geometry_ohm_per_m'):
        np.testing.assert_array_equal(getattr(mod,name),getattr(pq,name))
    original=analysis['case'].phase_result.primitive
    np.testing.assert_array_equal(pq.z_ohm_per_m,original.z_ohm_per_m)
    assert len(mod.conductors)==12
    assert pq.k.max()<.1


def test_7d_7e_reference_values_conserved_not_used_as_outputs(analysis):
    from ste_calculator.sequence_discrepancy import analyze_dove
    previous=analyze_dove()['scenarios'][:2]
    for s in analysis['scenarios']:
        if s['method_id']==PQ_TRUNCATED and s['state']==STATES[1]:
            before=previous[0 if s['resistance'].startswith('AC') else 1]
            np.testing.assert_array_equal(s['phase_ohm_m'],before.transposed_phase_ohm_per_m)
            np.testing.assert_array_equal(s['sequence_ohm_m'],before.sequence_ohm_per_m)


def test_bundle_aggregation_independent_pair_sums_and_all_contributions(analysis):
    for s in analysis['scenarios']:
        np.testing.assert_allclose(sum(s['parts_ohm_m'].values()),s['phase_ohm_m'],rtol=1e-14,atol=1e-18)
        if s['state']==STATES[0]:
            expected=np.array([[s['primitive_ohm_m'][i*4:(i+1)*4,j*4:(j+1)*4].sum()/16
                                for j in range(3)] for i in range(3)])
            np.testing.assert_allclose(s['phase_ohm_m'],expected,atol=1e-18,rtol=1e-14)


def test_dc_shift_is_only_real_diagonal_and_same_for_both_methods(analysis):
    for method in (MODIFIED,PQ_TRUNCATED):
        for state in STATES:
            ac,dc=[s for s in analysis['scenarios'] if s['method_id']==method and s['state']==state]
            expected=(.102-.1859/1.609344)/4/1000*np.eye(3)
            np.testing.assert_allclose(dc['phase_ohm_m']-ac['phase_ohm_m'],expected,rtol=1e-13,atol=1e-18)
            np.testing.assert_allclose(dc['sequence_ohm_m']-ac['sequence_ohm_m'],expected,rtol=1e-13,atol=1e-18)
            np.testing.assert_array_equal(dc['phase_ohm_m'].imag,ac['phase_ohm_m'].imag)
            np.testing.assert_array_equal(ac['parts_ohm_m']['earth'],dc['parts_ohm_m']['earth'])


def test_finite_q_difference_has_no_balanced_subspace_component(analysis):
    # Qfin-Qmod = c + beta(hi+hj), se deduce simbólicamente del libro.
    mod,pq=analysis['primitives'].values()
    h=np.array([c.height_m for c in pq.conductors])
    beta=.0008565/.3048*math.sqrt(60/100)/(3*math.sqrt(2))
    constant=-.0386+.5*math.log(2/.0008565)-7.6786/2
    expected=constant+beta*(h[:,None]+h[None,:])
    np.testing.assert_allclose(pq.q-mod.q,expected,rtol=1e-12,atol=2e-15)
    t=analysis['weights']; projector=np.eye(3)-np.ones((3,3))/3
    np.testing.assert_allclose(projector@(t.T@expected@t)@projector,0,atol=1e-16)
    ac=[s for s in analysis['scenarios'] if s['state']==STATES[1] and s['resistance'].startswith('AC')]
    assert abs((ac[1]['sequence_ohm_m']-ac[0]['sequence_ohm_m'])[1,1].imag)<1e-18
    assert abs((ac[1]['sequence_ohm_m']-ac[0]['sequence_ohm_m'])[0,0].imag)>1e-6


def test_symmetry_cyclic_invariance_and_independent_dft(analysis):
    a=complex(-.5,math.sqrt(3)/2)
    transform=np.array([[1,1,1],[1,a*a,a],[1,a,a*a]])
    for s in analysis['scenarios']:
        z=s['phase_ohm_m']
        np.testing.assert_allclose(z,z.T,rtol=1e-14,atol=1e-18)
        independently=np.linalg.solve(transform,z@transform)
        np.testing.assert_allclose(s['sequence_ohm_m'],independently,rtol=1e-12,atol=1e-18)
        if s['state']==STATES[1]:
            np.testing.assert_allclose(z,z[np.ix_([1,2,0],[1,2,0])],atol=1e-18)
            expected=[z[0,0]+2*z[0,1],z[0,0]-z[0,1],z[0,0]-z[0,1]]
            np.testing.assert_allclose(np.diag(s['sequence_ohm_m']),expected,atol=1e-18)
        else:
            off=s['sequence_ohm_m']-np.diag(np.diag(s['sequence_ohm_m']))
            assert np.max(np.abs(off))>1e-6


@pytest.mark.parametrize('source,dest,factor',[('Ω/m','Ω/km',1000),('Ω/mile','Ω/km',1/1.609344),('Ω/km','Ω/m',.001),('Ω/km','Ω/mile',1.609344)])
def test_independent_length_conversion(source,dest,factor):
    z=np.array([[.1859+.627j,.01+.4j],[.01+.4j,.102+.55j]])
    np.testing.assert_allclose(convert_impedance(z,source,dest),z*factor,rtol=1e-15,atol=1e-18)


def test_all_element_errors_and_controls(analysis):
    assert len(analysis['comparison'])==144  # 8 escenarios × (9 fases + 9 secuencias)
    assert len(analysis['controlled'])==72
    for key in ('comparison','controlled'):
        for row in analysis[key].to_dict('records'):
            for part in ('R','X'):
                value,ref=row[part+'_ohm_km'],row['Ref_'+part+'_ohm_km']
                assert row['Delta_'+part+'_ohm_km']==pytest.approx(value-ref,abs=1e-18)
                assert row['Abs_delta_'+part+'_ohm_km']==pytest.approx(abs(value-ref),abs=1e-18)
                if row['Porcentaje_'+part+'_interpretable']:
                    assert row['Error_'+part+'_pct']==pytest.approx(100*abs(value-ref)/abs(ref))
                else:
                    assert np.isnan(row['Error_'+part+'_pct'])
    rows=analysis['comparison'].query("Dominio == 'secuencia' and Fila == '1' and Columna == '1' and Estado == 'con_transposicion'")
    np.testing.assert_allclose(rows.Error_R_pct,[9.99467799,2.87269470,10.01453247,2.85284022],atol=1e-7,rtol=0)


def test_json_and_pdf_preserve_confirmed_selectors_and_full_matrices(analysis):
    record=validation_record(analysis)
    json.dumps(record,allow_nan=False)
    assert record['selector_0_verificado'] is True
    assert record['selector_2_verificado'] is True
    assert record['equivalencia_PSCAD_demostrada'] is False
    assert len(record['scenarios'])==8
    assert np.shape(record['scenarios'][0]['primitive_ohm_m']['real'])==(12,12)
    reader=PdfReader(BytesIO(earth_validation_pdf(analysis)))
    assert len(reader.pages)==7
    text='\n'.join(page.extract_text() for page in reader.pages)
    for word in ('EarthImpedanceFormula=0','RMG','Deri-Semlyen','PSCAD','P/Q finito','DC temporal','0.102','Ω/km'):
        assert word in text


def test_numerical_reference_matches_supplied_sequences_and_independent_scalars(analysis):
    reference=analysis['numerical_reference']
    z=reference['phase_ohm_m']*1000
    np.testing.assert_allclose(np.diag(z),.0838480984+1j*.639290544,rtol=0,atol=1e-15)
    assert z[0,1]==pytest.approx(.0575947846+1j*.384430764,abs=1e-15)
    scalar=np.array([z[0,0]+2*z[0,1],z[0,0]-z[0,1],z[0,0]-z[0,1]])
    expected=np.array([.1990376676+1.408152072j,.0262533138+.254859780j,.0262533138+.254859780j])
    np.testing.assert_allclose(scalar,expected,rtol=0,atol=5e-15)
    np.testing.assert_allclose(np.diag(reference['sequence_ohm_m'])*1000,expected,rtol=0,atol=5e-15)
    assert reference['residual_ohm_m']<1e-18
    assert reference['metadata']['relative_permittivity_final']==1
    assert reference['metadata']['Y_unchanged']['numeric_matrix_supplied'] is True


def test_both_pscad_references_and_comparisons_are_kept(analysis):
    assert len(analysis['comparison'])==144
    assert len(analysis['numerical_comparison'])==72
    df=analysis['numerical_comparison']
    assert set(df.Estado)=={'con_transposicion'}
    for row in df.to_dict('records'):
        scenario=next(s for s in analysis['scenarios'] if s['method']==row['Metodo'] and s['resistance']==row['Resistencia'] and s['state']==row['Estado'])
        labels=('A','B','C') if row['Dominio']=='fase' else ('0','1','2')
        matrix=scenario['phase_ohm_m'] if row['Dominio']=='fase' else scenario['sequence_ohm_m']
        value=matrix[labels.index(row['Fila']),labels.index(row['Columna'])]*1000
        assert row['R_ohm_km']==value.real
        assert row['X_ohm_km']==value.imag
        for part in ('R','X'):
            if row['Porcentaje_'+part+'_interpretable']:
                assert row['Error_'+part+'_pct']==pytest.approx(100*abs(row[part+'_ohm_km']-row['Ref_'+part+'_ohm_km'])/abs(row['Ref_'+part+'_ohm_km']))
    delta=(analysis['numerical_reference']['sequence_ohm_m']-analysis['pscad_sequence_ohm_m'][STATES[1]])*1000
    assert delta[0,0]==pytest.approx(-.0009298204-.016167730j,abs=2e-15)
    assert delta[1,1]==pytest.approx(-.0000008893+.000005072j,abs=2e-15)


def test_documented_inputs_and_supplied_y_match_original_transposed_output(analysis):
    from pathlib import Path
    from ste_calculator.pscad_series import PAIR
    metadata=analysis['numerical_reference']['metadata']
    known=metadata['known_PSCAD_inputs']
    assert {key:known[key] for key in ('Sag_m','Strand_Radius_m','Number_of_Outer_Strands',
        'Total_Number_of_Strands','Conductor_Relative_Permeability','DCResistance_ohm_km',
        'GroundWires','GroundPermittivity_final')}==dict(Sag_m=0,Strand_Radius_m=.001858,
        Number_of_Outer_Strands=16,Total_Number_of_Strands=26,Conductor_Relative_Permeability=1,
        DCResistance_ohm_km=.102,GroundWires=0,GroundPermittivity_final=1)
    ydata=metadata['Y_unchanged']
    supplied=np.asarray(ydata['real'])+1j*np.asarray(ydata['imag'])
    text=Path(analysis['case'].pscad['files']['con_transposicion']).read_text(encoding='utf-8-sig')
    lines=text.split(' SHUNT ADMITTANCE MATRIX (Y) [mhos/m]:')[1].strip().splitlines()[:3]
    original=np.array([[complex(float(p[1]),float(p[2])) for p in PAIR.finditer(line)] for line in lines])
    np.testing.assert_array_equal(supplied,original)
    assert ydata['unit']=='S/m'
    assert ydata['max_absolute_difference_S_per_m']==float(np.max(np.abs(supplied-original)))==0
