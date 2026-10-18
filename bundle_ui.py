"""Interfaz de la etapa 4; los cálculos están en bundles y bundle_electrical."""

from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from .bundle_electrical import (calculate_bundle_inductance, calculate_bundle_capacitance,
                                calculate_center_capacitance_approximation)
from .inductance import (IDEAL_GROUND, NO_GROUND,
                         convert_inductance, calculate_reactance, INDUCTANCE_FACTOR_H_PER_M)
from .capacitance import capacitance_to_nf_per_km, VACUUM_PERMITTIVITY_F_PER_M
from .models import InputError, PHASES
from .bundle_inputs import MATERIALS, build_bundle_context



def load_bundle_case():
    st.session_state.circuit_count = 1
    st.session_state.coordinates = {"C1-A":(-3.0,13.0),"C1-B":(3.0,13.0),"C1-C":(0.0,9.0)}
    for phase in PHASES:
        st.session_state[f"haz_n_{phase}"] = 1
        st.session_state[f"haz_r_{phase}"] = .011765
    st.session_state.haz_material = MATERIALS[1]
    st.session_state.haz_confirm = True
    st.session_state.example_mode = True
    st.session_state.editor_revision = st.session_state.get("editor_revision",0)+1


def table(title, values, labels=PHASES, fmt="{:.9e}"):
    st.write(title)
    st.dataframe(pd.DataFrame(values,index=labels,columns=labels).style.format(fmt),width="stretch")


def figure(geometry, focus):
    fig = go.Figure()
    selected = [i for i,p in enumerate(geometry.phase_index) if focus == "Todas" or PHASES[p] == focus]
    for phase,color in enumerate(["#D45141","#087F8C","#6854B5"]):
        indices = [i for i in selected if geometry.phase_index[i] == phase]
        if not indices:
            continue
        pts = geometry.positions_m[indices]
        fig.add_trace(go.Scatter(x=pts[:,0],y=pts[:,1],mode="markers+text",text=[geometry.labels[i] for i in indices],
            name=f"Fase {PHASES[phase]}",textposition="top center",marker={"color":color,"size":9},
            hovertemplate="%{text}<br>X=%{x:.9g} m<br>Y=%{y:.9g} m<extra></extra>"))
        for i in indices:
            x,y = geometry.positions_m[i]
            r = geometry.radii_m[i]
            fig.add_shape(type="circle",x0=x-r,x1=x+r,y0=y-r,y1=y+r,line={"color":color})
    points = geometry.positions_m[selected]
    padding = max(float(points[:,0].max()-points[:,0].min()),float(points[:,1].max()-points[:,1].min()),.1)*.3
    left,right = float(points[:,0].min()-padding),float(points[:,0].max()+padding)
    low = min(0,float(points[:,1].min()-padding)) if focus == "Todas" else float(points[:,1].min()-padding)
    fig.add_trace(go.Scatter(x=[left,right],y=[0,0],mode="lines",name="Y=0",line={"color":"#947455"}))
    fig.update_layout(template="plotly_white",height=460,dragmode="pan",
        xaxis={"title":"X [m]","range":[left,right]},
        yaxis={"title":"Y [m]","range":[low,float(points[:,1].max()+padding)],"scaleanchor":"x","scaleratio":1},
        margin={"t":20,"b":20},legend={"orientation":"h"})
    return fig


def render_bundle_tab(conductors,circuit_count,frequency_hz,coordinate_error=""):
    st.subheader("Conductores en haz · etapa 4")
    st.caption("Un circuito A/B/C. Los centros se toman de Geometría; radios y opciones de esta sección son independientes de los modelos individuales. La comparación carga datos sintéticos del caso previamente verificado, con n=1.")
    st.button("Cargar comparación sin haz (n=1)",on_click=load_bundle_case)
    for phase,col in zip(PHASES,st.columns(3)):
        with col:
            st.write(f"Fase {phase}")
            n = int(st.number_input(f"Subconductores {phase}",min_value=1,max_value=4,value=1,step=1,key=f"haz_n_{phase}"))
            st.number_input(f"Radio exterior individual {phase} [m]",value=None,format="%.9f",key=f"haz_r_{phase}")
            st.number_input(f"Separación entre vecinos {phase} [m]",value=None,format="%.6f",disabled=n==1,key=f"haz_s_{phase}")
            st.number_input(f"Rotación adicional {phase} [°]",value=0.0,disabled=n==1,key=f"haz_angle_{phase}")
    st.caption("n=2: horizontal; n=3: triángulo con vértice arriba; n=4: cuadrado. La separación es el lado, no la diagonal ni el radio circunscrito. La rotación permite orientar cada haz.")
    material = st.selectbox("Modelo inductivo del subconductor",MATERIALS,key="haz_material")
    if material == MATERIALS[1]:
        st.checkbox("Confirmo subconductores macizos, μr=1 y corriente uniforme",key="haz_confirm")
    elif material == MATERIALS[2]:
        st.text_input("Fuente del RMG individual ACSR/fabricante",key="haz_source")
        for phase,col in zip(PHASES,st.columns(3)):
            col.number_input(f"RMG individual fabricante {phase} [m]",value=None,format="%.12f",key=f"haz_g_{phase}")
        st.caption("El RMG suministrado se usa directamente. No se reconstruyen hebras ACSR ni se aplica R·exp(−1/4) a un conductor trenzado.")
    cap_choice = st.selectbox("Suelo para capacitancia del haz",["Suelo ideal","Sin suelo · carga total cero"],key="haz_cap_ground")
    ind_choice = st.selectbox("Suelo para inductancia del haz",["Suelo ideal","Sin suelo · corrientes de suma cero"],key="haz_ind_ground")
    cap_model = IDEAL_GROUND if cap_choice == "Suelo ideal" else NO_GROUND
    ind_model = IDEAL_GROUND if ind_choice == "Suelo ideal" else NO_GROUND
    try:
        context = build_bundle_context(conductors,circuit_count,st.session_state.to_dict(),coordinate_error)
        geometry = context["geometry"]
    except InputError as exc:
        st.info(f"Haces no calculados: {exc}")
        return

    focus = st.selectbox("Vista de subconductores",["Todas",*PHASES],key="haz_focus")
    st.plotly_chart(figure(geometry,focus),width="stretch",config={"scrollZoom":True,"displaylogo":False})
    st.caption("Posiciones calculadas de todos los subconductores, con ejes a igual escala. Los círculos indican el radio físico; los marcadores identifican centros. La vista por fase amplía el haz y puede dejar el terreno fuera del encuadre.")
    st.dataframe(pd.DataFrame({"Subconductor":geometry.labels,"X [m]":geometry.positions_m[:,0],"Y [m]":geometry.positions_m[:,1],"Radio [m]":geometry.radii_m}),hide_index=True,width="stretch")
    st.write("Radio equivalente capacitivo [m] · parte exclusivamente del radio exterior")
    st.dataframe(pd.DataFrame({"Fase":PHASES,"Radio equivalente capacitivo [m]":geometry.capacitive_radius_m}),hide_index=True)
    with st.expander("Distancias geométricas equivalentes y primitivas"):
        table("DMG entre haces [m]; diagonal cero",geometry.equivalent_distances_m,fmt="{:.9f}")
        table("DMG entre cada haz real e imágenes [m], incluida la propia",geometry.equivalent_images_m,fmt="{:.9f}")
        table("Todas las distancias reales [m]",geometry.real_distances_m,geometry.labels,"{:.9f}")
        table("Todas las distancias real-imagen [m]",geometry.image_distances_m,geometry.labels,"{:.9f}")

    st.subheader("Capacitancia · subconductores equipotenciales por fase")
    st.caption("Modelo matricial explícito de cargas lineales: cada subconductor tiene su radio y posición. Las cargas se resuelven individualmente; no se presuponen iguales.")
    if cap_model == NO_GROUND:
        st.warning("Sin suelo: Σq_sub = 0 y potencial común indeterminado. C tiene rango 2, no es una capacitancia a tierra ni se invierte.")
    cap = None
    try:
        cap = calculate_bundle_capacitance(geometry,cap_model)
        for values,unit,col in zip([cap.phase_f_per_m,capacitance_to_nf_per_km(cap.phase_f_per_m)],["F/m","nF/km"],st.columns(2)):
            with col:
                table(f"C de fases [{unit}]",values,fmt="{:.9e}" if unit=="F/m" else "{:.6f}")
        st.success(f"Equipotencialidad comprobada · residuo adimensional {cap.equipotential_residual:.3e}")
        if cap.neutrality_residual is not None:
            st.caption(f"Residuo de neutralidad normalizado: {cap.neutrality_residual:.3e}.")
        with st.expander("Sistema primitivo y respuesta de cargas"):
            table("P primitiva [adimensional]",cap.potential_coefficients,geometry.labels,"{:.9f}")
            st.write("E: asignación equipotencial de subconductores a fases [adimensional]")
            st.dataframe(pd.DataFrame(geometry.incidence,index=geometry.labels,columns=PHASES),width="stretch")
            st.write("Respuesta de carga q_sub por voltio de excitación de cada fase [F/m]. Con suelo: fase excitada a 1 V y otras a 0 V; sin suelo: mismas diferencias de potencial, con carga total cero.")
            st.dataframe(pd.DataFrame(cap.charge_response_f_per_m,index=geometry.labels,columns=PHASES).style.format("{:.9e}"),width="stretch")
        with st.expander("Comparación: aproximación de un círculo equivalente por fase"):
            st.warning("Aproximación en los centros con radio capacitivo equivalente. Esta tabla no sustituye la solución equipotencial explícita ni determina cargas individuales.")
            try:
                approximation = calculate_center_capacitance_approximation(geometry,cap_model)
                table("C aproximada en centros [nF/km]",capacitance_to_nf_per_km(approximation.phase_f_per_m),fmt="{:.6f}")
            except InputError as exc:
                st.info(f"Aproximación en centros fuera de su alcance: {exc}")
    except InputError as exc:
        st.info(f"Capacitancia del haz no calculada: {exc}")

    st.subheader("Inductancia · medias geométricas y corrientes iguales")
    st.warning("Se supone I_sub = I_fase/n. Se incluyen todas las distancias e imágenes, pero no se resuelve la redistribución real de corrientes entre subconductores. La matriz primitiva no constituye esa solución.")
    inductance = None
    inputs = None
    inductance_error = ""
    try:
        inputs = context["rmg_inputs"]
        if inputs is None:
            raise InputError(context["inductance_error"])
        inductance = calculate_bundle_inductance(geometry,inputs,ind_model)
        st.dataframe(pd.DataFrame({"Fase":PHASES,"RMG individual [m]":inductance.individual_rmg_m,
            "RMG inductivo equivalente [m]":inductance.equivalent_rmg_m,"Radio capacitivo equivalente [m]":geometry.capacitive_radius_m}),hide_index=True,width="stretch")
        unit = st.selectbox("Unidad de inductancia de haces",["mH/km","µH/m","H/m"],key="haz_l_unit")
        matrix = inductance.phase_h_per_m if ind_model == IDEAL_GROUND else inductance.projected_h_per_m
        if ind_model == NO_GROUND:
            st.warning("IA + IB + IC = 0. Se muestra la proyección de media cero, de rango 2, no una matriz absoluta para cualquier corriente.")
        table(f"L de fases {'proyectada ' if ind_model == NO_GROUND else ''}[{unit}]",convert_inductance(matrix,"H/m",unit),fmt="{:.9e}" if unit=="H/m" else "{:.8f}")
        if ind_model == NO_GROUND:
            table(f"L de lazos A−C/B−C [{unit}]",convert_inductance(inductance.loops_h_per_m,"H/m",unit),labels=("A−C","B−C"),fmt="{:.8f}")
        with st.expander("Matriz inductiva primitiva, antes de agregar fases"):
            st.caption("Sin suelo estos coeficientes canónicos no son una matriz absoluta única; solo se emplean con suma de corrientes cero.")
            table("L_sub [H/m] · supuesto de corrientes iguales al agregar",inductance.primitive_h_per_m,geometry.labels)
        try:
            x = calculate_reactance(matrix,frequency_hz)
            table("X de fases [Ω/km] · misma restricción que L",x.x_ohm_per_km)
        except InputError as exc:
            st.info(f"Reactancia no calculada: {exc}")
    except InputError as exc:
        inductance_error = str(exc)
        st.info(f"Inductancia del haz no calculada: {exc}")
    render_bundle_math(geometry,inductance,cap)
    with st.expander("Bibliografía, ecuaciones y límites del modelo de haces"):
        st.markdown((Path(__file__).resolve().parents[1]/"referencias"/"haces.md").read_text(encoding="utf-8"))
    return {"geometry":geometry,"rmg_inputs":inputs if inductance is not None else None,
            "inductance_model":ind_model,"capacitance_model":cap_model,"inductance_error":inductance_error}


def scientific(value):
    mantissa,exponent = f"{value:.10e}".split("e")
    return rf"{mantissa}\times10^{{{int(exponent)}}}"


def render_bundle_math(geometry,inductance,cap):
    st.subheader("Desarrollo matemático de haces")
    st.latex(r"g_{\mathrm{haz}}=\left(\prod_{u=1}^n\prod_{v=1}^n d^{(g)}_{uv}\right)^{1/n^2},\ d^{(g)}_{uu}=g;\qquad r_{\mathrm{cap}}=\left(\prod_{u=1}^n\prod_{v=1}^n d^{(r)}_{uv}\right)^{1/n^2},\ d^{(r)}_{uu}=R")
    st.latex(r"D_{AB}=\left(\prod_{u\in A}\prod_{v\in B}D_{uv}\right)^{1/(n_A n_B)},\quad S_{AB}=\left(\prod_{u\in A}\prod_{v\in B}S_{uv}\right)^{1/(n_A n_B)}")
    st.caption("Fuentes: notas generales PDF 49–50, 76–78 y 92; clase 17-09-26 PDF 2–3. Para el polígono regular, la media completa se reduce al producto de una fila con exponente 1/n.")
    for phase,spec in enumerate(geometry.specs):
        indices = [i for i,p in enumerate(geometry.phase_index) if p == phase]
        distances = [geometry.real_distances_m[indices[0],i] for i in indices[1:]]
        factors = "".join(rf"\times({d:.9g}\,\mathrm{{m}})" for d in distances)
        st.latex(rf"r_{{\mathrm{{cap}},{PHASES[phase]}}}=\left[({spec.radius_m:.9g}\,\mathrm{{m}}){factors}\right]^{{1/{spec.count}}}={geometry.capacitive_radius_m[phase]:.12g}\,\mathrm{{m}}")
        if inductance is not None:
            st.latex(rf"g_{{\mathrm{{haz}},{PHASES[phase]}}}=\left[({inductance.individual_rmg_m[phase]:.12g}\,\mathrm{{m}}){factors}\right]^{{1/{spec.count}}}={inductance.equivalent_rmg_m[phase]:.12g}\,\mathrm{{m}}")
    st.latex(r"\mathbf I_{sub}=\mathbf T\mathbf I_{fase},\quad T_{up}=E_{up}/n_p,\quad\mathbf L_{fase}=\mathbf T^T\mathbf L_{sub}\mathbf T")
    if inductance is not None:
        st.caption("Valores sustituidos en metros; k = μ₀/(2π) = 2×10⁻⁷ H/m.")
        if inductance.ground_model == IDEAL_GROUND:
            i,j = st.selectbox("Elemento L del haz para desarrollar",[(i,j) for i in range(3) for j in range(3)],
                               format_func=lambda pair: PHASES[pair[0]]+PHASES[pair[1]],key="haz_l_pair")
            denominator = inductance.equivalent_rmg_m[i] if i==j else geometry.equivalent_distances_m[i,j]
            st.latex(rf"L_{{{PHASES[i]}{PHASES[j]}}}=({scientific(INDUCTANCE_FACTOR_H_PER_M)}\,\mathrm{{H/m}})\ln\!\left(\frac{{{geometry.equivalent_images_m[i,j]:.12g}\,\mathrm{{m}}}}{{{denominator:.12g}\,\mathrm{{m}}}}\right)={scientific(inductance.phase_h_per_m[i,j])}\,\mathrm{{H/m}}")
        else:
            st.latex(r"\mathbf H=\mathbf I_3-\mathbf1\mathbf1^T/3,\quad\mathbf L_{proj}=\mathbf H\mathbf L_{fase}\mathbf H,\quad\mathbf B=\begin{bmatrix}1&0\\0&1\\-1&-1\end{bmatrix},\quad\mathbf L_{lazos}=\mathbf B^T\mathbf L_{fase}\mathbf B")
            st.latex(rf"L^{{lazos}}_{{11}}=({scientific(INDUCTANCE_FACTOR_H_PER_M)}\,\mathrm{{H/m}})\ln\!\left(\frac{{({geometry.equivalent_distances_m[0,2]:.12g}\,\mathrm{{m}})^2}}{{({inductance.equivalent_rmg_m[0]:.12g}\,\mathrm{{m}})({inductance.equivalent_rmg_m[2]:.12g}\,\mathrm{{m}})}}\right)={scientific(inductance.loops_h_per_m[0,0])}\,\mathrm{{H/m}}")
    if cap is not None:
        i,j = st.selectbox("Coeficiente P de subconductores para desarrollar",[(i,j) for i in range(len(geometry.labels)) for j in range(len(geometry.labels))],
                           format_func=lambda pair: geometry.labels[pair[0]]+" / "+geometry.labels[pair[1]],key="haz_p_pair")
        denominator = geometry.radii_m[i] if i==j else geometry.real_distances_m[i,j]
        numerator = geometry.image_distances_m[i,j] if cap.ground_model==IDEAL_GROUND else 1.0
        if cap.ground_model == NO_GROUND:
            st.caption("P₀ auxiliar: la unidad de 1 m solo normaliza los logaritmos; la proyección de carga total cero elimina esa referencia. No representa un retorno físico.")
        st.latex(rf"P_{{{i+1},{j+1}}}=\ln\!\left(\frac{{{numerator:.12g}\,\mathrm{{m}}}}{{{denominator:.12g}\,\mathrm{{m}}}}\right)={cap.potential_coefficients[i,j]:.12g}")
        st.latex(rf"\mathbf C_{{fase}}=2\pi\,({scientific(VACUUM_PERMITTIVITY_F_PER_M)}\,\mathrm{{F/m}})\,\mathbf E^T\mathbf W")
        st.caption("La sustitución matricial usa P, E y la respuesta W = q_sub/(2πε₀), mostradas en Sistema primitivo y respuesta de cargas. C se muestra en F/m y convertida por 10¹² a nF/km.")
    st.latex(r"\mathbf P\mathbf W=\mathbf E,\quad\mathbf C_{fase}=2\pi\varepsilon_0\mathbf E^T\mathbf W\quad\text{(suelo ideal)}")
    st.latex(r"\mathbf1^T\mathbf Z=0,\quad\mathbf W=\mathbf Z(\mathbf Z^T\mathbf P_0\mathbf Z)^{-1}\mathbf Z^T\mathbf E\quad\text{(sin suelo, carga total cero)}")
    st.caption("P usa el radio exterior individual y distancias reales/imágenes, no el radio equivalente ni el RMG. La agregación equipotencial se deriva de las ecuaciones de potencial de Kersting §5.1–5.2; la hipótesis I/n para inductancia está explícita en las notas PDF 76. Desarrollo y supuestos completos en Bibliografía.")
