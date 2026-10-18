# Capacitancia de tres fases con imágenes y suelo ideal

## Fuentes revisadas

1. **Notas de sistemas de transmision.pdf**, capítulo 3, páginas PDF 81-82
   (definición de capacitancia, permitividad y aire), 94-96 (suelo ideal,
   imágenes, coeficientes P y relación matricial). Las páginas PDF se cuentan
   desde 1. No se atribuyen autor, fecha ni edición no comprobados.
   Se inspeccionaron visualmente las páginas 94-96, además de extraer texto.
2. **William H. Kersting, Distribution System Modeling and Analysis**, CRC Press,
   copyright 2002, ISBN 0-8493-0812-7, capítulo 5, sección 5.2, páginas impresas
   111-113 (páginas PDF 126-128 del libro completo). Ecuaciones (5.3), (5.6),
   (5.7), (5.9), (5.10) y (5.14); figura 5.3. Se inspeccionaron las tres páginas
   renderizadas y el texto. La identidad editorial se verificó en páginas PDF 4-5.
   El archivo **Cap 4 Kersting - Ecuaciones Carson.pdf** también incluye esta
   sección: páginas PDF 35-37, impresas 111-113. Pese al nombre del archivo,
   el modelo usado corresponde al capítulo 5, no a Carson.

Se inventariaron los demás PDF y se buscaron términos de capacitancia en sus
capas de texto. Los apuntes manuscritos en `Notas de Clase/Notas de Clase/`
no tienen texto extraíble; no se les atribuyen ecuaciones ni revisión exhaustiva.
`Carson.pdf` y los documentos de inductancia no son fuentes del modelo implementado.

## Ecuaciones y notación de la implementación

Cada fase i tiene centro (x_i, h_i), radio exterior r_i, en metros. La imagen
respecto del plano Y = 0 está en (x_i, -h_i) y tiene carga opuesta
(Kersting, figura 5.3 y ecuación 5.3).

```text
D_ij = sqrt((x_i - x_j)^2 + (h_i - h_j)^2)       [m], i != j
S_ij = D_ij_imagen = sqrt((x_i - x_j)^2 + (h_i + h_j)^2) [m]
S_ii = 2 h_i                                   [m]
P_ii = ln(S_ii / r_i)                          [adimensional]
P_ij = ln(S_ij / D_ij), i != j                 [adimensional]
V = (1 / (2 pi epsilon_0)) P q
q = C V
C = 2 pi epsilon_0 P^(-1)                     [F/m]
P C = 2 pi epsilon_0 I                        [F/m]
```

Las expresiones de P y C aparecen en la página PDF 96 de las notas;
la construcción con imágenes, en la 95. S_ii = 2h_i y las expresiones de distancia
son consecuencias geométricas de la reflexión en Y = 0.

**Diferencia de notación:** Kersting define coeficientes dimensionales de potencial
P_hat = P / (2 pi epsilon), cuya inversa es C. En este proyecto P contiene solo
logaritmos, según las notas y la solicitud. No se toma la inversa de P sin
multiplicar por 2 pi epsilon_0. Tampoco se usa el coeficiente numérico en
mile/microfarad de las ecuaciones (5.9)-(5.10): se trabaja íntegramente en SI.
La diagonal de la matriz de distancias reales es cero y no se usa dentro del
logaritmo; se sustituye por el radio exterior únicamente para el término propio.

## Permitividad y unidades

- epsilon_0 = **8.8541878128e-12 F/m**, valor proporcionado expresamente por el
  usuario para este proyecto y el caso obligatorio. No se presenta como valor
  exacto ni como una cifra transcrita de los PDF.
- Las fuentes usan aproximadamente 8.85e-12 F/m y epsilon_r del aire igual a 1.
  Se conserva la hipótesis del aire con epsilon = epsilon_0; se usa la cifra
  indicada por el usuario para reproducir el caso requerido.
- Los argumentos de ln son cocientes de longitudes en las mismas unidades.
- 1 F/m = 10^9 nF/m = **10^12 nF/km**. La conversión se aplica a cada elemento
  de la matriz y conserva su signo.
- C es la **matriz de coeficientes de capacitancia de Maxwell**, con tensiones
  respecto del suelo: q [C/m] = C [F/m] V [V]. Los elementos fuera de la diagonal
  pueden ser negativos; no se deben reemplazar por su valor absoluto ni
  interpretar la diagonal como una capacitancia de secuencia positiva.

## Supuestos y límites

- Un circuito trifásico, exactamente A, B y C, un conductor circular por fase.
- Conductores rectos, paralelos y de gran longitud, geometría transversal uniforme.
- Suelo ideal: plano infinito perfectamente conductor y equipotencial a 0 V.
- Aire homogéneo con permitividad relativa 1. Modelo electrostático por unidad
  de longitud; ni frecuencia ni longitud longitudinal modifican C en F/m.
- Aproximación de carga lineal y radio circular exterior empleada por las fuentes;
  apropiada para conductores delgados respecto de alturas y separaciones.
  No es una solución exacta de la distribución superficial de carga para cilindros
  gruesos o próximos. No se inventa un umbral normativo de delgadez.
- r_i > 0, r_i < h_i; los círculos de los conductores no se tocan ni se solapan.
  La matriz debe ser finita, definida positiva y numéricamente invertible.
- Se usa el **radio exterior**, nunca GMR inductivo ni el factor inductivo de radio.
  No se modelan hebras, alma ni geometría ACSR con parámetros supuestos.
- Sin neutro ni cables de guarda, reducción de Kron, Carson, resistividad del suelo,
  haces, transposición, doble circuito, admitancia ni capacitancia total de la línea.
- Los circuitos múltiples siguen disponibles solo para la geometría previamente
  implementada; no se extiende a ellos este cálculo de capacitancia.

## Caso obligatorio y aceptación

Fuente de los datos y de la matriz esperada: solicitud del usuario, no un ejemplo
extraído de los PDF. A=(-3,13), B=(3,13), C=(0,9) m;
r_A=r_B=r_C=0.011765 m; epsilon_0 según se indicó arriba.

Matriz de referencia [nF/km], orden A, B, C:

```text
[[ 7.719800, -1.240982, -1.317160],
 [-1.240982,  7.719800, -1.317160],
 [-1.317160, -1.317160,  8.122161]]
```

Se acepta una diferencia absoluta <= 0.5e-6 nF/km por el redondeo de los valores
esperados a seis decimales. Se verifica además P C = 2 pi epsilon_0 I usando C
en F/m, simetría, definición positiva e invertibilidad. La comprobación residual
normalizada usa P C / (2 pi epsilon_0) - I, evitando una tolerancia absoluta que
oculte errores por la escala de 10^-11 F/m.
