"""Ensayo algebraico reproducible, sin propiedades comerciales inventadas."""

from dataclasses import replace
from .carson import kersting_example, FT_M, calculate_carson
from .kron import AuxiliaryConductor, ZERO_DROP, augment_carson


def two_guard_case(circuit_count=1):
    if circuit_count not in (1,2):
        raise ValueError("Ensayo disponible para uno o dos circuitos.")
    phases = kersting_example()
    if circuit_count==2:
        phases += tuple(replace(c,label=c.label+"'",x_m=c.x_m+20*FT_M) for c in phases)
    neutral_data = kersting_example(True)[-1]
    basis = "Ensayo algebraico: se impone ΔV=0; no representa conexiones de una instalación real"
    conditions = "Dos guardas ficticias: datos R_AC/RMG del neutro de Kersting reutilizados solo para verificar álgebra"
    guards = tuple(AuxiliaryConductor(replace(neutral_data,label=f"G{i+1}",x_m=x*FT_M,height_m=40*FT_M,
                                               conditions=conditions),"guard",ZERO_DROP,basis)
                   for i,x in enumerate((-4,11+20*(circuit_count-1))))
    return augment_carson(calculate_carson(phases,60,100),guards)
