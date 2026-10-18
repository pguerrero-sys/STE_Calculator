"""Presentación Streamlit de capacitancias; las operaciones están en capacitance.py."""

import pandas as pd
import streamlit as st

from .capacitance import CapacitanceResult


def matrix_table(values, labels, fmt):
    st.dataframe(pd.DataFrame(values, index=labels, columns=labels).style.format(fmt), width="stretch")


def scientific_latex(value: float, digits: int = 9) -> str:
    mantissa, exponent = f"{value:.{digits}e}".split("e")
    return rf"{mantissa}\times10^{{{int(exponent)}}}"


def render_capacitance_results(result: CapacitanceResult | None, message: str) -> None:
    st.divider()
    st.subheader("Capacitancia · suelo ideal por imágenes")
    if result is None:
        st.info(f"Capacitancia no calculada: {message}")
        return
    if st.session_state.get("example_mode", False):
        st.warning("Datos ilustrativos o de verificación del usuario; los resultados no constituyen un diseño eléctrico validado.")
    st.caption("Orden de filas y columnas: A, B, C. Un circuito, un conductor circular por fase; sin transposición ni haces.")
    st.write("Matriz geométrica P [adimensional]")
    matrix_table(result.p, result.labels, "{:.9f}")
    left, right = st.columns(2)
    with left:
        st.write("Matriz C [F/m]")
        matrix_table(result.c_f_per_m, result.labels, "{:.9e}")
    with right:
        st.write("Matriz C [nF/km]")
        matrix_table(result.c_nf_per_km, result.labels, "{:.6f}")
    st.caption("Matriz de Maxwell: q = C V, con V respecto del suelo y q en C/m. Los términos mutuos negativos son coeficientes de la matriz; no son un error de signo.")
    with st.expander("Distancias reales e imágenes [m]", expanded=False):
        st.write("D: distancias entre centros reales; diagonal cero, excluida del logaritmo mutuo")
        matrix_table(result.real_distances_m, result.labels, "{:.9f}")
        st.write("S: conductor i a imagen j; Sii = 2hi")
        matrix_table(result.image_distances_m, result.labels, "{:.9f}")
    with st.expander("Comprobación P × C = 2πε₀ I", expanded=True):
        st.write("Producto P × C [F/m], usando C en F/m")
        matrix_table(result.identity_product_f_per_m, result.labels, "{:.9e}")
        st.write("Objetivo 2πε₀ I [F/m]")
        matrix_table(result.identity_target_f_per_m, result.labels, "{:.9e}")
        st.success(f"Identidad comprobada · máximo residuo normalizado: {result.normalized_residual:.3e}")
        st.caption(f"Residuo = max|PC/(2πε₀) − I|; tolerancia 1e-10. Condición de P: {result.condition_number:.6g}. La comprobación verifica la inversión, no certifica el modelo físico.")
    st.caption("Fuentes: Notas de sistemas de transmision, PDF 94–96; Kersting (2002), §5.2, pp. 111–113, ecuaciones (5.6)–(5.10) y (5.14). Detalles y supuestos en Bibliografía.")


def render_capacitance_math(result: CapacitanceResult | None, message: str) -> None:
    st.divider()
    st.subheader("Capacitancia por el método de las imágenes")
    st.latex(r"j'=(x_j,-h_j),\quad D_{ij}=\sqrt{(x_i-x_j)^2+(h_i-h_j)^2},\quad S_{ij}=\sqrt{(x_i-x_j)^2+(h_i+h_j)^2}")
    st.latex(r"P_{ii}=\ln\!\left(\frac{2h_i}{r_i}\right),\quad P_{ij}=\ln\!\left(\frac{S_{ij}}{D_{ij}}\right)\ (i\ne j)")
    st.latex(r"\mathbf V=\frac{1}{2\pi\varepsilon_0}\mathbf P\mathbf q,\quad \mathbf C=2\pi\varepsilon_0\mathbf P^{-1},\quad \mathbf P\mathbf C=2\pi\varepsilon_0\mathbf I")
    st.latex(r"1\,\frac{\mathrm F}{\mathrm m}\times10^9\,\frac{\mathrm{nF}}{\mathrm F}\times1000\,\frac{\mathrm m}{\mathrm{km}}=10^{12}\,\frac{\mathrm{nF}}{\mathrm{km}}")
    st.caption("P es adimensional. Radios, alturas y distancias se ingresan en m. Se usa radio exterior, no GMR inductivo. ln es logaritmo natural.")
    if result is None:
        st.info(f"Sustituciones de capacitancia pendientes: {message}")
        return
    i, j = st.selectbox("Elemento de P y C para desarrollar", [(i, j) for i in range(3) for j in range(3)],
                        format_func=lambda pair: f"{result.labels[pair[0]]}{result.labels[pair[1]]}")
    first, second = result.conductors[i], result.conductors[j]
    st.latex(rf"S_{{{i+1}{j+1}}}=\sqrt{{({first.x_m:.9g}-({second.x_m:.9g}))^2+({first.y_m:.9g}+({second.y_m:.9g}))^2}}\,\mathrm{{m}}={result.image_distances_m[i,j]:.9g}\,\mathrm{{m}}")
    if i == j:
        st.latex(rf"P_{{{i+1}{i+1}}}=\ln\!\left(\frac{{2\times{first.y_m:.9g}\,\mathrm{{m}}}}{{{result.radii_m[i]:.9g}\,\mathrm{{m}}}}\right)={result.p[i,i]:.9g}")
    else:
        st.latex(rf"D_{{{i+1}{j+1}}}=\sqrt{{({first.x_m:.9g}-({second.x_m:.9g}))^2+({first.y_m:.9g}-({second.y_m:.9g}))^2}}\,\mathrm{{m}}={result.real_distances_m[i,j]:.9g}\,\mathrm{{m}}")
        st.latex(rf"P_{{{i+1}{j+1}}}=\ln\!\left(\frac{{{result.image_distances_m[i,j]:.9g}\,\mathrm{{m}}}}{{{result.real_distances_m[i,j]:.9g}\,\mathrm{{m}}}}\right)={result.p[i,j]:.9g}")
    st.write("Inversa completa de P [adimensional] (Cij usa un elemento de la inversa matricial, no 1/Pij):")
    matrix_table(result.p_inverse, result.labels, "{:.9f}")
    st.latex(rf"C_{{{i+1}{j+1}}}=2\pi\times({scientific_latex(result.epsilon0_f_per_m, 10)}\,\mathrm{{F/m}})\times({result.p_inverse[i,j]:.9g})={scientific_latex(result.c_f_per_m[i,j])}\,\mathrm{{F/m}}")
    st.latex(rf"C_{{{i+1}{j+1}}}=({scientific_latex(result.c_f_per_m[i,j])})\times10^{{12}}={result.c_nf_per_km[i,j]:.6f}\,\mathrm{{nF/km}}")
    st.caption("Las sustituciones se redondean para mostrar; el cálculo usa los valores completos. Fuente: notas PDF 95–96; Kersting §5.2. Se conserva la cifra de ε₀ indicada por el usuario.")
