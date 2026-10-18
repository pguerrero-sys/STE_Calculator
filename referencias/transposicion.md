# Etapa 5: transposición ideal completa de circuito sencillo

**Revisión física de etapa 7A:** los resultados aquí conservados corresponden
al procedimiento didáctico a carga de fase común. A potencial electrostático
común entre tramos se promedia C directamente; no se obtiene, en general,
la misma matriz. El promedio de P antes de invertir no se certifica como
equivalente shunt universal de una línea distribuida. Véase la derivación y
las condiciones de borde en `carson.md`, última sección. Esta aclaración no
modifica las matrices ni los casos numéricos históricos.

## Fuentes y contraste

- Notas de sistemas de transmision.pdf: PDF 53-57, tres tramos L/3,
  matrices de enlaces y promedio inductivo; PDF 89-91 y 96-98, promedio
  de potenciales por tramo antes de calcular capacitancia. Se extrajo texto
  de estas páginas y se inspeccionaron visualmente PDF 96-97.
- Notas clase STE 14-09-26.pdf: PDF 2-3, esquema longitudinal, promedio
  de enlaces de flujo y condición de fases iguales. Ambas páginas se
  inspeccionaron renderizadas. Se revisó la primera página en la etapa 3.
- Kersting, Distribution System Modeling and Analysis, CRC Press, 2002,
  §4.1.1, impresas 78-79 (PDF 93-94): transposición y carga equilibrada;
  §5.1-5.2, impresas 110-113 (PDF 125-128): relaciones de potencial y
  capacitancia. Las páginas pertinentes se consultaron en etapas anteriores.
- Para haces se reutiliza íntegramente la etapa 4: `referencias/haces.md`.
  La condensación equipotencial a tres fases es una derivación algebraica
  del modelo de potenciales; no es una fórmula textual atribuida a las notas.

Inconsistencias que se evitan: en PDF 56 cambia el orden escrito de los
enlaces sin cambiar coherentemente el vector de corrientes; en PDF 57 hay
un término diagonal repetido en el promedio. En PDF 97 algunos subíndices
de la matriz promedio no mantienen simetría. Se construyen las matrices con
asignaciones explícitas y no copiando esas entradas. PDF 89 usa un símbolo
R' en una fórmula capacitiva: se conserva radio exterior, nunca RMG inductivo.
La frase de PDF 96 sobre sumar capacitancias por tramos no sustituye el
procedimiento de promedio de potenciales que se desarrolla en PDF 97.

## Convención y geometría

Posiciones físicas fijas P1, P2, P3: centros inicialmente rotulados A, B, C.
Se elige el ciclo de asignaciones fase→posición:

```text
Tramo I:   A→P1, B→P2, C→P3
Tramo II:  A→P2, B→P3, C→P1
Tramo III: A→P3, B→P1, C→P2
```

Los tres pesos son 1/3 y las longitudes L/3. El ciclo inverso recorre las
mismas asignaciones en otro orden y produce el mismo promedio. Sin transposición
solo se usa el tramo I con peso 1. La longitud longitudinal no cambia los
coeficientes por unidad de longitud; si falta, se representa en fracciones de L.

Las características de cada fase (cantidad de subconductores, radio, separación,
rotación y RMG individual) viajan con la fase. En cada tramo se reconstruyen
TODAS las posiciones y se ejecutan los cálculos completos de la etapa 4.
Si las fases son idénticas, las matrices se relacionan por R_t^T M R_t,
con R_t[posición, fase]=1. Si difieren, se recalculan y no se fuerza que las
diagonales o los términos mutuos sean iguales. No se reduce un doble circuito.

## Inductancia

```text
L_t = T_t^T L_sub,t T_t                         [H/m]
L_prom = (L_I + L_II + L_III)/3                 [H/m]
```

Se conserva la hipótesis de I_fase/n por subconductor, radios RMG y suelo de
la etapa 4. Los promedios de matrices simétricas son simétricos. No se añade
una corrección inductiva por el cruce físico de conductores en la transposición.
Sin suelo se muestran H L_prom H (media cero, rango 2) y B^T L_prom B,
con H=I−11^T/3, B=[[1,0],[0,1],[-1,-1]] e IA+IB+IC=0.

## Capacitancia: condensar fases, promediar potenciales, invertir

Sea F=2πε₀, P_sub,t adimensional y E_t la matriz equipotencial de la etapa 4:

```text
G_t = E_t^T P_sub,t^(-1) E_t
C_t = F G_t                                   [F/m]
P_fase,t = G_t^(-1) = F C_t^(-1)               [adimensional]
P_prom = (P_fase,I + P_fase,II + P_fase,III)/3
C_transpuesta = F P_prom^(-1)                  [F/m]
```

P_fase es el operador efectivo que relaciona las cargas TOTALES de fase
con los potenciales comunes de fase. No es el promedio de los bloques de
P_sub suponiendo cargas iguales. Las cargas se resolvieron primero con
equipotencialidad, por lo que se incluyen efectos de todos los subconductores.
Las inversiones se implementan mediante resolución de sistemas simétricos.

Se promedian las relaciones V_t=(1/F)P_fase,t q para una misma carga de fase
de referencia y se obtiene V_prom. Este es el modelo ideal solicitado por
las notas. En general **inv(promedio(P)) != promedio(inv(P))**.
El promedio directo de C corresponde a imponer los mismos potenciales locales
y promediar cargas: otro procedimiento, que se muestra solo como comparación,
no se usa como resultado transpuesto solicitado. No se afirma que ambos
procedimientos sean intercambiables en un modelo de línea distribuida.

Con suelo ideal se verifica P_prom C_transpuesta/F = I. Sin suelo no existe
una inversa absoluta de C ni de P_fase: se usa una base ortonormal Q de
1^T q=0, con QQ^T=H:

```text
G_reducida,t = Q^T (C_t/F) Q
P_fase,t = Q G_reducida,t^(-1) Q^T
P_prom = promedio(P_fase,t)
C_transpuesta = F Q (Q^T P_prom Q)^(-1) Q^T
P_prom C_transpuesta/F = H
```

Σq_fase=0; el potencial común es indeterminado. Se muestran matrices 3x3
proyectadas de rango 2, nunca una capacitancia absoluta a tierra ni una
inversión de la matriz singular. No se introduce una distancia d₀ en la interfaz.

## Hipótesis, unidades y caso de comprobación

Transposición ideal completa, longitudes iguales, geometría constante en cada
tramo, un único circuito, aproximación cuasiestática por unidad de longitud.
Sin conexiones de transición, efectos de extremos, corona, piel/proximidad,
pérdidas de tierra, Carson, cascada exacta de tramos ni propagación distribuida.
Se conserva el modelo de cargas/corrientes lineales de la etapa 4: equipotencialidad
capacitiva y corriente I/n inductiva son supuestos distintos.

Se usan μ₀=4π×10^-7 H/m y ε₀=8.8541878128e-12 F/m, constantes del proyecto.
Conversión L: H/m→mH/km o µH/m, factor 10^6. Conversión C: F/m→nF/km, 10^12.
La matriz con todas las diagonales iguales y todos los mutuos iguales se obtiene
para fases constructivamente idénticas; no se impone manualmente a los resultados.

Caso obligatorio proporcionado por el usuario: centros (-3,13), (3,13), (0,9) m;
n=4 por fase, cuadrado con lados horizontales/verticales y separación de vecinos
0.4572 m; radio exterior individual 0.011765 m; macizo no magnético uniforme;
suelo ideal. Las referencias esperadas se conservan solo en pruebas, nunca en
el código de cálculo. Se comparan L y C con atol=0.5e-6 en mH/km y nF/km,
rtol=0, por su redondeo a seis decimales. La comprobación independiente se
realiza por promedios de diagonales/mutuos y la inversa analítica de una matriz
con diagonal a y mutuo b, además del cálculo de tramos completo.
