"""Vista de las secuencias completas de la impedancia reducida de Carson."""

from pathlib import Path
import numpy as np
import pandas as pd
import streamlit as st
from .sequences import phase_to_sequence
from .carson import convert_impedance
from .kron_validation import validate_two_guards


def render_sequences(augmented,reduced,unit):
    result = phase_to_sequence(reduced.z_ohm_per_m,augmented.phase_labels)
    z = convert_impedance(result.z_ohm_per_m,"Ω/m",unit)
    st.subheader("Componentes simétricas · etapa 7C")
    st.caption("Impedancia reducida de Carson/Kron. Orden 0: cero, 1: positiva, 2: negativa. Convención fasorial exp(jωt), fases ABC. No modifica suelo ideal ni capacitancia.")
    st.latex(r"a=e^{j2\pi/3}=-\frac12+j\frac{\sqrt3}{2}")
    st.latex(r"A=\begin{bmatrix}1&1&1\\1&a^2&a\\1&a&a^2\end{bmatrix},\quad A^{-1}=\frac13\begin{bmatrix}1&1&1\\1&a&a^2\\1&a^2&a\end{bmatrix}")
    st.latex(r"\begin{aligned}V_{abc}&=AV_{012},\quad I_{abc}=AI_{012}\\Z_{012}&=A^{-1}Z_{abc}A\end{aligned}")
    if len(result.labels)==6:
        st.latex(r"B=\operatorname{diag}(A,A),\quad Z_s=B^{-1}Z_{\mathrm{fase},6}B")
        st.info("Doble circuito: orden 0 C1, 1 C1, 2 C1, 0 C2, 1 C2, 2 C2. La matriz 6×6 conserva los acoplamientos entre circuitos; no es un equivalente de un solo circuito.")
    st.write(f"Z012 compleja completa [{unit}]")
    texts = [[f"{v.real:.9f} {'+' if v.imag>=0 else '−'} j{abs(v.imag):.9f}" for v in row] for row in z]
    st.dataframe(pd.DataFrame(texts,index=result.labels,columns=result.labels),width="stretch",
                 column_config={label:st.column_config.TextColumn(width="medium") for label in result.labels})
    for name,values in (("R",z.real),("X",z.imag)):
        st.write(f"Z012 · {name} [{unit}]")
        st.dataframe(pd.DataFrame(values,index=result.labels,columns=result.labels),width="stretch",
                     column_config={label:st.column_config.NumberColumn(width="small",format="%.9f") for label in result.labels})
    st.write(f"Términos diagonales Z0, Z1 y Z2 [{unit}] · conservando acoplamientos")
    st.dataframe(pd.DataFrame({"Secuencia":result.labels,"R":z.diagonal().real,"X":z.diagonal().imag}),hide_index=True,width="stretch")
    st.warning("Los términos fuera de la diagonal no se fuerzan a cero. La igualdad Z1=Z2 no demuestra transposición. Z012 no tiene por qué ser simétrica ni hermítica; las redes de secuencia pueden estar acopladas.")
    st.caption(f"Residuo relativo al reconstruir Zfase: {result.reconstruction_residual:.3e}. Fuente: Kersting §4.1.7, pp.89-91, (4.59)-(4.67); ejemplo 4.1 pp.94-95. Unidades conservadas: Ω/m→Ω/km ×1000 y Ω/m→Ω/milla ×1609.344.")
    if len(augmented.auxiliaries)==2 and all(a.role=="guard" for a in augmented.auxiliaries):
        validation = validate_two_guards(augmented,reduced)
        st.subheader("Contraste independiente · dos cables de guarda")
        st.caption("Se imponen Ip=I y ΔVn=0 en un sistema completo resuelto con SciPy; se obtiene ΔVp por multiplicación de la primitiva. No utiliza el complemento de Schur del programa. Es una comprobación algebraica, no una validación de la puesta a tierra física.")
        if validation.relative_error<1e-10 and validation.boundary_residual<1e-10:
            st.success(f"Dos guardas: contraste independiente correcto; error relativo={validation.relative_error:.3e}.")
        else:
            st.error(f"Discrepancia en el contraste independiente: error relativo={validation.relative_error:.3e}; residuo de frontera={validation.boundary_residual:.3e}.")
        with st.expander("Matrices independientes de dos guardas"):
            reference = convert_impedance(validation.independent_z_ohm_per_m,"Ω/m",unit)
            for name,values in (("R",reference.real),("X",reference.imag)):
                st.write(f"Z independiente · {name} [{unit}]")
                st.dataframe(pd.DataFrame(values,index=augmented.phase_labels,columns=augmented.phase_labels),width="stretch",
                             column_config={label:st.column_config.NumberColumn(width="small",format="%.9f") for label in augmented.phase_labels})
            st.caption(f"Error máximo={validation.max_error_ohm_per_m:.3e} Ω/m; residuo de frontera={validation.boundary_residual:.3e}.")
    with st.expander("Bibliografía y discrepancias · componentes simétricas"):
        st.markdown((Path(__file__).resolve().parents[1]/"referencias"/"secuencias.md").read_text(encoding="utf-8"))
