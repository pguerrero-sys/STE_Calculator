# Adaptador de integración de la UI validada antes de la refactorización. Solo pruebas.
r"""Punto de entrada: .venv\Scripts\python.exe -m streamlit run app.py"""

from pathlib import Path
from contextlib import nullcontext

import pandas as pd
import streamlit as st

from ste_calculator.geometry import calculate_geometry
from ste_calculator.capacitance import calculate_capacitance, VACUUM_PERMITTIVITY_F_PER_M
from ste_calculator.capacitance_ui import render_capacitance_math, render_capacitance_results
from ste_calculator.inductance_ui import render_inductance_tab
from ste_calculator.bundle_ui import render_bundle_tab
from ste_calculator.bundle_inputs import build_bundle_context
from ste_calculator.double_circuit_ui import render_double_circuit_panel
from ste_calculator.transposition_ui import render_transposition_panel
from ste_calculator.carson_ui import render_carson_panel
from ste_calculator.series_transposition_ui import render_series_transposition
from ste_calculator.models import Conductor, FutureOptions, InputError, LineInput, PHASES, finite_number
from ste_calculator.plotting import geometry_figure
from ste_calculator.units import convert_length

st.set_page_config(page_title="STE Calculator", page_icon="⚡", layout="wide")
st.markdown("""
<style>
.block-container {max-width: 1450px; padding-top: 2.2rem;}
.ste-hero {background: linear-gradient(115deg,#12334b,#087f8c); color:white;
 padding:28px 32px; border-radius:18px; margin-bottom:20px;}
.ste-hero h1 {color:white; margin:0; padding:0; font-size:2.35rem;}
.ste-hero p {margin:10px 0 0; opacity:.9;}
.ste-kicker {font-size:.78rem; letter-spacing:.13em; margin-bottom:8px;}
[data-testid="stMetric"] {background:white; padding:16px; border-radius:12px; border:1px solid #dae5ed;}
@media print {
  .block-container {max-width:100%; padding:0;}
  [data-testid="stLatex"], .katex-display {overflow:visible !important; height:auto !important;}
  .katex-display {font-size:0.8em; break-inside:avoid; white-space:normal;}
  [data-testid="stCode"] pre {white-space:pre-wrap !important; overflow-wrap:anywhere;}
}
</style>
<div class="ste-hero"><div class="ste-kicker">SISTEMAS DE TRANSMISIÓN · ETAPA 7D · TRANSPOSICIÓN SERIE Y COMPARACIÓN PSCAD</div>
<h1>⚡ STE Calculator</h1><p>Geometría, capacitancia e inductancia · Desarrollo matemático y fuentes</p></div>
""", unsafe_allow_html=True)
st.caption("Modelo de esta etapa: circuitos trifásicos A/B/C, sección transversal y terreno horizontal de referencia en Y = 0 m. Cada fila representa una posición de fase.")

with st.sidebar:
    st.subheader("Alcance de la versión")
    st.success("Disponible: geometría, capacitancia, inductancia, Carson, Kron y componentes simétricas")
    st.info("Circuito sencillo o doble: conductores individuales o haces de 1 a 4 subconductores por fase")
    st.caption("Inductancia: suelo ideal o sin suelo con suma de corrientes cero. Frecuencia necesaria para reactancia. Matrices eléctricas de hasta dos circuitos; sin reducción automática a tres fases.")

config_tab, geometry_tab, results_tab, math_tab, inductance_tab, bundles_tab, bibliography_tab = st.tabs([
    "⚙ Configuración", "📐 Geometría", "📊 Resultados", "∑ Desarrollo matemático", "Inductancia", "Haces", "📚 Bibliografía"
])

def load_capacitance_case():
    st.session_state.circuit_count = 1
    st.session_state.coordinates = {"C1-A": (-3.0, 13.0), "C1-B": (3.0, 13.0), "C1-C": (0.0, 9.0)}
    for phase in PHASES:
        st.session_state[f"radius_{phase}"] = 0.011765
    st.session_state.example_mode = True
    st.session_state.capacitance_case_loaded = True
    st.session_state.editor_revision = st.session_state.get("editor_revision", 0) + 1


with config_tab:
    st.subheader("Datos de la línea")
    st.button("Cargar caso obligatorio de capacitancia", on_click=load_capacitance_case,
              help="Reemplaza coordenadas y radios con el caso de verificación proporcionado por el usuario. No modifica frecuencia ni longitud.")
    if st.session_state.get("capacitance_case_loaded", False):
        st.info("Caso de verificación del usuario cargado: A=(−3,13), B=(3,13), C=(0,9) m; radios 0.011765 m. Puedes editarlo. No constituye un diseño eléctrico validado.")
    col1, col2, col3, col4 = st.columns([1, 1, 1, .65])
    circuit_count = int(col1.number_input("Número de circuitos", min_value=1, max_value=12, value=1, step=1, key="circuit_count"))
    frequency_hz = col2.number_input("Frecuencia [Hz]", value=None, placeholder="Ingresa la frecuencia", format="%.6f")
    length_value = col3.number_input("Longitud de la línea", value=None, placeholder="Ingresa la longitud", format="%.6f")
    length_unit = col4.selectbox("Unidad", ["km", "m"])
    st.subheader("Radio exterior para capacitancia")
    radius_columns = st.columns(3)
    radii_m = tuple(col.number_input(f"Radio exterior {phase} [m]", value=None, format="%.9f",
                                    placeholder="Radio físico exterior", key=f"radius_{phase}", disabled=circuit_count != 1)
                    for phase, col in zip(PHASES, radius_columns))
    st.caption("Usa el radio exterior de cada conductor circular. No uses GMR inductivo ni parámetros de hebras ACSR supuestos. La capacitancia puede calcularse sin frecuencia ni longitud.")
    st.write(f"Permitividad utilizada: ε₀ = {VACUUM_PERMITTIVITY_F_PER_M:.12g} F/m (cifra indicada por el usuario); aire con εᵣ = 1.")
    st.divider()
    st.subheader("Preparación de próximas etapas")
    st.warning("Carson aproximado y Kron condicionado están disponibles como módulos independientes en Inductancia → Impedancia serie · Carson. Pendientes: equivalentes automáticos de doble circuito y propagación distribuida. Configura haces y transposición ideal en Haces; los modelos anteriores conservan sus opciones.")
    st.caption("El control histórico de transposición del modelo individual permanece desactivado. La transposición ideal, también para un conductor por fase, se configura en Haces → Transposición ideal.")
    st.caption("El control histórico de Carson también permanece desactivado: no es un cambio de suelo del modelo capacitivo o inductivo anterior. El cálculo serie independiente se configura en Inductancia → Carson · etapa 7A.")
    opt1, opt2 = st.columns(2)
    with opt1:
        transposition = st.checkbox("Considerar transposición (pendiente)", value=False, disabled=True, key="pending_cap_transposition")
        ground_effect = st.checkbox("Suelo ideal por imágenes (capacitancia)", value=True, disabled=True)
        st.checkbox("Carson / suelo no ideal (pendiente)", value=False, disabled=True)
        conductor_reference = st.text_input("Referencia del conductor", placeholder="Fabricante, catálogo o documento técnico")
        material_notes = st.text_area("Características del conductor (sin valores predeterminados)", placeholder="Registrar datos con unidades y fuente; aún no se utilizan en cálculos.")
    with opt2:
        bundle_count = int(st.number_input("Subconductores por fase (modelo individual)", min_value=1, max_value=1, value=1, step=1, disabled=True, key="pending_cap_bundle"))
        bundle_spacing_notes = st.text_input("Separación del haz (configurar en Haces)", disabled=True, placeholder="Disponible en la sección Haces")
        st.caption("Estos controles pertenecen al modelo individual. La sección Haces expande cada fase en posiciones de subconductores y presenta sus propios cálculos.")

with geometry_tab:
    st.subheader("Coordenadas de las fases")
    st.write("Ingresa X e Y en metros usando punto decimal. X puede ser negativa; Y debe ser positiva. Los identificadores de circuito y fase son fijos.")
    st.caption("Al cambiar el número de circuitos se conservan las filas de los circuitos que permanecen. Los nuevos circuitos se agregan vacíos.")
    if "coordinates" not in st.session_state:
        st.session_state.coordinates = {}
    example_clicked = st.button("Cargar ejemplo geométrico ilustrativo", help="Reemplaza las coordenadas por una distribución sintética. No es un diseño ni una validación técnica.")
    if example_clicked:
        st.session_state.capacitance_case_loaded = False
        st.session_state.coordinates = {
            f"C{c}-{p}": (float((c - 1) * 12 + (i - 1) * 4), 12.0)
            for c in range(1, circuit_count + 1) for i, p in enumerate(PHASES)
        }
        st.session_state.example_mode = True
        st.session_state.editor_revision = st.session_state.get("editor_revision", 0) + 1
    if st.session_state.get("example_mode", False):
        st.warning("Se cargó un ejemplo sintético ilustrativo. Sus coordenadas y distancias no constituyen resultados de un proyecto validado, incluso si editas sus valores.")
    rows = []
    for c in range(1, circuit_count + 1):
        for p in PHASES:
            x, y = st.session_state.coordinates.get(f"C{c}-{p}", (None, None))
            rows.append({"Circuito": c, "Fase": p, "X [m]": x, "Y [m]": y})
    edited = st.data_editor(
        pd.DataFrame(rows), hide_index=True, num_rows="fixed", width="stretch",
        disabled=["Circuito", "Fase"],
        column_config={
            "X [m]": st.column_config.NumberColumn("X [m]", required=True, format="%.6f"),
            "Y [m]": st.column_config.NumberColumn("Y [m]", required=True, format="%.6f"),
        }, key=f"coordinates_{circuit_count}_{st.session_state.get('editor_revision', 0)}",
    )
    st.session_state.coordinates = {
        f"C{int(row['Circuito'])}-{row['Fase']}": (row["X [m]"], row["Y [m]"])
        for row in edited.to_dict("records")
    }

data = None
result = None
conductors = None
try:
    conductors = tuple(
        Conductor(int(row["Circuito"]), row["Fase"],
                  finite_number(row["X [m]"], f"C{row['Circuito']}-{row['Fase']}, X"),
                  finite_number(row["Y [m]"], f"C{row['Circuito']}-{row['Fase']}, Y"))
        for row in edited.to_dict("records")
    )
    data = LineInput(
        circuit_count, finite_number(frequency_hz, "Frecuencia"),
        convert_length(length_value, length_unit, "m"), conductors,
        FutureOptions(transposition, ground_effect, conductor_reference, material_notes, bundle_count, bundle_spacing_notes),
    )
    result = calculate_geometry(data)
except InputError as exc:
    validation_message = str(exc)

capacitance_result = None
capacitance_message = "Completa las coordenadas y radios exteriores de las tres fases."
try:
    if circuit_count != 1:
        raise InputError("Solo se admite un circuito para capacitancia. Los circuitos múltiples conservan únicamente el análisis geométrico.")
    if conductors is None:
        raise InputError(validation_message)
    capacitance_result = calculate_capacitance(conductors, radii_m)
except InputError as exc:
    capacitance_message = str(exc)

with geometry_tab:
    if result is None:
        st.info(f"Completa o corrige los datos para dibujar y calcular: {validation_message}")
    else:
        st.plotly_chart(geometry_figure(data), width="stretch", config={"scrollZoom": True, "displaylogo": False})
        st.caption("Escala igual en ambos ejes. Arrastra para desplazar, usa la rueda para acercar y doble clic para restablecer. El tamaño de los marcadores es simbólico; no representa el radio del conductor. La recta Y = 0 no es un levantamiento topográfico.")

with results_tab:
    st.subheader("Distancias geométricas")
    if result is None:
        st.info(f"Sin resultados: {validation_message}")
    else:
        st.caption("Resultados calculados a partir de las entradas actuales. La validación de entrada comprueba consistencia geométrica; no certifica un diseño eléctrico ni distancias de seguridad.")
        if st.session_state.get("example_mode", False):
            st.warning("Resultados de un ejemplo sintético ilustrativo; no validados para un proyecto real.")
        m1, m2, m3 = st.columns(3)
        m1.metric("Posiciones de fase", len(data.conductors))
        m2.metric("Pares calculados", len(result.pairs))
        m3.metric("Longitud ingresada [m]", f"{data.length_m:.6g}")
        records = [{"Conductor i": p.first.label, "Conductor j": p.second.label,
                    "ΔX [m]": p.dx_m, "ΔY [m]": p.dy_m, "Distancia [m]": p.distance_m} for p in result.pairs]
        distances = pd.DataFrame(records)
        st.dataframe(distances, hide_index=True, width="stretch", column_config={
            c: st.column_config.NumberColumn(c, format="%.6f") for c in ("ΔX [m]", "ΔY [m]", "Distancia [m]")
        })
        export = distances.copy()
        export.insert(0, "Contexto", "Ejemplo sintético ilustrativo; sin validación de diseño" if st.session_state.get("example_mode", False)
                      else "Entradas del usuario; sin validación de diseño")
        st.download_button("Descargar distancias en CSV", export.to_csv(index=False).encode("utf-8-sig"), "ste_distancias.csv", "text/csv")
        with st.expander("Matriz simétrica de distancias [m]"):
            st.dataframe(pd.DataFrame(result.matrix_m, index=result.labels, columns=result.labels).style.format("{:.6f}"), width="stretch")
            st.caption("La diagonal vale cero porque compara cada posición consigo misma.")
    render_capacitance_results(capacitance_result, capacitance_message)

with math_tab:
    st.subheader("Pitágoras, paso a paso")
    st.latex(r"\Delta x_{ij}=x_j-x_i,\qquad \Delta y_{ij}=y_j-y_i")
    st.latex(r"D_{ij}=\sqrt{(x_j-x_i)^2+(y_j-y_i)^2}=\sqrt{\Delta x_{ij}^{2}+\Delta y_{ij}^{2}}")
    st.write("Con X e Y en metros, los términos cuadrados se expresan en m² y la distancia se obtiene en m. Se calculan todos los pares, incluso entre circuitos distintos.")
    if result is None:
        st.info(f"La sustitución numérica estará disponible al completar los datos: {validation_message}")
    else:
        pair_index = st.selectbox("Par de posiciones", range(len(result.pairs)), format_func=lambda i: f"{result.pairs[i].first.label} ↔ {result.pairs[i].second.label}")
        p = result.pairs[pair_index]
        st.latex(rf"\Delta x=({p.second.x_m:.8g})\,\mathrm{{m}}-({p.first.x_m:.8g})\,\mathrm{{m}}={p.dx_m:.8g}\,\mathrm{{m}}")
        st.latex(rf"\Delta y=({p.second.y_m:.8g})\,\mathrm{{m}}-({p.first.y_m:.8g})\,\mathrm{{m}}={p.dy_m:.8g}\,\mathrm{{m}}")
        st.latex(rf"D=\sqrt{{({p.dx_m:.8g}\,\mathrm{{m}})^2+({p.dy_m:.8g}\,\mathrm{{m}})^2}}={p.distance_m:.8g}\,\mathrm{{m}}")
        st.caption("Los valores mostrados están redondeados. Los cálculos usan precisión de punto flotante sin redondeo previo.")
        with st.expander("Conversión de la longitud ingresada"):
            if length_unit == "km":
                st.latex(rf"L={length_value:.8g}\,\mathrm{{km}}\times1000\,\frac{{\mathrm{{m}}}}{{\mathrm{{km}}}}={data.length_m:.8g}\,\mathrm{{m}}")
            else:
                st.latex(rf"L={length_value:.8g}\,\mathrm{{m}}")
            st.caption("La longitud longitudinal se registra como entrada; no se usa para la distancia transversal entre fases.")
    render_capacitance_math(capacitance_result, capacitance_message)

with inductance_tab:
    render_inductance_tab(conductors, circuit_count, frequency_hz,
                          validation_message if conductors is None else "")

with bundles_tab:
    coordinate_error = validation_message if conductors is None else ""
    if circuit_count == 2:
        render_double_circuit_panel(conductors,circuit_count,frequency_hz,coordinate_error)
    with (st.expander("Modelos previos: Haces y Transposición de circuito sencillo") if circuit_count==2 else nullcontext()):
        render_bundle_tab(conductors,circuit_count,frequency_hz,coordinate_error)
        # La entrada es el estado ACTUAL de los widgets, nunca el retorno
        # del renderizador ni geometría guardada de otra ejecución.
        try:
            bundle_context = build_bundle_context(conductors,circuit_count,st.session_state.to_dict(),coordinate_error)
        except InputError as exc:
            bundle_context = {"geometry":None,"geometry_error":str(exc)}
        render_transposition_panel(bundle_context,frequency_hz,length_value,length_unit)
    if circuit_count != 2:
        render_double_circuit_panel(conductors,circuit_count,frequency_hz,coordinate_error)

with inductance_tab:
    # Después de los widgets de Haces para tomar su estado actual si se elige
    # expansión de subconductores. No se usa ni altera ningún resultado de C.
    render_carson_panel(conductors,circuit_count,validation_message if conductors is None else "")
    render_series_transposition(conductors,circuit_count,validation_message if conductors is None else "")

with bibliography_tab:
    st.subheader("Fuentes técnicas del curso")
    st.success("Método de las imágenes revisado en las notas del curso y Kersting. El registro siguiente distingue las fuentes, la notación y los datos aportados por el usuario.")
    reference_dir = Path(__file__).resolve().parents[2] / "referencias"
    st.markdown((reference_dir / "capacitancia.md").read_text(encoding="utf-8"))
    st.markdown((reference_dir / "inductancia.md").read_text(encoding="utf-8"))
    st.markdown((reference_dir / "haces.md").read_text(encoding="utf-8"))
    st.markdown((reference_dir / "transposicion.md").read_text(encoding="utf-8"))
    st.markdown((reference_dir / "doble_circuito.md").read_text(encoding="utf-8"))
    st.markdown((reference_dir / "carson.md").read_text(encoding="utf-8"))
    st.markdown((reference_dir / "kron.md").read_text(encoding="utf-8"))
    st.markdown((reference_dir / "secuencias.md").read_text(encoding="utf-8"))
    st.markdown((reference_dir / "transposicion_serie.md").read_text(encoding="utf-8"))
    files = sorted(str(p.relative_to(reference_dir)) for p in reference_dir.rglob("*.pdf"))
    if files:
        st.write("Archivos disponibles (su presencia no implica revisión):")
        for name in files:
            st.text(name)
    else:
        st.caption("Carpeta preparada; todavía no hay documentos técnicos incorporados.")
    st.caption("La geometría de la etapa 1 se conserva. No se han supuesto propiedades de materiales ni geometrías ACSR.")
