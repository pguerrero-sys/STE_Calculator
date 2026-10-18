from dataclasses import replace
import json
import numpy as np
import pytest

from ste_calculator.series_transposition import transpose_series,require_equivalent_phases
from ste_calculator.pscad_series import load_dove_case,phase_series_matrix,find_dove_folder,UNT,TRN
from ste_calculator.series_inputs import exported_case,state_case
from ste_calculator.series_comparison import comparison_table,percent_error,pscad_reference,comparison_csv
from ste_calculator.carson import calculate_carson,kersting_example,PQ_TRUNCATED,MODIFIED
from ste_calculator.carson_report import carson_record
from ste_calculator.sequence_examples import two_guard_case
from ste_calculator.kron import reduce_augmented,reduce_kron
from ste_calculator.models import InputError


def test_dove_first_original_reproduces_exported_json_from_twelve_conductors():
    case = load_dove_case()
    data = json.loads((find_dove_folder()/"ste_carson.json").read_text(encoding="utf-8"))
    saved = np.array(data["Z_ohm_m"]["real"])+1j*np.array(data["Z_ohm_m"]["imag"])
    np.testing.assert_array_equal(case.z_ohm_per_m,saved)
    assert case.metadata["residuo_JSON_original_ohm_m"]==0
    assert len(case.phase_result.primitive.conductors)==12
    assert case.phase_result.primitive.method==PQ_TRUNCATED
    assert case.phase_result.primitive.conductors[0].resistance_ac_ohm_per_km*1.609344==pytest.approx(.1859)
    assert case.pscad["input_resistance_ohm_per_km"]==.102
    assert case.pscad["resistance_type"]=="DC"


def test_dove_transposed_values_are_computed_by_cyclic_sections():
    case = load_dove_case()
    require_equivalent_phases(case.phase_result)
    r = transpose_series(case.z_ohm_per_m,case.labels)
    expected = np.full((3,3),.0575147177+.3845045830j)
    np.fill_diagonal(expected,.0863981565+.6358520847j)
    np.testing.assert_allclose(r.average_ohm_per_m*1000,expected,rtol=0,atol=5e-11)
    # Comprobación independiente mediante promedios propios/mutuos, ec.4.68-69.
    own = np.trace(case.z_ohm_per_m)/3
    mutual = (case.z_ohm_per_m[0,1]+case.z_ohm_per_m[1,2]+case.z_ohm_per_m[2,0])/3
    np.testing.assert_allclose(np.diag(r.average_ohm_per_m),own,rtol=1e-14)
    np.testing.assert_allclose(r.average_ohm_per_m[~np.eye(3,dtype=bool)],mutual,rtol=1e-14)


@pytest.mark.parametrize("circuits",[1,2])
@pytest.mark.parametrize("shift",[0,1,2])
def test_cyclic_invariance_reciprocity_trace_units_and_idempotence(circuits,shift):
    rng = np.random.default_rng(2026+circuits)
    raw = rng.random((3*circuits,)*2)+1j*rng.random((3*circuits,)*2)
    z = (raw+raw.T)*1e-4
    labels = ("A","B","C","A'","B'","C'")[:3*circuits]
    r = transpose_series(z,labels)
    perm = r.permutations[shift]
    reindexed = transpose_series(z[np.ix_(perm,perm)],labels)
    np.testing.assert_allclose(reindexed.average_ohm_per_m,r.average_ohm_per_m,rtol=1e-14,atol=1e-18)
    np.testing.assert_allclose(r.average_ohm_per_m[np.ix_(perm,perm)],r.average_ohm_per_m,rtol=1e-14,atol=1e-18)
    np.testing.assert_allclose(r.average_ohm_per_m,r.average_ohm_per_m.T,atol=1e-18)
    np.testing.assert_allclose(np.trace(r.average_ohm_per_m),np.trace(z),rtol=1e-14)
    np.testing.assert_allclose(transpose_series(r.average_ohm_per_m,labels).average_ohm_per_m,r.average_ohm_per_m,rtol=1e-14)
    np.testing.assert_allclose(transpose_series(z*1000,labels).average_ohm_per_m,r.average_ohm_per_m*1000,rtol=1e-14)
    np.testing.assert_array_equal(z,r.original_ohm_per_m)
    if circuits==2:
        assert r.average_ohm_per_m.shape==(6,6)
        assert np.min(np.abs(r.average_ohm_per_m[:3,3:]))>0


def test_selection_off_on_and_off_keeps_original_unchanged():
    case = load_dove_case()
    initial = case.z_ohm_per_m.copy()
    for enabled in (False,True,False):
        result = transpose_series(initial,case.labels,enabled=enabled)
        expected = result.average_ohm_per_m if enabled else initial
        np.testing.assert_array_equal(result.selected_ohm_per_m,expected)
    np.testing.assert_array_equal(case.z_ohm_per_m,initial)


@pytest.mark.parametrize("method",[MODIFIED,PQ_TRUNCATED])
def test_kron_per_section_before_average_not_kron_of_primitive_average(method):
    from tests.test_kron import example
    aug = example()
    if method==PQ_TRUNCATED:
        from ste_calculator.kron import augment_carson
        aug = augment_carson(calculate_carson(kersting_example(),60,100,method),aug.auxiliaries)
    reduced = reduce_augmented(aug,confirmed=True)
    result = transpose_series(reduced.z_ohm_per_m,aug.phase_labels)
    primitives,sections = [],[]
    for perm in result.permutations:
        full = perm+(3,)
        primitive = aug.z_ohm_per_m[np.ix_(full,full)]
        primitives.append(primitive)
        sections.append(reduce_kron(primitive,(0,1,2),aug.auxiliaries,confirmed=True).z_ohm_per_m)
    np.testing.assert_allclose(sum(sections)/3,result.average_ohm_per_m,rtol=1e-14,atol=1e-18)
    wrong = reduce_kron(sum(primitives)/3,(0,1,2),aug.auxiliaries,confirmed=True).z_ohm_per_m
    assert np.linalg.norm(wrong-result.average_ohm_per_m)>1e-8


def test_double_circuit_two_guards_reduced_transposition_preserves_mutual_blocks():
    case = two_guard_case(2)
    red = reduce_augmented(case,confirmed=True)
    result = transpose_series(red.z_ohm_per_m,case.phase_labels)
    assert result.average_ohm_per_m.shape==(6,6)
    assert np.linalg.norm(result.average_ohm_per_m[:3,3:])>1e-4


def test_pscad_phase_parser_does_not_select_long_line_or_modal_values():
    folder = find_dove_folder()
    text = (folder/TRN).read_text(encoding="utf-8")
    z,f = phase_series_matrix(text,("A","B","C"))
    assert f==60
    np.testing.assert_array_equal(phase_series_matrix(text.replace('\n','\r\n'),('A','B','C'))[0],z)
    assert z[0,0]==pytest.approx(.841586314e-4+1j*.644676406e-3,abs=1e-16)
    assert abs(z[0,0])<.001  # No se usan 8.319...+j64.122... ohms totales.
    with pytest.raises(InputError):
        phase_series_matrix(text.replace("SERIES IMPEDANCE MATRIX (Z) [ohms/m]","OTHER DATA"),("A","B","C"))
    with pytest.raises(InputError):
        phase_series_matrix(text,("A","B","C","A'","B'","C'"))


def test_actual_pscad_transposed_matrix_matches_its_own_untransposed_average():
    case = load_dove_case()
    _,m = pscad_reference(case.pscad,case.labels)
    p = transpose_series(m["sin_transposicion"],case.labels)
    # API algebraica: aquí conserva la unidad Ω/km de entrada/salida.
    np.testing.assert_allclose(p.average_ohm_per_m,m["con_transposicion"],rtol=0,atol=7e-10)


def test_dove_comparison_real_data_percentage_convention_and_ac_dc_disclosure():
    case = load_dove_case()
    result = transpose_series(case.z_ohm_per_m,case.labels)
    table = comparison_table(result,case.pscad)
    assert len(table)==18
    own = table.query("Estado=='con_transposicion' and Fila=='A' and Columna=='A'").iloc[0]
    mutual = table.query("Estado=='con_transposicion' and Fila=='A' and Columna=='B'").iloc[0]
    assert own.Error_R_pct==pytest.approx(2.661076,abs=5e-7)
    assert own.Error_X_pct==pytest.approx(1.368799,abs=5e-7)
    assert mutual.Error_R_pct==pytest.approx(.673024,abs=5e-7)
    assert mutual.Error_X_pct==pytest.approx(1.363986,abs=5e-7)
    assert "R_AC STE frente a R_DC PSCAD" in own.Base_R
    csv = comparison_csv(table)
    assert csv.startswith(b'\xef\xbb\xbf')
    assert len(csv.decode('utf-8-sig').splitlines())==19


def test_zero_reference_and_missing_pscad_are_not_reported_as_zero_errors():
    assert percent_error(1,0) is None
    assert percent_error(0,0) is None
    assert percent_error(2,-1)==300
    case = load_dove_case()
    result = transpose_series(case.z_ohm_per_m,case.labels)
    table = comparison_table(result)
    assert table.PSCAD_R_ohm_km.isna().all() and table.Error_R_pct.isna().all()
    partial = dict(case.pscad)
    del partial['con_transposicion']
    table = comparison_table(result,partial)
    assert table.query("Estado=='con_transposicion'").Error_X_pct.isna().all()


def test_json_import_is_recalculated_even_if_saved_result_has_been_edited():
    data = carson_record(calculate_carson(kersting_example(),60,100))
    data['Z_ohm_m']['real'][0][0]+=1
    case = exported_case(json.dumps(data))
    assert case.metadata['residuo_JSON_original_ohm_m']==pytest.approx(1)
    assert case.z_ohm_per_m[0,0].real<.001


def test_nonidentical_phase_parameters_are_not_averaged_as_if_identical():
    data = list(kersting_example())
    data[1] = replace(data[1],resistance_ac_ohm_per_km=.9)
    result = calculate_carson(data,60,100)
    with pytest.raises(InputError,match="fases equivalentes"):
        require_equivalent_phases(result)


@pytest.mark.parametrize("z,labels,enabled",[(np.eye(4),("A","B","C"),True),
    (np.eye(3)*np.nan,("A","B","C"),True),(np.eye(3),("B","A","C"),True),
    (np.array([[1,2,3],[0,1,2],[3,2,1]]),("A","B","C"),True),(np.eye(3),("A","B","C"),1)])
def test_invalid_transposition_inputs(z,labels,enabled):
    with pytest.raises(InputError):
        transpose_series(z,labels,enabled=enabled)
