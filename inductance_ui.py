"""Sección Streamlit independiente para inductancia. Cálculos en inductance.py."""

from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from .inductance import (
    IDEAL_GROUND, NO_GROUND, SOLID_UNIFORM, MANUFACTURER, RMGInput,
    INDUCTANCE_FACTOR_H_PER_M, MU0_H_PER_M, calculate_inductance,
    calculate_reactance, convert_inductance, balanced_flux_linkages,
    balanced_trial_currents, inductive_voltage_drop,
)
from .models import InputError, PHASES

MODELS = ["Seleccionar modelo", "Circular macizo (μr = 1, corriente uniforme)", "RMG conocido del fabricante"]
GROUND_OPTIONS = ["Suelo ideal por imágenes", "Sin efecto suelo · corrientes de suma cero"]


def load_inductance_case():
    """Callback previo al rerun; conserva los radios y opciones de capacitancia."""
    st.session_state.circuit_count = 1
    st.session_state.coordinates = {"C1-A": (-3.0, 13.0), "C1-B": (3.0, 13.0), "C1-C": (0.0, 9.0)}
    for phase in PHASES:
        st.session_state[f"ind_radius_{phase}"] = .011765
    st.session_state.ind_model = MODELS[1]
    st.session_state.ind_ground = GROUND_OPTIONS[0]
    st.session_state.ind_confirm_solid = True
    st.session_state.ind_case_loaded = True
    st.session_state.example_mode = True
    st.session_state.capacitance_case_loaded = False
    st.session_state.editor_revision = st.session_state.get("editor_revision", 0) + 1


def show_matrix(title, values, labels=PHASES, fmt="{:.9e}"):
    st.write(title)
    st.dataframe(pd.DataFrame(values, index=labels, columns=labels).style.format(fmt), width="stretch")


def sci(value):
    mantissa, exponent = f"{value:.10e}".split("e")
    return rf"{mantissa}\times10^{{{int(exponent)}}}"


def complex_text(value):
    return f"{value.real:.6e} {value.imag:+.6e}j"


def inductance_figure(result):
    figure = go.Figure()
    colors = ["#D45141", "#087F8C", "#6854B5"]
    for index, (phase, color, conductor) in enumerate(zip(PHASES, colors, result.conductors)):
        figure.add_trace(go.Scatter(x=[conductor.x_m], y=[conductor.y_m], mode="markers+text",
            text=[phase], textposition="top center", name=phase,
            marker={"size": 14, "color": color}, hovertemplate=f"{phase}<br>X=%{{x}} m<br>Y=%{{y}} m<extra></extra>"))
        if result.ground_model == IDEAL_GROUND:
            figure.add_trace(go.Scatter(x=[result.image_positions_m[index, 0]], y=[result.image_positions_m[index, 1]], mode="markers+text",
                text=[f"{phase}′ (−I{phase})"], textposition="bottom center", name=f"Imagen {phase}",
                marker={"size": 12, "symbol": "x", "color": color}))
    xs = [c.x_m for c in result.conductors]
    heights = [c.y_m for c in result.conductors]
    padding = max(max(xs) - min(xs), max(heights), 1) * .15
    left, right = min(xs) - padding, max(xs) + padding
    figure.add_trace(go.Scatter(x=[left, right], y=[0, 0], mode="lines",
        name="Suelo ideal" if result.ground_model == IDEAL_GROUND else "Y=0 (solo referencia geométrica)",
        line={"color": "#947455", "width": 2}))
    bottom = -max(heights) - padding if result.ground_model == IDEAL_GROUND else -padding
    figure.update_layout(template="plotly_white", height=520, margin={"t": 25, "b": 25},
        xaxis={"title": "X [m]", "range": [left, right]},
        yaxis={"title": "Y [m]", "range": [bottom, max(heights) + padding], "scaleanchor": "x", "scaleratio": 1},
        legend={"orientation": "h"}, dragmode="pan")
    return figure


def render_inductance_tab(conductors, circuit_count, frequency_hz, coordinate_error=""):
    st.subheader("Inductancia de una línea trifásica aérea")
    st.caption("Las coordenadas y la frecuencia se comparten con Configuración y Geometría. Los radios, RMG y elección de suelo de esta sección son independientes de capacitancia.")
    st.button("Cargar caso obligatorio de inductancia", on_click=load_inductance_case,
              help="Reemplaza la geometría compartida y las entradas inductivas. Conserva radios capacitivos, frecuencia y longitud.")
    if st.session_state.get("ind_case_loaded", False):
        st.info("Se cargó el caso de verificación del usuario. Los resultados usan las entradas actuales, incluidas las ediciones posteriores; no certifican un diseño eléctrico.")
    model = st.selectbox("Modelo del conductor (inductancia)", MODELS, key="ind_model")
    confirmation = False
    if model == MODELS[1]:
        confirmation = st.checkbox("Confirmo conductor circular macizo, no magnético y corriente uniforme", key="ind_confirm_solid")
        st.caption("RMG = R·exp(−1/4) solo bajo estas hipótesis. No se aplica automáticamente a ACSR trenzado.")
    source = ""
    if model == MODELS[2]:
        source = st.text_input("Fuente del RMG del fabricante", key="ind_rmg_source", placeholder="Catálogo, fabricante, página y condiciones del dato")
    columns = st.columns(3)
    radii, manufacturer_rmg = [], []
    for phase, col in zip(PHASES, columns):
        with col:
            radii.append(st.number_input(f"Radio exterior inductivo {phase} [m]", value=None, format="%.12f", key=f"ind_radius_{phase}"))
            manufacturer_rmg.append(st.number_input(f"RMG fabricante {phase} [m]", value=None, format="%.12f", key=f"ind_manufacturer_{phase}") if model == MODELS[2] else None)
    ground_option = st.radio("Modelo de suelo (inductancia)", GROUND_OPTIONS, key="ind_ground")
    ground_model = IDEAL_GROUND if ground_option == GROUND_OPTIONS[0] else NO_GROUND
    if ground_model == NO_GROUND:
        st.warning("Restricción: I_A + I_B + I_C = 0. La matriz proyectada representa el subespacio de suma cero; no es una matriz absoluta para cualquier corriente ni describe secuencia cero. No necesitas introducir una distancia de referencia.")
    st.caption(f"μ₀ = {MU0_H_PER_M:.12g} H/m, constante del modelo solicitada; μ₀/(2π) = 2×10⁻⁷ H/m. Sin Carson, retorno de resistividad finita, transposición, haces ni doble circuito.")
    try:
        if circuit_count != 1:
            raise InputError("Inductancia disponible solo para un circuito A/B/C; los circuitos múltiples conservan únicamente la geometría.")
        if model == MODELS[0]:
            raise InputError("Selecciona un modelo de RMG para comenzar.")
        if model == MODELS[1] and not confirmation:
            raise InputError("Confirma las hipótesis del conductor macizo antes de usar R·exp(−1/4), o utiliza un RMG documentado del fabricante.")
        if conductors is None:
            raise InputError(coordinate_error or "Completa las coordenadas de las fases en Geometría.")
        method = SOLID_UNIFORM if model == MODELS[1] else MANUFACTURER
        parameters = tuple(RMGInput(radius, method, known, source) for radius, known in zip(radii, manufacturer_rmg))
        # El módulo verificado ya obtiene ambas reducciones desde la forma
        # canónica, sin usar d0. 1 m solo normaliza los logaritmos internos de
        # su API de bajo nivel; L_ref no se presenta como resultado principal.
        result = calculate_inductance(conductors, parameters, ground_model,
                                      1.0 if ground_model == NO_GROUND else None)
    except InputError as exc:
        st.info(f"Inductancia no calculada: {exc}")
        return

    st.success("Inductancia calculada con las entradas actuales.")
    st.plotly_chart(inductance_figure(result), width="stretch", config={"scrollZoom": True, "displaylogo": False})
    st.caption("Escala igual en ambos ejes; marcadores simbólicos, sin representar el radio real. Las imágenes tienen corrientes opuestas y solo intervienen en el modo de suelo ideal.")
    st.dataframe(pd.DataFrame({"Fase": PHASES, "Radio exterior [m]": result.radii_m, "RMG usado [m]": result.rmg_m}),
                 hide_index=True, column_config={name: st.column_config.NumberColumn(name, format="%.12f") for name in ["Radio exterior [m]", "RMG usado [m]"]})
    with st.expander("Distancias propias, mutuas e imágenes", expanded=False):
        show_matrix("D: distancias entre centros reales [m]; diagonal cero, no usada en ln", result.real_distances_m, fmt="{:.9f}")
        if result.image_distances_m is not None:
            show_matrix("S: conductor real i a imagen j [m]; Sii = 2hi", result.image_distances_m, fmt="{:.9f}")
        st.caption("La distancia propia efectiva en el logaritmo inductivo es el RMG; no se sustituye por el radio capacitivo.")

    title = "Matriz L con suelo ideal" if ground_model == IDEAL_GROUND else "Matriz proyectada · corrientes de suma cero"
    st.subheader(title)
    applicable_matrix = result.l_h_per_m if ground_model == IDEAL_GROUND else result.balanced_l_h_per_m
    for unit, col in zip(["H/m", "µH/m", "mH/km"], st.columns(3)):
        with col:
            show_matrix(f"L {'proyectada ' if ground_model == NO_GROUND else ''}[{unit}]", convert_inductance(applicable_matrix, "H/m", unit), fmt="{:.9e}" if unit == "H/m" else "{:.8f}")
    st.caption("1 H/m = 10⁶ µH/m = 10⁶ mH/km: µH/m y mH/km tienen el mismo valor numérico.")
    if ground_model == NO_GROUND:
        st.caption("Representación 3×3 de media cero y rango 2. No se invierte ni se usa para corrientes con suma no nula.")
        st.subheader("Matriz de inductancias de lazos A−C / B−C")
        for unit, col in zip(["H/m", "µH/m", "mH/km"], st.columns(3)):
            with col:
                show_matrix(f"L de lazos [{unit}]", convert_inductance(result.loop_l_h_per_m, "H/m", unit), labels=("A−C", "B−C"), fmt="{:.9e}" if unit == "H/m" else "{:.8f}")
        st.caption("Corrientes independientes IA e IB, con IC = −IA − IB. La salida corresponde a λA−λC y λB−λC; la matriz depende de esta base de lazos, no de una referencia arbitraria.")
    st.caption(f"Condición de la matriz en el espacio aplicable: {result.condition_number:.6g} (L completa con suelo; L de lazos sin suelo).")

    st.subheader("Reactancia a la frecuencia ingresada")
    reactance = None
    try:
        reactance = calculate_reactance(applicable_matrix, frequency_hz)
        for values, unit, col in zip([reactance.x_ohm_per_m, reactance.x_ohm_per_km], ["Ω/m", "Ω/km"], st.columns(2)):
            with col:
                show_matrix(f"X {'equilibrada' if ground_model == NO_GROUND else ''} [{unit}]", values)
        if ground_model == NO_GROUND:
            x_loops = calculate_reactance(result.loop_l_h_per_m, frequency_hz)
            show_matrix("X de lazos A−C / B−C [Ω/km]", x_loops.x_ohm_per_km, labels=("A−C", "B−C"))
        st.latex(rf"\mathbf X=2\pi f\mathbf L=2\pi\times{reactance.frequency_hz:.9g}\,\mathrm{{Hz}}\times\mathbf L\,[\mathrm{{H/m}}]\quad[\Omega/\mathrm{{m}}]")
        st.caption("X es la matriz real de reactancia por unidad de longitud. La impedancia inductiva es jX. No se calcula resistencia ni reactancia total de la línea. Fuente: solución de ejercicio PDF 3–4.")
    except InputError as exc:
        st.info(f"Reactancia no calculada: {exc}. L y RMG siguen disponibles.")

    render_flux(result, reactance)
    if ground_model == IDEAL_GROUND:
        render_math(result)
    else:
        render_balanced_math(result)
        with st.expander("Avanzado · deducción con distancia de referencia", expanded=False):
            st.caption("Exploración opcional de L_ref. Ningún valor ni error de esta opción condiciona las matrices principales, enlaces proyectados o reactancias.")
            if st.checkbox("Mostrar deducción con referencia d₀", key="ind_show_reference"):
                reference = st.number_input("Distancia de referencia d₀ [m]", value=None, format="%.9g", key="ind_reference")
                try:
                    advanced = calculate_inductance(conductors, parameters, NO_GROUND, reference)
                    st.subheader("L_ref(d₀): coeficientes referidos, NO matriz absoluta única")
                    show_matrix("L_ref [H/m] · solo para la deducción", advanced.l_h_per_m)
                    render_math(advanced)
                except InputError as exc:
                    st.info(f"Deducción avanzada no disponible: {exc}. Los resultados principales siguen disponibles.")
    with st.expander("Fuentes, condiciones de aplicación y correcciones detectadas"):
        record = Path(__file__).resolve().parents[1] / "referencias" / "inductancia.md"
        st.markdown(record.read_text(encoding="utf-8"))


def render_flux(result, reactance):
    st.subheader("Enlaces de flujo · ensayo trifásico equilibrado ABC")
    st.caption("Ensayo explícito, no una corriente deducida de un proyecto: I = I₀[1, exp(−j2π/3), exp(j2π/3)] A. Corrientes de suma cero; fasores expresados con la misma convención de amplitud que I₀.")
    amplitude = st.number_input("Amplitud del ensayo equilibrado [A]", value=1.0, min_value=0.0, format="%.6f", key="ind_trial_amplitude")
    try:
        currents = balanced_trial_currents(amplitude)
        flux = balanced_flux_linkages(result, currents)
    except InputError as exc:
        st.info(str(exc))
        return
    rows = []
    for i, phase in enumerate(PHASES):
        if result.ground_model == NO_GROUND:
            rows.append({"Fase": phase, "I [A]": complex_text(currents[i]),
                         "λ proyectada, media cero [Wb·vuelta/m]": complex_text(flux.zero_mean_flux_wb_turn_per_m[i])})
            continue
        own = flux.own_flux_wb_turn_per_m[i]
        mutual = flux.mutual_flux_wb_turn_per_m[i]
        rows.append({"Fase": phase, "I [A]": complex_text(currents[i]), "λ propia [Wb·vuelta/m]": complex_text(own),
                     "Σ λ mutuas [Wb·vuelta/m]": complex_text(mutual), "λ suma [Wb·vuelta/m]": complex_text(flux.flux_wb_turn_per_m[i])})
    st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
    st.dataframe(pd.DataFrame({"Lazo": ["A−C", "B−C"], "Diferencia de enlaces [Wb·vuelta/m]": [complex_text(v) for v in flux.loop_flux_wb_turn_per_m]}), hide_index=True)
    if reactance is not None:
        # La caída diferencial se obtiene de los enlaces físicos de lazos.
        try:
            voltage = inductive_voltage_drop(flux.loop_flux_wb_turn_per_m, reactance.frequency_hz)
            st.dataframe(pd.DataFrame({"Lazo": ["A−C", "B−C"], "Diferencia de caída inductiva [V/m]": [complex_text(v) for v in voltage]}), hide_index=True)
        except InputError as exc:
            st.info(str(exc))
    if result.ground_model == NO_GROUND:
        st.caption("λ proyectada = L proyectada I, con IA + IB + IC = 0. Se muestran enlaces de media cero y diferencias de lazos, sin elegir una referencia física. No se fuerza una inductancia escalar igual para fases de geometría asimétrica.")
    else:
        st.caption("λ_i = Σ_j Lij Ij. Propios y mutuos por separado dependen de la referencia sin suelo; su suma para corrientes equilibradas y las diferencias de enlaces no dependen de d₀. No se aplica transposición ni se fuerza una inductancia escalar igual para todas las fases de una geometría asimétrica.")


def render_balanced_math(result):
    st.subheader("Desarrollo matemático · resultados de suma cero")
    render_rmg_math(result)
    st.latex(r"I_A+I_B+I_C=0,\quad\mathbf B=\begin{bmatrix}1&0\\0&1\\-1&-1\end{bmatrix},\quad\mathbf I=\mathbf B\begin{bmatrix}I_A\\I_B\end{bmatrix}")
    st.latex(r"\mathbf L_{\mathrm{lazos}}=\frac{\mu_0}{2\pi}\begin{bmatrix}\ln\!\frac{D_{AC}^2}{g_Ag_C}&\ln\!\frac{D_{AC}D_{BC}}{D_{AB}g_C}\\\ln\!\frac{D_{AC}D_{BC}}{D_{AB}g_C}&\ln\!\frac{D_{BC}^2}{g_Bg_C}\end{bmatrix},\quad g_i=\mathrm{RMG}_i")
    st.latex(r"\mathbf T=\mathbf B(\mathbf B^T\mathbf B)^{-1}=\frac13\begin{bmatrix}2&-1\\-1&2\\-1&-1\end{bmatrix},\quad\mathbf L_{\mathrm{proyectada}}=\mathbf T\mathbf L_{\mathrm{lazos}}\mathbf T^T")
    st.caption("Derivación algebraica de los enlaces de flujo del apunte 08-09-26, PDF 1–4, y notas generales PDF 43–45. Los cocientes de estas fórmulas son adimensionales y no contienen una distancia de referencia. La proyección es de media cero y rango 2.")
    dac, dbc, dab = result.real_distances_m[0,2], result.real_distances_m[1,2], result.real_distances_m[0,1]
    ga, gb, gc = result.rmg_m
    for row, col, numerator, denominator in [
        (0,0,rf"({dac:.12g}\,\mathrm{{m}})^2",rf"({ga:.12g}\,\mathrm{{m}})({gc:.12g}\,\mathrm{{m}})"),
        (1,1,rf"({dbc:.12g}\,\mathrm{{m}})^2",rf"({gb:.12g}\,\mathrm{{m}})({gc:.12g}\,\mathrm{{m}})"),
        (0,1,rf"({dac:.12g}\,\mathrm{{m}})({dbc:.12g}\,\mathrm{{m}})",rf"({dab:.12g}\,\mathrm{{m}})({gc:.12g}\,\mathrm{{m}})"),
    ]:
        st.latex(rf"L^{{\mathrm{{lazos}}}}_{{{row+1}{col+1}}}=({sci(INDUCTANCE_FACTOR_H_PER_M)}\,\mathrm{{H/m}})\ln\!\left(\frac{{{numerator}}}{{{denominator}}}\right)={sci(result.loop_l_h_per_m[row,col])}\,\mathrm{{H/m}}")
    st.caption("La deducción original con coeficientes propios y mutuos referidos puede consultarse en la opción avanzada. No se incorpora retorno físico ni secuencia cero.")


def render_rmg_math(result):
    st.write("RMG por fase · notas generales PDF 37–39; alternativa: dato documentado del fabricante")
    for phase, data, radius, rmg in zip(PHASES, result.rmg_inputs, result.radii_m, result.rmg_m):
        if data.method == SOLID_UNIFORM:
            st.latex(rf"\mathrm{{RMG}}_{{{phase}}}=R_{{{phase}}}e^{{-1/4}}=({radius:.12g}\,\mathrm{{m}})e^{{-1/4}}={rmg:.12g}\,\mathrm{{m}}")
        else:
            st.latex(rf"\mathrm{{RMG}}_{{{phase}}}={rmg:.12g}\,\mathrm{{m}}\quad\text{{(dato del fabricante, sin recalcular)}}")
            st.text(f"Fuente {phase}: {data.source}")


def render_math(result):
    st.subheader("Desarrollo matemático de inductancia")
    render_rmg_math(result)
    if result.ground_model == IDEAL_GROUND:
        st.latex(r"L_{ii}=\frac{\mu_0}{2\pi}\ln\!\left(\frac{2h_i}{\mathrm{RMG}_i}\right),\quad L_{ij}=\frac{\mu_0}{2\pi}\ln\!\left(\frac{S_{ij}}{D_{ij}}\right)\ (i\ne j)")
        st.caption("Fuentes: clase 08-09-26, PDF 7–10; notas generales PDF 46–48. RMG incorpora el flujo interno; no se suma de nuevo una inductancia interna.")
    else:
        st.latex(r"K_{ii}=\ln(d_0/\mathrm{RMG}_i),\quad K_{ij}=\ln(d_0/D_{ij}),\quad\mathbf L_{\mathrm{ref}}=\frac{\mu_0}{2\pi}\mathbf K")
        st.latex(r"\mathbf L_{\mathrm{ref}}(a d_0)-\mathbf L_{\mathrm{ref}}(d_0)=\frac{\mu_0}{2\pi}\ln(a)\,\mathbf1\mathbf1^T,\quad\mathbf1^T\mathbf I=0")
        st.latex(r"\lambda_i=\frac{\mu_0}{2\pi}\left[I_i\ln\!\left(\frac{d_0}{\mathrm{RMG}_i}\right)+\sum_{j\ne i}I_j\ln\!\left(\frac{d_0}{D_{ij}}\right)\right]")
        st.caption("Fuente del desarrollo equilibrado: clase 08-09-26, PDF 1–4; notas generales PDF 43–45; Kersting (4.1)–(4.4). El término de referencia se anula al multiplicar por corrientes de suma cero.")
    show_matrix("Coeficientes logarítmicos K [adimensionales]", result.logarithmic_coefficients, fmt="{:.10f}")
    i, j = st.selectbox("Elemento inductivo para desarrollar", [(i,j) for i in range(3) for j in range(3)],
                        format_func=lambda pair: f"L{PHASES[pair[0]]}{PHASES[pair[1]]}", key="ind_math_pair")
    first, second = result.conductors[i], result.conductors[j]
    if i != j:
        st.latex(rf"D_{{{i+1}{j+1}}}=\sqrt{{({first.x_m:.9g}-({second.x_m:.9g}))^2+({first.y_m:.9g}-({second.y_m:.9g}))^2}}\,\mathrm{{m}}={result.real_distances_m[i,j]:.10g}\,\mathrm{{m}}")
    if result.ground_model == IDEAL_GROUND:
        st.latex(rf"S_{{{i+1}{j+1}}}=\sqrt{{({first.x_m:.9g}-({second.x_m:.9g}))^2+({first.y_m:.9g}+({second.y_m:.9g}))^2}}\,\mathrm{{m}}={result.image_distances_m[i,j]:.10g}\,\mathrm{{m}}")
        numerator = result.image_distances_m[i,j]
    else:
        numerator = result.reference_distance_m
    denominator = result.rmg_m[i] if i == j else result.real_distances_m[i,j]
    value = result.l_h_per_m[i,j]
    st.latex(rf"L_{{{i+1}{j+1}}}=({sci(INDUCTANCE_FACTOR_H_PER_M)}\,\mathrm{{H/m}})\ln\!\left(\frac{{{numerator:.12g}\,\mathrm{{m}}}}{{{denominator:.12g}\,\mathrm{{m}}}}\right)={sci(value)}\,\mathrm{{H/m}}")
    converted = float(convert_inductance(value, "H/m", "mH/km"))
    st.latex(rf"L_{{{i+1}{j+1}}}\,[\mathrm{{\mu H/m}}]=L_{{{i+1}{j+1}}}\,[\mathrm{{mH/km}}]=({sci(value)})\times10^6={converted:.8f}")
    st.caption("Argumentos de ln adimensionales. Sustituciones redondeadas solo al mostrar. En el modo sin suelo, este elemento pertenece a L_ref(d₀), no a una matriz absoluta única.")
