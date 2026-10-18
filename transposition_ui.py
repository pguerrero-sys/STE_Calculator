"""Panel de etapa 5; reutiliza la configuración y las vistas de Haces."""

from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from .bundle_ui import table, figure, load_bundle_case
from .capacitance import capacitance_to_nf_per_km
from .inductance import convert_inductance, calculate_reactance, NO_GROUND
from .models import InputError, PHASES
from .transposition import calculate_transposition, permutation_matrix, section_lengths_m
from .units import convert_length
from .transposition_schedule import MODES, migrate_mode

def load_transposition_case():
    load_bundle_case()
    for phase in PHASES:
        st.session_state[f"haz_n_{phase}"] = 4
        st.session_state[f"haz_s_{phase}"] = .4572
        st.session_state[f"haz_angle_{phase}"] = 0.0
    st.session_state.haz_cap_ground = "Suelo ideal"
    st.session_state.haz_ind_ground = "Suelo ideal"
    st.session_state.trans_mode = MODES[1]


def diagram(result):
    fig = go.Figure()
    n = len(result.sections)
    for phase,color in enumerate(["#D45141","#087F8C","#6854B5"]):
        xs,ys = [],[]
        for i,section in enumerate(result.sections):
            xs.extend([i/n,(i+1)/n])
            ys.extend([section.phase_to_position[phase]+1]*2)
        fig.add_trace(go.Scatter(x=xs,y=ys,mode="lines+markers",name=PHASES[phase],line={"color":color,"width":3},
            hovertemplate=f"Fase {PHASES[phase]}<br>Fracción de L=%{{x:.3f}}<br>Posición=%{{y}}<extra></extra>"))
    for i in range(n):
        fig.add_annotation(x=(i+.5)/n,y=0.65,text=f"Tramo {i+1} · {'L/3' if n==3 else 'L'}",showarrow=False)
    centers = result.sections[0].geometry.specs
    labels = [f"P{i+1}: ({s.center.x_m:g}, {s.center.y_m:g}) m" for i,s in enumerate(centers)]
    fig.update_layout(template="plotly_white",height=300,margin={"t":20,"b":25},
        xaxis={"title":"Fracción de la longitud total L","range":[0,1]},
        yaxis={"title":"Posición física · esquema","tickvals":[1,2,3],"ticktext":labels,"range":[3.4,.4]},
        legend={"orientation":"h"})
    return fig


def render_transposition_panel(context,frequency_hz,length_value=None,length_unit="m"):
    st.divider()
    st.subheader("Transposición ideal · etapa 5")
    st.caption("Usa las posiciones, haces, modelos de conductor y opciones de suelo configurados arriba. Los resultados anteriores de Haces corresponden al tramo I; este panel muestra el tratamiento longitudinal seleccionado.")
    st.button("Cargar caso obligatorio de transposición",on_click=load_transposition_case,
              help="Carga centros del caso, cuatro subconductores cuadrados por fase, separación 0.4572 m, radio 0.011765 m y modelo macizo con suelo ideal. No cambia frecuencia ni longitud.")
    current_mode=st.session_state.get('trans_mode')
    if current_mode not in MODES:
        st.session_state.trans_mode=migrate_mode(current_mode)
    mode = st.radio("Tratamiento de la línea",MODES,key="trans_mode")
    if context is None:
        st.error("Transposición no calculada: no se recibió el contexto de entrada (context=None). Es un fallo de integración; no implica que falten radios o coordenadas.")
        return
    if context.get("geometry") is None:
        st.error("Transposición no calculada: "+context.get("geometry_error","El contexto no contiene geometry ni un diagnóstico de validación."))
        return
    complete = mode == MODES[1]
    try:
        result = calculate_transposition(context["geometry"].specs,context["rmg_inputs"],complete,
            context["inductance_model"],context["capacitance_model"])
    except InputError as exc:
        st.error(f"Transposición no calculada: {exc}")
        return
    st.success("Promedio por tramos calculado." if complete else "Tramo único calculado sin transposición.")
    st.caption("Caso numérico y modelo ideal: no constituyen una validación reglamentaria ni un diseño eléctrico certificado.")
    st.plotly_chart(diagram(result),width="stretch",config={"displaylogo":False})
    st.caption("Las conexiones verticales del esquema tienen longitud idealizada nula. No se modelan sus campos ni las estructuras de cruce.")
    lengths = None
    if length_value is not None:
        try:
            lengths = section_lengths_m(convert_length(length_value,length_unit,"m"),complete)
        except InputError as exc:
            st.info(f"Longitudes no mostradas: {exc}. Los coeficientes por unidad de longitud siguen disponibles.")
    mapping = []
    for i,section in enumerate(result.sections):
        row = {"Tramo":i+1,"Peso":section.weight,**{p:f"P{section.phase_to_position[j]+1}" for j,p in enumerate(PHASES)}}
        row["Longitud"] = f"{lengths[i]:.9g} m" if lengths else ("L/3" if complete else "L")
        mapping.append(row)
    st.dataframe(pd.DataFrame(mapping),hide_index=True,width="stretch")
    st.subheader("Resultado de inductancia")
    if result.l_h_per_m is not None:
        if result.inductance_model == NO_GROUND:
            st.warning("IA + IB + IC = 0. L es la proyección de media cero, de rango 2, no una matriz absoluta para corrientes arbitrarias.")
        for unit,col in zip(["H/m","µH/m","mH/km"],st.columns(3)):
            with col:
                table(f"L {'transpuesta' if complete else 'sin transposición'} [{unit}]",convert_inductance(result.l_h_per_m,"H/m",unit),fmt="{:.9e}" if unit=="H/m" else "{:.6f}")
        if result.inductance_model == NO_GROUND:
            table("L de lazos A−C/B−C [mH/km]",convert_inductance(result.l_loops_h_per_m,"H/m","mH/km"),labels=("A−C","B−C"),fmt="{:.6f}")
        try:
            x = calculate_reactance(result.l_h_per_m,frequency_hz)
            table("X del modelo seleccionado [Ω/km]",x.x_ohm_per_km)
        except InputError as exc:
            st.info(f"Reactancia no calculada: {exc}")
    else:
        st.info("Inductancia no disponible: corrige el modelo o RMG individual en Haces. "+context["inductance_error"])
    st.subheader("Resultado de capacitancia · promedio de potenciales antes de invertir")
    st.caption("Modelo didáctico a carga de fase común entre tramos. A potencial común corresponde promediar C; este resultado no se presenta como equivalente shunt universal. Revisión física en referencias/carson.md; se conservan los valores anteriores.")
    if result.capacitance_model == NO_GROUND:
        st.warning("Sin suelo: Σq_fase = 0 y potencial común indeterminado. P efectiva y C son proyecciones de rango 2; las inversiones se realizan en el subespacio reducido.")
    table("P efectiva promedio de fases [adimensional]",result.average_phase_p,fmt="{:.9f}")
    for values,unit,col in zip([result.c_f_per_m,capacitance_to_nf_per_km(result.c_f_per_m)],["F/m","nF/km"],st.columns(2)):
        with col:
            table(f"C {'transpuesta' if complete else 'sin transposición'} [{unit}]",values,fmt="{:.9e}" if unit=="F/m" else "{:.6f}")
    target = "H = I − 11ᵀ/3" if result.capacitance_model == NO_GROUND else "I"
    st.caption(f"Comprobación P_prom C/(2πε₀) = {target}; residuo máximo {result.inversion_residual:.3e}.")
    with st.expander("Comparación didáctica: promedio directo de C (otro procedimiento)"):
        st.warning("Esta matriz no se usa como resultado transpuesto. Corresponde a promediar cargas a potencial local fijo, mientras el procedimiento solicitado promedia potenciales antes de invertir.")
        table("Promedio directo de capacitancias [nF/km] · solo comparación",capacitance_to_nf_per_km(result.direct_average_c_f_per_m),fmt="{:.6f}")
    st.subheader("Tramos y matrices intermedias")
    for i,section in enumerate(result.sections):
        with st.expander(f"Tramo {i+1} · {'L/3' if complete else 'L'} · peso {section.weight:.6g}"):
            st.write("R: filas posiciones, columnas fases [adimensional]")
            st.dataframe(pd.DataFrame(permutation_matrix(section.phase_to_position),index=("P1","P2","P3"),columns=PHASES).style.format("{:.0f}"),width="stretch")
            st.caption("Las columnas de R corresponden a A/B/C. Las propiedades del conductor y del haz viajan con la fase; no se permutan a ciegas matrices de fases constructivamente distintas.")
            geometry = section.geometry
            st.dataframe(pd.DataFrame({"Subconductor":geometry.labels,"X [m]":geometry.positions_m[:,0],"Y [m]":geometry.positions_m[:,1]}),hide_index=True)
            if st.checkbox(f"Mostrar geometría del tramo {i+1}",key=f"trans_plot_{i}"):
                st.plotly_chart(figure(geometry,"Todas"),width="stretch",config={"scrollZoom":True,"displaylogo":False},key=f"trans_geometry_{i}")
            if section.inductance is not None:
                matrix = section.inductance.phase_h_per_m if result.inductance_model != NO_GROUND else section.inductance.projected_h_per_m
                table("L de este tramo [mH/km]",convert_inductance(matrix,"H/m","mH/km"),fmt="{:.9f}")
            table("P efectiva de fases de este tramo [adimensional]",section.effective_phase_p,fmt="{:.9f}")
            table("C de este tramo [nF/km]",capacitance_to_nf_per_km(section.capacitance.phase_f_per_m),fmt="{:.9f}")
            if st.checkbox(f"Mostrar sistema completo de subconductores del tramo {i+1}",key=f"trans_primitive_{i}"):
                table("P primitiva de subconductores [adimensional]",section.capacitance.potential_coefficients,geometry.labels,"{:.9f}")
                st.write("Respuesta q_sub por voltio de cada fase [F/m]")
                st.dataframe(pd.DataFrame(section.capacitance.charge_response_f_per_m,index=geometry.labels,columns=PHASES).style.format("{:.9e}"),width="stretch")
                if section.inductance is not None:
                    table("L primitiva de subconductores [H/m]",section.inductance.primitive_h_per_m,geometry.labels)
    st.subheader("Procedimiento matemático de transposición")
    st.latex(r"w_t=1/3,\quad\overline{\mathbf L}=\sum_{t=1}^3 w_t\mathbf L_t" if complete else r"w_1=1,\quad\overline{\mathbf L}=\mathbf L_1,\quad\overline{\mathbf P}=\mathbf P_{fase,1}")
    if result.capacitance_model == NO_GROUND:
        st.latex(r"\mathbf Q^T\mathbf Q=\mathbf I_2,\quad\mathbf Q\mathbf Q^T=\mathbf H,\quad\mathbf P_{fase,t}=\mathbf Q\left[\mathbf Q^T(\mathbf C_t/(2\pi\varepsilon_0))\mathbf Q\right]^{-1}\mathbf Q^T")
        st.latex(r"\overline{\mathbf P}=\sum_t w_t\mathbf P_{fase,t},\quad\mathbf C_{trans}=2\pi\varepsilon_0\mathbf Q(\mathbf Q^T\overline{\mathbf P}\mathbf Q)^{-1}\mathbf Q^T")
    else:
        st.latex(r"\mathbf G_t=\mathbf E_t^T\mathbf P_{sub,t}^{-1}\mathbf E_t,\quad\mathbf P_{fase,t}=\mathbf G_t^{-1},\quad\overline{\mathbf P}=\sum_t w_t\mathbf P_{fase,t},\quad\mathbf C_{trans}=2\pi\varepsilon_0\overline{\mathbf P}^{-1}")
    st.caption("Con suelo, estas son inversiones completas. Sin suelo se invierte solo la representación reducida de carga total cero. Si se elige sin transposición, solo hay un tramo de peso 1.")
    element = st.selectbox("Elemento promedio para desarrollar",[(i,j) for i in range(3) for j in range(3)],format_func=lambda pair: PHASES[pair[0]]+PHASES[pair[1]],key="trans_element")
    i,j = element
    terms = "+".join(f"({s.effective_phase_p[i,j]:.12g})" for s in result.sections)
    st.latex(rf"\overline P_{{{PHASES[i]}{PHASES[j]}}}=\frac{{{terms}}}{{{len(result.sections)}}}={result.average_phase_p[i,j]:.12g}")
    if result.l_h_per_m is not None:
        values = [s.inductance.phase_h_per_m if result.inductance_model != NO_GROUND else s.inductance.projected_h_per_m for s in result.sections]
        terms = "+".join(f"({float(convert_inductance(v[i,j],'H/m','mH/km')):.12g})" for v in values)
        st.latex(rf"\overline L_{{{PHASES[i]}{PHASES[j]}}}=\frac{{{terms}}}{{{len(result.sections)}}}\,\mathrm{{mH/km}}={float(convert_inductance(result.l_h_per_m[i,j],'H/m','mH/km')):.12g}\,\mathrm{{mH/km}}")
    st.caption("Fuentes: notas generales PDF 53–57 y 96–98; clase 14-09-26 PDF 2–3; Kersting §4.1.1 y §5.1–5.2. Se conservan los modelos de la etapa 4: cargas equipotenciales y corrientes I/n. No se realiza una cascada exacta de líneas distribuidas.")
    if st.checkbox("Preparar informe PDF de haces y transposición",key="trans_pdf"):
        from .printing import transposition_pdf
        st.download_button("Descargar informe PDF · haces y transposición",transposition_pdf(result),"ste_transposicion.pdf","application/pdf")
        st.caption("Tablas con ajuste al ancho y bloques de hasta seis columnas; encabezados repetidos al paginar. Usa este informe para imprimir las matrices completas.")
    with st.expander("Bibliografía, hipótesis y discrepancias de las notas"):
        st.markdown((Path(__file__).resolve().parents[1]/"referencias"/"transposicion.md").read_text(encoding="utf-8"))
