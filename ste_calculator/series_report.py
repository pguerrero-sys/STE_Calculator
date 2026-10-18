"""Informe 7D con matrices y comparación PSCAD: R/X y porcentajes separados."""

from html import escape
from io import BytesIO
import numpy as np
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,KeepTogether,LongTable,TableStyle
from .printing import font_name,MatrixBlock,matrix_tables,PAGE_SIZE,MARGIN,TABLE_WIDTH
from .carson import convert_impedance


def series_record(case,result,table,reference=None):
    def encode(z):
        return {"real":z.real.tolist(),"imag":z.imag.tolist()}
    return {"etapa":"7D","modelo":case.description,"entradas":case.metadata,"orden_fases":result.labels,
            "transposicion_activada":result.enabled,"permutaciones":result.permutations,"pesos":[1/3]*3,
            "Z_original_ohm_m":encode(result.original_ohm_per_m),
            "Z_tramos_ohm_m":[encode(z) for z in result.sections_ohm_per_m],
            "Z_transpuesta_ohm_m":encode(result.average_ohm_per_m),
            "Z_seleccionada_ohm_m":encode(result.selected_ohm_per_m),
            "PSCAD":reference,"comparacion_ohm_km":table.astype(object).where(pd.notna(table),None).to_dict(orient="records"),
            "formula_error":"100*abs(STE-PSCAD)/abs(PSCAD), por R y X; indefinido si referencia=0",
            "advertencia":"R_AC bibliográfica y R_DC PSCAD son entradas distintas; no equivalencia exacta de modelos."}


def series_pdf(case,result,table,reference=None):
    styles = getSampleStyleSheet()
    for style in styles.byName.values():
        style.fontName = font_name()
    styles["BodyText"].fontSize=9
    styles["BodyText"].leading=13
    styles["BodyText"].splitLongWords=True
    styles["Heading2"].keepWithNext=True
    story = [Paragraph("STE Calculator · Transposición serie Carson · Etapa 7D",styles["Title"])]
    def note(text):
        story.append(Paragraph(escape(str(text)),styles["BodyText"]))
        story.append(Spacer(1,6))
    note(case.metadata.get("nombre","Datos actuales de Carson"))
    note(case.description)
    note("Selección principal: "+("transposición ideal activada" if result.enabled else "sin transposición")+". La comparación conserva ambos estados.")
    note(f"Método: {case.metadata['metodo']}; f={case.metadata['frecuencia_Hz']} Hz; resistividad={case.metadata['resistividad_ohm_m']} Ω·m.")
    note("Tres secciones de igual longitud (1/3 cada una). Permutaciones: ABC, BCA, CAB. En doble circuito se aplica el mismo ciclo simultáneamente a ambos circuitos; se conservan seis fases y todos los acoplamientos.")
    for equation in ("St: matriz de asignación de fase a posición física; Zt=Stᵀ Zoriginal St.",
                      "Ztranspuesta=(Z0+Z1+Z2)/3. Ω/m→Ω/km: ×1000.",
                      "Un circuito recíproco: Zpropio=(ZAA+ZBB+ZCC)/3; Zmutuo=(ZAB+ZBC+ZCA)/3.",
                      "Error_R [%]=100 |R_STE-R_PSCAD|/|R_PSCAD|.",
                      "Error_X [%]=100 |X_STE-X_PSCAD|/|X_PSCAD|."):
        note(equation)
    note("Porcentajes indefinidos si la referencia correspondiente es cero; '--' indica dato ausente o porcentaje indefinido, nunca error cero supuesto.")
    note("R_AC de STE y R_DC de PSCAD no se igualan ni se convierten automáticamente. La diferencia porcentual mide discrepancia entre resultados con esas entradas, no error puro del algoritmo de Carson.")
    primitive = getattr(case.phase_result,"primitive",case.phase_result)
    conductor = primitive.conductors[0]
    note(f"Primer subconductor: R_AC={conductor.resistance_ac_ohm_per_km*1.609344:.12g} Ω/milla = {conductor.resistance_ac_ohm_per_km:.12g} Ω/km. No se sustituye por R_DC de PSCAD.")
    for warning in primitive.warnings:
        note(warning)
    note("Entradas por subconductor: "+"; ".join(f"{c.label}: ({c.x_m:.9g},{c.height_m:.9g}) m, R_AC={c.resistance_ac_ohm_per_km:.12g} Ω/km, RMG={c.gmr_m:.12g} m" for c in primitive.conductors))
    note("Fuentes R_AC/RMG: "+"; ".join(dict.fromkeys(c.source for c in primitive.conductors)))
    if "residuo_JSON_original_ohm_m" in case.metadata:
        note(f"Comprobación previa sin transposición: residuo máximo contra Z del JSON={case.metadata['residuo_JSON_original_ohm_m']:.6e} Ω/m. Se recalcula desde entradas, sin utilizar resultados guardados como salidas fijas.")
    if reference:
        note("PSCAD: "+reference["source"])
        note(f"Tipo de resistencia declarada en PSCAD: {reference['resistance_type']}; entrada por subconductor: {reference.get('input_resistance_ohm_per_km','no indicada')} Ω/km.")
        note("Se compara únicamente SERIES IMPEDANCE MATRIX (Z) [ohms/m], PHASE DOMAIN DATA. No se mezclan impedancias modales, secuencias, valores totales ni long-line corrected.")
        note("Frecuencias PSCAD por estado: "+str(reference.get("frequencies_Hz","no indicadas")))
    else:
        note("Sin resultados PSCAD suministrados: se exporta la tabla STE con referencias y porcentajes pendientes.")
    note("Hipótesis: fases equivalentes por circuito, corrientes continuas a través de los tramos, cruces de longitud despreciable. No es una cascada distribuida exacta. Si hay auxiliares, Kron se aplica por sección bajo ΔVn=0, antes de promediar; no Kron del promedio primitivo.")
    note("Fuente: Kersting (2002), pp.91 y 95, ecs.4.68-4.72; referencias/transposicion_serie.md. Capacitancia e inductancia con suelo ideal no se modifican.")
    for unit in ("Ω/km","Ω/m"):
        for name,z in (("Original sin transposición",result.original_ohm_per_m),("Promedio transpuesto",result.average_ohm_per_m)):
            converted = convert_impedance(z,"Ω/m",unit)
            for part,values in (("R",converted.real),("X",converted.imag)):
                for start,end,tab in matrix_tables(MatrixBlock(name+" · "+part,values,result.labels,result.labels,unit)):
                    story.append(KeepTogether([Spacer(1,9),Paragraph(escape(f"{name} · {part} [{unit}]"),styles["Heading3"]),tab]))
    for component in ("R","X"):
        story.append(Paragraph(f"Comparación STE / PSCAD · {component} [Ω/km]",styles["Heading2"]))
        rows = [["Estado","Elemento",f"{component} STE",f"{component} PSCAD",f"Error {component} [%]"]]
        for row in table.to_dict(orient="records"):
            values = [row[f"STE_{component}_ohm_km"],row[f"PSCAD_{component}_ohm_km"],row[f"Error_{component}_pct"]]
            rows.append(["Sin" if row['Estado']=="sin_transposicion" else "Ideal",row['Fila']+" / "+row['Columna'],
                         *["--" if pd.isna(v) else f"{v:.10g}" for v in values]])
        tab = LongTable(rows,colWidths=[70,90,(TABLE_WIDTH-160)/3,(TABLE_WIDTH-160)/3,(TABLE_WIDTH-160)/3],repeatRows=1,hAlign="LEFT")
        tab.setStyle(TableStyle([("FONTNAME",(0,0),(-1,-1),font_name()),("FONTSIZE",(0,0),(-1,-1),8),
                                ("LEADING",(0,0),(-1,-1),11),("BACKGROUND",(0,0),(-1,0),colors.HexColor("#e1eff2")),
                                ("GRID",(0,0),(-1,-1),.3,colors.HexColor("#b9ced7")),
                                ("ALIGN",(2,1),(-1,-1),"RIGHT")]))
        story.append(tab)
    for number,(permutation,z) in enumerate(zip(result.permutations,result.sections_ohm_per_m),1):
        note(f"Tramo {number}, peso 1/3: "+", ".join(f"{p}→posición {result.labels[i]}" for p,i in zip(result.labels,permutation)))
        for part,values in (("R",z.real*1000),("X",z.imag*1000)):
            for _,_,tab in matrix_tables(MatrixBlock(f"Tramo {number}",values,result.labels,result.labels,"Ω/km")):
                story.append(KeepTogether([Spacer(1,7),Paragraph(f"Tramo {number} · {part} [Ω/km]",styles["Heading3"]),tab]))
    def footer(canvas,doc):
        canvas.setFont(font_name(),8)
        canvas.drawString(MARGIN,20,"STE Calculator · Comparación numérica con entradas AC/DC diferentes")
        canvas.drawRightString(PAGE_SIZE[0]-MARGIN,20,f"Página {doc.page}")
    output = BytesIO()
    doc = SimpleDocTemplate(output,pagesize=PAGE_SIZE,leftMargin=MARGIN,rightMargin=MARGIN,topMargin=MARGIN,bottomMargin=MARGIN)
    doc.build(story,onFirstPage=footer,onLaterPages=footer)
    return output.getvalue()
