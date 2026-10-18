# Etapa 4: conductores en haz, fuentes y ecuaciones

## Revisión de fuentes

- Notas de sistemas de transmision.pdf: PDF 49-50, medias geométricas de
  distancias propias y mutuas; PDF 76-78, haces regulares e hipótesis I/n;
  PDF 85-86, superposición de potenciales; PDF 92, radio capacitivo de haz;
  PDF 94-96, imágenes y matriz de capacitancia ya revisadas en la etapa 2.
  Se extrajo texto de estas secciones y se inspeccionaron visualmente PDF 76 y 92.
- Notas clase STE 17-09-26.pdf, PDF 2-3: geometría del polígono regular y
  distancia propia inductiva. Se inspeccionaron ambas páginas renderizadas.
- Kersting, Distribution System Modeling and Analysis, CRC Press, 2002:
  §4.1, ecuaciones (4.1)-(4.4), enlaces de flujo de varios conductores;
  §5.1, ecuaciones (5.1)-(5.2), superposición de potenciales; §5.2,
  ecuaciones (5.3), (5.6)-(5.10) y (5.14), imágenes e inversión del operador
  de potencial. Páginas impresas 77-78 y 110-113, PDF 92-93 y 125-128,
  revisadas en las etapas anteriores. La agregación equipotencial y la
  proyección neutral descritas abajo son derivaciones algebraicas de esas
  relaciones; no se atribuyen como fórmulas textuales del libro.

Correcciones y precauciones: en las notas generales PDF 77 aparece un signo
incorrecto al despejar el ángulo: de 2π/n+2α=π resulta α=π/2−π/n.
El manuscrito PDF 2 sí usa el signo correcto. En estas notas s representa
el radio circunscrito; en la interfaz **s es la separación entre vecinos**,
y se reserva a para el radio circunscrito. La separación anotada de 18 pulgadas
no se adopta como un valor óptimo universal ni como entrada predeterminada.
Los errores de subíndices de potencial en PDF 85-86 se evitan calculando cada
D_uv desde coordenadas: la influencia de C en A usa D_AC, no D_AB.
Los ejemplos de doble circuito y fórmulas promediadas por transposición no
se incorporan. No se confunde un haz espacial con las hebras de un ACSR.

## Geometría y medias geométricas

Un circuito, fases A/B/C. Cada fase permite n=1,2,3,4 subconductores idénticos.
Para n>1 se usa un polígono regular de lado s editable:

```text
a = s / [2 sin(π/n)]                                    [m]
x_k = x_c + a cos(θ_0 + 2πk/n)
y_k = h_c + a sin(θ_0 + 2πk/n)
```

Orientaciones iniciales: dos horizontales, triángulo con un vértice arriba,
cuadrado con lados horizontales/verticales. Una rotación adicional por fase
puede editarse. n=1 es exactamente el centro y no necesita separación.
Las distancias son entre centros reales y entre cada real y la imagen
reflejada respecto de Y=0. Se rechazan contactos entre círculos y con el suelo.

Sean d_uv las distancias dentro del haz y d_uu el término propio:

```text
g_haz = exp[(1/n²) Σ_u Σ_v ln(d_uv)], d_uu = g_individual [m]
r_cap = exp[(1/n²) Σ_u Σ_v ln(d_uv)], d_uu = R_exterior   [m]
D_AB  = exp[(1/(n_A n_B)) Σ_u∈A Σ_v∈B ln(D_uv)]          [m]
S_AB  = exp[(1/(n_A n_B)) Σ_u∈A Σ_v∈B ln(S_uv)]          [m]
```

Las medias geométricas se evalúan como medias de logaritmos de longitudes
normalizadas por 1 m, y se restituyen en m. No se redondea antes de calcular.
Para subconductores iguales y separación de vecinos s, tanto g_haz como r_cap
tienen la forma f(t), cambiando únicamente el término propio t:

| n | f(t) |
|---|---|
| 1 | t |
| 2 | (t s)^(1/2) |
| 3 | (t s²)^(1/3) |
| 4 | (t √2 s³)^(1/4) |

Se contrastan estas formas con la fórmula de las notas (n t a^(n−1))^(1/n).
El factor √2 del cuadrado proviene de la diagonal, no de un ajuste empírico.
El RMG individual puede ser del fabricante (obligatorio para el modo ACSR),
o R exp(−1/4) exclusivamente para macizo no magnético de corriente uniforme.
El radio capacitivo siempre parte del radio exterior, nunca del RMG inductivo.

## Inductancia: agregado geométrico, corrientes iguales

Con E_uv=1 si el subconductor u pertenece a fase v, n_v su cantidad y
T_uv=E_uv/n_v, se supone I_sub=T I_fase, es decir I_fase/n_v por subconductor.

```text
L_sub,uu = k ln(2h_u/g_u); L_sub,uv = k ln(S_uv/D_uv)   (suelo ideal)
k = μ₀/(2π), μ₀=4π×10^-7 H/m, como en la etapa 3
L_fase = T^T L_sub T                                  [H/m]
```

Esto equivale a L_aa=k ln(S_aa/g_haz,a) y L_ab=k ln(S_ab/D_ab),
usando TODAS las distancias a imágenes, incluidas las del mismo haz.
No se sustituye S_aa por 2h_c cuando hay subconductores a distintas alturas.
Sin suelo se usa la forma canónica de los enlaces, se agrega con T y se
obtienen H L_fase H y B^T L_fase B como en la etapa 3; solo IA+IB+IC=0.

Este agregado es exacto respecto del modelo de cargas/corrientes lineales
**bajo la hipótesis de corrientes iguales**, pero no resuelve su redistribución
por inductancias mutuas, impedancias o conexiones de los separadores.
Se muestra L_sub como matriz primitiva, no como una solución de corrientes.
La opción de un único conductor en cada centro con g_haz y r_cap es una
aproximación adicional, distinta del uso de distancias geométricas completas.

## Capacitancia: matriz explícita y fases equipotenciales

Se representan N=n_A+n_B+n_C conductores circulares con sus radios exteriores.
Con suelo ideal, P usa los mismos coeficientes de la etapa 2, ahora N×N:

```text
P_uu=ln(2h_u/R_u), P_uv=ln(S_uv/D_uv)
F=2πε₀, ε₀=8.8541878128e-12 F/m (valor del proyecto)
P W = E
q_sub = F W V_fase
C_fase = F E^T W = F E^T P^(-1) E                     [F/m]
```

Las cargas individuales se resuelven; no se impone q_fase/n. E V_fase impone
el mismo potencial a todos los subconductores de una fase. Se verifica P W=E,
simetría y energía positiva. Se muestran respuestas de carga para excitaciones
unitarias A, B y C. No es una reducción de Kron de neutros: se agregan cargas
de conductores conectados equipotencialmente. Se resuelve el sistema lineal
sin construir innecesariamente la inversa completa.

Sin suelo, solo está definido el problema de carga total cero y potencial
común indeterminado. P0 usa ln(1 m/R_u) y ln(1 m/D_uv). Sea Z una base
ortonormal de 1^T q=0, con N−1 columnas:

```text
A = Z^T P0 Z
W = Z A^(-1) Z^T E
q_sub = F W V_fase
C_fase = F E^T W
```

La proyección elimina el término común de cualquier referencia, igual que
el desarrollo de las notas para diferencias de potencial. Se verifica carga
total cero y que P0 W−E sea un vector común a todos los subconductores para
cada excitación: es decir, la equipotencialidad relativa, no un potencial
absoluto a infinito. C_fase tiene rango 2 y anula el vector [1,1,1]. No se
invierte esa matriz ni se calcula capacitancia a tierra sin suelo.

## Aproximación de centro y límites

Se ofrece por separado una comparación capacitiva con tres conductores
equivalentes ubicados en los centros y radios r_cap. La aproximación no
reproduce necesariamente las cargas individuales ni su equipotencialidad.
No se usan los r_cap en la formulación matricial explícita.

Ambos modelos siguen siendo aproximaciones de conductores delgados con
cargas/corrientes lineales y sección circular. Resolver explícitamente cada
subconductor no resuelve exactamente su carga superficial ni la estructura
trenzada ACSR. El dato de fabricante debe corresponder al subconductor real.
Sin efectos piel/proximidad, corona, flecha, topografía ni pérdidas en tierra.
Se conserva un único circuito sin transposición. No se implementa Carson.
Los criterios de condición numérica (1e12) no son distancias reglamentarias.
Unidades: L en H/m, µH/m o mH/km (factor 10^6); C en F/m o nF/km (10^12).
Las pruebas n=1 deben reproducir los módulos originales y los casos conocidos;
para n=2,3,4 contrastan geometría, formas cerradas, agregación y equipotencialidad.
