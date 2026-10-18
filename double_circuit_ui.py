"""Panel de doble circuito; los cálculos permanecen fuera de Streamlit."""

from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from .bundles import BundleSpec
from .models import PHASES, InputError
from .inductance import RMGInput, SOLID_UNIFORM, MANUFACTURER, resolve_rmg, IDEAL_GROUND, NO_GROUND
from .double_circuit import (LABELS, calculate_double_circuit,
                             reactance_six, reproducible_specs)
from .printing import double_circuit_pdf
from .transposition_schedule import MODES, migrate_mode

TRANS_MODES = list(MODES)
MATERIALS = ["Seleccionar modelo", "Macizo no magnético uniforme", "ACSR/trenzado · RMG del fabricante"]


def load_double_case():
    specs = reproducible_specs()
    st.session_state.circuit_count = 2
    st.session_state.coordinates = {s.center.label:(s.center.x_m,s.center.y_m) for s in specs}
    st.session_state.editor_revision = st.session_state.get("editor_revision",0)+1
    st.session_state.example_mode = True
    for label in LABELS:
        for name,value in (("n",1),("r",.011765),("s",.4572),("angle",0.0)):
            st.session_state[f"dc_{name}_{label}"] = value
    st.session_state.dc_material = MATERIALS[1]
    st.session_state.dc_confirm = True
    st.session_state.dc_ind_ground = "Suelo ideal"
    st.session_state.dc_cap_ground = "Suelo ideal"
    st.session_state.dc_trans_mode = TRANS_MODES[0]


def matrix(title,values,labels=LABELS,columns=None,fmt="{:.6f}"):
    st.write(title)
    st.dataframe(pd.DataFrame(values,index=labels,columns=columns or labels).style.format(fmt),width="stretch")


def geometry_figure(geometry,images=False):
    fig = go.Figure()
    for phase,label in enumerate(LABELS):
        ids = np.where(geometry.phase_index==phase)[0]
        points = geometry.positions_m[ids]
        color = ["#cb4038","#007e87","#7057ad"][phase%3]
        fig.add_trace(go.Scatter(x=points[:,0],y=points[:,1],mode="markers+text",text=[geometry.labels[i] for i in ids],
                                name=label,textposition="top center",marker={"color":color,"size":10,"symbol":"circle" if phase<3 else "diamond"}))
        for i in ids:
            x,y = geometry.positions_m[i]
            r = geometry.radii_m[i]
            fig.add_shape(type="circle",x0=x-r,x1=x+r,y0=y-r,y1=y+r,line={"color":color})
        if images:
            fig.add_trace(go.Scatter(x=points[:,0],y=-points[:,1],mode="markers",name=f"Imagen {label}",
                                    marker={"color":color,"symbol":"x","size":8},opacity=.55))
    x = geometry.positions_m[:,0]
    fig.add_trace(go.Scatter(x=[float(x.min()-2),float(x.max()+2)],y=[0,0],mode="lines",name="Terreno Y=0",line={"color":"#947455"}))
    fig.update_layout(template="plotly_white",height=500,xaxis_title="X [m]",yaxis_title="Y [m]",
                      yaxis={"scaleanchor":"x","scaleratio":1},legend={"orientation":"h"},dragmode="pan")
    return fig


def render_double_circuit_panel(conductors,circuit_count,frequency_hz,coordinate_error=""):
    st.divider()
    st.subheader("Doble circuito · etapa 6")
    st.button("Cargar caso reproducible de doble circuito",on_click=load_double_case)
    st.caption("Seis terminales independientes A/B/C/A'/B'/C'. Centros editables en Geometría: circuito 1 y circuito 2. Los controles de este panel son independientes de Haces de circuito sencillo.")
    if circuit_count != 2:
        st.info(f"Doble circuito: Número de circuitos={circuit_count}; selecciona 2 en Configuración o carga el caso reproducible. Los módulos anteriores de un circuito se conservan.")
        return
    ordered = sorted(conductors,key=lambda c:(c.circuit,PHASES.index(c.phase))) if conductors is not None else None
    specs = []
    for index,label in enumerate(LABELS):
        with st.expander(f"Conductor y haz de {label}",expanded=True):
            c1,c2,c3 = st.columns(3)
            count = int(c1.number_input(f"Subconductores {label} · doble",1,4,1,key=f"dc_n_{label}"))
            radius = c2.number_input(f"Radio exterior {label} · doble [m]",value=None,format="%.9f",key=f"dc_r_{label}")
            spacing = c3.number_input(f"Separación {label} · doble [m]",value=None,format="%.6f",disabled=count==1,key=f"dc_s_{label}")
            angle = st.number_input(f"Rotación {label} · doble [°]",value=0.0,disabled=count==1,key=f"dc_angle_{label}")
            if ordered is not None and len(ordered)==6:
                center = ordered[index]
                st.caption(f"Posición física P{index+1}: ({center.x_m:g}, {center.y_m:g}) m; edítala en Geometría.")
                specs.append(BundleSpec(center,count,radius,spacing,angle))
    material = st.selectbox("Modelo de conductor · doble circuito",MATERIALS,key="dc_material")
    confirmed,source = False,""
    known = [None]*6
    if material == MATERIALS[1]:
        confirmed = st.checkbox("Confirmo macizo no magnético uniforme · doble circuito",key="dc_confirm")
    elif material == MATERIALS[2]:
        source = st.text_input("Fuente técnica del RMG · doble circuito",key="dc_rmg_source")
        for i,label in enumerate(LABELS):
            known[i] = st.number_input(f"RMG fabricante {label} · doble [m]",value=None,format="%.12f",key=f"dc_rmg_{label}")
    ind_choice = st.selectbox("Suelo para L · doble circuito",["Suelo ideal","Sin suelo · suma global cero"],key="dc_ind_ground")
    cap_choice = st.selectbox("Suelo para C · doble circuito",["Suelo ideal","Sin suelo · carga global cero"],key="dc_cap_ground")
    ind_model = IDEAL_GROUND if ind_choice=="Suelo ideal" else NO_GROUND
    cap_model = IDEAL_GROUND if cap_choice=="Suelo ideal" else NO_GROUND
    current_mode=st.session_state.get('dc_trans_mode')
    if current_mode not in TRANS_MODES:
        st.session_state.dc_trans_mode=migrate_mode(current_mode)
    mode = st.radio("Transposición de doble circuito",TRANS_MODES,key="dc_trans_mode")
    complete=mode==TRANS_MODES[1]
    st.caption('Plan automático: nueve combinaciones independientes de los ciclos de ambos circuitos, peso interno 1/9 por tramo; sin transposición, un tramo de peso 1. Las fases conservan sus haces completos. El motor eléctrico admite uno o dos circuitos; el generador de planes es extensible.')
    if ordered is None or len(specs)!=6:
        st.error("Doble circuito no calculado: "+(coordinate_error or "Geometría no entregó las seis posiciones completas."))
        return
    inputs,ind_error = None,""
    try:
        if material == MATERIALS[0] or (material==MATERIALS[1] and not confirmed):
            raise InputError("Selecciona y confirma el modelo macizo o ingresa un RMG de fabricante documentado.")
        method = SOLID_UNIFORM if material==MATERIALS[1] else MANUFACTURER
        data = []
        for label,spec,rmg in zip(LABELS,specs,known):
            item = RMGInput(spec.radius_m,method,rmg,source)
            try:
                resolve_rmg(item)
            except InputError as exc:
                raise InputError(f"Fase {label}: {exc}") from exc
            data.append(item)
        inputs = tuple(data)
    except InputError as exc:
        ind_error = str(exc)
    try:
        result = calculate_double_circuit(tuple(specs),inputs,inductance_model=ind_model,
                                         capacitance_model=cap_model,complete=complete)
    except InputError as exc:
        st.error(f"Doble circuito no calculado: {exc}")
        return
    st.success("Doble circuito calculado: seis terminales con acoplamiento entre circuitos.")
    st.warning("Caso y modelo ideal, sin validación de diseño. No hay conexión en paralelo ni equivalente automático 3×3. L presupone corriente I_fase/n por subconductor.")
    if ind_model==NO_GROUND:
        st.warning("Sin suelo para L: IA+IB+IC+IA'+IB'+IC'=0. La matriz principal es una proyección de rango 5; no es una matriz absoluta para cualquier corriente.")
    if cap_model==NO_GROUND:
        st.warning("Sin suelo para C: Σq de las seis fases=0, rango 5 y potencial común indeterminado. No se impone neutralidad separada de cada circuito.")
    st.caption('Tabla de tramos de solo lectura. Los decimales mostrados no intervienen en el cálculo: las fracciones se normalizan internamente.')
    st.dataframe(pd.DataFrame([{"Tramo":i+1,"Fracción L":w,"Fracción exacta":f"1/{len(result.sections)}",**{label:f"P{pos+1}" for label,pos in zip(LABELS,row)}}
                               for i,(row,w) in enumerate(zip(result.assignments,result.weights))]),hide_index=True,width="stretch")
    if st.session_state.get('dc_view_section',0) not in range(len(result.sections)):
        st.session_state.dc_view_section=0
    section_index = st.selectbox("Tramo para visualizar · doble circuito",range(len(result.sections)),format_func=lambda i:f"Tramo {i+1}",key="dc_view_section")
    section = result.sections[section_index]
    g = section.geometry
    show_images = st.checkbox("Mostrar imágenes · doble circuito",key="dc_show_images")
    st.plotly_chart(geometry_figure(g,show_images),width="stretch",config={"scrollZoom":True,"displaylogo":False})
    st.dataframe(pd.DataFrame({"Subconductor":g.labels,"X [m]":g.positions_m[:,0],"Y [m]":g.positions_m[:,1],"Radio [m]":g.radii_m}),hide_index=True,width="stretch")
    st.subheader("Matrices principales · seis fases independientes")
    if result.l_h_per_m is not None:
        unit = st.selectbox("Unidad L · doble circuito",["mH/km","µH/m","H/m"],key="dc_l_unit")
        factor = 1 if unit=="H/m" else 1e6
        matrix(f"L6 promedio {'proyectada' if ind_model==NO_GROUND else 'primitiva de terminales'} [{unit}]",result.l_h_per_m*factor,fmt="{:.9e}" if factor==1 else "{:.6f}")
        try:
            matrix("X6 [Ω/km]",reactance_six(result.l_h_per_m,frequency_hz))
        except InputError as exc:
            st.info(f"Reactancia no calculada: {exc}. L y C siguen disponibles.")
        st.dataframe(pd.DataFrame({"Fase":LABELS,"Radio [m]":[s.radius_m for s in g.specs],"RMG individual [m]":section.rmg_m}),hide_index=True)
        if ind_model==NO_GROUND:
            with st.expander("Condición adicional: equilibrio independiente de cada circuito"):
                st.write("IA+IB+IC=0 e IA'+IB'+IC'=0. Cuatro corrientes de lazo independientes, sin unir terminales.")
                matrix("L6 proyectada por circuito [mH/km]",result.l_circuit_balanced_h_per_m*1e6)
                matrix("L de cuatro lazos [mH/km]",result.l_loops_h_per_m*1e6,("A-C","B-C","A'-C'","B'-C'"))
    else:
        st.info("Inductancia de doble circuito no calculada: "+ind_error)
    matrix("P efectiva promedio de seis fases [adimensional]",result.average_phase_p,fmt="{:.9f}")
    matrix("C6 [F/m]",result.c_f_per_m,fmt="{:.9e}")
    matrix("C6 [nF/km]",result.c_f_per_m*1e12)
    st.caption("Con varios tramos se conserva el modelo didáctico a carga de fase común: promedio P antes de invertir. A potencial común corresponde promediar C. No son equivalentes universales de una línea distribuida; revisión en referencias/carson.md.")
    st.caption(f"Pprom C/(2πε₀) = {'I6' if cap_model==IDEAL_GROUND else 'H6'}; residuo {result.inversion_residual:.3e}. Se promedia P efectiva por tramos antes de invertir.")
    with st.expander("Bloques por circuito y acoplamientos, sin reducción"):
        st.latex(r"\lambda_1=L_{11}I_1+L_{12}I_2,\quad\lambda_2=L_{21}I_1+L_{22}I_2,\quad q_1=C_{11}V_1+C_{12}V_2")
        st.caption("Bloques diagonales del operador completo, no circuitos aislados. Con suelo, C11 corresponde a V2=0; no a un circuito 2 flotante.")
        for name,values in (("L",result.l_h_per_m),("C",result.c_f_per_m)):
            if values is None:
                continue
            for i in range(2):
                for j in range(2):
                    matrix(f"Bloque {name}{i+1}{j+1} [{'H/m' if name=='L' else 'F/m'}]",values[3*i:3*i+3,3*j:3*j+3],LABELS[3*i:3*i+3],LABELS[3*j:3*j+3],fmt="{:.9e}")
    with st.expander("Matrices intermedias de todos los tramos"):
        for i,s in enumerate(result.sections,1):
            st.write(f"Tramo {i}, fracción {result.weights[i-1]:.9g}")
            matrix(f"P efectiva tramo {i}",s.effective_phase_p,fmt="{:.9f}")
            matrix(f"C6 tramo {i} [nF/km]",s.c_f_per_m*1e12)
            if s.l_h_per_m is not None:
                matrix(f"L6 tramo {i} [mH/km]",s.l_h_per_m*1e6)
    with st.expander("Primitivas de subconductores y distancias del tramo seleccionado"):
        st.caption("N×N de subconductores y 6×6 de terminales son niveles distintos. Sin suelo, las primitivas logarítmicas son auxiliares referidas a 1 m.")
        matrix("D reales [m]",g.real_distances_m,g.labels,fmt="{:.6f}")
        matrix("S imágenes [m]",g.image_distances_m,g.labels,fmt="{:.6f}")
        matrix("Psub [adimensional]",section.potential_sub,g.labels,fmt="{:.9f}")
        matrix("E: pertenencia equipotencial [adimensional]",g.incidence,g.labels,LABELS,fmt="{:.0f}")
        matrix("T: reparto de corriente [adimensional]",g.current_weights,g.labels,LABELS,fmt="{:.9f}")
        matrix("qsub por voltio de fase [F/m]",section.charge_response_f_per_m,g.labels,LABELS,fmt="{:.9e}")
        if section.l_sub_h_per_m is not None:
            matrix("Lsub [H/m]",section.l_sub_h_per_m,g.labels,fmt="{:.9e}")
        st.caption(f"Residuo equipotencial {section.equipotential_residual:.3e}; neutralidad {section.neutrality_residual:.3e}.")
    st.subheader("Desarrollo matemático · doble circuito")
    st.latex(r"D_{uv}=\sqrt{(x_u-x_v)^2+(h_u-h_v)^2},\quad S_{uv}=\sqrt{(x_u-x_v)^2+(h_u+h_v)^2}")
    st.latex(r"L_{sub,uu}=\frac{\mu_0}{2\pi}\ln\frac{2h_u}{RMG_u},\quad L_{sub,uv}=\frac{\mu_0}{2\pi}\ln\frac{S_{uv}}{D_{uv}},\quad L_6=T^T L_{sub}T\quad\text{(suelo ideal)}")
    st.latex(r"P_{sub,uu}=\ln\frac{2h_u}{R_u},\quad P_{sub,uv}=\ln\frac{S_{uv}}{D_{uv}},\quad C_6=2\pi\varepsilon_0 E^T P_{sub}^{-1}E\quad\text{(suelo ideal)}")
    st.latex(r"\overline L=\sum_t w_t L_t,\quad P_{fase,t}=(C_t/(2\pi\varepsilon_0))^{-1},\quad\overline P=\sum_t w_t P_{fase,t},\quad C=2\pi\varepsilon_0\overline P^{-1}\quad\text{(suelo ideal)}")
    st.latex(r"H_6=I_6-11^T/6,\quad L_{proj}=H_6 L_{0,fase}H_6,\quad C_6=2\pi\varepsilon_0 E^T Z(Z^T P_0 Z)^{-1}Z^T E\quad\text{(sin suelo)}")
    st.latex(r"P_{fase,t}=Q[Q^T(C_t/(2\pi\varepsilon_0))Q]^{-1}Q^T,\quad C=2\pi\varepsilon_0 Q(Q^T\overline P Q)^{-1}Q^T,\quad Q^T1=0\quad\text{(sin suelo)}")
    u,v = st.selectbox("Par de subconductores para desarrollar · doble",[(i,j) for i in range(len(g.labels)) for j in range(len(g.labels))],
                       format_func=lambda pair:g.labels[pair[0]]+" / "+g.labels[pair[1]],key="dc_pair")
    xu,hu = g.positions_m[u]
    xv,hv = g.positions_m[v]
    st.latex(rf"D=\sqrt{{({xu:.9g}-{xv:.9g})^2+({hu:.9g}-{hv:.9g})^2}}={g.real_distances_m[u,v]:.12g}\,\mathrm{{m}}")
    st.latex(rf"S=\sqrt{{({xu:.9g}-{xv:.9g})^2+({hu:.9g}+{hv:.9g})^2}}={g.image_distances_m[u,v]:.12g}\,\mathrm{{m}}")
    denominator = g.radii_m[u] if u==v else g.real_distances_m[u,v]
    numerator = g.image_distances_m[u,v] if cap_model==IDEAL_GROUND else 1.0
    st.latex(rf"P_{{{u+1},{v+1}}}=\ln\frac{{{numerator:.12g}\,\mathrm{{m}}}}{{{denominator:.12g}\,\mathrm{{m}}}}={section.potential_sub[u,v]:.12g}")
    if section.rmg_m is not None:
        pu = g.phase_index[u]
        if material==MATERIALS[1]:
            st.latex(rf"RMG=({g.specs[pu].radius_m:.12g}\,\mathrm{{m}})e^{{-1/4}}={section.rmg_m[pu]:.12g}\,\mathrm{{m}}")
        else:
            st.write(f"RMG individual usado sin recalcular: {section.rmg_m[pu]:.12g} m. Fuente: {source}")
        d = section.rmg_m[pu] if u==v else g.real_distances_m[u,v]
        s = g.image_distances_m[u,v] if ind_model==IDEAL_GROUND else 1.0
        st.latex(rf"L_{{sub,{u+1},{v+1}}}=(2\times10^{{-7}}\,\mathrm{{H/m}})\ln\frac{{{s:.12g}\,\mathrm{{m}}}}{{{d:.12g}\,\mathrm{{m}}}}={section.l_sub_h_per_m[u,v]:.12g}\,\mathrm{{H/m}}")
    st.caption("Logaritmos adimensionales. Sin suelo el numerador 1 m solo normaliza la primitiva auxiliar. H/m→µH/m o mH/km: ×10⁶; F/m→nF/km: ×10¹². X=2πfL. Fuentes y condiciones completas a continuación.")
    i,j = st.selectbox("Elemento de fase para desarrollar · doble",[(i,j) for i in range(6) for j in range(6)],
                       format_func=lambda pair:LABELS[pair[0]]+" / "+LABELS[pair[1]],key="dc_phase_pair")
    indices_i,indices_j = np.where(g.phase_index==i)[0],np.where(g.phase_index==j)[0]
    terms = "+".join(f"({section.charge_response_f_per_m[u,j]:.12g})" for u in indices_i)
    st.latex(rf"C_{{fase,{i+1},{j+1}}}={terms}={section.c_f_per_m[i,j]:.12g}\,\mathrm{{F/m}}")
    if section.l_sub_h_per_m is not None:
        terms = "+".join(f"({section.l_sub_h_per_m[u,v]:.12g})" for u in indices_i for v in indices_j)
        raw_value = np.mean(section.l_sub_h_per_m[np.ix_(indices_i,indices_j)])
        st.latex(rf"(T^T L_{{sub}} T)_{{{i+1},{j+1}}}=\frac{{{terms}}}{{{len(indices_i)*len(indices_j)}}}={raw_value:.12g}\,\mathrm{{H/m}}")
        if ind_model==NO_GROUND:
            st.caption("El valor agregado anterior es auxiliar; el resultado principal aplica H6 a ambos lados y exige suma global de corrientes cero.")
    terms = "+".join(f"({w:.9g})({s.effective_phase_p[i,j]:.12g})" for w,s in zip(result.weights,result.sections))
    st.latex(rf"\overline P_{{{i+1},{j+1}}}={terms}={result.average_phase_p[i,j]:.12g}")
    if st.checkbox("Preparar informe PDF de doble circuito",key="dc_pdf"):
        data = double_circuit_pdf(result,frequency_hz)
        st.download_button("Descargar informe PDF · doble circuito",data,"ste_doble_circuito.pdf","application/pdf")
        st.caption("PDF A4 horizontal: matrices anchas divididas en bloques de seis columnas, filas completas y encabezados repetidos. No imprime los canvas de tablas del navegador.")
    with st.expander("Fuentes, conexiones y limitaciones de doble circuito"):
        st.markdown((Path(__file__).resolve().parents[1]/"referencias"/"doble_circuito.md").read_text(encoding="utf-8"))
