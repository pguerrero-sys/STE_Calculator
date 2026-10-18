# Etapa 7E: validación de secuencias y análisis de discrepancias

Revisión: 16 de octubre de 2026. Se conserva la versión 7D: no se cambian sus
módulos, interfaz, datos técnicos, matrices ni artefactos exportados.
El análisis nuevo es reproducible por script y produce un informe independiente.

## Fuentes y orden de validación

- Entradas DOVE y archivos PSCAD originales identificados en
  `transposicion_serie.md`, dentro de
  `Datos_DOVE_PSCAD_para_Codex/referencias/comparacion_pscad/`.
- Kersting, *Distribution System Modeling and Analysis*, CRC Press 2002:
  ecuaciones primitivas de tensión pp.86-89, en particular (4.48); transformación
  pp.89-90 (4.59)-(4.67); transposición p.91 (4.68)-(4.72); ejemplo 4.1 pp.94-95.
  Se consultaron las páginas pertinentes de la copia local del capítulo 4.
- Notas y ecuaciones previamente contrastadas en `haces.md`, `secuencias.md`
  y `transposicion_serie.md`. Se conserva su separación entre modelos.

Se recalcula primero el caso original con P/Q finitos de Kersting, R_AC,
12 subconductores e I_fase/4. Se compara con la Z transpuesta 7D. Después se
transforman las matrices de fases de STE y PSCAD mediante A^-1 Zabc A.
Las secuencias publicadas de PSCAD se usan como control adicional, NO como
sustitución de la transformación requerida. No se utilizan datos modales,
LOAD FLOW totales ni LONG-LINE CORRECTED.

## Cambio de base y comprobación escalar independiente

Fasores exp(jωt), a=exp(j2π/3), orden de fases ABC y secuencias 0,1,2:

```text
A=[[1,1,1],[1,a²,a],[1,a,a²]]
Z012=A^-1 Zabc A
Si Zabc tiene propias Zs y mutuas Zm iguales:
Z0=Zs+2 Zm; Z1=Z2=Zs-Zm
```

La verificación escalar rechaza matrices que no estén idealmente transpuestas.
No descarta acoplamientos de una geometría no transpuesta. Los residuos de los
escalares frente a la transformación son menores de 10^-18 Ω/m. Los pequeños
términos fuera de la diagonal de las matrices transformadas son del orden de
la precisión numérica; se conservan sin forzarlos a cero.

Para PSCAD transpuesto se obtiene, desde fase [Ω/km]:

```text
Z0 = .199967488 + j1.424319802
Z1 = .0262542031 + j.254854708
Z2 = .0262542031 + j.254854708
```

La Zsq publicada en el TXT difiere hasta 2e-9 Ω/km por redondeo textual:
publica X0=1.424319800 y X1=X2=.254854709. Esa discrepancia mínima no se
confunde con la diferencia entre programas de aproximadamente 10.01 % en R1.
Se mantienen los valores derivados de fase como referencia principal.

## Resultados principales: corrientes iguales I/n

Todas las impedancias están en Ω/km. Los errores son absolutos por componente,
con denominador PSCAD, sin mezclar R y X ni usar el módulo complejo.

| Escenario | Secuencia | R STE | X STE | Error R [%] | Error X [%] |
|---|---|---:|---:|---:|---:|
| AC original | 0 | .201427591918 | 1.404861250640 | .730170655 | 1.366164490 |
| AC original | 1 y 2 | .028883438794 | .251347501739 | 10.014532469 | 1.376159102 |
| DC temporal | 0 | .198049365758 | 1.404861250640 | .959217051 | 1.366164490 |
| DC temporal | 1 y 2 | .025505212635 | .251347501739 | 2.852840220 | 1.376159102 |

## Por qué la diferencia relativa de R1 es mayor

```text
R1_STE   = .086398156502 - .057514717708 = .028883438794 Ω/km
R1_PSCAD = .084158631400 - .057904428300 = .026254203100 Ω/km
ΔRs = +.002239525102 Ω/km
ΔRm = -.000389710592 Ω/km
ΔR1 = ΔRs-ΔRm = +.002629235694 Ω/km
100 ΔR1/R1_PSCAD = +10.014532469 %
```

La propia está +2.661075952 % por encima y la mutua -0.673023814 % por debajo
de PSCAD. Sus diferencias SUMAN al restar propia menos mutua. El denominador
R1 es menor que la propia y que la suma de módulos. No se pueden promediar los
errores de los elementos para estimar el error de secuencia.

La contribución al porcentaje firmado es +8.530158365 puntos por la propia
y +1.484374104 por la mutua. El factor de cancelación
(|Rs_PSCAD|+|Rm_PSCAD|)/|Rs_PSCAD-Rm_PSCAD| es 5.411059675.
No siempre hay amplificación: depende de las magnitudes y signos de los
errores. Para X ambos desvíos son negativos y aproximadamente proporcionales;
la diferencia relativa de X1 permanece alrededor de 1.376 %, no 10 %.

Esto verifica la aritmética, pero no identifica de forma única las causas
internas del modelo PSCAD a partir de matrices terminales.

## Sensibilidad DC: sustitución temporal, no cambio del conductor original

Se conserva R_AC=.1859 Ω/milla=.11551290463692038 Ω/km. Para el escenario
temporal se utiliza el dato del usuario R_DC=.102 Ω/km por subconductor:

```text
Zsub_DC=Zsub_AC+diag((R_DC-R_AC)/1000)      [Ω/m]
```

Se modifica una COPIA de la diagonal real. No se modifica el campo técnico
R_AC de los conductores, ni el JSON, ni se recalculan RMG, geometría, P/Q,
frecuencia o resistividad. No se invierte el problema para ajustar R a PSCAD.
Con cuatro subconductores e I/n:

```text
ΔZfase = ((R_DC-R_AC)/4/1000) I3          [Ω/m]
ΔZ012  = la misma diagonal real
ΔR por secuencia = -.003378226159 Ω/km
R1_STE_AC = R_AC/4 + .000005212635 Ω/km
R1_STE_DC = .025500000000 + .000005212635 Ω/km
R1_PSCAD - R_DC/4 = .000754203100 Ω/km
```

El último exceso no se asigna a una causa única: pueden coexistir tratamientos
de corriente interna, correcciones AC y diferencias del retorno por tierra.
La entrada DC de PSCAD no es necesariamente su resistencia serie efectiva AC.
El cambio DC disminuye R1 más que la discrepancia original y la deja por debajo
de PSCAD. No se busca un valor intermedio que fuerce concordancia.
En el modelo I/n las reactancias permanecen idénticas. Esto no afirma que una
resistencia DC sea físicamente la entrada AC apropiada a 60 Hz.

## Reparto desigual: modelo auxiliar con condiciones explícitas

El modelo principal conserva Isub=T Iphase y Zigual=Tᵀ Zsub T, con T=E diag(1/n).
E[u,p]=1 identifica la fase del subconductor u. Para estudiar la influencia
de I/n se deduce un equivalente auxiliar de la ecuación primitiva de tensión:

```text
Zsub Isub=E Vgradiente; Iphase=Eᵀ Isub
W=solve(Zsub,E)
Zdesigual=solve(Eᵀ W,I3) = (Eᵀ Zsub^-1 E)^-1
J=W Zdesigual; Isub=J Iphase
```

Supuestos adicionales: sección uniforme, subconductores conectados idealmente
por fase en ambos extremos, gradiente longitudinal común y eliminación serie
sin admitancias shunt. La derivación es álgebra con restricciones, NO una
ecuación de reparto atribuida literalmente a Kersting. Se comprueban
EᵀJ=I3 y Zsub J=E Zdesigual, simetría e igualdad de potencia compleja entre
terminales de fase y subconductores para corrientes arbitrarias. Otra resolución
independiente utiliza el sistema completo por bloques [[Zsub,-E],[Eᵀ,0]].

Se rechazan matrices singulares/mal condicionadas y asignaciones inválidas;
no se usa pseudoinversa. Esta agregación no es eliminación de guardas por Kron.
No resuelve las distribuciones superficiales dentro de cada cable, hebras ACSR,
conexiones reales de separadores, shunt distribuido o correcciones adicionales
de piel/proximidad. Mantiene la misma primitiva de Carson aproximado.
No se afirma que sea el algoritmo que utiliza PSCAD.

| Entrada / reparto | R1 [Ω/km] | X1 [Ω/km] | Error R1 [%] | Error X1 [%] |
|---|---:|---:|---:|---:|
| AC / I/n | .028883438794 | .251347501739 | 10.014532469 | 1.376159102 |
| DC temporal / I/n | .025505212635 | .251347501739 | 2.852840220 | 1.376159102 |
| AC / desigual | .028949457130 | .251165794119 | 10.265991 | 1.447458 |
| DC temporal / desigual | .025565041962 | .251160998419 | 2.624955 | 1.449339 |

Con R_AC, el reparto desigual aumenta R1 aproximadamente 0.228568 % frente
a I/n y eleva el error 0.251458 puntos porcentuales: no explica ni corrige
el 10.01 % inicial. No es una cota general para otras geometrías o conexiones.
Al variar R también varía el reparto complejo; por eso las pequeñas variaciones
de X del modelo desigual no contradicen la invariancia de X del caso I/n.

Excitación diagnóstica del PRIMER TRAMO ORIGINAL: Iphase=[1,a²,a] A.
I/n fuerza 0.25 A por subconductor. Con R_AC el equivalente desigual produce
aproximadamente 0.23798949-0.26285486 A, desviación máxima de módulo 5.141945 %
y desfase máximo respecto a su fase de 3.067983 grados. Estos valores dependen
de la excitación y del tramo; no son constantes del conductor ni una solución
de toda la línea transpuesta. Se exporta además la excitación [1,1,1] A.

## Reproducción y preservación

`scripts/sequence_discrepancy_case.py` genera PDF, JSON, tabla de secuencias CSV
y tabla de corrientes CSV nuevos. No introduce controles en la aplicación ni
modifica ningún cálculo 7D. Se preservan con hashes los módulos existentes,
app.py, entradas originales y los tres artefactos DOVE de etapa 7D.
Las conclusiones separan verificación matemática, sensibilidad de parámetros
y límites de los modelos; no se certifica equivalencia con PSCAD.
