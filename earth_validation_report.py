"""Informe breve 7F: matrices y comparaciones controladas auditables."""
from io import BytesIO
from html import escape
import numpy as np
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether
from .printing import PAGE_SIZE, MARGIN, TABLE_WIDTH, font_name, MatrixBlock, matrix_tables
from .earth_validation import STATES


def earth_validation_pdf(analysis):
    styles=getSampleStyleSheet()
    for style in styles.byName.values():
        style.fontName=font_name()
    styles['BodyText'].fontSize=8.5
    styles['BodyText'].leading=11
    styles['BodyText'].spaceAfter=6
    styles.add(ParagraphStyle(name='Cell7F',parent=styles['BodyText'],fontSize=7.5,leading=9,spaceAfter=0))
    styles.add(ParagraphStyle(name='Source7F',parent=styles['BodyText'],fontSize=7,leading=9,spaceAfter=3,splitLongWords=True))
    story=[]
    def p(text,style='BodyText'):
        story.append(Paragraph(escape(str(text)),styles[style]))
    def h(text):
        p(text,'Heading2')
    def table(headers,rows,widths):
        cells=[[Paragraph(escape(str(v)),styles['Cell7F']) for v in row] for row in [headers,*rows]]
        tab=Table(cells,colWidths=widths,repeatRows=1,hAlign='LEFT')
        tab.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#deedf3')),
            ('GRID',(0,0),(-1,-1),.3,colors.HexColor('#b4c9d1')),('VALIGN',(0,0),(-1,-1),'TOP'),
            ('TOPPADDING',(0,0),(-1,-1),2),('BOTTOMPADDING',(0,0),(-1,-1),2)]))
        story.append(tab)
    def matrix(title,z):
        vals=np.column_stack([v for j in range(3) for v in (z[:,j].real*1000,z[:,j].imag*1000)])
        block=MatrixBlock(title,vals,('A','B','C'),('R/A','X/A','R/B','X/B','R/C','X/C'),'Ω/km')
        for _,_,tab in matrix_tables(block):
            tab.setStyle(TableStyle([('FONTSIZE',(0,0),(-1,-1),7),('LEADING',(0,0),(-1,-1),8),
                ('TOPPADDING',(0,0),(-1,-1),2),('BOTTOMPADDING',(0,0),(-1,-1),2)]))
            story.append(KeepTogether([Paragraph(escape(title+' · R/X [Ω/km]'),styles['Heading3']),tab,Spacer(1,5)]))

    p('STE Calculator · Etapa 7F','Title')
    h('DOVE: retorno por tierra y conductor ACSR frente a PSCAD')
    p('Ensayo controlado: solo cambia el método de retorno por tierra. Se conservan las etapas 7A-7E y los archivos originales. Ambos métodos son aproximados; P/Q finito no evalúa la integral completa de Carson. No se demuestra equivalencia con PSCAD.')
    p('Entradas STE originales: A=(-3,13), B=(3,13), C=(0,9) m; cuatro subconductores por fase, s=0.4572 m, r=0.011765 m, RMG=0.00954024 m; 60 Hz; ρ=100 Ω·m; sin guardas. Se usan las 12 coordenadas del JSON, sin reconstruirlas con otra orientación.')
    p('AC bibliográfica: 0.1859 Ω/milla = 0.115512904637 Ω/km por subconductor. DC temporal: 0.102 Ω/km, dato declarado para PSCAD. Se sustituye exclusivamente la diagonal resistiva de una copia; RMG, f, ρ y geometría permanecen iguales entre los dos métodos y entre escenarios.')
    h('Ecuaciones conservadas · Kersting pp.82-84')
    for text in (
        'Sij=√[(xi-xj)²+(hi+hj)²]; dij=Dij si i≠j, dii=RMGi; cosθ=(hi+hj)/Sij.',
        'k=8.565×10^-4 (Sij/0.3048) √(f/ρ); S en metros se convierte a pies; f en Hz, ρ en Ω·m.',
        'Zsub,ij=δij R_i/1000 + j 2ωg ln(Sij/dij) + 4ωg(Pij+jQij); ω=2πf; g=10^-7 H/m; Z en Ω/m.',
        'Modificado: P=π/8; Q=[7.6786-ln(Sij/0.3048)+0.5 ln(ρ/f)]/2.',
        'P/Q finito: P=π/8-k cosθ/(3√2)+(k² cos2θ/16)[0.6728+ln(2/k)].',
        'P/Q finito: Q=-0.0386+0.5 ln(2/k)+k cosθ/(3√2). Se conserva el redondeo bibliográfico.',
        'Zfase=Tᵀ Zsub T, T[u,p]=1/4 en su fase (corrientes iguales). Ztr=(Z+ΠᵀZΠ+(Π²)ᵀZΠ²)/3.',
        'Z012=A^-1 Zabc A; a=exp(j2π/3); A=[[1,1,1],[1,a²,a],[1,a,a²]]; orden 0,1,2.',
    ):
        p(text)
    pq=analysis['primitives']['kersting_pq_finite']
    p(f'k mínimo={pq.k.min():.9f}; máximo={pq.k.max():.9f}. Pequeño k; el umbral de software no garantiza una cota de error. La longitud de 100 km no interviene en las matrices por unidad de longitud.')
    h('Errores de las matrices de fases frente a PSCAD Deri-Semlyen (0)')
    rows=[]
    phase_rows=analysis['comparison'].query("Dominio == 'fase'")
    for s in analysis['scenarios']:
        sub=phase_rows[(phase_rows.Metodo==s['method'])&(phase_rows.Resistencia==s['resistance'])&(phase_rows.Estado==s['state'])]
        rows.append([s['method']+' / '+('AC' if s['resistance'].startswith('AC') else 'DC'),
            'Sin' if s['state']==STATES[0] else 'Ideal',
            *[f'{sub[k].max():.9f}' for k in ('Abs_delta_R_ohm_km','Abs_delta_X_ohm_km')],
            *[f'{sub[k].max():.6f}' for k in ('Error_R_pct','Error_X_pct')]])
    table(['Método / R','Transp.','máx |ΔR| [Ω/km]','máx |ΔX| [Ω/km]','máx error R %','máx error X %'],
          rows,[120,50,*[(TABLE_WIDTH-170)/4]*4])

    for state in STATES:
        story.append(PageBreak())
        h('Matrices de fases · '+('sin transposición' if state==STATES[0] else 'transposición ideal completa'))
        p('Se muestran todas las entradas R y X por separado, sin usar impedancias modales ni valores corregidos por línea larga. Cada pareja R/X pertenece a la columna de fase indicada. Signo inductivo +jX.')
        matrix('PSCAD Deri-Semlyen (0) · matriz de fases del TXT',analysis['pscad_phase_ohm_m'][state])
        for s in analysis['scenarios']:
            if s['state']==state:
                matrix(s['method']+' · '+s['resistance'],s['phase_ohm_m'])
        p('Las contribuciones de conductor, referencia geométrica con suelo ideal y corrección por tierra, las primitivas 12×12 y las diferencias de cada elemento se exportan en JSON/CSV. No se modifica la capacitancia ni la inductancia con suelo ideal.')

    story.append(PageBreak())
    h('Secuencias y errores frente a PSCAD Deri-Semlyen (0)')
    p('Unidades R, X y diferencias: Ω/km. Δ=STE-PSCAD; error%=100|Δ|/|PSCAD|, por componente. Los valores diagonales de Z012 no transpuesta coinciden con los de su promedio cíclico (hasta redondeo); se calculan ambos y se conservan sus matrices completas en JSON/CSV. Sin transposición hay acoplamientos de secuencia y los tres escalares no describen toda la línea.')
    ref=analysis['pscad_sequence_ohm_m'][STATES[1]]*1000
    table(['PSCAD transpuesta','R [Ω/km]','X [Ω/km]'],
          [['Z'+str(k),f'{ref[k,k].real:.10f}',f'{ref[k,k].imag:.10f}'] for k in range(3)],
          [180,(TABLE_WIDTH-180)/2,(TABLE_WIDTH-180)/2])
    p('Escenarios STE transpuestos; Z2=Z1 por reciprocidad y transposición ideal. Sin transposición, los datos diagonales PSCAD difieren hasta 2×10^-9 Ω/km por redondeo de los TXT. Se usan referencias distintas para cada estado en los CSV.')
    rows=[]
    df=analysis['comparison']
    for row in df[(df.Dominio=='secuencia')&(df.Fila==df.Columna)&(df.Estado==STATES[1])].to_dict('records'):
        rows.append([row['Metodo']+' / '+('AC' if row['Resistencia'].startswith('AC') else 'DC'),
            'Z'+row['Fila'],*[f'{row[k]:.9f}' for k in ('R_ohm_km','X_ohm_km','Delta_R_ohm_km','Delta_X_ohm_km')],
            f"{row['Error_R_pct']:.6f}",f"{row['Error_X_pct']:.6f}"])
    table(['Método / R','Sec.','R STE','X STE','ΔR','ΔX','Error R %','Error X %'],rows,
          [115,35,*[(TABLE_WIDTH-150)/6]*6])
    p('Control independiente: para la matriz transpuesta, Z0=Zpropio+2Zmutuo y Z1=Z2=Zpropio-Zmutuo. No se fuerzan a cero términos de Z012.')
    p('CSV: porcentajes omitidos si |referencia|≤10^-12 del máximo de su componente R/X; se conservan el valor y la diferencia absoluta. Evita interpretar cocientes sobre residuos de precisión numérica como errores físicos.')
    rows=[]
    for name,seqs in [('PSCAD',analysis['pscad_sequence_ohm_m']),*[(s['method']+' / '+s['resistance'],{s['state']:s['sequence_ohm_m']}) for s in analysis['scenarios'] if s['state']==STATES[0]]]:
        z=seqs[STATES[0]]*1000
        off=z-np.diag(np.diag(z))
        rows.append([name,f'{np.max(np.abs(off)):.9f}'])
    table(['Sin transposición: acoplamientos conservados','máx |Z012,ij|, i≠j [Ω/km]'],rows,[TABLE_WIDTH-220,220])

    story.append(PageBreak())
    h('PSCAD integración numérica directa de Carson (2) · transpuesta')
    numerical=analysis['numerical_reference']
    p('Nueva referencia suministrada y confirmada por el usuario en la interfaz PSCAD: EarthImpedanceFormula=2; método original 0=Deri-Semlyen. 60 Hz, ρ=100 Ω·m, permitividad relativa final=1, cuatro DOVE/fase y sin guardas. No se extrapola este ensayo al caso sin transposición.')
    matrix('PSCAD integración numérica (2) · matriz suministrada [Ω/km]',numerical['phase_ohm_m'])
    ref=numerical['sequence_ohm_m']*1000
    p('Secuencias obtenidas de la matriz de fases mediante A^-1 Zabc A y verificadas por Z0=Zs+2Zm, Z1=Z2=Zs-Zm:')
    table(['Referencia numérica PSCAD','R [Ω/km]','X [Ω/km]'],
          [['Z'+str(k),f'{ref[k,k].real:.10f}',f'{ref[k,k].imag:.10f}'] for k in range(3)],
          [180,(TABLE_WIDTH-180)/2,(TABLE_WIDTH-180)/2])
    rows=[]
    for row in analysis['numerical_comparison'].query("Dominio == 'secuencia' and Fila == Columna").to_dict('records'):
        rows.append([row['Metodo']+' / '+('AC' if row['Resistencia'].startswith('AC') else 'DC'),
            'Z'+row['Fila'],*[f'{row[k]:.9f}' for k in ('R_ohm_km','X_ohm_km','Delta_R_ohm_km','Delta_X_ohm_km')],
            f"{row['Error_R_pct']:.6f}",f"{row['Error_X_pct']:.6f}"])
    table(['Método / R','Sec.','R STE','X STE','ΔR','ΔX','Error R %','Error X %'],rows,[115,35,*[(TABLE_WIDTH-150)/6]*6])
    p('Δ=STE-integración numérica PSCAD. Las matrices STE son exactamente las de los escenarios anteriores; no se cambia RMG, resistencia, geometría ni ecuaciones. Los CSV conservan las 144 comparaciones Deri-Semlyen y añaden 72 comparaciones con integración numérica, incluyendo todos los elementos de fase y secuencia.')
    p('La matriz Y completa de la nueva simulación fue suministrada. Comparada con el bloque SHUNT ADMITTANCE MATRIX (Y) [mhos/m] del TXT transpuesto anterior, coincide elemento a elemento: máximo |ΔY|=0 S/m a la precisión suministrada. No se usan valores corregidos por línea larga ni se modifica la capacitancia STE.')
    table(['Y nueva [S/m]','A','B','C'],
          [[phase,*['1e-11 + j5.20392911e-9' if i==j else '-j1.24409590e-9' for j in range(3)]] for i,phase in enumerate(('A','B','C'))],
          [90,*[(TABLE_WIDTH-90)/3]*3])

    story.append(PageBreak())
    h('Qué explica el cambio de método · mismas entradas')
    p('Diferencias P/Q finito menos modificado, con resistencia AC y transposición. El mismo cambio se obtiene con DC: la sustitución resistiva es idéntica en los dos métodos.')
    rows=[]
    control=analysis['controlled']
    for row in control[(control.Dominio=='secuencia')&(control.Fila==control.Columna)&(control.Resistencia.str.startswith('AC'))&(control.Estado==STATES[1])].to_dict('records'):
        rows.append(['Z'+row['Fila'],f"{row['Delta_R_ohm_km']:.12f}",f"{row['Delta_X_ohm_km']:.12f}",f"{row['Error_R_pct']:.6f}",f"{row['Error_X_pct']:.6f}"])
    table(['Sec.','ΔR [Ω/km]','ΔX [Ω/km]','|ΔR|/|Rmod| %','|ΔX|/|Xmod| %'],rows,[50,*[(TABLE_WIDTH-50)/4]*4])
    p('1. El método afecta principalmente al modo cero. En este truncamiento, ΔQ=c+β(hi+hj), con β=(8.565e-4/0.3048)√(f/ρ)/(3√2). Su proyección sobre corrientes equilibradas se anula; por eso X1 y X2 no cambian entre estas dos aproximaciones. No demuestra coincidencia con la integral exacta.')
    p('2. Frente a Deri-Semlyen, el error R1 con AC sigue siendo 9.994678 % (modificado) y 10.014532 % (P/Q). La resta propia-mutua amplifica diferencias, como se verificó en 7E. Frente a integración numérica los errores se recalculan en la tabla anterior; no se atribuye el residuo exclusivamente al retorno por tierra.')
    p('3. Cambiar temporalmente a DC reduce R1 exactamente en (0.102-0.1859/1.609344)/4=-0.003378226159 Ω/km y no altera X. Esa sensibilidad no calcula la impedancia interna AC de ACSR ni identifica piel, proximidad, hebras o RMG efectivo PSCAD.')
    delta=(analysis['numerical_reference']['sequence_ohm_m']-analysis['pscad_sequence_ohm_m'][STATES[1]])*1000
    p(f'4. Cambio PSCAD numérica menos Deri-Semlyen: ΔZ0={delta[0,0].real:+.10f}+j({delta[0,0].imag:+.10f}) Ω/km; ΔZ1=ΔZ2={delta[1,1].real:+.10f}+j({delta[1,1].imag:+.10f}) Ω/km. Afecta principalmente a Z0; R1 cambia muy poco y su discrepancia AC persiste.')
    h('Auditoría física · datos conocidos y pendientes')
    table(['Parámetro','Evidencia / límite'],analysis['audit'],[145,TABLE_WIDTH-145])

    story.append(PageBreak())
    h('Documentación PSCAD: conclusiones y límites de atribución')
    p('Actualización de evidencia: el usuario confirmó en la interfaz del caso que EarthImpedanceFormula=0 selecciona Deri-Semlyen y 2 selecciona Direct numerical integration. Se sustituye la conclusión anterior de selector desconocido por esta confirmación explícita, sin presentarla como una tabla universal para otras versiones. La ayuda Ground Plane distingue ambos procedimientos; el ejemplo documental aislado no bastaba para identificar el código.')
    p('Entradas PSCAD conocidas, suministradas desde el archivo de entrada: Sag=0 m; Strand Radius=0.001858 m; Number of Outer Strands=16; Total Number of Strands=26; Conductor Relative Permeability=1; DCResistance=0.102 Ω/km; GroundWires=0; GroundPermittivity final=1. Se corrigen las afirmaciones anteriores de información faltante. Los nombres de los campos se conservan sin inferir una descomposición adicional Al/acero ni un RMG efectivo.')
    p('La documentación de bibliotecas y las ecuaciones verificadas se conservan como referencias generales. Los datos de hebras y permeabilidad suministrados se distinguen del tratamiento interno de esas entradas: no se aplica R exp(-1/4) al ACSR ni se introduce ningún parámetro en los cálculos STE para forzar concordancia.')
    p('Conductor Elimination describe expansión de subconductores, corrientes repartidas igualmente, tensión común y reducción de Kron. Esta descripción general no permite afirmar que su implementación sea algebraicamente idéntica a TᵀZT para este caso. El diagnóstico de reparto desigual de 7E sigue siendo un escenario auxiliar bajo gradiente longitudinal común; no demuestra el algoritmo interno de PSCAD ni explica por sí solo el residuo.')
    p('Demostrado: conservación del caso 7D y de las matrices STE previas, diferencias entre las dos referencias PSCAD, desplazamiento DC exacto y concordancia de la nueva matriz con sus secuencias. El cambio de método PSCAD reduce el desacuerdo reactivo de modo cero, pero no elimina el residuo de secuencia positiva. No hay equivalencia exacta entre el modelo ACSR de PSCAD y el modelo R_AC/RMG de STE.')
    p('Pendientes de identificación: RMG efectivo e impedancia interna AC calculados por PSCAD, tratamiento exacto de las hebras en ese cálculo, correcciones internas de frecuencia y reducción efectiva del haz. No se confunden esos detalles internos con la disponibilidad de los datos de entrada, que sí están suministrados. La versión de PSCAD/LCP y una descripción de sus algoritmos ayudarían a cerrar la comparación física. No se ajustan R ni RMG a las matrices de salida; GroundPermittivity=1 no se introduce como corrección artificial de la impedancia serie STE.')
    h('Fuentes utilizadas · consulta 16-10-2026')
    for i,(title,url) in enumerate(analysis['sources'],1):
        p(f'[{i}] {title}. {url}','Source7F')
    p('[7] Parámetros del archivo de entrada, selectores comprobados en interfaz y matrices Z/Y suministrados por el usuario, registrados en referencias/Datos_DOVE_PSCAD_para_Codex/referencias/comparacion_pscad/pscad_integracion_numerica_confirmada.json. Y anterior: TXT DOVE transpuesto, bloque SHUNT ADMITTANCE MATRIX, líneas 63-66.','Source7F')
    p('Material local complementario: referencias/Carson.pdf, diap.5-8; notas STE 01-10-26, pp.PDF1-2. Las erratas de la presentación se resuelven con Kersting p.83 según referencias/carson.md. Entradas: ste_carson.json, ambos DOVE_220kV_*_Prueba.txt y LEEME del directorio comparacion_pscad. Procedimiento y pruebas: referencias/validacion_tierra_acsr.md.','Source7F')
    def footer(canvas,doc):
        canvas.setFont(font_name(),8)
        canvas.drawString(MARGIN,20,'STE Calculator · 7F · Sin ajustes de parámetros ni equivalencia PSCAD demostrada')
        canvas.drawRightString(PAGE_SIZE[0]-MARGIN,20,f'Página {doc.page}')
    output=BytesIO()
    SimpleDocTemplate(output,pagesize=PAGE_SIZE,leftMargin=MARGIN,rightMargin=MARGIN,
        topMargin=MARGIN,bottomMargin=MARGIN).build(story,onFirstPage=footer,onLaterPages=footer)
    return output.getvalue()
