"""Exportación reproducible de entradas, bloques y reducción de Kron."""

from dataclasses import asdict
import numpy as np
from .carson import convert_impedance
from .carson_report import carson_record
from .printing import MatrixBlock, render_pdf
from .sequences import phase_to_sequence
from .sequence_report import sequence_record, sequence_notes, sequence_blocks
from .kron_validation import validate_two_guards


def kron_record(augmented, reduced=None):
    def encode(m):
        return {"real":m.real.tolist(), "imag":m.imag.tolist()}
    record = {"modelo":"Carson y Kron; ΔVn=0 solo si declarado; sin transposición automática",
              "fases":list(augmented.phase_labels),
              "auxiliares":[asdict(a) for a in augmented.auxiliaries],
              "primitiva_Carson":carson_record(augmented.primitive),
              "A_reparto_corriente":augmented.current_weights.tolist(),
              "orden_terminales":list(augmented.labels),
              "Z_terminal_ohm_m":encode(augmented.z_ohm_per_m),
              "bloques_ohm_m":{name:encode(getattr(augmented.blocks,name)) for name in ("pp","pn","np","nn")},
              "reduccion_aplicada":reduced is not None}
    if reduced is not None:
        record.update({"hipotesis_declarada":"ΔVn=0 en todos los auxiliares eliminados",
                       "Z_reducida_ohm_m":encode(reduced.z_ohm_per_m),
                       "Z_reducida_ohm_km":encode(reduced.z_ohm_per_km),
                       "Z_reducida_ohm_mile":encode(convert_impedance(reduced.z_ohm_per_m,"Ω/m","Ω/mile")),
                       "correccion_ohm_m":encode(reduced.correction_ohm_per_m),
                       "In_por_Ip":encode(reduced.auxiliary_current_response),
                       "cond_Znn":reduced.condition_number,"residuo":reduced.solve_residual})
        record["componentes_simetricas"] = sequence_record(phase_to_sequence(reduced.z_ohm_per_m,augmented.phase_labels))
        if len(augmented.auxiliaries)==2 and all(a.role=="guard" for a in augmented.auxiliaries):
            check = validate_two_guards(augmented,reduced)
            record["contraste_dos_guardas"] = {"metodo":"Sistema completo de restricciones Ip=I y ΔVn=0, SciPy",
                "Z_independiente_ohm_m":encode(check.independent_z_ohm_per_m),
                "error_relativo":check.relative_error,"error_maximo_ohm_m":check.max_error_ohm_per_m,
                "residuo_frontera":check.boundary_residual}
    return record


def kron_pdf(augmented, reduced=None):
    p = augmented.primitive
    notes = [
        "Impedancia serie por unidad de longitud. Fases conservadas: "+", ".join(augmented.phase_labels)+".",
        f"Carson: {p.method}; f={p.frequency_hz:.12g} Hz; resistividad={p.resistivity_ohm_m:.12g} Ω·m.",
        "Zterminal=Aᵀ Zsub A. Con haces: I_sub=I_fase/n; esta agregación es una aproximación de corrientes iguales, distinta de Kron.",
        "Dij=sqrt((xi-xj)²+(hi-hj)²); Sij=sqrt((xi-xj)²+(hi+hj)²); dii=RMGi, dij=Dij.",
        "g=10^-7 H/m; ω=2πf. Zsub,ij=δij ri+j2ωg ln(Sij/dij)+4ωg(Pij+jQij) [Ω/m].",
        "ΔVp/ℓ=Zpp Ip+Zpn In; ℓ es la longitud del tramo uniforme.",
        "ΔVn/ℓ=Znp Ip+Znn In. Solo si ΔVn=0: Znn Y=Znp; In=-Y Ip.",
        "Zreducida=Zpp-Zpn Y=Zpp-Zpn inversa(Znn) Znp. La implementación usa solve, sin inversa explícita.",
        "Unidades coherentes: Ω/m a Ω/km, multiplicar por 1000; Ω/m a Ω/milla, por 1609.344. Y es adimensional.",
        "No se eliminan conductores aislados o con conexión desconocida. Si In=0, el bloque de fases es Zpp, no el complemento de Schur.",
        "Multitierra ideal supone neutro a potencial de tierra en ambos extremos de cada tramo. No se modelan electrodos finitos, tierras discretas ni elevaciones de potencial de torre.",
        "No cambia capacitancia ni inductancia con suelo ideal. Sin transposición automática, equivalentes de circuitos en paralelo ni equivalencia certificada con PSCAD.",
        "Fuentes: Kersting, CRC 2002, §4.1.5-4.1.6 pp.86-87, ecs.4.45-4.54; ejemplo 4.1 pp.92-94, fig.4.7; Carson.pdf diapositivas 9-11. Detalles: referencias/kron.md.",
    ]
    notes.extend(p.warnings)
    for c in p.conductors:
        notes.append(f"{c.label}: X={c.x_m:.12g} m; h={c.height_m:.12g} m; R_AC={c.resistance_ac_ohm_per_km:.12g} Ω/km; RMG={c.gmr_m:.12g} m. Fuente: {c.source}. Condiciones: {c.conditions or 'no indicadas'}.")
    for a in augmented.auxiliaries:
        notes.append(f"Auxiliar {a.conductor.label}: tipo={a.role}; conexión={a.connection}; justificación={a.justification or 'no declarada'}.")
    if reduced is None:
        notes.append("REDUCCIÓN NO APLICADA. Se exportan la primitiva y los bloques, sin afirmar ΔVn=0.")
    else:
        notes += ["HIPÓTESIS DECLARADA: ΔVn=0 para todos los auxiliares eliminados.",
                  f"cond(Znn)={reduced.condition_number:.9g}; residuo normalizado={reduced.solve_residual:.3e}.",
                  f"Sustitución elemento (1,1) [Ω/km]: Zred={reduced.blocks.pp[0,0]*1000:.9g} - ({reduced.correction_ohm_per_m[0,0]*1000:.9g}) = {reduced.z_ohm_per_m[0,0]*1000:.9g}."]
        sequences = phase_to_sequence(reduced.z_ohm_per_m,augmented.phase_labels)
        notes.extend(sequence_notes(sequences))
        if len(augmented.auxiliaries)==2 and all(a.role=="guard" for a in augmented.auxiliaries):
            check = validate_two_guards(augmented,reduced)
            notes.append(f"Dos guardas: contraste independiente por sistema completo de restricciones (SciPy). Error relativo={check.relative_error:.3e}; error máximo={check.max_error_ohm_per_m:.3e} Ω/m; residuo de frontera={check.boundary_residual:.3e}. Verifica álgebra, no puesta a tierra física.")
    blocks = []
    def add(title,z,rows,columns,unit="Ω/m"):
        blocks.extend(MatrixBlock(title+" · "+part,values,tuple(rows),tuple(columns),unit)
                      for part,values in (("R",z.real),("X",z.imag)))
    add("Primitiva completa de subconductores",p.z_ohm_per_m,p.labels,p.labels)
    for unit in ("Ω/m","Ω/km","Ω/mile"):
        add("Zterminal antes de Kron",convert_impedance(augmented.z_ohm_per_m,"Ω/m",unit),augmented.labels,augmented.labels,unit)
        if reduced is not None:
            add("Zreducida de fases",convert_impedance(reduced.z_ohm_per_m,"Ω/m",unit),augmented.phase_labels,augmented.phase_labels,unit)
    phases = augmented.phase_labels
    aux = tuple(a.conductor.label for a in augmented.auxiliaries)
    for name,rows,cols in (("pp",phases,phases),("pn",phases,aux),("np",aux,phases),("nn",aux,aux)):
        add("Bloque Z"+name,getattr(augmented.blocks,name),rows,cols)
    if reduced is not None:
        add("Corrección Zpn Y",reduced.correction_ohm_per_m,phases,phases)
        add("Respuesta In por Ip",reduced.auxiliary_current_response,aux,phases,"adimensional")
        for unit in ("Ω/m","Ω/km","Ω/mile"):
            blocks.extend(sequence_blocks(sequences,unit))
        if len(augmented.auxiliaries)==2 and all(a.role=="guard" for a in augmented.auxiliaries):
            add("Z independiente dos guardas",check.independent_z_ohm_per_m,phases,phases)
    return render_pdf("STE Calculator · Carson y reducción de Kron",notes,blocks,
                      "STE Calculator · Hipótesis eléctricas declaradas; sin validación de diseño")
