"""Contenido de informe de secuencias, independiente de Streamlit."""

from .carson import convert_impedance
from .printing import EquationBlock, MatrixBlock


def sequence_record(result):
    def encode(z):
        return {"real":z.real.tolist(),"imag":z.imag.tolist()}
    return {"convencion":"exp(jωt); a=exp(j2π/3); Vabc=A V012 e Iabc=A I012",
            "orden_fases":result.phase_labels,"orden_secuencias":result.labels,
            "a":{"real":result.operator_a.real,"imag":result.operator_a.imag},
            "B":encode(result.transform),"B_inversa":encode(result.inverse_transform),
            "Z012_por_unidad":{u:encode(convert_impedance(result.z_ohm_per_m,"Ω/m",u))
                                for u in ("Ω/m","Ω/km","Ω/mile")},
            "residuo_reconstruccion":result.reconstruction_residual,
            "nota":"Matriz completa sin diagonalización ni simetrización; con dos circuitos B=diag(A,A)."}


def sequence_notes(result):
    return [EquationBlock("Componentes simétricas · convención y transformación",(
                "Convención fasorial exp(jωt); a=exp(j2π/3)=-1/2+j√3/2; a³=1; 1+a+a²=0.",
                "Orden de fases: A,B,C. Orden de secuencias: 0 (cero), 1 (positiva), 2 (negativa).",
                "A = [[1,1,1], [1,a²,a], [1,a,a²]]",
                "A^-1 = (1/3) [[1,1,1], [1,a,a²], [1,a²,a]] = A conjugada transpuesta/3.",
                "Vabc=A V012; Iabc=A I012; Z012=A^-1 Zabc A.",
                "Con dos circuitos: B=diag(A,A); Zs=B^-1 Zfase B, conservando todos los bloques entre circuitos.")),
            "Etiquetas de esta matriz: "+", ".join(result.labels)+". Todas las impedancias conservan sus unidades.",
            "Los términos fuera de la diagonal son acoplamientos entre secuencias y no se anulan. Z012 no tiene por qué ser simétrica ni hermítica, aunque Zabc sea recíproca.",
            "Z1=Z2 en el bloque de un circuito recíproco no prueba transposición ni desacoplamiento. Con otros I012 no nulos, ΔVi/ℓ=Σj Zij Ij: no basta usar solo Zii.",
            f"Residuo relativo de reconstrucción B Zs B^-1: {result.reconstruction_residual:.3e}.",
            "Fuente: Kersting (2002), §4.1.7, pp.89-91, ecs.4.59-4.67; ejemplo 4.1 pp.94-95. Carson.pdf diapositiva 15; referencias/secuencias.md."]


def sequence_blocks(result,unit):
    z = convert_impedance(result.z_ohm_per_m,"Ω/m",unit)
    return [MatrixBlock("Z012 completa · "+part,values,result.labels,result.labels,unit,"Secuencia/circuito")
            for part,values in (("R",z.real),("X",z.imag))]
