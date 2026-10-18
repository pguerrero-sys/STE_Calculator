"""Etapa 7F: experimento controlado, sin modificar los modelos 7A-7E.

Todas las matrices internas en Ω/m. DC es sensibilidad de una copia, no un
modelo de impedancia interna ACSR ni una reproducción de PSCAD.
"""
from dataclasses import asdict
import json
import numpy as np
import pandas as pd

from .carson import calculate_carson, MODIFIED, PQ_TRUNCATED
from .pscad_series import load_dove_case, find_dove_folder
from .models import InputError
from .series_comparison import pscad_reference, percent_error
from .series_transposition import transpose_series
from .sequences import phase_to_sequence

METHOD_NAMES = {MODIFIED: 'Modificado', PQ_TRUNCATED: 'P/Q finito'}
STATES = ('sin_transposicion', 'con_transposicion')
SOURCES = (
    ('Kersting, CRC 2002, pp.82-84, ecs.(4.20)-(4.38); copia local', 'referencias/Cap 4 Kersting - Ecuaciones Carson.pdf'),
    ('PSCAD Ground Plane: Analytical Approximation / Numerical Integration', 'https://www.pscad.com/webhelp/Master_Library_Models/Transmission_Lines_Cables/ground_plane.htm'),
    ('PSCAD EMTDC: Mutual Impedance with Earth Return, Aerial Lines, ecs.(8-26)-(8-29)', 'https://www.pscad.com/webhelp-v5-ol/EMTDC/Transmission_Lines/Mutual_Impedance_with_Earth_Return.htm'),
    ('PSCAD Segment Input File: ejemplo EarthImpedanceFormula=0, sin tabla de códigos', 'https://www.pscad.com/webhelp-v5-ol/PSCAD/Transmission_Lines_and_Cables/Line_Constants_Files/Input_File.htm'),
    ('PSCAD Using/Maintaining a Conductor Library: conductor.clb / conductor_stranded.clb', 'https://www.pscad.com/webhelp/Master_Library_Models/Transmission_Lines_Cables/Transmission_Line_Models/Using_Maintaining_a_Conductor_Library.htm'),
    ('PSCAD Conductor Elimination: Conductor Bundling', 'https://www.pscad.com/webhelp-pscad-v5.1.0-ol/EMTDC/Transmission_Lines/Conductor_Elimination.htm'),
)

AUDIT = (
    ('Geometría, haz, f, ρ, r exterior', 'Entradas conocidas: Sag=0 m; A=(-3,13), B=(3,13), C=(0,9) m; cuatro DOVE/fase; separación=0.4572 m; 60 Hz; ρ=100 Ω·m; r=0.011765 m.'),
    ('R_AC STE', '0.1859 Ω/milla, dato bibliográfico del JSON; se conserva. Equivale a 0.115512904637 Ω/km por subconductor.'),
    ('R_DC PSCAD', '0.102 Ω/km por subconductor, declarado por el usuario y LEEME; no es resistencia AC a 60 Hz.'),
    ('RMG STE / PSCAD', 'STE: 0.00954024 m, JSON. RMG efectivo e impedancia interna calculados por PSCAD: resultados internos aún no identificados; no se deducen del radio exterior.'),
    ('Entradas de hebras y μ conocidas', 'Strand Radius=0.001858 m; Number of Outer Strands=16; Total Number of Strands=26; Conductor Relative Permeability=1. Son entradas PSCAD suministradas, no propiedades inferidas ni un RMG efectivo calculado.'),
    ('Métodos PSCAD confirmados', 'Usuario confirma en la interfaz: 0=Deri-Semlyen; 2=Direct numerical integration. Confirmación del caso, no tabla universal para todas las versiones.'),
    ('Suelo y auxiliares conocidos', 'GroundWires=0; GroundPermittivity final=1. DCResistance=0.102 Ω/km por subconductor. Estos datos no determinan por sí solos la impedancia interna AC del conductor.'),
    ('Matriz Y suministrada', 'Y completa de la nueva simulación: diagonal 1e-11+j5.20392911e-9 S/m; mutua -j1.24409590e-9 S/m. Coincide con el bloque Y del TXT transpuesto anterior; máximo |ΔY|=0 S/m a la precisión suministrada.'),
)


def numerical_pscad_reference(case, root=None):
    folder=find_dove_folder() if root is None else find_dove_folder(root)
    path=folder/'pscad_integracion_numerica_confirmada.json'
    data=json.loads(path.read_text(encoding='utf-8'))
    base=case.phase_result.primitive
    if (data['unit']!='Ω/km' or tuple(data['labels'])!=case.labels
            or data['state']!=STATES[1] or data['EarthImpedanceFormula']!=2
            or data['frequency_Hz']!=base.frequency_hz
            or data['resistivity_ohm_m']!=base.resistivity_ohm_m):
        raise InputError('Referencia PSCAD numérica incompatible: revisar unidades, fases, transposición, método, f y ρ.')
    z=np.full((3,3),complex(**dict(real=data['mutual']['real'],imag=data['mutual']['imag']))/1000)
    np.fill_diagonal(z,complex(data['self']['real'],data['self']['imag'])/1000)
    seq=phase_to_sequence(z,case.labels).z_ohm_per_m
    published=(np.asarray(data['published_sequences']['real'])+1j*np.asarray(data['published_sequences']['imag']))/1000
    residual=float(np.max(np.abs(np.diag(seq)-published)))
    if not np.all(np.isfinite(z)) or residual>5e-13:
        raise InputError('Matriz de fase y secuencias PSCAD numéricas no concuerdan con el redondeo declarado.')
    return dict(metadata=dict(data,path=str(path)),phase_ohm_m=z,sequence_ohm_m=seq,
                published_sequence_ohm_m=published,residual_ohm_m=residual)


def _comparison(rows, scenario, domain, labels, model, reference, against):
    # Mantener los residuos numéricos de Z012, sin porcentajes sobre ceros de máquina.
    floors = {part:1e-12*float(np.max(np.abs(values)))*1000
              for part,values in (('R',reference.real),('X',reference.imag))}
    for i, left in enumerate(labels):
        for j, right in enumerate(labels):
            z, ref = model[i,j]*1000, reference[i,j]*1000
            rows.append(dict(Metodo=scenario['method'], Resistencia=scenario['resistance'],
                Estado=scenario['state'], Dominio=domain, Fila=left, Columna=right, Referencia=against,
                R_ohm_km=float(z.real), X_ohm_km=float(z.imag),
                Ref_R_ohm_km=float(ref.real), Ref_X_ohm_km=float(ref.imag),
                Delta_R_ohm_km=float(z.real-ref.real), Delta_X_ohm_km=float(z.imag-ref.imag),
                Abs_delta_R_ohm_km=float(abs(z.real-ref.real)), Abs_delta_X_ohm_km=float(abs(z.imag-ref.imag)),
                Error_R_pct=percent_error(z.real,ref.real) if abs(ref.real)>floors['R'] else None,
                Error_X_pct=percent_error(z.imag,ref.imag) if abs(ref.imag)>floors['X'] else None,
                Porcentaje_R_interpretable=bool(abs(ref.real)>floors['R']),
                Porcentaje_X_interpretable=bool(abs(ref.imag)>floors['X'])))


def analyze_earth_return(root=None):
    case = load_dove_case() if root is None else load_dove_case(root)
    base = case.phase_result.primitive
    t = case.phase_result.current_weights
    r_ac = np.array([c.resistance_ac_ohm_per_km for c in base.conductors])
    r_dc = np.full(len(r_ac),case.pscad['input_resistance_ohm_per_km'])
    _, ref_km = pscad_reference(case.pscad,case.labels)
    refs = {state:np.asarray(ref_km[state])/1000 for state in STATES}
    ref_seq = {state:phase_to_sequence(z,case.labels).z_ohm_per_m for state,z in refs.items()}
    rows, controlled, scenarios, primitives = [], [], [], {}
    for method in (MODIFIED,PQ_TRUNCATED):
        primitive = calculate_carson(base.conductors,base.frequency_hz,base.resistivity_ohm_m,method)
        primitives[method] = primitive
        for resistance, values in (('AC bibliográfica',r_ac),('DC temporal',r_dc)):
            # Cambio exclusivo de la diagonal real de una COPIA; no se cambia el dato AC.
            conductor = primitive.z_conductor_ohm_per_m + np.diag((values-r_ac)/1000)
            parts = dict(conductor=t.T@conductor@t,
                         geometry=t.T@primitive.z_geometry_ohm_per_m@t,
                         earth=t.T@primitive.z_earth_ohm_per_m@t)
            for state in STATES:
                enabled = state=='con_transposicion'
                selected = {name:transpose_series(z,case.labels,enabled=enabled).selected_ohm_per_m
                            for name,z in parts.items()}
                # Se transpone el total con el mismo orden de operaciones de 7D.
                sub = conductor+primitive.z_geometry_ohm_per_m+primitive.z_earth_ohm_per_m
                phase = transpose_series(t.T@sub@t,case.labels,enabled=enabled).selected_ohm_per_m
                seq = phase_to_sequence(phase,case.labels).z_ohm_per_m
                scenario = dict(method=METHOD_NAMES[method],method_id=method,resistance=resistance,state=state,
                    phase_ohm_m=phase,sequence_ohm_m=seq,parts_ohm_m=selected,primitive_ohm_m=sub,
                    resistance_input_ohm_km=values.copy())
                scenarios.append(scenario)
                _comparison(rows,scenario,'fase',case.labels,phase,refs[state],'PSCAD Deri-Semlyen (0)')
                _comparison(rows,scenario,'secuencia',('0','1','2'),seq,ref_seq[state],'PSCAD Deri-Semlyen (0)')
    for pq in scenarios:
        if pq['method_id']!=PQ_TRUNCATED:
            continue
        mod=next(s for s in scenarios if s['method_id']==MODIFIED and s['resistance']==pq['resistance'] and s['state']==pq['state'])
        for domain,key,labels in (('fase','phase_ohm_m',case.labels),('secuencia','sequence_ohm_m',('0','1','2'))):
            _comparison(controlled,pq,domain,labels,pq[key],mod[key],'Modificado (mismas entradas)')
    numerical=numerical_pscad_reference(case,root)
    numerical_rows=[]
    for scenario in scenarios:
        if scenario['state']==STATES[1]:
            _comparison(numerical_rows,scenario,'fase',case.labels,scenario['phase_ohm_m'],numerical['phase_ohm_m'],'PSCAD integración numérica (2)')
            _comparison(numerical_rows,scenario,'secuencia',('0','1','2'),scenario['sequence_ohm_m'],numerical['sequence_ohm_m'],'PSCAD integración numérica (2)')
    return dict(case=case,scenarios=tuple(scenarios),primitives=primitives,pscad_phase_ohm_m=refs,
                pscad_sequence_ohm_m=ref_seq,comparison=pd.DataFrame(rows),controlled=pd.DataFrame(controlled),
                numerical_reference=numerical,numerical_comparison=pd.DataFrame(numerical_rows),
                audit=AUDIT,sources=SOURCES,weights=t.copy())


def validation_record(analysis):
    def encode(value):
        if isinstance(value,np.ndarray):
            if np.iscomplexobj(value):
                return dict(real=value.real.tolist(),imag=value.imag.tolist())
            return value.tolist()
        if isinstance(value,dict):
            return {k:encode(v) for k,v in value.items()}
        if isinstance(value,(list,tuple)):
            return [encode(v) for v in value]
        return value
    primitives={method:dict(conductors=[asdict(c) for c in p.conductors],f_Hz=p.frequency_hz,
        rho_ohm_m=p.resistivity_ohm_m,k=p.k,P=p.p,Q=p.q,real_distances_m=p.real_distances_m,
        image_distances_m=p.image_distances_m,warnings=p.warnings) for method,p in analysis['primitives'].items()}
    return encode(dict(etapa='7F',unidad_matrices='Ω/m',convencion='exp(jωt); a=exp(j2π/3); secuencias 0,1,2',
        metadatos=analysis['case'].metadata,primitives=primitives,weights=analysis['weights'],
        scenarios=analysis['scenarios'],PSCAD_phase=analysis['pscad_phase_ohm_m'],PSCAD_sequence=analysis['pscad_sequence_ohm_m'],
        comparison=analysis['comparison'].replace({np.nan:None}).to_dict(orient='records'),
        PSCAD_numerical=analysis['numerical_reference'],
        numerical_comparison=analysis['numerical_comparison'].replace({np.nan:None}).to_dict(orient='records'),
        controlled=analysis['controlled'].replace({np.nan:None}).to_dict(orient='records'),
        audit=analysis['audit'],sources=analysis['sources'],consulta_fuentes='2026-10-16',
        selector_0_verificado=True,selector_2_verificado=True,
        fuente_confirmacion_selectores='Usuario: selección comprobada en la interfaz del caso PSCAD',
        equivalencia_PSCAD_demostrada=False))
