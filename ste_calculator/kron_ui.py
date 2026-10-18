"""Controles de auxiliares; no establece automáticamente sus conexiones."""

import json
from pathlib import Path
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from .carson import CarsonConductor, kersting_example, convert_impedance
from .kron import (AuxiliaryConductor, CONNECTIONS, ZERO_DROP, UNKNOWN,
                   augment_carson, reduce_augmented)
from .kron_report import kron_record, kron_pdf
from .models import InputError, finite_number
from .sequences_ui import render_sequences


def load_full_kersting_case():
    from .carson_ui import load_kersting_case
    load_kersting_case()
    c = kersting_example(True)[-1]
    st.session_state.kron_count = 1
    for key,value in {"label":c.label,"role":"neutral","x":c.x_m,"h":c.height_m,
                      "gmr":c.gmr_m,"r":c.resistance_ac_ohm_per_km,"source":c.source,
                      "connection":ZERO_DROP,
                      "basis":"Kersting §4.1.6 p.87 y ejemplo 4.1 pp.92-94: neutro multitierra ideal"}.items():
        st.session_state[f"kron_0_{key}"] = value
    # Cargar un ejemplo no confirma las condiciones de una instalación del usuario.
    st.session_state.kron_confirm = False


def load_two_guard_case():
    from .carson_ui import load_kersting_case
    from .sequence_examples import two_guard_case
    count = st.session_state.get("circuit_count",1)
    count = count if count in (1,2) else 1
    case = two_guard_case(count)
    phases = case.primitive.conductors[:3*count]
    load_kersting_case()
    st.session_state.circuit_count = count
    st.session_state.coordinates = {f"C{1 if i<3 else 2}-{c.label.rstrip(chr(39))}":(c.x_m,c.height_m)
                                    for i,c in enumerate(phases)}
    st.session_state.car_r_unit = "Ω/km"
    st.session_state.car_conditions = "Ensayo algebraico, geometría sintética; datos eléctricos de fases del ejemplo 4.1"
    for c in phases:
        st.session_state[f"car_r_{c.label}"] = c.resistance_ac_ohm_per_km
        st.session_state[f"car_gmr_{c.label}"] = c.gmr_m
    st.session_state.kron_count = 2
    for i,a in enumerate(case.auxiliaries):
        c = a.conductor
        for key,value in {"label":c.label,"role":"guard","x":c.x_m,"h":c.height_m,
                          "gmr":c.gmr_m,"r":c.resistance_ac_ohm_per_km,
                          "source":c.source+"; R/RMG del neutro reutilizados para ensayo de dos guardas",
                          "connection":ZERO_DROP,"basis":a.justification}.items():
            st.session_state[f"kron_{i}_{key}"] = value
    st.session_state.kron_confirm = False


def render_kron_inputs():
    st.subheader("Neutros y cables de guarda · Kron · etapa 7B")
    st.button("Cargar ejemplo 4.1 completo de Kersting · con neutro",on_click=load_full_kersting_case,
              help="Carga coordenadas, R_AC y RMG del libro. Revisa y declara la hipótesis ΔVn=0 para reducir.")
    st.button("Cargar ensayo algebraico · dos guardas",on_click=load_two_guard_case,
              help="Conserva uno o dos circuitos. Usa geometría sintética y reutiliza R/RMG del neutro del libro para verificar álgebra; no es una selección comercial de guardas. Requiere declarar ΔVn=0.")
    count = st.number_input("Número de conductores auxiliares · Kron",min_value=0,max_value=12,
                            value=0,step=1,key="kron_count")
    if count == 0:
        st.caption("Agrega auxiliares o carga el ejemplo completo. Carson conserva su cálculo de fases sin reducción.")
        return (),False,""
    st.info("La primitiva incluye todos los auxiliares. Kron requiere ΔVn=0 en cada auxiliar eliminado. Aislados o conexiones desconocidas bloquean la reducción, sin ocultar la primitiva.")
    auxiliaries = []
    error = ""
    for i in range(count):
        prefix = f"kron_{i}_"
        with st.expander(f"Conductor auxiliar {i+1}",expanded=True):
            cols = st.columns(2)
            label = cols[0].text_input(f"Etiqueta auxiliar {i+1}",value=f"N{i+1}",key=prefix+"label")
            role = cols[1].selectbox(f"Tipo auxiliar {i+1}",["neutral","guard"],
                                     format_func=lambda v:"Neutro" if v=="neutral" else "Cable de guarda",key=prefix+"role")
            x = cols[0].number_input(f"X auxiliar {i+1} [m]",value=None,key=prefix+"x",format="%.9f")
            h = cols[1].number_input(f"Altura auxiliar {i+1} [m]",value=None,key=prefix+"h",format="%.9f")
            r = cols[0].number_input(f"R_AC auxiliar {i+1} [Ω/km]",value=None,key=prefix+"r",format="%.12f")
            gmr = cols[1].number_input(f"RMG auxiliar {i+1} [m]",value=None,key=prefix+"gmr",format="%.12f")
            source = st.text_input(f"Fuente técnica auxiliar {i+1}",key=prefix+"source")
            connection = st.selectbox(f"Conexión auxiliar {i+1}",list(CONNECTIONS),format_func=CONNECTIONS.get,key=prefix+"connection")
            basis = st.text_input(f"Justificación eléctrica auxiliar {i+1}",key=prefix+"basis")
            try:
                values = [finite_number(v,f"{name} del auxiliar {i+1}")
                          for v,name in ((x,"X"),(h,"Altura"),(r,"R_AC [Ω/km]"),(gmr,"RMG [m]"))]
                auxiliaries.append(AuxiliaryConductor(CarsonConductor(label,*values[:2],values[2],values[3],source),
                                                      role,connection,basis))
            except InputError as exc:
                error = error or str(exc)
    confirmed = st.checkbox("Declaro ΔVn = 0 en todos los auxiliares eliminados",key="kron_confirm",
                            help="Hipótesis multitierra ideal del modelo. No representa electrodos con impedancia finita ni guardas aisladas.")
    return tuple(auxiliaries),confirmed,error


def matrix(title,z,rows,columns=None):
    st.write(title)
    st.dataframe(pd.DataFrame(z,index=rows,columns=rows if columns is None else columns).style.format("{:.9f}"),width="stretch")


def render_kron_results(phase_result,auxiliaries,confirmed,error):
    if error:
        st.warning("Primitiva con auxiliares no calculada: "+error)
        return
    if not auxiliaries:
        return
    st.divider()
    st.subheader("Primitiva completa y reducción de Kron")
    try:
        augmented = augment_carson(phase_result,auxiliaries)
    except InputError as exc:
        st.error("Primitiva con auxiliares no calculada: "+str(exc))
        return
    for warning in augmented.primitive.warnings:
        st.warning("Primitiva con auxiliares: "+warning)
    reduced = None
    try:
        reduced = reduce_augmented(augmented,confirmed=confirmed)
    except InputError as exc:
        st.warning("Kron no aplicado: "+str(exc))
    unit = st.selectbox("Unidad de impedancia Kron",["Ω/km","Ω/m","Ω/mile"],key="kron_z_unit")
    scale = lambda z:convert_impedance(z,"Ω/m",unit)
    labels = augmented.labels
    aux_labels = tuple(a.conductor.label for a in auxiliaries)
    st.caption("Orden conservado: "+", ".join(augmented.phase_labels)+". Auxiliares: "+", ".join(aux_labels)+". No hay reducción de dos circuitos a tres fases ni transposición automática.")
    for title,z,rows,cols in [("Zterminal antes de Kron",augmented.z_ohm_per_m,labels,labels),
                              ("Zpp",augmented.blocks.pp,augmented.phase_labels,augmented.phase_labels),
                              ("Zpn",augmented.blocks.pn,augmented.phase_labels,aux_labels),
                              ("Znp",augmented.blocks.np,aux_labels,augmented.phase_labels),
                              ("Znn",augmented.blocks.nn,aux_labels,aux_labels)]:
        matrix(f"{title} · R [{unit}]",scale(z).real,rows,cols)
        matrix(f"{title} · X [{unit}]",scale(z).imag,rows,cols)
    if reduced is not None:
        st.success(f"Kron calculado: {len(augmented.phase_labels)} fases conservadas; ΔVn=0 declarado.")
        z = scale(reduced.z_ohm_per_m)
        matrix(f"Zreducida · R [{unit}]",z.real,augmented.phase_labels)
        matrix(f"Zreducida · X [{unit}]",z.imag,augmented.phase_labels)
        st.caption(f"cond(Znn)={reduced.condition_number:.6g}; residuo normalizado={reduced.solve_residual:.3e}; simetría: {np.max(np.abs(z-z.T)):.3e} {unit}.")
        render_sequences(augmented,reduced,unit)
    with st.expander("Primitiva de subconductores, geometría y contribuciones · Kron"):
        p = augmented.primitive
        matrix(f"Zsub completa · R [{unit}]",scale(p.z_ohm_per_m).real,p.labels)
        matrix(f"Zsub completa · X [{unit}]",scale(p.z_ohm_per_m).imag,p.labels)
        matrix(f"R_AC primitiva [{unit}]",scale(p.z_conductor_ohm_per_m).real,p.labels)
        matrix(f"X geométrica de referencia [{unit}]",scale(p.z_geometry_ohm_per_m).imag,p.labels)
        matrix(f"ΔR tierra primitiva [{unit}]",scale(p.z_earth_ohm_per_m).real,p.labels)
        matrix(f"ΔX tierra primitiva [{unit}]",scale(p.z_earth_ohm_per_m).imag,p.labels)
        fig = go.Figure(go.Scatter(x=[c.x_m for c in p.conductors],y=[c.height_m for c in p.conductors],
                                  mode="markers+text",text=p.labels,textposition="top center",name="Fases y auxiliares"))
        fig.add_hline(y=0,line_color="#947455")
        fig.update_layout(template="plotly_white",xaxis_title="X [m]",yaxis_title="Altura [m]",yaxis={"scaleanchor":"x"},height=440)
        st.plotly_chart(fig,width="stretch",key="kron_geometry")
    st.subheader("Desarrollo matemático · Kron")
    st.latex(r"\begin{aligned}\Delta V_p/\ell&=Z_{pp}I_p+Z_{pn}I_n\\\Delta V_n/\ell&=Z_{np}I_p+Z_{nn}I_n\end{aligned}")
    st.latex(r"\begin{aligned}\Delta V_n=0&\Rightarrow I_n=-Z_{nn}^{-1}Z_{np}I_p\\Z_{\mathrm{reducida}}&=Z_{pp}-Z_{pn}Z_{nn}^{-1}Z_{np}\end{aligned}")
    st.caption("Kersting (2002), pp.86-87, (4.45)-(4.54), adaptadas por unidad de longitud: ℓ es la longitud del tramo uniforme. Z está en una única unidad Ω/longitud. In/Ip es adimensional. Ω/m→Ω/km: ×1000; Ω/m→Ω/milla: ×1609.344. Se resuelve Znn Y=Znp sin formar la inversa.")
    if reduced is not None:
        corr = scale(reduced.correction_ohm_per_m)
        pp = scale(augmented.blocks.pp)
        st.code(f"Elemento (1,1), {unit}:\nZpn @ solve(Znn,Znp) = {corr[0,0]:.9g}\nZred = ({pp[0,0]:.9g}) - ({corr[0,0]:.9g})\n     = {scale(reduced.z_ohm_per_m)[0,0]:.9g}",language="text")
        matrix("In por Ip · parte real [adimensional]",reduced.auxiliary_current_response.real,aux_labels,augmented.phase_labels)
        matrix("In por Ip · parte imaginaria [adimensional]",reduced.auxiliary_current_response.imag,aux_labels,augmented.phase_labels)
    st.info("Si In=0 (auxiliar aislado), las fases usan Zpp bajo esa condición, no Zreducida. Electrodos finitos o conexión en un solo extremo requieren otro modelo de frontera. No se altera capacitancia ni inductancia ideal.")
    st.download_button("Descargar matrices y entradas Kron JSON",json.dumps(kron_record(augmented,reduced),ensure_ascii=False,indent=2),"ste_kron.json","application/json")
    if st.checkbox("Preparar informe PDF Kron",key="kron_pdf"):
        st.download_button("Descargar informe PDF Kron",kron_pdf(augmented,reduced),"ste_kron.pdf","application/pdf")
    with st.expander("Bibliografía y condiciones de Kron"):
        st.markdown((Path(__file__).resolve().parents[1]/"referencias"/"kron.md").read_text(encoding="utf-8"))
