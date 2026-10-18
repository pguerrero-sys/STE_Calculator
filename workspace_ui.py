"""Interfaz de cuatro secciones. Ninguna ecuación electromagnética vive aquí."""
import hashlib
import json
from dataclasses import replace
from pathlib import Path
import math
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from .conductor_library import load_catalog,ConductorData
from .models import Conductor,InputError
from .bundles import BundleSpec
from .double_circuit import build_circuit_geometry
from .inductance import IDEAL_GROUND,NO_GROUND,SOLID_UNIFORM,MANUFACTURER
from .transposition_schedule import MODES,automatic_schedule
from .resistance import ACADEMIC,SPECIFIED
from .study import StudyConfig,calculate_study,derived_matrices,section_arrays,positive_equivalents,external_comparisons,rmg_values
from .study_report import summary_pdf,annex_pdf,study_record
from .carson import METHODS,CarsonConductor
from .kron import AuxiliaryConductor,CONNECTIONS,UNKNOWN
from .series_comparison import pscad_reference,percent_error
from .sequences import phase_to_sequence

ROOT=Path(__file__).resolve().parents[1]
NAV=('Configuración y geometría','Resultados','Desarrollo matemático','Bibliografía y exportación')
GROUND={'Suelo ideal':IDEAL_GROUND,'Sin suelo · suma global cero':NO_GROUND}
PRESETS=('DOVE académico · sencillo, haz de cuatro','DOVE académico · doble, haz de dos','DOVE C6 · regresión histórica sin suelo')


def load_preset():
    choice=st.session_state['un_preset'];double=choice!=PRESETS[0]
    values=dict(un_circuits=2 if double else 1,un_voltage=220.,un_frequency=60.,un_length=100.,
                un_power=250.,un_power_kind='MVA',un_pf=.9,un_library='DOVE',un_bundles=True,
                un_count=2 if double else 4,un_spacing=.4572,un_rotation=0.,un_trans=MODES[1],
                un_rmode=ACADEMIC,un_case=choice,un_individual=choice==PRESETS[2],un_parallel=False)
    st.session_state.update(values)
    st.session_state.un_coords=[dict(Circuito=c,Fase=p,**{'X [m]':x,'Y [m]':h+12*(c-1)})
        for c in range(1,3 if double else 2) for p,x,h in (('A',-3.,13.),('B',3.,13.),('C',0.,9.))]
    st.session_state.un_cap='Sin suelo · suma global cero' if choice==PRESETS[2] else 'Comparar con y sin suelo'
    st.session_state.un_overrides=[{'Fase':p+"'"*(c-1),'n':2,'Separación [m]':.4572,'Rotación [°]':0.,'Radio [m]':.011765,'RMG [m]':.00954024,'Fuente geométrica':'Caso C6 validado del usuario; RMG histórico de DOVE, no tabla ACSR nueva'}
        for c in (1,2) for p in 'ABC'] if choice==PRESETS[2] else []
    st.session_state.un_revision=st.session_state.get('un_revision',0)+1
    st.session_state.pop('un_result',None)


def matrix(title,values,labels,unit='',factor=1):
    st.caption(title+(' ['+unit+']' if unit else ''))
    if values is None: st.info('Resultado no disponible con los datos actuales.');return
    arr=np.asarray(values)*factor
    if np.iscomplexobj(arr):
        part=st.radio('Componente · '+title,('R / parte real','X / parte imaginaria'),horizontal=True,key='part_'+title)
        arr=arr.real if part.startswith('R') else arr.imag
    cols=labels if arr.shape[1]==len(labels) else [str(i+1) for i in range(arr.shape[1])]
    st.dataframe(pd.DataFrame(arr,index=labels,columns=cols).style.format('{:.9g}'),width='stretch')


def plot(geometry,images=False):
    fig=go.Figure()
    for i,label in enumerate(geometry.phase_labels):
        ids=geometry.phase_index==i;xy=geometry.positions_m[ids]
        fig.add_trace(go.Scatter(x=xy[:,0],y=xy[:,1],mode='markers+text',name=label,
            text=[geometry.labels[j] for j in np.where(ids)[0]],textposition='top center',marker=dict(size=9)))
        if images:fig.add_trace(go.Scatter(x=xy[:,0],y=-xy[:,1],mode='markers',name='Imagen '+label,marker=dict(symbol='x')))
    x=geometry.positions_m[:,0];fig.add_trace(go.Scatter(x=[x.min()-2,x.max()+2],y=[0,0],mode='lines',name='Terreno'))
    fig.update_layout(template='plotly_white',height=350,margin=dict(l=20,r=20,t=15,b=30),xaxis_title='X [m]',yaxis_title='Y [m]',yaxis=dict(scaleanchor='x'),legend=dict(orientation='h'))
    return fig


def configure():
    for key,value in dict(un_frequency=60.,un_pf=.9,un_count=1,un_spacing=.4572,un_rotation=0.).items():
        if key not in st.session_state:st.session_state[key]=value
    a,b=st.columns([3,1])
    a.selectbox('Caso de comprobación',PRESETS,key='un_preset')
    b.button('Cargar caso DOVE',on_click=load_preset,width='stretch')
    st.caption(st.session_state.get('un_case','Configuración del usuario; completa los datos y pulsa Calcular.'))
    c=st.columns(4)
    voltage=c[0].number_input('Tensión línea-línea [kV]',value=None,format='%.6f',key='un_voltage')
    frequency=c[1].number_input('Frecuencia [Hz]',value=None,format='%.6f',key='un_frequency')
    length=c[2].number_input('Longitud [km]',value=None,format='%.6f',key='un_length')
    circuits=c[3].selectbox('Circuitos trifásicos',(1,2),key='un_circuits',format_func=lambda n:'Sencillo' if n==1 else 'Doble')
    st.caption('Tres fases por circuito. Triple circuito y superiores permanecen desactivados: el motor eléctrico está validado para uno o dos.')
    c=st.columns(4)
    power=c[0].number_input('Potencia total',value=None,key='un_power')
    power_kind=c[1].selectbox('Unidad de potencia',('MVA','MW'),key='un_power_kind')
    pf=c[2].number_input('Factor de potencia',value=None,format='%.6f',key='un_pf')
    load_type=c[3].selectbox('Tipo de carga',('Inductiva','Capacitiva','Resistiva'),key='un_load')
    catalog=load_catalog()
    c=st.columns([2,2,2])
    name=c[0].selectbox('Conductor',('Seleccionar conductor',*catalog,'Personalizado'),key='un_library')
    trans=c[1].selectbox('Transposición',MODES,key='un_trans')==MODES[1]
    bundles=c[2].checkbox('Activar haces',key='un_bundles')
    data=catalog.get(name)
    if name=='Personalizado':
        with st.expander('Datos del conductor personalizado',expanded=True):
            cols=st.columns(4)
            diameter=cols[0].number_input('Diámetro exterior [m]',value=None,format='%.9f',key='un_custom_d')
            gmr=cols[1].number_input('RMG documentado [m]',value=None,format='%.12f',key='un_custom_gmr')
            nominal=cols[2].number_input('Capacidad nominal documentada [A]',value=None,key='un_custom_nom')
            dc=cols[3].number_input('R_DC20 documentada [Ω/km]',value=None,format='%.8f',key='un_custom_dc')
            cols=st.columns(4);rac={str(t):cols[i].number_input(f'R_AC {t} °C [Ω/km]',value=None,format='%.8f',key=f'un_custom_r{t}') for i,t in enumerate((25,50,75))}
            rf=cols[3].number_input('Frecuencia de los datos AC [Hz]',value=60.,key='un_custom_rf')
            source=st.text_input('Fuente del conductor personalizado',key='un_custom_source')
            rmg_mode=st.selectbox('Modelo inductivo del personalizado',('RMG documentado','Macizo no magnético uniforme'),key='un_custom_model')
            solid=st.checkbox('Confirmo conductor circular macizo, μr=1 y corriente uniforme',key='un_solid_confirm',disabled=rmg_mode=='RMG documentado')
            data=ConductorData('Personalizado','No especificado',None,None,diameter,gmr,nominal,dc,rac,dict(resistance_capacity=source,diameter_gmr=source),resistance_frequency_hz=rf,
                               rmg_method=SOLID_UNIFORM if rmg_mode!='RMG documentado' and solid else MANUFACTURER)
    if data:
        st.dataframe(pd.DataFrame([{'Designación':data.designation,'Calibre AWG/MCM':data.gauge,'Hilos Al':data.aluminium_strands,'Hilos acero':data.steel_strands,'Diámetro [mm]':None if data.diameter_m is None else data.diameter_m*1000,'Radio [m]':data.radius_m,'RMG [m]':data.gmr_m,'I nominal [A]':data.nominal_current_a,'R_DC20 [Ω/km]':data.r_dc20_ohm_km,**{f'R_AC{t} [Ω/km]':data.r_ac_ohm_km.get(str(t)) for t in (25,50,75)}}]),hide_index=True,width='stretch')
        st.caption('Fuentes: '+'; '.join(data.sources.values()))
        for warning in data.warnings:st.warning(warning)
    c=st.columns(4)
    count_value=c[0].number_input('Subconductores por fase',1,4,value=None,key='un_count',disabled=not bundles)
    count=(None if count_value is None else int(count_value)) if bundles else 1
    spacing=c[1].number_input('Separación del haz [m]',value=None,format='%.6f',key='un_spacing',disabled=not bundles)
    layout=c[2].selectbox('Disposición del haz',('Simétrica regular','Rotación especificada'),key='un_layout')
    angle=c[3].number_input('Rotación del haz [°]',value=None,key='un_rotation',disabled=layout=='Simétrica regular')
    if layout=='Simétrica regular': angle=0.
    st.caption('Dos: par; tres: triángulo equilátero; cuatro: cuadrado. La separación es la distancia entre vecinos. Configuración global por defecto.')
    revision=st.session_state.get('un_revision',0)
    stored={(r['Circuito'],r['Fase']):r for r in st.session_state.get('un_coords',[])}
    rows=[stored.get((i,p),dict(Circuito=i,Fase=p,**{'X [m]':None,'Y [m]':None})) for i in range(1,circuits+1) for p in 'ABC']
    left,right=st.columns([1,1])
    with left:
        coords=st.data_editor(pd.DataFrame(rows),hide_index=True,disabled=['Circuito','Fase'],num_rows='fixed',column_config={name:st.column_config.NumberColumn(format='%.6f') for name in ('X [m]','Y [m]')},key=f'un_coords_{circuits}_{revision}',width='stretch')
        st.session_state.un_coords=coords.to_dict('records')
    phase_rows=[]
    individual=st.checkbox('Editar propiedades geométricas por fase',key='un_individual')
    if data and individual:
        with st.expander('Edición individual de haces y datos geométricos',expanded=True):
            old={r['Fase']:r for r in st.session_state.get('un_overrides',[])}
            phase_rows=[old.get(p+"'"*(i-1),{'Fase':p+"'"*(i-1),'n':count,'Radio [m]':data.radius_m,'RMG [m]':data.gmr_m,'Separación [m]':spacing,'Rotación [°]':angle,'Fuente geométrica':data.sources['diameter_gmr']}) for i in range(1,circuits+1) for p in 'ABC']
            phase_rows=st.data_editor(pd.DataFrame(phase_rows),hide_index=True,disabled=['Fase'],num_rows='fixed',column_config={
                'n':st.column_config.NumberColumn(min_value=1,max_value=4,step=1),
                **{name:st.column_config.NumberColumn(format='%.12f') for name in ('Radio [m]','RMG [m]')},
                'Separación [m]':st.column_config.NumberColumn(format='%.6f')},key=f'un_phases_{circuits}_{revision}',width='stretch').to_dict('records')
            st.session_state.un_overrides=phase_rows
    specs=[];conductor_data=[];geometry=None;geometry_error='Selecciona un conductor y completa las coordenadas.'
    if data:
        try:
            for i,r in enumerate(coords.to_dict('records')):
                edit=phase_rows[i] if phase_rows else None
                s=BundleSpec(Conductor(int(r['Circuito']),r['Fase'],r['X [m]'],r['Y [m]']),int(edit['n']) if edit else count,edit['Radio [m]'] if edit else data.radius_m,edit['Separación [m]'] if edit else spacing,edit['Rotación [°]'] if edit else angle)
                specs.append(s)
                conductor_data.append(replace(data,gmr_m=edit['RMG [m]'],sources=dict(data.sources,diameter_gmr=edit['Fuente geométrica'])) if edit else data)
            geometry=build_circuit_geometry(specs)
        except (InputError,ValueError,TypeError) as exc:geometry_error=str(exc)
    with right:
        if geometry is not None:st.plotly_chart(plot(geometry),width='stretch',key='un_geo_plot')
        else:st.info(geometry_error)
    with st.expander('Modelos, resistencia y conexiones',expanded=False):
        c=st.columns(3)
        l_model=c[0].selectbox('Modelo de inductancia',tuple(GROUND),key='un_lmodel')
        cap_choice=c[1].selectbox('Modelo de capacitancia',(*GROUND,'Comparar con y sin suelo'),key='un_cap')
        rmode=c[2].selectbox('Selección de resistencia',(ACADEMIC,SPECIFIED),key='un_rmode')
        temp=st.selectbox('Temperatura tabulada [°C]',(25,50,75),disabled=rmode==ACADEMIC,key='un_temp')
        parallel=st.checkbox('Declaro circuitos conectados en paralelo (solo equivalente resistivo)',key='un_parallel',disabled=circuits==1)
        st.caption('La selección académica no predice temperatura física. Datos AC de la biblioteca: 60 Hz. Sin suelo se exige suma global cero; el promedio P capacitivo conserva el modelo didáctico a carga común.')
        carson=st.checkbox('Calcular también impedancia de Carson',key='un_carson')
        c=st.columns(2)
        method=c[0].selectbox('Método Carson',tuple(METHODS),format_func=METHODS.get,key='un_carson_method',disabled=not carson)
        rho=c[1].number_input('Resistividad del terreno [Ω·m]',value=100.,key='un_rho',disabled=not carson)
        aux_count=st.number_input('Conductores auxiliares de Carson',0,8,0,key='un_aux_count',disabled=not carson)
        auxiliaries=[]
        if carson and aux_count:
            rows=[dict(Nombre=f'G{i+1}',Tipo='guard',**{'X [m]':None,'Y [m]':None,'R_AC [Ω/km]':None,'RMG [m]':None,'Conexión':UNKNOWN,'Justificación':'','Fuente':''}) for i in range(aux_count)]
            aux=st.data_editor(pd.DataFrame(rows),hide_index=True,num_rows='fixed',column_config={'Conexión':st.column_config.SelectboxColumn(options=list(CONNECTIONS)),'Tipo':st.column_config.SelectboxColumn(options=['guard','neutral'])},key=f'un_aux_{aux_count}',width='stretch')
            for r in aux.to_dict('records'):
                auxiliaries.append(AuxiliaryConductor(CarsonConductor(r['Nombre'],r['X [m]'],r['Y [m]'],r['R_AC [Ω/km]'],r['RMG [m]'],r['Fuente']),r['Tipo'],r['Conexión'],r['Justificación']))
        confirmed=st.checkbox('Confirmo ΔV=0 en todos los auxiliares que se eliminarán por Kron',key='un_kron_confirm',disabled=not carson or not aux_count)
    cap_models=(IDEAL_GROUND,NO_GROUND) if cap_choice=='Comparar con y sin suelo' else (GROUND[cap_choice],)
    config=None if geometry is None else StudyConfig(tuple(specs),tuple(conductor_data),frequency,length,voltage,power,power_kind,pf,load_type,trans,rmode,temp,parallel and circuits==2,carson,method,rho,tuple(auxiliaries),confirmed,st.session_state.get('un_case','Configuración del usuario'))
    fingerprint=hashlib.sha256(repr(config).encode()).hexdigest()
    if st.button('Calcular parámetros',type='primary',width='stretch'):
        if config is None:st.error('No se puede calcular: '+geometry_error)
        else:
            try:
                with st.spinner('Calculando matrices y contrastes con los motores verificados…'):
                    st.session_state.un_result=calculate_study(config)
                    st.session_state.un_result_key=fingerprint
                st.success('Cálculo actualizado.')
            except InputError as exc:st.error(str(exc));st.session_state.pop('un_result',None)
    result=st.session_state.get('un_result')
    if result is not None and st.session_state.get('un_result_key')!=fingerprint:
        st.info('Las entradas cambiaron. Pulsa Calcular parámetros para actualizar los resultados.');result=None
    return result,GROUND[l_model],cap_models


def resistance_view(study):
    r=study.resistance
    if r is None:st.info(study.messages.get('resistance','Resistencia no disponible.'));return
    st.caption(r.mode+' · No es una predicción de temperatura del conductor.')
    if r.total_current_a is not None:
        cols=st.columns(3);cols[0].metric('Corriente total [A]',f'{r.total_current_a:.5f}');cols[1].metric('Corriente por circuito [A]',f'{r.circuit_current_a:.5f}');cols[2].metric('Corriente sub. mínima [A]',f'{r.subconductor_current_a.min():.5f}')
    rows=[{'Fase':label,'I sub [A]':None if r.subconductor_current_a is None else r.subconductor_current_a[i],'Carga [%]':None if r.load_percent is None else r.load_percent[i],'T tabla [°C]':r.temperatures_c[i],'R conductor [Ω/km]':r.conductor_ohm_km[i],'R fase [Ω/km]':r.phase_ohm_km[i],'R fase total [Ω]':None if study.config.length_km is None else r.phase_ohm_km[i]*study.config.length_km} for i,label in enumerate(study.geometry.phase_labels)]
    st.dataframe(pd.DataFrame(rows).style.format({'I sub [A]':'{:.5f}','Carga [%]':'{:.5f}',
        'R conductor [Ω/km]':'{:.8f}','R fase [Ω/km]':'{:.8f}','R fase total [Ω]':'{:.8f}'},na_rep='—'),hide_index=True,width='stretch')
    if r.parallel_ohm_km is not None:st.write('Equivalente resistivo por fase del sistema declarado en paralelo [Ω/km]:',r.parallel_ohm_km.tolist())
    else:st.caption('No se calcula equivalente del sistema sin declarar la conexión en paralelo. Cada circuito conserva sus terminales.')
    for w in r.warnings:st.caption(w)
    st.caption('DOVE de esta tabla: R_DC20=0.1007 Ω/km; PSCAD del ensayo histórico: R_DC=0.102 Ω/km; STE histórico 7F: R_AC=0.1859 Ω/milla. Son fuentes y condiciones distintas; no se reemplazan entre sí.')


def external_comparison(study,matrix_z):
    st.caption('Contraste externo PSCAD; no constituye una comparación del efecto suelo dentro de STE.')
    uploaded=st.file_uploader('Referencia PSCAD JSON (source, labels, matrices por estado y unit)',type=['json'],key='un_pscad_upload')
    choice=st.selectbox('Referencia externa disponible',('Ninguna','DOVE Deri-Semlyen (0)','DOVE integración numérica (2)'),key='un_pscad_choice')
    if uploaded is None and choice=='Ninguna':return
    if matrix_z is None:st.info('Se necesita una matriz Z disponible para contrastar.');return
    try:
        if uploaded:
            data,refs=pscad_reference(uploaded.getvalue(),study.geometry.phase_labels)
            ref=refs['con_transposicion' if study.config.complete else 'sin_transposicion']
            source=data['source']
        else:
            if len(study.geometry.specs)!=3:raise InputError('Las referencias externas DOVE disponibles son 3×3; no se comparan con seis fases.')
            from .pscad_series import load_dove_case
            case=load_dove_case()
            if choice.endswith('(0)'):
                _,refs=pscad_reference(case.pscad,study.geometry.phase_labels);ref=refs['con_transposicion' if study.config.complete else 'sin_transposicion']
            else:
                if not study.config.complete:raise InputError('No se suministró integración numérica sin transposición.')
                from .earth_validation import numerical_pscad_reference
                ref=numerical_pscad_reference(case)['phase_ohm_m']*1000
            source=choice+'; ensayo histórico: 4 subconductores, r=0.011765 m, 60 Hz, ρ=100 Ω·m, R_DC=0.102 Ω/km.'
        st.warning(source+' La configuración actual puede tener otras entradas; no se declara equivalencia ACSR.')
        rows,sequences=external_comparisons(matrix_z,ref,study.geometry.phase_labels)
        st.session_state.un_external=dict(key=st.session_state.un_result_key,source=source,sequences=sequences,phases=rows)
        df=pd.DataFrame(rows);st.dataframe(df,hide_index=True,width='stretch')
        st.download_button('Descargar comparación CSV',df.to_csv(index=False).encode('utf-8-sig'),'comparacion_pscad.csv','text/csv')
        st.dataframe(pd.DataFrame(sequences),hide_index=True)
    except (InputError,KeyError,ValueError) as exc:st.error('Referencia externa: '+str(exc))


def results(study,l_model,c_models):
    if study is None:st.info('Configura la geometría y pulsa Calcular parámetros.');return
    labels=study.geometry.phase_labels;trans=study.config.complete
    part=st.selectbox('Apartado de resultados',('Inductancia','Capacitancia','Resistencia','Impedancia y admitancia','Comparaciones'))
    if part=='Inductancia':
        unit=st.selectbox('Unidad L',('mH/km','µH/m','H/m'));factor=1 if unit=='H/m' else 1e6
        matrix('L completa · '+l_model,study.variants[l_model,trans].l_h_per_m,labels,unit,factor)
        for circuit,value in positive_equivalents(study.variants[l_model,trans].l_h_per_m,labels):
            st.write(f'Circuito {circuit}: L equivalente de secuencia positiva = {value.real*factor:.9g} {unit}, solo para el modo trifásico equilibrado desacoplado.')
        if rmg_values(study) is not None:
            st.dataframe(pd.DataFrame({'Fase':labels,'Radio exterior [m]':[s.radius_m for s in study.geometry.specs],'RMG utilizado [m]':rmg_values(study),'Fuente':[d.sources['diameter_gmr'] for d in study.config.conductor_data]}),hide_index=True,width='stretch')
        if l_model==NO_GROUND:st.warning('L proyectada: ΣI de todas las fases=0. No es una matriz absoluta para corrientes arbitrarias.')
        if 'inductance' in study.messages:st.info(study.messages['inductance'])
        st.caption('Diagonal: términos propios; fuera de diagonal: acoplamientos mutuos. No se reduce un doble circuito a tres fases.')
    elif part=='Capacitancia':
        unit=st.selectbox('Unidad C',('nF/km','F/m'));factor=1e12 if unit=='nF/km' else 1
        show_both=st.checkbox('Comparar también con/sin transposición')
        for model in c_models:
            for mode in ((False,True) if show_both else (trans,)):
                c=study.variants[model,mode].c_f_per_m
                matrix('C · '+model+(' · automática' if mode else ' · sin transposición'),c,labels,unit,factor)
                for circuit,value in positive_equivalents(c,labels):
                    st.write(f'Circuito {circuit}: C equivalente en modo positivo = {value.real*factor:.9g} {unit}; cargas equilibradas y modo desacoplado, sin reducir la matriz completa.')
                if model==NO_GROUND:st.warning(f'Σq global=0; potencial común indeterminado; rango {np.linalg.matrix_rank(c,tol=1e-22)}; máximo |C·1|={np.max(np.abs(c@np.ones(len(c)))):.3e} F/m. No es capacitancia a tierra.')
        st.caption('Se conserva el promedio de P efectiva antes de invertir, bajo carga común. A potencial común se promedia C; no son equivalentes universales de una línea distribuida.')
    elif part=='Resistencia':resistance_view(study)
    elif part=='Impedancia y admitancia':
        d=derived_matrices(study,l_model,c_models[0],trans)
        zunit=st.selectbox('Unidad Z',('Ω/km','Ω/m'));zf=1000 if zunit=='Ω/km' else 1
        matrix('Z geométrica = R_AC+jωL',d['Z_ohm_m'],labels,zunit,zf)
        zeq=positive_equivalents(d['Z_ohm_m'],labels)
        for circuit,value in zeq:st.write(f'Circuito {circuit}: Z equivalente en modo positivo = {value*zf:.9g} {zunit}, bajo excitación equilibrada y modo desacoplado.')
        yunit=st.selectbox('Unidad Y',('S/km','S/m'));yf=1000 if yunit=='S/km' else 1
        for model in c_models:
            y=derived_matrices(study,l_model,model,trans)['Y_s_m']
            matrix('Y = jωC · '+model,y,labels,yunit,yf)
            for circuit,value in positive_equivalents(y,labels):st.write(f'Circuito {circuit}: Y equivalente en modo positivo = {value*yf:.9g} {yunit}; excitación equilibrada y modo desacoplado.')
        if len(zeq)==len(labels)//3:
            with st.expander('Representación diagonal del equivalente equilibrado'):
                matrix('Z diagonal equivalente, solo subespacio equilibrado por circuito',np.diag([v for _,v in zeq for _ in range(3)]),labels,zunit,zf)
                st.caption('Esta representación solo actúa sobre corrientes trifásicas equilibradas con suma cero en cada circuito. Descarta otros modos y no sustituye la matriz física completa ni sus acoplamientos.')
        st.caption('Z geométrica conserva el modelo L seleccionado y su restricción de corrientes si no hay suelo. Y no incluye fuga. Carson se calcula aparte, con R_AC y RMG documentados.')
        if d['sequences']:
            with st.expander('Equivalentes equilibrados y matriz de secuencias completa'):
                matrix('Z012 geométrica completa',d['sequences'].z_ohm_per_m,d['sequences'].labels,zunit,zf)
                st.caption('No se fuerzan a cero acoplamientos. Una diagonal es un equivalente independiente solo si el sistema está desacoplado para esa excitación.')
        if study.carson and study.carson.get('phase') is not None:
            matrix('Z Carson · '+study.config.carson_method,study.carson['phase'],labels,zunit,zf)
            matrix('Z012 Carson',study.carson['sequence'].z_ohm_per_m,study.carson['sequence'].labels,zunit,zf)
        elif study.config.carson_enabled:st.info(study.messages.get('carson','Carson no disponible.'))
    else:
        rows=[]
        for model in (IDEAL_GROUND,NO_GROUND):
            for mode in (False,True):
                v=study.variants[model,mode]
                rows.append(dict(Modelo=model,Transposición='Automática' if mode else 'Sin',Propia_A_nF_km=v.c_f_per_m[0,0]*1e12,Mutua_AB_nF_km=v.c_f_per_m[0,1]*1e12))
        st.dataframe(pd.DataFrame(rows),hide_index=True,width='stretch')
        st.caption('Comparación del suelo dentro del mismo motor STE, manteniendo geometría, haces y el mismo tratamiento de transposición por fila.')
        if study.circuit_comparison:
            model=c_models[0];single=study.circuit_comparison[model,trans].c_f_per_m;double=study.variants[model,trans].c_f_per_m
            st.dataframe(pd.DataFrame(dict(Fase=list('ABC'),C_propia_circuito1_aislado_nF_km=np.diag(single)*1e12,C_propia_en_doble_nF_km=np.diag(double)[:3]*1e12)),hide_index=True)
            st.caption('Circuito sencillo aislado frente al circuito 1 dentro de la estructura doble: el bloque del doble conserva acoplamientos; no representa el circuito aislado ni una conexión paralela.')
        d=derived_matrices(study,l_model,c_models[0],trans)
        z=study.carson['phase'] if study.carson and study.carson.get('phase') is not None else d['Z_ohm_m']
        external_comparison(study,z)


def mathematics(study,l_model,c_models):
    if study is None:st.info('Calcula un estudio para consultar su desarrollo.');return
    labels=study.geometry.phase_labels;cfg=study.config
    with st.expander('Corriente, carga y selección de resistencia'):
        st.latex(r'I=S/(\sqrt{3}V_{LL}),\quad S=P/fp,\quad I_{sub}=I/(N_c n),\quad \%carga=100 I_{sub}/I_{nom}')
        st.latex(r'R_{fase}=R_{AC}/n,\quad R_{paralelo}=1/\sum_c(1/R_{fase,c})')
        resistance_view(study)
    with st.expander('Tramos y permutaciones automáticas · solo lectura'):
        plan=automatic_schedule(len(labels)//3,cfg.complete)
        st.dataframe(pd.DataFrame([dict(Tramo=i+1,Peso=w,Fracción=f'1/{len(plan.weights)}',**{p:f'P{pos+1}' for p,pos in zip(labels,row)}) for i,(row,w) in enumerate(zip(plan.assignments,plan.weights))]),hide_index=True,width='stretch')
        st.caption('Cada haz completo viaja con su fase. Los circuitos mantienen sus terminales; para dos circuitos se promedia el grupo independiente Z3×Z3. Las cadenas redondeadas de fracción no intervienen en el cálculo.')
    with st.expander('Distancias, imágenes y subconductores'):
        images=st.checkbox('Visualizar conductores imagen')
        st.plotly_chart(plot(study.geometry,images),width='stretch',key='math_geometry')
        st.dataframe(pd.DataFrame(dict(Subconductor=study.geometry.labels,X_m=study.geometry.positions_m[:,0],Y_m=study.geometry.positions_m[:,1])),hide_index=True)
        st.latex(r'D_{ij}=\sqrt{(x_i-x_j)^2+(h_i-h_j)^2},\quad S_{ij}=\sqrt{(x_i-x_j)^2+(h_i+h_j)^2}')
        matrix('D reales',study.geometry.real_distances_m,study.geometry.labels,'m')
        matrix('S imágenes',study.geometry.image_distances_m,study.geometry.labels,'m')
    with st.expander('Matrices primitivas, tramos y coeficientes de potencial'):
        model=st.selectbox('Modelo del desarrollo',tuple(GROUND),key='math_model')
        v=study.variants[GROUND[model],cfg.complete]
        i=st.selectbox('Tramo del desarrollo',range(len(v.sections)),format_func=lambda x:str(x+1),key='math_section')
        a=section_arrays(v,i);g=a['geometry']
        matrix('P primitiva',a['P'],g.labels,'adimensional');matrix('P efectiva promedio',v.average_phase_p,labels)
        matrix('L primitiva',a['Lsub'],g.labels,'H/m');matrix('q subconductores por V de fase',a['response'],g.labels,'F/m')
        st.latex(r'P_{ii}=\ln(2h_i/r_i),\quad P_{ij}=\ln(S_{ij}/D_{ij}),\quad L_{ii}=\mu_0/(2\pi)\ln(2h_i/RMG_i)')
        st.latex(r'\overline L=\sum_t w_tL_t,\quad\overline P=\sum_t w_tP_{fase,t},\quad C=2\pi\epsilon_0\overline P^{-1}')
        st.latex(r'RMG=R\exp(-1/4)\quad\text{solo para macizo no magnético con corriente uniforme confirmado}')
        st.caption('Sin suelo se usa la inversa restringida Q(QᵀP Q)⁻¹Qᵀ, Qᵀ1=0. La referencia auxiliar se elimina en ese subespacio. RMG de ACSR es tabulado/documentado; nunca se infiere mediante el factor macizo.')
    with st.expander('Carson, auxiliares, Kron y componentes simétricas'):
        if not study.carson:st.info('Activa Carson en Configuración y geometría para obtener este desarrollo.')
        else:
            for i,s in enumerate(study.carson['sections'],1):
                p=s['phase'];raw=p.primitive
                matrix(f'Z sub Carson, tramo {i}',raw.z_ohm_per_m,raw.labels,'Ω/km',1000)
                matrix(f'Retorno por tierra, tramo {i}',raw.z_earth_ohm_per_m,raw.labels,'Ω/km',1000)
                if s['augmented']:
                    augmented=s['augmented'];matrix(f'Z primitiva con auxiliares, tramo {i}',augmented.z_ohm_per_m,augmented.labels,'Ω/km',1000)
                    for name,m in (('Zpp',augmented.blocks.pp),('Zpn',augmented.blocks.pn),('Znp',augmented.blocks.np),('Znn',augmented.blocks.nn)):
                        matrix(f'{name}, tramo {i}',m,tuple(str(x+1) for x in range(len(m))),'Ω/km',1000)
                if s['reduced']:matrix(f'Kron reducida, tramo {i}',s['reduced'].z_ohm_per_m,labels,'Ω/km',1000)
            if study.carson.get('error'):st.warning(study.carson['error'])
        st.latex(r'Z_{reducida}=Z_{pp}-Z_{pn}Z_{nn}^{-1}Z_{np},\quad Z_{012}=A^{-1}Z_{abc}A')
        st.caption('Kron exige ΔVaux=0 justificado y confirmado; no elimina aislados ni conexiones desconocidas. a=exp(j2π/3), secuencias 0/1/2 por circuito; se preservan los acoplamientos.')


def bibliography(study,l_model,c_models):
    primary=('Tablas_ACSR.pdf','Notas de sistemas de transmision.pdf')
    refs=(*primary,*sorted(str(p.relative_to(ROOT/'referencias')) for p in (ROOT/'referencias').rglob('*.pdf') if p.name not in primary),*sorted(p.name for p in (ROOT/'referencias').glob('*.md')))
    topic=st.selectbox('Biblioteca de fuentes',refs)
    path=ROOT/'referencias'/topic
    if path.suffix=='.pdf':
        st.caption('Resistencia: notas pp.PDF109–111. Tabla ACSR: p.PDF1 resistencias/capacidad; p.PDF2 diámetro/RMG. Se conserva la unidad de cada columna y su fila de origen.')
        st.download_button('Abrir documento técnico',path.read_bytes(),path.name,'application/pdf')
    elif path.exists():
        with st.expander('Consultar documento',expanded=True):st.markdown(path.read_text(encoding='utf-8'))
    if study is None:st.info('Calcula un estudio para exportar sus resultados.');return
    st.caption('El informe resumido omite las primitivas y el listado de tramos. El anexo completo se genera solo cuando lo solicitas.')
    c=st.columns(2)
    if c[0].button('Preparar informe resumido'):
        external=st.session_state.get('un_external')
        st.session_state.un_summary=summary_pdf(study,l_model,c_models,external=external if external and external['key']==st.session_state.un_result_key else None)
        st.session_state.un_export_key=(st.session_state.un_result_key,l_model,c_models)
    if c[1].button('Preparar anexo matemático completo'):
        with st.spinner('Generando anexo de primitivas y tramos…'):st.session_state.un_annex=annex_pdf(study,l_model,c_models)
        st.session_state.un_export_annex_key=(st.session_state.un_result_key,l_model,c_models)
    key=(st.session_state.un_result_key,l_model,c_models)
    if st.session_state.get('un_export_key')==key:st.download_button('Descargar informe resumido PDF',st.session_state.un_summary,'ste_resumen.pdf','application/pdf')
    if st.session_state.get('un_export_annex_key')==key:st.download_button('Descargar anexo matemático PDF',st.session_state.un_annex,'ste_anexo.pdf','application/pdf')
    st.download_button('Descargar estudio JSON',json.dumps(study_record(study),ensure_ascii=False,indent=2,allow_nan=False).encode('utf-8'),'ste_estudio.json','application/json')


def main():
    st.set_page_config(page_title='STE Calculator',page_icon='⚡',layout='wide')
    st.markdown('<style>.block-container{max-width:1450px;padding-top:1.4rem}h1{font-size:1.8rem!important}[data-testid="stMetric"]{background:#eff4f7;padding:10px;border-radius:8px}</style>',unsafe_allow_html=True)
    st.title('STE Calculator')
    st.caption('Parámetros de líneas aéreas · Datos con fuente · Motores verificados · Uno o dos circuitos trifásicos')
    config_tab,result_tab,math_tab,bib_tab=st.tabs(NAV)
    with config_tab:study,l_model,c_models=configure()
    with result_tab:results(study,l_model,c_models)
    with math_tab:mathematics(study,l_model,c_models)
    with bib_tab:bibliography(study,l_model,c_models)
