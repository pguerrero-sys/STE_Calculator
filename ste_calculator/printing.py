"""Informes PDF con tablas paginadas, sin capturar los canvas de Streamlit."""

from dataclasses import dataclass
from html import escape
from io import BytesIO
from pathlib import Path
import os

import numpy as np
import reportlab
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether

PAGE_SIZE = landscape(A4)
MARGIN = 36
TABLE_WIDTH = PAGE_SIZE[0]-2*MARGIN


@dataclass(frozen=True)
class MatrixBlock:
    title: str
    values: np.ndarray
    row_labels: tuple
    column_labels: tuple
    unit: str
    axis_label: str = "Fase / posición"


@dataclass(frozen=True)
class EquationBlock:
    """Ecuaciones por pasos: texto ajustable y título unido a su desarrollo."""
    title: str
    lines: tuple


def font_name():
    name = "STEReport"
    if name not in pdfmetrics.getRegisteredFontNames():
        candidates = [Path(os.environ.get("WINDIR","C:/Windows"))/"Fonts"/"arial.ttf",
                      Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
                      Path(reportlab.__file__).parent/"fonts"/"Vera.ttf"]
        path = next(p for p in candidates if p.is_file())
        pdfmetrics.registerFont(TTFont(name,str(path)))
    return name


def matrix_tables(block, max_columns=6):
    """Partición horizontal, todas las filas y etiquetas repetidas en cada bloque."""
    matrix = np.asarray(block.values,dtype=float)
    if matrix.shape != (len(block.row_labels),len(block.column_labels)) or not np.all(np.isfinite(matrix)):
        raise ValueError("Dimensiones o valores inválidos para la tabla PDF.")
    tables = []
    for start in range(0,matrix.shape[1],max_columns):
        end = min(start+max_columns,matrix.shape[1])
        data = [[block.axis_label,*block.column_labels[start:end]]]
        data.extend([label,*[f"{v:.9e}" for v in row[start:end]]] for label,row in zip(block.row_labels,matrix))
        widths = [90]+[(TABLE_WIDTH-90)/(end-start)]*(end-start)
        table = Table(data,colWidths=widths,repeatRows=1,hAlign="LEFT")
        table.setStyle(TableStyle([
            ("FONTNAME",(0,0),(-1,-1),font_name()),
            ("FONTSIZE",(0,0),(-1,-1),7.5),
            ("LEADING",(0,0),(-1,-1),10),
            ("TOPPADDING",(0,0),(-1,-1),4),
            ("BOTTOMPADDING",(0,0),(-1,-1),4),
            ("BACKGROUND",(0,0),(-1,0),colors.HexColor("#e1eff2")),
            ("TEXTCOLOR",(0,0),(-1,0),colors.HexColor("#12334b")),
            ("GRID",(0,0),(-1,-1),.3,colors.HexColor("#b9ced7")),
            ("ALIGN",(1,1),(-1,-1),"RIGHT"),
            ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
        ]))
        tables.append((start,end,table))
    return tables


def render_pdf(title,paragraphs,blocks,footer_text="STE Calculator · Modelo ideal, sin validación de diseño"):
    buffer = BytesIO()
    styles = getSampleStyleSheet()
    for style in styles.byName.values():
        style.fontName = font_name()
    # Las fórmulas como texto pueden contener productos/sustituciones sin espacios.
    # splitLongWords y wordWrap permiten paginarlas sin un canvas horizontal recortado.
    styles.add(ParagraphStyle(name="STEBody",fontName=font_name(),fontSize=9,leading=13,
                              spaceAfter=7,splitLongWords=1,wordWrap="LTR"))
    styles.add(ParagraphStyle(name="STEEquation",parent=styles["STEBody"],
                              backColor=colors.HexColor("#edf5f7"),borderPadding=7,
                              spaceBefore=7,spaceAfter=12))
    story = [Paragraph(escape(title),styles["Title"])]
    for text in paragraphs:
        if isinstance(text,EquationBlock):
            content = "<br/>".join(escape(line) for line in text.lines)
            story.append(KeepTogether([Paragraph(escape(text.title),styles["Heading3"]),
                                      Paragraph(content,styles["STEEquation"])]))
        else:
            story.append(Paragraph(escape(text).replace("\n", "<br/>"),styles["STEBody"]))
    for block in blocks:
        for start,end,table in matrix_tables(block):
            suffix = f" · columnas {start+1}-{end}" if len(block.column_labels)>6 else ""
            story.append(KeepTogether([Spacer(1,10),Paragraph(escape(f"{block.title} [{block.unit}]{suffix}"),styles["Heading3"]),table]))

    def footer(canvas,doc):
        canvas.saveState()
        canvas.setFont(font_name(),8)
        canvas.drawString(MARGIN,20,footer_text)
        canvas.drawRightString(PAGE_SIZE[0]-MARGIN,20,f"Página {doc.page}")
        canvas.restoreState()

    doc = SimpleDocTemplate(buffer,pagesize=PAGE_SIZE,leftMargin=MARGIN,rightMargin=MARGIN,
                            topMargin=MARGIN,bottomMargin=MARGIN,title=title,author="STE Calculator")
    doc.build(story,onFirstPage=footer,onLaterPages=footer)
    return buffer.getvalue()


def double_circuit_pdf(result,frequency_hz=None):
    from .double_circuit import LABELS, reactance_six
    from .inductance import IDEAL_GROUND, SOLID_UNIFORM
    from .models import InputError
    from .transposition_schedule import automatic_schedule

    notes = [
        "Seis terminales independientes: A, B, C, A', B', C'. No se aplica reducción a 3×3 ni conexión en paralelo.",
        f"Suelo de inductancia: {result.inductance_model}. Suelo de capacitancia: {result.capacitance_model}.",
        "Duv = sqrt((xu-xv)²+(hu-hv)²); Suv = sqrt((xu-xv)²+(hu+hv)²), metros.",
        "μ0 = 4π×10^-7 H/m; ε0 = 8.8541878128×10^-12 F/m; k = μ0/(2π); F = 2πε0.",
        "Con suelo: Lsub,uu = k ln(2hu/RMG_u); Lsub,uv = k ln(Suv/Duv). L6 = Tᵀ Lsub T; T[u,p] = E[u,p]/n_p.",
        "Con suelo: Psub,uu = ln(2hu/Ru); Psub,uv = ln(Suv/Duv); W = Psub^-1 E; C6 = F Eᵀ W; Pfase = (C6/F)^-1.",
        "Sin suelo: L0 = k ln(1 m/d), diagonal d=RMG. P0=ln(1 m/d), diagonal d=R. Referencia auxiliar, no retorno físico.",
        "Sin suelo: H6=I6-11ᵀ/6; Lproj=H6 L0,fase H6, solo ΣI6=0. Zᵀ1=0; W=Z(ZᵀP0 Z)^-1 ZᵀE; C6=F EᵀW, solo Σq6=0, potencial común indeterminado.",
        "Tramos: Lprom=Σwt Lt; Pprom=Σwt Pfase,t; C=F Pprom^-1. Sin suelo, invertir solo en Qᵀ1=0: C=F Q(QᵀPprom Q)^-1 Qᵀ.",
        "Unidades: H/m a µH/m o mH/km, multiplicar por 10^6; F/m a nF/km, por 10^12. X=2πfL; Ω/m a Ω/km, por 1000.",
        "RMG=R exp(-1/4) solo para macizo no magnético uniforme. ACSR: RMG documentado del fabricante; sin reconstrucción de hebras.",
        "Supuestos: cargas lineales, subconductores equipotenciales por haz, corrientes I_fase/n, tramos uniformes, cruces sin longitud. Sin Carson ni propagación distribuida exacta.",
        "Bloques por circuito: λ1=L11 I1+L12 I2 y q1=C11 V1+C12 V2. Los bloques diagonales no representan circuitos aislados.",
        "Revisión de etapa 7A: promediar P antes de invertir corresponde a carga de fase común; a potencial común se promedia C. No son equivalentes shunt universales de una línea distribuida. No se cambian las matrices históricas; ver referencias/carson.md.",
        "Fuentes: notas generales PDF 67-75; clase 15-09-26 PDF 6-9; clase 17-09-26 PDF 1; clase 24-09-26 PDF 1-2; Kersting (2002) §4.1 y §5.1-5.2. Derivación y correcciones: referencias/doble_circuito.md.",
        f"Residuo normalizado de inversión de P promedio: {result.inversion_residual:.3e}.",
    ]
    automatic=automatic_schedule(2,True)
    if result.assignments==automatic.assignments and np.allclose(result.weights,automatic.weights,rtol=0,atol=1e-15):
        notes.append('Transposición ideal completa automática: nueve combinaciones independientes Z3×Z3; peso interno 1/9 por tramo. Haces completos por fase, circuitos separados. Los pesos mostrados redondeados no se utilizan como entradas.')
    elif len(result.sections)==1:
        notes.append('Sin transposición: un tramo de peso interno 1.')
    for t,(section,row,w) in enumerate(zip(result.sections,result.assignments,result.weights),1):
        notes.append(f"Tramo {t}: fracción L={w:.12g}; "+", ".join(f"{p}→P{pos+1}" for p,pos in zip(LABELS,row)))
    for label,spec in zip(LABELS,result.sections[0].geometry.specs):
        spacing = f"{spec.spacing_m:g} m" if spec.count>1 else "no aplica (n=1)"
        notes.append(f"Fase {label}: centro ({spec.center.x_m:.9g}, {spec.center.y_m:.9g}) m; n={spec.count}; R={spec.radius_m:.12g} m; separación={spacing}; rotación={spec.rotation_deg:g} grados.")
    if result.sections[0].rmg_m is not None:
        notes.append("RMG utilizados [m]: "+", ".join(f"{p}={v:.12g}" for p,v in zip(LABELS,result.sections[0].rmg_m)))
        for label,data,rmg in zip(LABELS,result.sections[0].rmg_inputs,result.sections[0].rmg_m):
            if data.method==SOLID_UNIFORM:
                notes.append(f"Fase {label}: modelo macizo no magnético uniforme; RMG=({data.radius_m:.12g} m) exp(-1/4)={rmg:.12g} m.")
            else:
                notes.append(f"Fase {label}: RMG del fabricante={rmg:.12g} m; fuente: {data.source}. No se aplica el factor macizo.")
    for t,section in enumerate(result.sections,1):
        g = section.geometry
        for u,v in ((0,0),(0,len(g.labels)-1)):
            d = g.radii_m[u] if u==v else g.real_distances_m[u,v]
            s = g.image_distances_m[u,v] if result.capacitance_model==IDEAL_GROUND else 1.0
            notes.append(f"Tramo {t}, Psub({g.labels[u]},{g.labels[v]}) = ln(({s:.12g} m)/({d:.12g} m)) = {section.potential_sub[u,v]:.12g}.")
            if section.rmg_m is not None:
                d = section.rmg_m[g.phase_index[u]] if u==v else g.real_distances_m[u,v]
                s = g.image_distances_m[u,v] if result.inductance_model==IDEAL_GROUND else 1.0
                notes.append(f"Tramo {t}, Lsub({g.labels[u]},{g.labels[v]}) = (2×10^-7 H/m) ln(({s:.12g} m)/({d:.12g} m)) = {section.l_sub_h_per_m[u,v]:.12g} H/m.")
    terms = " + ".join(f"{w:.9g}×{s.effective_phase_p[0,0]:.12g}" for w,s in zip(result.weights,result.sections))
    notes.append(f"Sustitución Pprom(A,A) = {terms} = {result.average_phase_p[0,0]:.12g}, adimensional.")
    notes.append(f"C(A,A) = {result.c_f_per_m[0,0]:.12g} F/m × 10^12 = {result.c_f_per_m[0,0]*1e12:.12g} nF/km; se usa la inversa de la matriz, no 1/P(A,A).")
    blocks = []

    def add(title,values,unit,labels=LABELS,columns=None):
        blocks.append(MatrixBlock(title,values,tuple(labels),tuple(columns or labels),unit))

    if result.l_h_per_m is not None:
        for unit,factor in (("H/m",1),("µH/m",1e6),("mH/km",1e6)):
            add("L6 principal promedio",result.l_h_per_m*factor,unit)
        try:
            add("X6",reactance_six(result.l_h_per_m,frequency_hz),"Ω/km")
        except InputError as exc:
            notes.append(f"Reactancia no calculada: {exc}")
        if result.inductance_model != IDEAL_GROUND:
            add("L6 con equilibrio en cada circuito",result.l_circuit_balanced_h_per_m*1e6,"mH/km")
            add("Cuatro lazos independientes",result.l_loops_h_per_m*1e6,"mH/km",("A-C","B-C","A'-C'","B'-C'"))
    add("P efectiva promedio",result.average_phase_p,"adimensional")
    add("C6 principal",result.c_f_per_m,"F/m")
    add("C6 principal",result.c_f_per_m*1e12,"nF/km")
    for t,section in enumerate(result.sections,1):
        g = section.geometry
        add(f"Tramo {t}: posiciones reales",g.positions_m,"m",g.labels,("X","Y"))
        add(f"Tramo {t}: distancias reales D",g.real_distances_m,"m",g.labels)
        add(f"Tramo {t}: distancias a imágenes S",g.image_distances_m,"m",g.labels)
        add(f"Tramo {t}: Psub primitiva"+ (" auxiliar sin suelo" if result.capacitance_model!=IDEAL_GROUND else ""),section.potential_sub,"adimensional",g.labels)
        add(f"Tramo {t}: respuesta qsub por voltio de fase",section.charge_response_f_per_m,"F/m",g.labels,LABELS)
        add(f"Tramo {t}: E equipotencial",g.incidence,"adimensional",g.labels,LABELS)
        add(f"Tramo {t}: T reparto de corriente",g.current_weights,"adimensional",g.labels,LABELS)
        add(f"Tramo {t}: P efectiva",section.effective_phase_p,"adimensional")
        add(f"Tramo {t}: C6",section.c_f_per_m*1e12,"nF/km")
        if section.l_h_per_m is not None:
            add(f"Tramo {t}: Lsub primitiva"+(" auxiliar sin suelo" if result.inductance_model!=IDEAL_GROUND else ""),section.l_sub_h_per_m,"H/m",g.labels)
            add(f"Tramo {t}: L6 principal",section.l_h_per_m*1e6,"mH/km")
    return render_pdf("STE Calculator · Doble circuito",notes,blocks)


def transposition_pdf(result):
    """Mismo ajuste de columnas para el informe de las etapas 4-5."""
    from .models import PHASES
    from .inductance import IDEAL_GROUND

    notes = [
        "Tres fases independientes. Los tramos y sus pesos son los seleccionados en la interfaz.",
        f"Suelo de L: {result.inductance_model}; suelo de C: {result.capacitance_model}.",
        "Lsub,uu = μ0/(2π) ln(2hu/RMG_u); Lsub,uv = μ0/(2π) ln(Suv/Duv); Lfase=TᵀLsubT, con corriente I/n por subconductor (suelo ideal).",
        "Psub,uu=ln(2hu/Ru); Psub,uv=ln(Suv/Duv); Cfase=2πε0 EᵀPsub^-1 E; Pfase=(Cfase/(2πε0))^-1 (suelo ideal).",
        "Lprom=Σwt Lt; Pprom=Σwt Pfase,t; C=2πε0 Pprom^-1. Se promedian potenciales antes de invertir, no capacitancias directamente.",
        "Condición física: carga de fase común entre tramos. A potencial común se promedia C directamente. Los resultados difieren en general; no se certifica el promedio P como equivalente shunt universal. Revisión en referencias/carson.md sin cambiar resultados históricos.",
        "Sin suelo, los logaritmos primitivos usan referencia auxiliar 1 m: ln(1 m/d), con diagonal d=RMG o R. Solo se usan proyecciones de suma cero.",
        "Sin suelo: IA+IB+IC=0; Σq_fase=0 y potencial común indeterminado. C y L son proyectadas de rango 2; la inversión se realiza en una base Q de suma cero.",
        "μ0=4π×10^-7 H/m; ε0=8.8541878128×10^-12 F/m. RMG=R exp(-1/4) solo para macizo no magnético uniforme; ACSR exige dato documentado.",
        "H/m→µH/m o mH/km: ×10^6. F/m→nF/km: ×10^12. Sin Carson, reparto inductivo real, cruces finitos ni cascada distribuida exacta.",
        "Fuentes y supuestos: referencias/haces.md y referencias/transposicion.md; notas generales PDF 53-57 y 96-98; Kersting (2002) §4.1 y §5.1-5.2.",
    ]
    blocks = []
    def add(title,values,unit,labels=PHASES,columns=None):
        blocks.append(MatrixBlock(title,values,tuple(labels),tuple(columns or labels),unit))
    if result.l_h_per_m is not None:
        add("L promedio",result.l_h_per_m,"H/m")
        add("L promedio",result.l_h_per_m*1e6,"mH/km")
    add("P efectiva promedio",result.average_phase_p,"adimensional")
    add("C principal",result.c_f_per_m,"F/m")
    add("C principal",result.c_f_per_m*1e12,"nF/km")
    for i,section in enumerate(result.sections,1):
        notes.append(f"Tramo {i}: peso={section.weight:.12g}; "+", ".join(f"{p}→P{loc+1}" for p,loc in zip(PHASES,section.phase_to_position)))
        g = section.geometry
        add(f"Tramo {i}: posiciones",g.positions_m,"m",g.labels,("X","Y"))
        add(f"Tramo {i}: Psub",section.capacitance.potential_coefficients,"adimensional",g.labels)
        add(f"Tramo {i}: P efectiva de fases",section.effective_phase_p,"adimensional")
        add(f"Tramo {i}: C de fases",section.capacitance.phase_f_per_m*1e12,"nF/km")
        if section.inductance is not None:
            l = section.inductance.phase_h_per_m if result.inductance_model==IDEAL_GROUND else section.inductance.projected_h_per_m
            add(f"Tramo {i}: L de fases",l*1e6,"mH/km")
            add(f"Tramo {i}: Lsub",section.inductance.primitive_h_per_m,"H/m",g.labels)
    return render_pdf("STE Calculator · Haces y transposición",notes,blocks)
