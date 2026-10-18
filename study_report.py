"""Dos salidas explícitas: resumen compacto y anexo completo solicitado."""
from dataclasses import fields,is_dataclass
from html import escape
from io import BytesIO
import numpy as np
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle,PageBreak,KeepTogether
from pypdf import PdfReader,PdfWriter
from .printing import PAGE_SIZE,MARGIN,TABLE_WIDTH,font_name,MatrixBlock,matrix_tables,render_pdf,EquationBlock,double_circuit_pdf,transposition_pdf
from .study import derived_matrices,rmg_values
from .inductance import IDEAL_GROUND,NO_GROUND


def study_record(study):
    def encode(v):
        if isinstance(v,np.ndarray):
            return {'real':v.real.tolist(),'imag':v.imag.tolist()} if np.iscomplexobj(v) else v.tolist()
        if isinstance(v,np.generic): return encode(v.item())
        if isinstance(v,complex): return {'real':v.real,'imag':v.imag}
        if is_dataclass(v): return {f.name:encode(getattr(v,f.name)) for f in fields(v)}
        if isinstance(v,dict): return {str(k):encode(x) for k,x in v.items()}
        if isinstance(v,(tuple,list)): return [encode(x) for x in v]
        return v
    return dict(format='STE estudio unificado 1',units='Matrices internas SI por metro; resistencia tabulada Ω/km',study=encode(study))


def summary_pdf(study,l_model=IDEAL_GROUND,c_models=(IDEAL_GROUND,),complete=None,external=None):
    complete=study.config.complete if complete is None else complete
    styles=getSampleStyleSheet()
    for style in styles.byName.values(): style.fontName=font_name()
    styles['BodyText'].fontSize=8;styles['BodyText'].leading=10;styles['BodyText'].spaceAfter=5
    story=[];labels=study.geometry.phase_labels
    def p(text,style='BodyText'): story.append(Paragraph(escape(str(text)),styles[style]))
    def table(head,rows,widths):
        data=[[Paragraph(escape(str(v)),styles['BodyText']) for v in row] for row in [head,*rows]]
        t=Table(data,colWidths=widths,repeatRows=1,hAlign='LEFT')
        t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#e0edf1')),('GRID',(0,0),(-1,-1),.3,colors.grey),('VALIGN',(0,0),(-1,-1),'TOP'),('TOPPADDING',(0,0),(-1,-1),2),('BOTTOMPADDING',(0,0),(-1,-1),2)]))
        story.append(t);story.append(Spacer(1,7))
    def matrix(title,m,unit,factor=1):
        if m is None: p(title+': no disponible; ver diagnóstico.');return
        for _,_,tab in matrix_tables(MatrixBlock(title,np.asarray(m)*factor,labels,labels,unit)):
            tab.setStyle(TableStyle([('TOPPADDING',(0,0),(-1,-1),2),('BOTTOMPADDING',(0,0),(-1,-1),2)]))
            story.append(KeepTogether([Paragraph(escape(title+' ['+unit+']'),styles['Heading3']),tab,Spacer(1,6)]))
    cfg=study.config
    p('STE Calculator · Informe resumido','Title');p(cfg.case_name)
    p(f'{len(labels)//3} circuito(s), {len(labels)} fases; transposición automática={complete}. V={cfg.voltage_kv} kV; f={cfg.frequency_hz} Hz; L={cfg.length_km} km; potencia total={cfg.power} {cfg.power_kind}; fp={cfg.power_factor}; carga={cfg.load_type}.')
    rmgs=rmg_values(study)
    table(['Fase','X [m]','Y [m]','n','Radio [m]','RMG usado [m]'],
          [[label,s.center.x_m,s.center.y_m,s.count,f'{s.radius_m:.9f}','—' if rmgs is None else f'{rmgs[i]:.9f}'] for i,(label,s) in enumerate(zip(labels,study.geometry.specs))],
          [80,100,100,50,160,TABLE_WIDTH-490])
    r=study.resistance
    if r is not None:
        p(r.mode,'Heading3')
        p(f'I total={r.total_current_a} A; reparto uniforme. Fronteras: <25 %→25 °C, 25–75 % inclusive→50 °C, >75 %→75 °C. No es un cálculo térmico.')
        table(['Fase','I sub [A]','Carga [%]','T tabla [°C]','R conductor [Ω/km]','R fase [Ω/km]'],
              [[label,'—' if r.subconductor_current_a is None else f'{r.subconductor_current_a[i]:.5f}',
                '—' if r.load_percent is None else f'{r.load_percent[i]:.5f}',r.temperatures_c[i],f'{r.conductor_ohm_km[i]:.8f}',f'{r.phase_ohm_km[i]:.8f}'] for i,label in enumerate(labels)],
              [65,100,90,90,190,TABLE_WIDTH-545])
        if r.parallel_ohm_km is not None:p('Circuitos declarados en paralelo: R equivalente por fase [Ω/km]='+str(r.parallel_ohm_km.tolist())+'. No se reduce L/C automáticamente.')
    for name,message in study.messages.items():p(name+': '+message)
    story.append(PageBreak());p('Inductancia y capacitancia','Heading1')
    matrix('L · '+l_model,study.variants[l_model,complete].l_h_per_m,'mH/km',1e6)
    for model in c_models:
        matrix('C · '+model,study.variants[model,complete].c_f_per_m,'nF/km',1e12)
    p('Sin suelo: ΣI=0 para L, Σq=0 para C; potencial común indeterminado. C no es capacitancia absoluta a tierra. H/m×10⁶=µH/m=mH/km; F/m×10¹²=nF/km.')
    p('Capacitancia transpuesta: se conserva el promedio de P efectiva antes de invertir, bajo carga común. No equivale universalmente al promedio C ni a una cascada distribuida.')
    story.append(PageBreak());p('Impedancia y admitancia','Heading1')
    d=derived_matrices(study,l_model,c_models[0],complete)
    if d['Z_ohm_m'] is not None:
        matrix('R de Z=R_AC+jωL',d['Z_ohm_m'].real,'Ω/km',1000)
        matrix('X de Z=R_AC+jωL',d['Z_ohm_m'].imag,'Ω/km',1000)
    for model in c_models:
        y=derived_matrices(study,l_model,model,complete)['Y_s_m']
        if y is not None:matrix('B de Y=jωC · '+model,y.imag,'S/km',1000)
    p('Y no incluye conductancia de fuga. Z geométrica no incluye retorno por tierra de resistividad finita; Carson se mantiene como modelo serie distinto.')
    story.append(PageBreak());p('Comparaciones y fuentes','Heading1')
    rows=[]
    for model in c_models:
        for mode in (False,True):
            v=study.variants[model,mode]
            rows.append([model,'Automática' if mode else 'Sin',f'{v.c_f_per_m[0,0]*1e12:.9f}',f'{v.c_f_per_m[0,1]*1e12:.9f}'])
    table(['Modelo C','Transposición','C propia A [nF/km]','C mutua AB [nF/km]'],rows,[210,100,200,TABLE_WIDTH-510])
    if external:
        p('Contraste externo PSCAD: '+external['source'])
        table(['Secuencia','R STE','X STE','R PSCAD','X PSCAD','Error R %','Error X %'],
              [[r['Elemento'],*[f'{r[k]:.7g}' if r[k] is not None else '—' for k in ('R_STE','X_STE','R_PSCAD','X_PSCAD','Error_R_pct','Error_X_pct')]] for r in external['sequences']],
              [65,*[(TABLE_WIDTH-65)/6]*6])
    if study.carson and study.carson.get('phase') is not None:
        p('Carson · '+cfg.carson_method+'; R_AC y RMG documentados, suelo ρ='+str(cfg.resistivity_ohm_m)+' Ω·m. Resultado independiente; ver anexo para primitivas, Kron y secuencias.')
        matrix('R Carson',study.carson['phase'].real,'Ω/km',1000)
        matrix('X Carson',study.carson['phase'].imag,'Ω/km',1000)
    for text in sorted({source for d in cfg.conductor_data for source in d.sources.values()}):p(text)
    p('Resistencia: Notas de sistemas de transmision.pdf, pp.PDF109–111; biblioteca: Tablas_ACSR.pdf, pp.PDF1–2. Capacidad tabulada: condiciones térmicas no especificadas en las páginas disponibles.')
    p('Modelos verificados: referencias/inductancia.md, capacitancia.md, haces.md, doble_circuito.md, carson.md, kron.md, secuencias.md y correccion_transposicion_automatica.md. PSCAD usa en el ensayo histórico R_DC=0.102 Ω/km; la tabla da DOVE R_DC20=0.1007 Ω/km. No se sustituyen estas fuentes ni se afirma equivalencia física.')
    def footer(canvas,doc):
        canvas.setFont(font_name(),8);canvas.drawString(MARGIN,20,'STE Calculator · Resumen · Modelos y fuentes identificados');canvas.drawRightString(PAGE_SIZE[0]-MARGIN,20,str(doc.page))
    out=BytesIO();SimpleDocTemplate(out,pagesize=PAGE_SIZE,leftMargin=MARGIN,rightMargin=MARGIN,topMargin=MARGIN,bottomMargin=MARGIN).build(story,onFirstPage=footer,onLaterPages=footer)
    return out.getvalue()


def annex_pdf(study,l_model=IDEAL_GROUND,c_models=(IDEAL_GROUND,)):
    """Exportación completa explícita; conserva las primitivas de cada modelo C solicitado."""
    writer=PdfWriter()
    r=study.resistance
    notes=['Anexo matemático completo; separado del informe resumido. Sin truncar tramos ni primitivas.',
           'I_total=S_total/(√3 V_LL); S=P/fp si se ingresan MW; I_sub=I_total/(Nc n).',
           'Carga%=100 I_sub/I_nom. Carga<25:25 °C; 25≤carga≤75:50 °C; carga>75:75 °C.',
           'R_haz=R_AC/n; equivalente resistivo paralelo=1/Σ(1/Rfase) solo si se declara la conexión.',
           'Zgeom=diag(Rfase)/1000+j2πfL [Ω/m]; Y=j2πfC [S/m]. No son una reproducción de PSCAD.']
    if r:
        for i,label in enumerate(study.geometry.phase_labels):
            notes.append(f'{label}: I_sub={None if r.subconductor_current_a is None else r.subconductor_current_a[i]} A; carga={None if r.load_percent is None else r.load_percent[i]} %; T tabulada={r.temperatures_c[i]} °C; R_AC={r.conductor_ohm_km[i]} Ω/km; n={study.geometry.specs[i].count}; Rfase={r.phase_ohm_km[i]} Ω/km. Fuente: {r.sources[i]}')
    writer.append(PdfReader(BytesIO(render_pdf('STE Calculator · Anexo matemático',notes,[]))))
    for model in dict.fromkeys((l_model,*c_models)):
        v=study.variants[model,study.config.complete]
        content=double_circuit_pdf(v,study.config.frequency_hz) if len(study.geometry.specs)==6 else transposition_pdf(v)
        writer.append(PdfReader(BytesIO(content)))
    if study.carson:
        blocks=[]
        for t,s in enumerate(study.carson['sections'],1):
            p=s['phase'];primitive=p.primitive
            for component,values in (('R',primitive.z_ohm_per_m.real),('X',primitive.z_ohm_per_m.imag)):
                blocks.append(MatrixBlock(f'Carson tramo {t}: {component} primitiva',values*1000,primitive.labels,primitive.labels,'Ω/km'))
            for name,values in (('R conductor',primitive.z_conductor_ohm_per_m.real),('X geometría',primitive.z_geometry_ohm_per_m.imag),
                                ('R tierra',primitive.z_earth_ohm_per_m.real),('X tierra',primitive.z_earth_ohm_per_m.imag)):
                blocks.append(MatrixBlock(f'Carson tramo {t}: {name}',values*1000,primitive.labels,primitive.labels,'Ω/km'))
            if s['augmented']:
                a=s['augmented'];b=a.blocks
                for name,m in (('Zpp',b.pp),('Zpn',b.pn),('Znp',b.np),('Znn',b.nn)):
                    rows=tuple(str(i+1) for i in range(m.shape[0]));cols=tuple(str(i+1) for i in range(m.shape[1]))
                    for part,values in (('R',m.real),('X',m.imag)):blocks.append(MatrixBlock(f'Tramo {t}: {part} {name}',values*1000,rows,cols,'Ω/km'))
            if s['reduced']:
                for part,m in (('R',s['reduced'].z_ohm_per_m.real),('X',s['reduced'].z_ohm_per_m.imag)):
                    blocks.append(MatrixBlock(f'Tramo {t}: {part} Kron',m*1000,p.phase_labels,p.phase_labels,'Ω/km'))
        if study.carson.get('phase') is not None:
            phase=study.carson['phase'];seq=study.carson['sequence']
            for part,m in (('R',phase.real),('X',phase.imag)):
                blocks.append(MatrixBlock(f'{part} Carson promedio',m*1000,study.geometry.phase_labels,study.geometry.phase_labels,'Ω/km'))
            for part,m in (('R',seq.z_ohm_per_m.real),('X',seq.z_ohm_per_m.imag)):
                blocks.append(MatrixBlock(f'{part} Z012 completa',m*1000,seq.labels,seq.labels,'Ω/km'))
        writer.append(PdfReader(BytesIO(render_pdf('Carson, auxiliares y Kron',[
            'Fuentes y expresiones completas: referencias/carson.md y kron.md. Kron solo bajo ΔVaux=0 declarado. No elimina aislados ni conexiones desconocidas.',
            'Zreducida=Zpp-Zpn solve(Znn,Znp); Z012=A^-1 Zabc A; a=exp(j2π/3), orden 0,1,2 por circuito.'],blocks))))
    out=BytesIO();writer.write(out);return out.getvalue()
