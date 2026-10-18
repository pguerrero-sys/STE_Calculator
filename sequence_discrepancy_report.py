"""Informe de validación 7E, sin sustituir informes ni modelos de etapas previas."""

from html import escape
from io import BytesIO
from pathlib import Path
import numpy as np
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet,ParagraphStyle
from reportlab.platypus import (SimpleDocTemplate,Paragraph,Spacer,KeepTogether,
                                LongTable,TableStyle,PageBreak)
from .printing import PAGE_SIZE,MARGIN,TABLE_WIDTH,font_name,MatrixBlock,matrix_tables


def discrepancy_record(analysis):
    def encode(z):
        return {"real":np.asarray(z).real.tolist(),"imag":np.asarray(z).imag.tolist()}
    scenarios=[]
    for s in analysis['scenarios']:
        scenarios.append({"name":s.name,"R_entrada_ohm_km":s.resistance_input_ohm_km.tolist(),
            "Zsub_ohm_m":encode(s.primitive_ohm_per_m),"Zfase_original_ohm_m":encode(s.original_phase_ohm_per_m),
            "Zfase_transpuesta_ohm_m":encode(s.transposed_phase_ohm_per_m),"Z012_ohm_m":encode(s.sequence_ohm_per_m),
            "Z012_escalar_ohm_m":encode(s.scalar_sequence_ohm_per_m),"residuo_escalar_ohm_m":s.scalar_residual_ohm_per_m,
            "Isub_por_Ifase":encode(s.response),"reparto_desigual":None if s.current_sharing is None else {
                "residuo_corriente":s.current_sharing.current_residual,"residuo_gradiente":s.current_sharing.voltage_residual,
                "cond_Zsub":s.current_sharing.condition_primitive,"cond_Yfase":s.current_sharing.condition_phase_admittance}})
    return {"etapa":"7E","entradas_originales":analysis['case'].metadata,"referencia_PSCAD":analysis['case'].pscad,
        "convencion":"exp(jωt), a=exp(j2π/3), secuencias 0/1/2, Z012=A^-1 Zabc A",
        "PSCAD_Zfase_transpuesta_ohm_m":encode(analysis['pscad_phase_ohm_m']),
        "PSCAD_Z012_desde_fases_ohm_m":encode(analysis['pscad_sequence_ohm_m']),
        "PSCAD_Z012_escalar_ohm_m":encode(analysis['pscad_scalar_ohm_m']),
        "PSCAD_Z012_publicada_ohm_m":encode(analysis['pscad_published_sequence_ohm_m']),
        "PSCAD_residuo_publicacion_ohm_km":analysis['pscad_publication_residual_ohm_km'],
        "E":analysis['incidence'].tolist(),"T_Iguales":analysis['weights'].tolist(),"escenarios":scenarios,
        "comparacion_secuencias":analysis['comparison'].to_dict(orient='records'),
        "corrientes_primer_tramo_original":analysis['currents'].to_dict(orient='records'),
        "cancelacion_R1":analysis['cancellation'],
        "presupuesto_resistencia_positiva":analysis['positive_resistance_budget'],
        "advertencia":"La sustitución DC y el reparto desigual son diagnósticos con hipótesis explícitas, no reproducción del modelo interno PSCAD. Datos y salidas 7D intactos."}


def discrepancy_pdf(analysis):
    styles=getSampleStyleSheet()
    for s in styles.byName.values():
        s.fontName=font_name()
    styles['BodyText'].fontSize=9
    styles['BodyText'].leading=13
    styles['BodyText'].spaceAfter=7
    styles['BodyText'].splitLongWords=True
    styles.add(ParagraphStyle(name='Equation7E',parent=styles['BodyText'],backColor=colors.HexColor('#edf5f7'),borderPadding=7,spaceBefore=8,spaceAfter=12))
    story=[]
    def p(text):
        story.append(Paragraph(escape(str(text)),styles['BodyText']))
    def heading(text):
        story.append(Paragraph(escape(text),styles['Heading2']))
    def equation(*lines):
        story.append(Paragraph('<br/>'.join(escape(line) for line in lines),styles['Equation7E']))
    def table(headers,rows,widths):
        # Párrafos en etiquetas largas; alturas automáticas y encabezados repetidos.
        data=[[Paragraph(escape(str(v)),styles['BodyText']) for v in headers]]
        for row in rows:
            data.append([Paragraph(escape(str(v)),styles['BodyText']) for v in row])
        tab=LongTable(data,colWidths=widths,repeatRows=1,hAlign='LEFT')
        tab.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#e1eff2')),
            ('GRID',(0,0),(-1,-1),.3,colors.HexColor('#b9ced7')),('VALIGN',(0,0),(-1,-1),'TOP'),
            ('TOPPADDING',(0,0),(-1,-1),3),('BOTTOMPADDING',(0,0),(-1,-1),3)]))
        story.append(tab)
    def matrices(title,z,labels,columns=None,unit='Ω/km',factor=1000):
        if z.shape==(3,3) and columns is None:
            # Tres fases: seis columnas R/X intercaladas evitan partir una pareja
            # de matrices entre páginas y mantienen precisión científica completa.
            values=np.column_stack([component for j in range(3) for component in (z[:,j].real*factor,z[:,j].imag*factor)])
            names=tuple(prefix+str(label) for label in labels for prefix in ('R/','X/'))
            block=MatrixBlock(title,values,tuple(labels),names,unit,
                              'Secuencia' if tuple(labels)==('0','1','2') else 'Fase')
            for _,_,tab in matrix_tables(block):
                story.append(KeepTogether([Spacer(1,7),Paragraph(escape(f'{title} · R/X [{unit}]'),styles['Heading3']),tab]))
            return
        for part,values in (('R',z.real*factor),('X',z.imag*factor)):
            block=MatrixBlock(title+' · '+part,values,tuple(labels),tuple(columns or labels),unit)
            for start,end,tab in matrix_tables(block):
                suffix=f' · columnas {start+1}-{end}' if len(block.column_labels)>6 else ''
                story.append(KeepTogether([Spacer(1,7),Paragraph(escape(f'{title} · {part} [{unit}]{suffix}'),styles['Heading3']),tab]))
    story.append(Paragraph('STE Calculator · Etapa 7E',styles['Title']))
    heading('Validación de secuencias y análisis de discrepancias DOVE / PSCAD')
    p('Diagnóstico independiente: se conservan todos los cálculos, datos técnicos e informes de etapa 7D. No se ajusta ningún parámetro para forzar concordancia.')
    p('Datos originales: 60 Hz, ρ=100 Ω·m, cuatro subconductores por fase, separación 0.4572 m, radio exterior 0.011765 m y RMG individual 0.00954024 m. A=(-3,13), B=(3,13), C=(0,9) m.')
    p('STE mantiene P/Q finitos de Kersting y R_AC=0.1859 Ω/milla=0.115512904637 Ω/km por subconductor. PSCAD declara entrada R_DC=0.102 Ω/km por subconductor. Las correcciones internas AC de PSCAD no están identificadas completamente.')
    equation('a=exp(j2π/3); A=[[1,1,1],[1,a²,a],[1,a,a²]]; orden 0,1,2.',
             'Z012=A^-1 Zabc A; unidades conservadas.',
             'Matriz idealmente transpuesta: Z0=Zpropio+2 Zmutuo; Z1=Z2=Zpropio-Zmutuo.',
             'Error_R=100 |R_STE-R_PSCAD|/|R_PSCAD|; Error_X análogo, por separado.')
    p('Se transforma la matriz transpuesta de fases de cada programa. Como control adicional se compara con Zsq publicada en el TXT PSCAD, sin utilizar impedancias modales ni long-line corrected.')
    p(f"Residuo máximo PSCAD entre Z012 transformada y Zsq publicada: {analysis['pscad_publication_residual_ohm_km']:.3e} Ω/km; corresponde al redondeo de la salida textual.")
    heading('Comparación principal y sensibilidad DC · corrientes I/n')
    rows=[]
    for row in analysis['comparison'].iloc[:6].to_dict(orient='records'):
        rows.append(['AC original' if row['Escenario']==analysis['scenarios'][0].name else 'DC temporal',
            'Z'+str(row['Secuencia']),f"{row['STE_R_ohm_km']:.9f}",f"{row['STE_X_ohm_km']:.9f}",
            f"{row['PSCAD_R_ohm_km']:.9f}",f"{row['PSCAD_X_ohm_km']:.9f}",f"{row['Error_R_pct']:.6f}",f"{row['Error_X_pct']:.6f}"])
    table(['Escenario','Sec.','R STE','X STE','R PSCAD','X PSCAD','Error R [%]','Error X [%]'],rows,
          [90,38,*[(TABLE_WIDTH-128)/6]*6])
    p('Todas las impedancias de las tablas comparativas están en Ω/km. Los errores son absolutos; el signo de las diferencias se analiza a continuación.')
    story.append(PageBreak())
    heading('Por qué R1 difiere aproximadamente 10.01 %')
    c=analysis['cancellation']
    equation(f"R1_STE={c['Rs_STE_ohm_km']:.12f}-{c['Rm_STE_ohm_km']:.12f}={c['R1_STE_ohm_km']:.12f} Ω/km.",
             f"R1_PSCAD={c['Rs_PSCAD_ohm_km']:.12f}-{c['Rm_PSCAD_ohm_km']:.12f}={c['R1_PSCAD_ohm_km']:.12f} Ω/km.",
             'ΔR1=ΔRpropio-ΔRmutuo.',
             f"ΔR1=({c['delta_Rs_ohm_km']:.12f})-({c['delta_Rm_ohm_km']:.12f})={c['delta_R1_ohm_km']:.12f} Ω/km.")
    p(f"La propia STE es {c['signed_error_Rs_pct']:+.6f}% distinta y la mutua {c['signed_error_Rm_pct']:+.6f}% distinta de PSCAD. Como los signos son opuestos, ambas diferencias se suman en R1. El denominador R1_PSCAD es mucho menor que la propia.")
    equation(f"Aportes al porcentaje firmado: propio {c['contribution_own_percentage_points']:.6f} puntos + mutuo {c['contribution_mutual_percentage_points']:.6f} puntos = {c['signed_error_R1_pct']:.6f}%.",
             f"Factor de cancelación (|Rs|+|Rm|)/|Rs-Rm|={c['cancellation_factor']:.6f}.")
    p('Es amplificación relativa por resta, no un nuevo fenómeno físico ni evidencia de error en la transformación. No corresponde promediar los errores porcentuales de los elementos para obtener el error de secuencia.')
    heading('Sustitución temporal de resistencia: alcance y verificación')
    delta=(analysis['scenarios'][1].resistance_input_ohm_km[0]-analysis['scenarios'][0].resistance_input_ohm_km[0])/4
    equation('Zsub_DC=Zsub_AC+diag((R_DC-R_AC)/1000), matrices en Ω/m.',
             'Se conservan geometría, RMG, P/Q, frecuencia y resistividad.',
             f"Con I/n y n=4: ΔZfase=({delta:.12f} Ω/km) I3; por ello ΔZ012 es la misma diagonal real.")
    p('En el escenario I/n las reactancias permanecen idénticas: solo se cambia una copia de la diagonal resistiva primitiva. R1 pasa de estar por encima de PSCAD a estar por debajo; sustituir DC no reproduce PSCAD ni determina sus correcciones de piel, proximidad, temperatura o material. No se busca un valor intermedio que elimine el error.')
    budget=analysis['positive_resistance_budget']
    equation(f"STE con I/n: R1_AC=R_AC/4+R1_externo={budget['Rconductor_AC_sobre_4_ohm_km']:.12f}+{budget['R1_externo_STE_ohm_km']:.12f} Ω/km.",
             f"STE temporal DC: R1_DC={budget['Rconductor_DC_sobre_4_ohm_km']:.12f}+{budget['R1_externo_STE_ohm_km']:.12f} Ω/km.",
             f"PSCAD: R1-R_DC/4={budget['R1_PSCAD_menos_RDC_sobre_4_ohm_km']:.12f} Ω/km; no se asigna este exceso a una causa interna única.")
    heading('Fuentes y trazabilidad')
    p('Kersting, Distribution System Modeling and Analysis, CRC 2002: pp.86-90, matrices primitivas y ecuaciones de tensión/cambio de base, especialmente (4.48), (4.59)-(4.67); p.91 (4.68)-(4.72), y ejemplo 4.1 pp.94-95. Notas y registros previos del proyecto: referencias/secuencias.md, haces.md y transposicion_serie.md.')
    p('La reducción auxiliar de reparto desigual se deduce algebraicamente de la ecuación primitiva de tensión y las restricciones indicadas; no se presenta como una fórmula de reparto publicada por Kersting ni como método interno de PSCAD.')
    folder=Path(analysis['case'].metadata['ruta_JSON']).parent
    p('Carpeta de comparación: '+str(folder))
    p('Entradas: ste_carson.json. Resultados: DOVE_220kV_SinTransposicion_Prueba.txt y DOVE_220kV_ConTransposicion_Prueba.txt.')
    story.append(PageBreak())
    heading('Influencia del reparto de corrientes en el haz · diagnóstico')
    equation('Modelo 7D: Isub=T Iphase, T=E diag(1/n); Zigual=Tᵀ Zsub T.',
             'Alternativa: Zsub Isub=E Vgradiente, Iphase=Eᵀ Isub.',
             'W=solve(Zsub,E); Zdesigual=solve(Eᵀ W,I3); Isub=W Zdesigual Iphase.')
    p('E es la incidencia subconductor-fase. La alternativa supone gradiente longitudinal común por fase, conexiones ideales en los extremos, sección uniforme y eliminación serie sin shunt. No resuelve la distribución superficial dentro de cada cable, hebras ACSR, transitorios o conexiones reales de separadores. No sustituye al modelo I/n de la aplicación ni certifica el modelo PSCAD.')
    p('Se calcula primero el reparto en la sección original y después el promedio transpuesto de sus matrices de fase. Si las conexiones y corrientes varían longitudinalmente por las admitancias shunt, este equivalente de sección no es una solución distribuida exacta.')
    rows=[]
    for row in analysis['comparison'].to_dict(orient='records'):
        if row['Secuencia']!=1:
            continue
        s=next(s for s in analysis['scenarios'] if s.name==row['Escenario'])
        rows.append([s.name,f"{row['STE_R_ohm_km']:.9f}",f"{row['STE_X_ohm_km']:.9f}",f"{row['Error_R_pct']:.6f}",f"{row['Error_X_pct']:.6f}"])
    table(['Escenario','R1 [Ω/km]','X1 [Ω/km]','Error R1 [%]','Error X1 [%]'],rows,[245,*[(TABLE_WIDTH-245)/4]*4])
    for s in analysis['scenarios'][2:]:
        baseline=analysis['scenarios'][0 if s is analysis['scenarios'][2] else 1]
        difference=100*(s.sequence_ohm_per_m[1,1].real/baseline.sequence_ohm_per_m[1,1].real-1)
        p(f"{s.name}: R1 cambia {difference:+.6f}% respecto a su escenario I/n. Residuos: suma de corrientes {s.current_sharing.current_residual:.3e}, gradiente común {s.current_sharing.voltage_residual:.3e}. El efecto calculado aquí no explica por sí solo la discrepancia inicial del 10.01%.")
    rows=[]
    positive=analysis['currents'][analysis['currents'].Excitacion.str.startswith('Positiva')]
    for s in analysis['scenarios'][2:]:
        subset=positive[positive.Escenario==s.name]
        rows.append([s.name,f"{subset.Modulo_A.min():.8f}",f"{subset.Modulo_A.max():.8f}",
                     f"{subset.Desviacion_modulo_pct.abs().max():.5f}",f"{subset.Desfase_grados.abs().max():.5f}"])
    p('Excitación de diagnóstico del primer tramo original: Iphase=[1,a²,a] A. El modelo I/n fuerza 0.25 A por subconductor y fase alineada con la de su fase. La alternativa produce:')
    table(['Escenario','Mín. |Isub| [A]','Máx. |Isub| [A]','Máx. desv. módulo [%]','Máx. desfase [grados]'],rows,[245,*[(TABLE_WIDTH-245)/4]*4])
    story.append(PageBreak())
    heading('Conclusiones físicas')
    p('1. La transformación y las fórmulas escalares independientes concuerdan. La mayor diferencia porcentual de R1 surge de la cancelación entre propia y mutua.')
    p('2. La resistencia AC/DC es una diferencia de entradas importante: la sensibilidad DC reduce el valor de R1, pero no demuestra equivalencia con PSCAD ni permite atribuir un porcentaje causal único a cada aproximación.')
    p('3. Permitir reparto desigual cambia ligeramente el resultado bajo las hipótesis ensayadas y aumenta R1 respecto a I/n. No corrige el desacuerdo AC original. Ese efecto no es una cota universal para otras geometrías, frecuencias o conexiones.')
    p('4. Los detalles del cálculo interno AC/retorno por tierra de PSCAD no se identifican a partir de estas matrices. Se conservan las diferencias restantes sin modificar parámetros para forzar concordancia.')
    heading('Matrices de referencia PSCAD · derivadas de fase transpuesta')
    off_diagonal=analysis['pscad_sequence_ohm_m']-np.diag(np.diag(analysis['pscad_sequence_ohm_m']))
    p(f"La transposición ideal desacopla las secuencias. Los términos no diagonales conservados aquí son residuos de precisión numérica: máximo PSCAD={np.max(np.abs(off_diagonal))*1000:.3e} Ω/km, sin forzar ceros artificiales.")
    matrices('PSCAD fase transpuesta',analysis['pscad_phase_ohm_m'],('A','B','C'))
    matrices('PSCAD Z012 calculada',analysis['pscad_sequence_ohm_m'],('0','1','2'))
    for s in analysis['scenarios']:
        story.append(PageBreak())
        heading(s.name)
        p(f"Verificación independiente de escalares frente a A^-1 Zabc A: residuo máximo={s.scalar_residual_ohm_per_m:.3e} Ω/m. No se anulan numéricamente los términos fuera de la diagonal.")
        matrices('Matriz de fases transpuesta',s.transposed_phase_ohm_per_m,('A','B','C'))
        matrices('Matriz Z012 completa',s.sequence_ohm_per_m,('0','1','2'))
        rows=[]
        subset=analysis['comparison'][analysis['comparison'].Escenario==s.name]
        for row in subset.to_dict(orient='records'):
            rows.append(['Z'+str(row['Secuencia']),f"{row['STE_R_ohm_km']:.9f}",f"{row['STE_X_ohm_km']:.9f}",f"{row['Error_R_pct']:.6f}",f"{row['Error_X_pct']:.6f}"])
        table(['Secuencia','R [Ω/km]','X [Ω/km]','Error R [%]','Error X [%]'],rows,[80,*[(TABLE_WIDTH-80)/4]*4])
    def footer(canvas,doc):
        canvas.setFont(font_name(),8)
        canvas.drawString(MARGIN,20,'STE Calculator · Diagnóstico 7E: hipótesis explícitas, sin ajustar el modelo 7D')
        canvas.drawRightString(PAGE_SIZE[0]-MARGIN,20,f'Página {doc.page}')
    output=BytesIO()
    doc=SimpleDocTemplate(output,pagesize=PAGE_SIZE,leftMargin=MARGIN,rightMargin=MARGIN,topMargin=MARGIN,bottomMargin=MARGIN)
    doc.build(story,onFirstPage=footer,onLaterPages=footer)
    return output.getvalue()
