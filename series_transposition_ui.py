"""Extensión 7D añadida después de los paneles anteriores, sin modificarlos."""

import json
from pathlib import Path
import numpy as np
import pandas as pd
import streamlit as st
from .models import InputError
from .series_inputs import state_case,exported_case
from .pscad_series import load_dove_case,find_dove_folder
from .series_transposition import transpose_series,require_equivalent_phases
from .series_comparison import comparison_table,comparison_csv,pscad_reference
from .series_report import series_pdf,series_record
from .carson import convert_impedance,METHODS
from .sequences import phase_to_sequence

CURRENT = "Controles actuales de Carson"
DOVE = "DOVE · JSON y TXT PSCAD del proyecto"
UPLOAD = "JSON Carson exportado"


def select_dove():
    st.session_state.series_source = DOVE


def matrix(title,z,labels):
    st.write(title)
    st.dataframe(pd.DataFrame(z,index=labels,columns=labels),width="stretch",
                 column_config={p:st.column_config.NumberColumn(width="small",format="%.10f") for p in labels})


def render_series_transposition(conductors,circuit_count,coordinate_error=""):
    st.divider()
    st.subheader("Transposición de impedancia serie · Carson · etapa 7D")
    st.caption("Extensión independiente. No cambia las matrices de capacitancia, inductancia ideal ni los resultados anteriores de Carson/Kron. Las entradas se leen de nuevo en cada cálculo.")
    st.button("Cargar caso DOVE · JSON y PSCAD",on_click=select_dove,
              help="Lee los archivos suministrados dentro de referencias. Carga datos únicamente en 7D; no modifica Geometría ni los controles anteriores.")
    source = st.radio("Origen de datos · Carson transpuesto",[CURRENT,DOVE,UPLOAD],key="series_source")
    enabled = st.checkbox("Activar transposición ideal de Carson",key="series_enabled")
    with_kron = False
    if source==CURRENT:
        with_kron = st.checkbox("Usar fases reducidas por Kron en cada tramo · 7D",key="series_kron",
                                help="Requiere auxiliares y declaración ΔVn=0 en los controles de Kron. Auxiliares fijos; se reduce cada tramo antes de promediar.")
    uploaded = st.file_uploader("JSON exportado de Carson · entradas de 7D",type=["json"],key="series_json") if source==UPLOAD else None
    try:
        if source==DOVE:
            case = load_dove_case()
        elif source==UPLOAD:
            if uploaded is None:
                raise InputError("Selecciona el JSON exportado de Carson para cargar sus entradas.")
            if uploaded.size>5*1024*1024:
                raise InputError("JSON demasiado grande; límite de entrada 5 MiB.")
            case = exported_case(uploaded.getvalue())
        else:
            case = state_case(conductors,circuit_count,st.session_state.to_dict(),with_kron=with_kron,coordinate_error=coordinate_error)
        require_equivalent_phases(case.phase_result)
        result = transpose_series(case.z_ohm_per_m,case.labels,enabled=enabled)
    except (InputError,OSError) as exc:
        st.info("Transposición serie no calculada: "+str(exc))
        return
    primitive = getattr(case.phase_result,"primitive",case.phase_result)
    for warning in primitive.warnings:
        st.warning(warning)
    st.caption(f"Origen: {case.metadata.get('nombre',case.description)}. Método conservado: {METHODS[primitive.method]}; f={primitive.frequency_hz:g} Hz, ρ={primitive.resistivity_ohm_m:g} Ω·m.")
    if "residuo_JSON_original_ohm_m" in case.metadata:
        residual = case.metadata["residuo_JSON_original_ohm_m"]
        if residual<=1e-12:
            st.success(f"Caso sin transposición recalculado desde entradas: residuo máximo contra JSON={residual:.3e} Ω/m.")
        else:
            st.warning(f"El JSON almacena una Z distinta del recálculo: residuo máximo={residual:.3e} Ω/m. Se usa el recálculo, no la Z guardada.")
    if len(case.labels)==6:
        st.info("Doble circuito: tres secciones con ciclos sincronizados ABC/BCA/CAB en ambos circuitos. Se conservan seis fases y todos los acoplamientos; no se presupone un equivalente 3×3 ni nueve combinaciones independientes.")
    st.success("Carson 7D: transposición ideal activada." if enabled else "Carson 7D: sin transposición seleccionada; matriz original conservada.")
    unit = st.selectbox("Unidad de impedancia serie · 7D",["Ω/km","Ω/m"],key="series_unit")
    selected = convert_impedance(result.selected_ohm_per_m,"Ω/m",unit)
    matrix(f"Resultado seleccionado · R [{unit}]",selected.real,case.labels)
    matrix(f"Resultado seleccionado · X [{unit}]",selected.imag,case.labels)
    with st.expander("Comparar matrices original y transpuesta · 7D",expanded=True):
        for name,z in (("Original sin transposición",result.original_ohm_per_m),("Promedio transpuesto",result.average_ohm_per_m)):
            m = convert_impedance(z,"Ω/m",unit)
            matrix(f"{name} · R [{unit}]",m.real,case.labels)
            matrix(f"{name} · X [{unit}]",m.imag,case.labels)
    with st.expander("Tres tramos, asignaciones y desarrollo matemático · 7D"):
        rows = [{"Tramo":i+1,"Fracción":1/3,**{p:case.labels[q] for p,q in zip(case.labels,perm)}} for i,perm in enumerate(result.permutations)]
        st.dataframe(pd.DataFrame(rows),hide_index=True,width="stretch")
        st.caption("Cada columna de fase indica la posición física ocupada. Todas ocupan cada posición una vez por circuito.")
        st.latex(r"\begin{aligned}Z_t&=S_t^{\mathsf T}Z_{\mathrm{original}}S_t\\\overline Z&=\frac13(Z_0+Z_1+Z_2)\end{aligned}")
        st.latex(r"Z_s=\frac{Z_{AA}+Z_{BB}+Z_{CC}}3,\quad Z_m=\frac{Z_{AB}+Z_{BC}+Z_{CA}}3")
        st.caption("Última expresión: bloque trifásico recíproco. Modelo de fases equivalentes por circuito, corrientes continuas y cruces sin longitud. Con Kron: se reduce cada sección bajo ΔVn=0 y luego se promedia; no Kron del promedio primitivo.")
        for i,z in enumerate(result.sections_ohm_per_m,1):
            m = convert_impedance(z,"Ω/m",unit)
            matrix(f"Tramo {i} · R [{unit}]",m.real,case.labels)
            matrix(f"Tramo {i} · X [{unit}]",m.imag,case.labels)
        avgseq = phase_to_sequence(result.average_ohm_per_m,case.labels)
        st.caption(f"Orden de secuencias del promedio: {', '.join(avgseq.labels)}. No se fuerzan ceros; en doble circuito se conserva el acoplamiento entre circuitos.")
    reference = case.pscad
    override = st.file_uploader("Referencia PSCAD opcional · JSON de matrices",type=["json"],key="series_pscad_json")
    if override is not None:
        try:
            reference = json.loads(override.getvalue())
        except (ValueError,TypeError) as exc:
            st.error("PSCAD no comparado: JSON inválido.")
            return
    try:
        table = comparison_table(result,reference)
    except InputError as exc:
        st.error("PSCAD no comparado: "+str(exc))
        return
    st.subheader("Comparación STE Calculator / PSCAD · R y X por separado")
    st.caption("La tabla conserva ambos estados aunque el selector principal esté desactivado. Todas las impedancias de esta tabla están en Ω/km. Error=100·|STE−PSCAD|/|PSCAD|; referencia cero ⇒ porcentaje indefinido.")
    if reference is None:
        st.info("No hay resultados PSCAD cargados: columnas PSCAD y errores pendientes. No se asumen errores cero ni se generan datos de referencia desde STE.")
    else:
        st.warning(f"STE usa resistencia AC bibliográfica. PSCAD declara {reference['resistance_type']}. No se consideran modelos de conductor idénticos ni se convierte R_DC en R_AC.")
        if reference.get("input_resistance_ohm_per_km") is not None:
            first = primitive.conductors[0]
            st.caption(f"Por subconductor: R_AC STE={first.resistance_ac_ohm_per_km*1.609344:.12g} Ω/milla={first.resistance_ac_ohm_per_km:.12g} Ω/km; R_{reference['resistance_type']} PSCAD={reference['input_resistance_ohm_per_km']:.12g} Ω/km.")
        for state,f in reference.get("frequencies_Hz",{}).items():
            if not np.isclose(f,primitive.frequency_hz):
                st.warning(f"{state}: frecuencia PSCAD={f} Hz distinta de STE={primitive.frequency_hz} Hz; comparación de condiciones diferentes.")
    st.dataframe(table,width="stretch",hide_index=True)
    st.download_button("Descargar comparación Carson transpuesto CSV",comparison_csv(table),"ste_carson_transposicion.csv","text/csv")
    st.download_button("Descargar matrices Carson transpuesto JSON",json.dumps(series_record(case,result,table,reference),ensure_ascii=False,indent=2,allow_nan=False),"ste_carson_transposicion.json","application/json")
    if st.checkbox("Preparar informe PDF Carson transpuesto",key="series_pdf"):
        st.download_button("Descargar comparación Carson transpuesto PDF",series_pdf(case,result,table,reference),"ste_carson_transposicion.pdf","application/pdf")
    with st.expander("Bibliografía, hipótesis y comparación PSCAD · 7D"):
        st.markdown((Path(__file__).resolve().parents[1]/"referencias"/"transposicion_serie.md").read_text(encoding="utf-8"))
