"""Exportación auditable de Carson, sin dependencias de Streamlit."""

import numpy as np

from .carson import METHODS, FT_M, G_SI_H_PER_M, convert_impedance
from .printing import MatrixBlock, render_pdf


def carson_record(result):
    primitive = getattr(result,"primitive",result)
    labels = getattr(result,"phase_labels",primitive.labels)
    def record(matrix):
        return {"real":matrix.real.tolist(),"imag":matrix.imag.tolist()}
    return {
        "contexto":"Carson aproximado, sin Kron ni comparación independiente con PSCAD",
        "metodo":primitive.method,"descripcion_metodo":METHODS[primitive.method],
        "frecuencia_Hz":primitive.frequency_hz,"resistividad_ohm_m":primitive.resistivity_ohm_m,
        "orden_fases":labels,"k_max":float(primitive.k.max()),"advertencias":primitive.warnings,
        "conductores":[vars(c) for c in primitive.conductors],
        "Z_ohm_km":record(result.z_ohm_per_km),"Z_ohm_m":record(result.z_ohm_per_m),
        "R_conductores_ohm_km":(result.z_conductor_ohm_per_m.real*1000).tolist(),
        "X_geometrica_ohm_km":(result.z_geometry_ohm_per_m.imag*1000).tolist(),
        "correccion_tierra_ohm_km":record(result.z_earth_ohm_per_m*1000),
        "orden_subconductores":primitive.labels,"Z_primitiva_ohm_m":record(primitive.z_ohm_per_m),
        "D_m":primitive.real_distances_m.tolist(),"S_m":primitive.image_distances_m.tolist(),
        "P_carson":primitive.p.tolist(),"Q_carson":primitive.q.tolist(),"k":primitive.k.tolist(),
        "nota_capacitancia":"No se modifica C. Promediar C a potencial común difiere de invertir P media a carga común; ver referencias/carson.md.",
    }


def carson_pdf(result):
    primitive = getattr(result,"primitive",result)
    labels = getattr(result,"phase_labels",primitive.labels)
    omega = 2*np.pi*primitive.frequency_hz
    notes = [
        "Fasores exp(+jωt), Z=R+jX. Matrices simétricas por transposición, no hermíticas. Ningún conductor ha sido eliminado mediante Kron.",
        f"Método: {METHODS[primitive.method]}. NO es evaluación completa de la serie infinita ni comparación exacta con PSCAD.",
        f"f={primitive.frequency_hz:.12g} Hz; ρ={primitive.resistivity_ohm_m:.12g} Ω·m; k máximo={primitive.k.max():.12g}.",
        "Dij=hypot(xi-xj,hi-hj); Sij=hypot(xi-xj,hi+hj), metros. dii=RMGi; dij=Dij para i≠j.",
        "g=μ0/(4π)=10^-7 H/m; ω=2πf. Z=diag(R_AC/1000)+j2ωg ln(S/d)+4ωg(P+jQ), Ω/m.",
        "Contribución suministrada: R_AC diagonal. Referencia geométrica: jωL con imágenes de suelo ideal. Retorno por tierra: ΔZ=4ωg(P+jQ), corrección respecto de esa referencia; separación reactiva no única.",
        "Carson modificado: P=π/8; 2Q=7.6786-ln(S_ft)+0.5 ln(ρ/f); Zii=R_AC/1000+π²fg+j4πfg[ln(0.3048/RMG_m)+7.6786+0.5ln(ρ/f)]; Zij igual sin R_AC y con Dij en lugar de RMG.",
        "P/Q finitos: k=8.565e-4 S_ft sqrt(f/ρ); cosθ=(hi+hj)/S; P=π/8-k cosθ/(3√2)+k²cos(2θ)[0.6728+ln(2/k)]/16; Q=-0.0386+0.5ln(2/k)+k cosθ/(3√2). No se añaden términos no publicados.",
        "S_ft=S_m/0.3048. f y ρ son los valores numéricos en Hz y Ω·m. 1 mile=1609.344 m, 1 ft=0.3048 m. Ω/m→Ω/km: ×1000.",
        "Dominio preventivo de software: k>0.1 genera aviso y k≥1 se rechaza. No es cota de error bibliográfica. No se valida alta frecuencia ni el límite ρ→0 con estas series truncadas.",
        "R_AC y RMG son datos técnicos suministrados; no se calculan correcciones de temperatura, frecuencia, piel ni estructura ACSR. El flujo interno ya está en el RMG.",
        "Suelo plano, homogéneo e infinito, resistividad constante; no se representan capas ni efectos de extremos. Carson modifica solo la impedancia serie. Capacitancia y suelo ideal anteriores permanecen separados.",
        "Capacitancia transpuesta: a potencial V común, C_equiv=Σwt Ct; a carga q común, C_equiv=(Σwt Ct^-1)^-1. En general difieren. Las etapas anteriores conservan el segundo procedimiento didáctico, no validado como equivalente shunt universal.",
        "Fuentes: Kersting, CRC 2002, §4.1.3-4.1.4 pp.81-85 (4.20)-(4.42); ejemplo 4.1 pp.92-93, SIN Kron. Presentación Carson, diapositivas 4-9; notas clase 01-10-26 PDF 1-2. Discrepancias y condiciones: referencias/carson.md.",
    ]
    if hasattr(result,"current_weights"):
        notes.append("Haces: Zfase=TᵀZsubT con T[u,p]=E[u,p]/n_p. Corrientes iguales I_fase/n; no redistribución de corrientes, no Kron, no promedio nuevo de transposición.")
    notes.extend(primitive.warnings)
    for c in primitive.conductors:
        notes.append(f"{c.label}: ({c.x_m:.12g}, {c.height_m:.12g}) m; R_AC={c.resistance_ac_ohm_per_km:.12g} Ω/km; RMG={c.gmr_m:.12g} m. Fuente: {c.source}. Condiciones: {c.conditions or 'no especificadas por el usuario'}.")
    for i,j in ((0,0),(0,min(1,len(primitive.labels)-1))):
        c = primitive.conductors[i]
        s = primitive.image_distances_m[i,j]
        d = c.gmr_m if i==j else primitive.real_distances_m[i,j]
        notes.append(f"Elemento {primitive.labels[i]}/{primitive.labels[j]}: S={s:.12g} m; d={d:.12g} m; k=8.565e-4×({s/FT_M:.12g})×sqrt({primitive.frequency_hz:.12g}/{primitive.resistivity_ohm_m:.12g})={primitive.k[i,j]:.12g}; P={primitive.p[i,j]:.12g}; Q={primitive.q[i,j]:.12g}.")
        base_r = c.resistance_ac_ohm_per_km/1000 if i==j else 0
        xgeom = 2*omega*G_SI_H_PER_M*np.log(s/d)
        ze = primitive.z_earth_ohm_per_m[i,j]
        z = primitive.z_ohm_per_m[i,j]
        notes.append(f"Z=({base_r:.12g})+j({xgeom:.12g})+({ze.real:.12g}+j{ze.imag:.12g})={z.real:.12g}+j{z.imag:.12g} Ω/m; ×1000={z.real*1000:.12g}+j{z.imag*1000:.12g} Ω/km.")
    blocks = []
    def add(title,values,unit,rows=labels,columns=None):
        blocks.append(MatrixBlock(title,np.asarray(values,dtype=float),tuple(rows),tuple(columns or rows),unit))
    for unit,factor in (("Ω/km",1000),("Ω/m",1)):
        add("R total: parte real de Z",result.z_ohm_per_m.real*factor,unit)
        add("X total: parte imaginaria de Z",result.z_ohm_per_m.imag*factor,unit)
    add("R_AC de conductores",result.z_conductor_ohm_per_m.real*1000,"Ω/km")
    add("X geométrica de referencia",result.z_geometry_ohm_per_m.imag*1000,"Ω/km")
    add("ΔR por retorno de tierra",result.z_earth_ohm_per_m.real*1000,"Ω/km")
    add("ΔX por retorno de tierra",result.z_earth_ohm_per_m.imag*1000,"Ω/km")
    for title,values,unit in (("D reales",primitive.real_distances_m,"m"),("S imágenes",primitive.image_distances_m,"m"),
                               ("k",primitive.k,"adimensional"),("P Carson",primitive.p,"adimensional"),("Q Carson",primitive.q,"adimensional")):
        add(title,values,unit,primitive.labels)
    if hasattr(result,"current_weights"):
        add("T, corrientes iguales por subconductor",result.current_weights,"adimensional",primitive.labels,labels)
        add("R primitiva",primitive.z_ohm_per_m.real*1000,"Ω/km",primitive.labels)
        add("X primitiva",primitive.z_ohm_per_m.imag*1000,"Ω/km",primitive.labels)
    return render_pdf("STE Calculator · Carson · Etapa 7A",notes,blocks,
                      footer_text="STE Calculator · Carson aproximado, sin Kron ni validación de diseño")
