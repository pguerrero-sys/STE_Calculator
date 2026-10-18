"""Panel independiente de impedancia serie, sin alterar los modelos anteriores."""

import json
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from .carson import (CarsonConductor, calculate_carson, calculate_carson_layout,
                      convert_impedance, METHODS, MODIFIED, FT_M, G_SI_H_PER_M, kersting_example)
from .carson_report import carson_record, carson_pdf
from .bundles import BundleSpec
from .double_circuit import build_circuit_geometry
from .models import InputError, PHASES, finite_number
from .kron_ui import render_kron_inputs, render_kron_results

CENTERS = "Centros de Geometría · un conductor por fase"
BUNDLES = "Subconductores configurados en Haces"


def load_kersting_case():
    data = kersting_example()
    st.session_state.circuit_count = 1
    st.session_state.coordinates = {f"C1-{c.label}":(c.x_m,c.height_m) for c in data}
    st.session_state.editor_revision = st.session_state.get("editor_revision",0)+1
    st.session_state.capacitance_case_loaded = False
    st.session_state.example_mode = True
    st.session_state.car_f = 60.0
    st.session_state.car_rho = 100.0
    st.session_state.car_method = MODIFIED
    st.session_state.car_geometry_choice = CENTERS
    st.session_state.car_r_unit = "Ω/mile"
    st.session_state.car_source = data[0].source
    st.session_state.car_conditions = "Ejemplo bibliográfico a 60 Hz; no es ficha vigente del fabricante"
    for c in data:
        st.session_state[f"car_r_{c.label}"] = c.resistance_ac_ohm_per_km*1.609344
        st.session_state[f"car_gmr_{c.label}"] = c.gmr_m


def current_bundle_geometry(conductors,circuit_count,state):
    specs = []
    for c in conductors:
        label = c.phase+("'" if c.circuit==2 else "")
        prefix = "haz" if circuit_count==1 else "dc"
        specs.append(BundleSpec(c,state.get(f"{prefix}_n_{label}",1),state.get(f"{prefix}_r_{label}"),
                                state.get(f"{prefix}_s_{label}"),state.get(f"{prefix}_angle_{label}",0.0)))
    return build_circuit_geometry(specs)


def numeric_matrix(title,values,labels,fmt="{:.9f}"):
    st.write(title)
    st.dataframe(pd.DataFrame(values,index=labels,columns=labels).style.format(fmt),width="stretch")


def render_carson_panel(conductors,circuit_count,coordinate_error=""):
    st.divider()
    st.subheader("Impedancia serie · Carson · etapa 7A")
    st.caption("Módulo independiente: no reemplaza suelo ideal, inductancia ni capacitancia. Usa las coordenadas actuales de Geometría. Su frecuencia es propia de este cálculo. No elimina neutros/cables de guarda por Kron ni aplica la transposición de los otros paneles.")
    st.button("Cargar fases del ejemplo 4.1 de Kersting · sin Kron",on_click=load_kersting_case,
              help="Reemplaza las coordenadas comunes por las tres fases del ejemplo en metros y carga R_AC/RMG bibliográficos. No carga el neutro ni modifica los radios capacitivos o la frecuencia general.")
    if circuit_count not in (1,2):
        st.info(f"Carson admite uno o dos circuitos; Número de circuitos={circuit_count}.")
        return
    method = st.selectbox("Método de Carson",list(METHODS),format_func=METHODS.get,key="car_method")
    st.caption("Ambos métodos son aproximaciones. Las series completas y una comparación independiente con PSCAD están fuera de esta versión. Las discrepancias de la presentación se documentan en Bibliografía.")
    left,right = st.columns(2)
    frequency = left.number_input("Frecuencia Carson [Hz]",value=None,format="%.6f",key="car_f")
    rho = right.number_input("Resistividad del terreno Carson [Ω·m]",value=None,format="%.6f",key="car_rho")
    geometry_choice = st.radio("Geometría para Carson",[CENTERS,BUNDLES],key="car_geometry_choice")
    source = st.text_input("Fuente técnica de R_AC y RMG · Carson",key="car_source")
    conditions = st.text_input("Condiciones de R_AC/RMG · Carson",key="car_conditions",help="Frecuencia, temperatura y referencia de ensayo/ficha. No se calculan correcciones automáticas.")
    st.caption("Para ACSR usa R_AC y RMG de la ficha del fabricante. Este módulo no aplica R·exp(−1/4) ni usa RMG como radio capacitivo. Los datos bibliográficos de un ejemplo son solo una comprobación numérica.")
    r_unit = st.selectbox("Unidad de R_AC ingresada · Carson",["Ω/km","Ω/m","Ω/mile"],key="car_r_unit")
    labels = tuple(p+("'" if c==2 else "") for c in range(1,circuit_count+1) for p in PHASES)
    resistances,gmr = [],[]
    for p,col in zip(labels,st.columns(len(labels))):
        with col:
            resistances.append(st.number_input(f"R_AC individual {p} [{r_unit}] · Carson",value=None,format="%.9f",key=f"car_r_{p}"))
            gmr.append(st.number_input(f"RMG técnico individual {p} [m] · Carson",value=None,format="%.12f",key=f"car_gmr_{p}"))
    auxiliaries,kron_confirm,kron_error = render_kron_inputs()
    try:
        if conductors is None:
            raise InputError("Coordenadas de Geometría: "+coordinate_error)
        ordered = tuple(sorted(conductors,key=lambda c:(c.circuit,PHASES.index(c.phase))))
        if len(ordered)!=len(labels):
            raise InputError("Se requieren coordenadas completas de las tres o seis fases.")
        r_km = tuple(float(convert_impedance(finite_number(r,f"R_AC de {p} [{r_unit}]"),r_unit,"Ω/km").real)
                     for p,r in zip(labels,resistances))
        if geometry_choice==CENTERS:
            data = tuple(CarsonConductor(p,c.x_m,c.y_m,r,g,source,conditions=conditions)
                         for p,c,r,g in zip(labels,ordered,r_km,gmr))
            result = calculate_carson(data,frequency,rho,method)
        else:
            geometry = current_bundle_geometry(ordered,circuit_count,st.session_state.to_dict())
            result = calculate_carson_layout(geometry,r_km,gmr,(source,)*len(labels),frequency,rho,method,conditions)
    except InputError as exc:
        st.info(f"Carson no calculado: {exc}")
        return
    primitive = getattr(result,"primitive",result)
    output_labels = getattr(result,"phase_labels",primitive.labels)
    st.success("Carson calculado: matriz serie compleja sin reducción de Kron.")
    for warning in primitive.warnings:
        st.warning(warning)
    st.caption(f"k máximo = {primitive.k.max():.9g}. k>0.1 genera aviso y k≥1 se bloquea por una política preventiva de software; no es una garantía bibliográfica de precisión. No se comprueba exactitud frente a PSCAD.")
    if hasattr(result,"current_weights"):
        st.warning("Haces: I_sub=I_fase/n y Zfase=TᵀZsubT. Es una agregación por corrientes iguales; no es Kron ni una solución del reparto real de corrientes.")
    unit = st.selectbox("Unidad de impedancia Carson",["Ω/km","Ω/m"],key="car_z_unit")
    z = convert_impedance(result.z_ohm_per_m,"Ω/m",unit)
    st.subheader("Z serie = R + jX · Carson")
    complex_text = [[f"{v.real:.9f} {'+' if v.imag>=0 else '−'} j{abs(v.imag):.9f}" for v in row] for row in z]
    st.write(f"Z compleja [{unit}] · orden de fases explícito")
    st.dataframe(pd.DataFrame(complex_text,index=output_labels,columns=output_labels),width="stretch")
    numeric_matrix(f"R total [{unit}]",z.real,output_labels)
    numeric_matrix(f"X total [{unit}]",z.imag,output_labels)
    residual = float(np.max(np.abs(z-z.T)))
    st.caption(f"Simetría Z=Zᵀ: residuo {residual:.3e} {unit}. Ω/m→Ω/km: ×1000. La simetría no implica que Z sea hermítica.")
    with st.expander("Contribuciones del conductor, geometría y retorno por tierra",expanded=True):
        st.caption("Zbase=R_AC diagonal+jXgeom (referencia con imágenes ideales). ΔZtierra es la corrección para resistividad finita. La separación reactiva depende de esta referencia y no representa una inductancia intrínseca única de la tierra.")
        numeric_matrix(f"R_AC de conductores [{unit}]",convert_impedance(result.z_conductor_ohm_per_m,"Ω/m",unit).real,output_labels)
        numeric_matrix(f"X geométrica de referencia [{unit}]",convert_impedance(result.z_geometry_ohm_per_m,"Ω/m",unit).imag,output_labels)
        earth = convert_impedance(result.z_earth_ohm_per_m,"Ω/m",unit)
        numeric_matrix(f"ΔR por retorno de tierra [{unit}]",earth.real,output_labels)
        numeric_matrix(f"ΔX por retorno de tierra [{unit}]",earth.imag,output_labels)
        error = float(np.max(np.abs(result.z_ohm_per_m-result.z_conductor_ohm_per_m-result.z_geometry_ohm_per_m-result.z_earth_ohm_per_m)))
        st.caption(f"Residuo de suma de contribuciones: {error:.3e} Ω/m. La resistencia del suelo está en términos propios y mutuos.")
    with st.expander("Primitiva, distancias y P/Q de Carson"):
        numeric_matrix("D reales [m]",primitive.real_distances_m,primitive.labels)
        numeric_matrix("S imágenes [m]",primitive.image_distances_m,primitive.labels)
        numeric_matrix("k [adimensional]",primitive.k,primitive.labels)
        numeric_matrix("P Carson [adimensional]",primitive.p,primitive.labels)
        numeric_matrix("Q Carson [adimensional]",primitive.q,primitive.labels)
        numeric_matrix(f"R primitiva [{unit}]",convert_impedance(primitive.z_ohm_per_m,"Ω/m",unit).real,primitive.labels)
        numeric_matrix(f"X primitiva [{unit}]",convert_impedance(primitive.z_ohm_per_m,"Ω/m",unit).imag,primitive.labels)
    with st.expander("Vista geométrica utilizada por Carson"):
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=[c.x_m for c in primitive.conductors],y=[c.height_m for c in primitive.conductors],
                                mode="markers+text",text=primitive.labels,textposition="top center",name="Conductores reales"))
        fig.add_hline(y=0,line_color="#947455")
        fig.update_layout(template="plotly_white",xaxis_title="X [m]",yaxis_title="Altura [m]",yaxis={"scaleanchor":"x","scaleratio":1},height=430)
        st.plotly_chart(fig,width="stretch",config={"scrollZoom":True,"displaylogo":False})
    st.subheader("Procedimiento matemático · Carson")
    st.latex(r"\begin{aligned}D_{ij}&=\sqrt{(x_i-x_j)^2+(h_i-h_j)^2}\\S_{ij}&=\sqrt{(x_i-x_j)^2+(h_i+h_j)^2}\\d_{ii}&=RMG_i,\quad d_{ij}=D_{ij}\ (i\ne j)\end{aligned}")
    st.latex(r"\begin{aligned}g&=\mu_0/(4\pi)=10^{-7}\,\mathrm{H/m},\quad \omega=2\pi f\\Z_{ij}&=\delta_{ij}r_i+j2\omega g\ln(S_{ij}/d_{ij})\\&\quad+4\omega g(P_{ij}+jQ_{ij})\quad[\Omega/\mathrm m]\end{aligned}")
    st.latex(r"k_{ij}=8.565\times10^{-4}\frac{S_{ij}[\mathrm m]}{0.3048}\sqrt{\frac{f[\mathrm{Hz}]}{\rho[\Omega\mathrm m]}},\quad\cos\theta_{ij}=\frac{h_i+h_j}{S_{ij}}")
    if method==MODIFIED:
        st.latex(r"P=\pi/8,\quad 2Q=7.6786-\ln(S_{ft})+\tfrac12\ln(\rho/f)\quad\text{(Carson modificado)}")
        st.latex(r"Z_{ij}=\delta_{ij}r_i+\pi^2fg+j4\pi fg\left[\ln(0.3048/d_{ij}[\mathrm m])+7.6786+\tfrac12\ln(\rho/f)\right]")
        st.caption("La cancelación de S del total es una propiedad del truncamiento modificado, no de la solución completa. ln(ρ/f) usa los valores numéricos en las unidades indicadas por Kersting.")
    else:
        st.latex(r"\begin{aligned}P&=\frac\pi8-\frac{k\cos\theta}{3\sqrt2}\\&\quad+\frac{k^2\cos(2\theta)}{16}[0.6728+\ln(2/k)]\\Q&=-0.0386+\tfrac12\ln(2/k)+\frac{k\cos\theta}{3\sqrt2}\end{aligned}")
        st.caption("Expresiones finitas impresas en Kersting (4.23)-(4.24); no serie infinita completa. Se corrigen los términos discrepantes de la diapositiva 6.")
    i,j = st.selectbox("Elemento primitivo para desarrollar · Carson",[(i,j) for i in range(len(primitive.labels)) for j in range(len(primitive.labels))],
                       format_func=lambda pair:primitive.labels[pair[0]]+" / "+primitive.labels[pair[1]],key="car_pair")
    ci,cj = primitive.conductors[i],primitive.conductors[j]
    s = primitive.image_distances_m[i,j]
    d = ci.gmr_m if i==j else primitive.real_distances_m[i,j]
    st.latex(rf"D_{{ij}}=\sqrt{{({ci.x_m:.9g}-{cj.x_m:.9g})^2+({ci.height_m:.9g}-{cj.height_m:.9g})^2}}={primitive.real_distances_m[i,j]:.12g}\,\mathrm{{m}}")
    st.latex(rf"S_{{ij}}={s:.12g}\,\mathrm{{m}},\quad d_{{ij}}={d:.12g}\,\mathrm{{m}},\quad k_{{ij}}=(8.565\times10^{{-4}})({s/FT_M:.12g})\sqrt{{{frequency:.12g}/{rho:.12g}}}={primitive.k[i,j]:.12g}")
    st.latex(rf"P_{{ij}}={primitive.p[i,j]:.12g},\quad Q_{{ij}}={primitive.q[i,j]:.12g}")
    base_r = primitive.z_conductor_ohm_per_m[i,j].real
    xgeom = primitive.z_geometry_ohm_per_m[i,j].imag
    ze = primitive.z_earth_ohm_per_m[i,j]
    zv = primitive.z_ohm_per_m[i,j]
    st.latex(rf"\begin{{aligned}}Z_{{ij}}&=({base_r:.12g})+j({xgeom:.12g})\\&\quad+({ze.real:.12g}+j{ze.imag:.12g})\\&=({zv.real:.12g}+j{zv.imag:.12g})\,\Omega/\mathrm{{m}}\end{{aligned}}")
    st.latex(rf"Z_{{ij}}=({zv.real*1000:.12g}+j{zv.imag*1000:.12g})\,\Omega/\mathrm{{km}}")
    st.caption(f"R_AC={ci.resistance_ac_ohm_per_km:.12g} Ω/km; RMG={ci.gmr_m:.12g} m. Fuente: {ci.source}. Condiciones: {ci.conditions or 'sin especificar'}. El flujo interno ya está incluido en RMG.")
    st.info("Capacitancia: promediar C a potencial común difiere de invertir P media a carga común. Se conservan los resultados históricos del segundo procedimiento; no se validan como equivalente shunt universal ni se modifican con Carson.")
    record = carson_record(result)
    st.download_button("Descargar matrices y entradas Carson JSON",json.dumps(record,ensure_ascii=False,indent=2),"ste_carson.json","application/json")
    if st.checkbox("Preparar informe PDF Carson",key="car_pdf"):
        st.download_button("Descargar informe PDF Carson",carson_pdf(result),"ste_carson.pdf","application/pdf")
    with st.expander("Bibliografía, dominio de aplicación y advertencia sobre C/P"):
        st.markdown((Path(__file__).resolve().parents[1]/"referencias"/"carson.md").read_text(encoding="utf-8"))
    render_kron_results(result,auxiliaries,kron_confirm,kron_error)
