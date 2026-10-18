# Etapa 3: ecuaciones, fuentes y revisión de inductancia

## Documentos consultados

- **Notas de sistemas de transmision.pdf**, capítulo 2, páginas PDF 32-39:
  enlaces de flujo interno/externo, corriente uniforme y radio equivalente;
  páginas PDF 43-45: tres conductores sin suelo y suma de corrientes cero;
  páginas PDF 46-48: imágenes con corrientes opuestas y matriz de inductancias.
  Se extrajo texto y se renderizaron las páginas 39 y 44-48. Sin atribuir autor
  o edición que no se hayan comprobado.
- **Notas de Clase/Notas de Clase/Notas clase STE 08-09-26.pdf**, manuscrito:
  páginas PDF 1-4, enlaces trifásicos sin suelo, cancelación del término lejano
  y advertencia de argumentos adimensionales; páginas PDF 7-10, suelo ideal,
  imágenes y matriz. Se inspeccionaron visualmente estas páginas completas.
- **Notas de Clase/Notas de Clase/Notas clase STE 15-09-26.pdf**, página PDF 1:
  caso equilátero como contraste, sin transposición implementada. Se revisó
  su primera página en la hoja de contacto del inventario.
- **Notas de Clase/Notas de Clase/Soucion Ejercicio Matriz Inductancia.pdf**,
  páginas PDF 1-4: aplicación de radio equivalente, distancias a imágenes,
  matriz L, reactancia e impedancia inductiva. Se extrajo el texto completo.
- **William H. Kersting, Distribution System Modeling and Analysis**, CRC Press,
  2002, ISBN 0-8493-0812-7, capítulo 4, §4.1, páginas impresas 77-78
  (PDF 92-93): ecuaciones (4.1)-(4.4), enlaces de flujo propios/mutuos,
  GMR y condición de suma de corrientes cero. Se inspeccionaron las páginas
  renderizadas. La sección de transposición se usa solo para contrastar límites;
  no se implementa ni se usa Carson.

Las páginas PDF se cuentan desde 1. El inventario visual de las primeras páginas
de los apuntes de clase permitió localizar los documentos pertinentes; no se
atribuye una revisión completa a todos los documentos de la carpeta.

## Correcciones y precauciones identificadas

1. Notas generales, página 44: tras la primera ecuación correcta de lambda_1,
   aparece un factor I_1 adicional fuera de una suma que ya contiene corrientes.
   Eso daría dimensiones incorrectas. Se usa un solo factor mu_0/(2 pi).
2. Notas generales, página 45: no es correcto escribir que las distancias lejanas
   son aproximadamente cero. Al alejar el punto, sus **cocientes tienden a 1**
   y los logaritmos de los cocientes tienden a cero. Esto coincide con el
   desarrollo manuscrito del 08-09-26, página 3.
3. Manuscrito 08-09-26, página 3: el término de i_2 en lambda_3 tiene escrito
   d_12; por geometría y simetría debe ser d_23. La matriz de la página 4
   sí utiliza d_32. Se usa D_ij = D_ji calculado desde las coordenadas.
4. Notas generales, página 48: una ecuación escalar usa R'_2 en el término
   propio de la fase 3; la matriz posterior usa correctamente R'_3.
5. Expresiones ln(1/RMG) o ln(1/D) de las notas y Kersting requieren una
   unidad de longitud implícita. Se explicita d_0 en metros y se usa ln(d_0/RMG)
   o ln(d_0/D). No se presenta esta matriz de referencia como absoluta y única.
6. Apunte 15-09-26, página 1: I_A=I_B=I_C no puede interpretarse como igualdad
   de fasores equilibrados distintos de cero. Son iguales sus magnitudes, con
   desfases de 120 grados, y su suma fasorial es cero.
7. Solución de ejercicio, página 3: el paso rotulado mH/km muestra un factor
   1000; de H/m a mH/km se necesitan **10^6**, pues hay 1000 m/km y
   1000 mH/H. Los números finales del ejemplo corresponden al orden de
   magnitud de la conversión completa. No se copia ese factor incompleto.
8. No se obtiene el radio exterior de un ACSR a partir de su área nominal
   mediante sqrt(A/pi), ni se supone que su RMG sea el de un cilindro macizo.
   La alternativa de fabricante requiere un RMG y su referencia técnica.
9. La frase de las notas generales, página 48, que afirma que los enlaces no
   cambian al considerar suelo ideal no se adopta como una igualdad general:
   las contribuciones de las imágenes sí modifican los coeficientes para una
   geometría y corrientes dadas. No se confunde esa modificación con la
   equivalencia entre radio real y RMG que incorpora el flujo interno.

## RMG y constante utilizada

Solo para un conductor **circular macizo, no magnético (mu_r=1), con corriente
uniforme**, el enlace interno equivale a L_interna=mu_0/(8 pi). Al sumarlo al
externo:

```text
L = mu_0/(2 pi) [ln(d/R) + 1/4]
  = mu_0/(2 pi) ln(d/(R exp(-1/4)))
RMG = R exp(-1/4)                               [m]
```

Fuente: notas generales, páginas PDF 37-39; la igualdad se comprueba
algebraicamente. El valor RMG del fabricante se usa directamente, sin aplicarle
otra vez exp(-1/4). No se calcula distribución de corriente, efecto piel, efecto
de proximidad ni permeabilidad del alma de un ACSR.

mu_0 = **4 pi 10^-7 H/m** es la constante de modelo indicada por el usuario.
En esta implementación k = mu_0/(2 pi) = 2e-7 H/m. No se afirma que esta cifra
sea una constante exacta del SI moderno; se conserva el valor solicitado.

## Suelo ideal

```text
Imagen j: (x_j, -h_j), corriente -I_j
D_ij = hypot(x_i-x_j, h_i-h_j)                   [m], i != j
S_ij = hypot(x_i-x_j, h_i+h_j)                   [m]
S_ii = 2h_i                                    [m]
K_ii = ln(S_ii/RMG_i); K_ij = ln(S_ij/D_ij)      [adimensional]
L = k K                                        [H/m]
lambda = L I                                   [Wb·vuelta/m]
```

Fuente: notas generales PDF 46-48; clase 08-09-26, PDF 7-10; solución PDF 2-3.
Los índices se verifican con simetría, coordenadas y las matrices de las fuentes.
El término propio **ya incluye el enlace interno a través del RMG**; no se añade
otra vez mu_0/(8 pi). El plano conductor ideal fija el retorno del modelo de
imágenes. No equivale a un suelo de resistividad finita ni a Carson.

## Sin suelo: resultados principales y deducción avanzada

La interfaz principal ya no solicita d_0. Presenta L_equilibrada de media cero
y L_lazos en H/m, microH/m y mH/km. El ensayo muestra enlaces proyectados y
diferencias de lazos. La referencia se conserva solo en una opción avanzada;
un dato ausente o inválido en ella no condiciona estos resultados.

Fuente del desarrollo por enlaces de flujo y cancelación del punto lejano:
notas generales PDF 43-45; clase 08-09-26, PDF 1-4; Kersting (4.1)-(4.4).
Se trabaja exclusivamente con corrientes cuya suma es cero, incluyendo los
fasores trifásicos equilibrados. Se excluye la componente de secuencia cero.

```text
K_ref,ii(d_0) = ln(d_0/RMG_i)
K_ref,ij(d_0) = ln(d_0/D_ij), i != j
L_ref(d_0) = k K_ref(d_0)                       [H/m]
lambda_i = k [ I_i ln(d_0/RMG_i) + sum_(j!=i) I_j ln(d_0/D_ij) ]
L_ref(a d_0) - L_ref(d_0) = k ln(a) 1 1^T
```

Como 1^T I=0, la variación aplicada a I es cero. Por tanto los enlaces
calculados bajo esta condición, las diferencias de enlaces y la energía
cuadrática no dependen de d_0. La matriz 3x3 L_ref sí depende de d_0 y no
describe corrientes arbitrarias sin un retorno físico. d_0 es una **referencia
algebraica común**, no una distancia real a un conductor de retorno; no se
simula un punto lejano finito. Puede elegirse cualquier d_0 positivo, aunque
algunas elecciones produzcan términos mutuos negativos.

La implementación añade dos representaciones derivadas algebraicamente
(no son ecuaciones nuevas atribuidas a los libros):

```text
H = I_3 - 1 1^T/3
L_equilibrada = H L_ref H                       [H/m], 3x3, rango 2
B = [[1,0], [0,1], [-1,-1]]
I = B [I_A,I_B]^T, I_C=-I_A-I_B
L_lazos = B^T L_ref B                           [H/m], 2x2
[lambda_A-lambda_C, lambda_B-lambda_C]^T = L_lazos [I_A,I_B]^T
```

El contraste con el desarrollo de las páginas PDF 2-4 del manuscrito 08-09-26
y 44-45 de las notas generales es el siguiente: al imponer I_C=-I_A-I_B y
restar los enlaces de C, todos los términos del punto lejano común se cancelan.
La advertencia manuscrita de que el argumento de ln debe ser adimensional se
respeta usando cocientes de distancias. La errata de las notas generales que
iguala las distancias lejanas a cero no se toma como hipótesis física.

Aplicando B a ambos lados se obtiene la forma directa de los dos lazos, sin d_0:

```text
g_i = RMG_i, k = mu_0/(2 pi)
L_lazos,11 = k ln(D_AC^2 / (g_A g_C))
L_lazos,22 = k ln(D_BC^2 / (g_B g_C))
L_lazos,12 = L_lazos,21 = k ln(D_AC D_BC / (D_AB g_C))
T = B (B^T B)^(-1) = (1/3) [[2,-1],[-1,2],[-1,-1]]
L_equilibrada = T L_lazos T^T
```

Las tres expresiones de lazos tienen cocientes m²/m². T es adimensional y
la proyección está en H/m. Son consecuencias algebraicas de los enlaces de
las notas, no nuevas fórmulas físicas atribuidas al profesor ni una modificación
del modelo. H = T B^T = I_3 - 11^T/3, por lo que T L_lazos T^T = H L_ref H.

El módulo numérico ya verificado se conserva íntegro: obtiene las reducciones
desde la matriz canónica de logaritmos normalizados con la unidad de 1 m, sin
utilizar d_0 en ellas. La interfaz aprovecha ese cálculo directo existente.
La normalización interna de unidades no representa una elección de retorno
físico. La API de bajo nivel mantiene su parámetro de referencia para consultar
L_ref por compatibilidad y para la deducción avanzada; la interfaz no expone
su matriz canónica auxiliar como resultado principal.

En la opción avanzada se verifican explícitamente d_0 = 10, 1000 y 2000 m.
Las pruebas comparan H L_ref H y B^T L_ref B con las fórmulas directas
anteriores, así como enlaces proyectados y reactancia. L_ref sí cambia;
los resultados físicos restringidos son invariantes (rtol=1e-14,
atol=1e-21 H/m para las matrices). La referencia es opcional y su validación
se limita a esa opción avanzada.

L_equilibrada conserva la acción proyectada de suma cero y las diferencias de
enlaces; es una representación de media cero, no una inductancia absoluta única.
L_lazos representa los lazos A-C y B-C con sus corrientes independientes; depende
de la base de lazos elegida, pero no de d_0. La proyección 3x3 es singular por
construcción y no debe invertirse ni usarse para secuencia cero. Se comprueba
definición positiva en los dos lazos, no en L_ref arbitraria.

Para ilustrar el resultado físico se permite un ensayo ABC explícito de amplitud
I_0 en amperios: I=I_0[1, exp(-j2pi/3), exp(j2pi/3)]. Es un fasor de ensayo,
no una corriente deducida de un proyecto. Se muestran enlaces propios/mutuos,
su suma y diferencias respecto de C. La parte común se elimina al mostrar
enlaces proyectados y diferencias de tensión inductiva.

## Unidades y reactancia

```text
1 H/m = 10^6 microH/m = 10^6 mH/km
X = omega L = 2 pi f L                          [ohm/m], con L en H/m
X [ohm/km] = 1000 X [ohm/m]
Delta V / longitud = j X I                      [V/m]
```

X es la matriz real de coeficientes de reactancia; la impedancia inductiva sería
jX. No se añade resistencia ni se calcula una impedancia completa. Para el
caso sin suelo, se usa la misma restricción de suma cero y se muestran X
proyectada y X de lazos, no una reactancia absoluta única.
Fuente de la relación armonica: solución del ejercicio PDF 3-4; se separa
reactancia por unidad de longitud de la reactancia total omega L longitud
que aparece en ese ejemplo. No se calcula reactancia total en esta etapa.

## Validación, alcance y caso obligatorio

- Tres fases A/B/C, un circuito; conductores paralelos de gran longitud y
  geometría transversal uniforme. Sin transposición, haz ni doble circuito.
- Radios y RMG finitos positivos. Para el alcance de conductor no magnético
  circular se exige RMG <= radio exterior. Un RMG conocido requiere fuente;
  el radio exterior se usa para validar contacto, no para recalcular ese RMG.
- Centros sobre Y=0; sin contacto con suelo ni entre círculos. Aunque el modelo
  sin suelo no usa imágenes, se conserva la geometría de línea aérea de la app.
- Aproximación de conductores delgados respecto a alturas y separaciones; no
  solución exacta de campos de cilindros gruesos o cercanos, ni de corrientes
  no uniformes. No se inventa un umbral reglamentario de delgadez.
- Matrices finitas y energía positiva en el espacio aplicable. Se rechazan
  matrices reducidas mal condicionadas (>1e12, criterio numérico de software).
- Frecuencia positiva para X; L y RMG pueden calcularse sin frecuencia.
- Las opciones y radios de inductancia y capacitancia son independientes;
  comparten las coordenadas y la frecuencia general de la línea.

Datos del caso, RMG de referencia y L esperada: **solicitud del usuario**, no
transcripción de un caso de los PDF. A=(-3,13), B=(3,13), C=(0,9) m;
R=0.011765 m; modelo macizo uniforme no magnético; suelo ideal.

```text
RMG esperado = 0.00916259121 m
L esperada [mH/km], orden A/B/C:
[[1.59014456, 0.29845590, 0.29816333],
 [0.29845590, 1.59014456, 0.29816333],
 [0.29816333, 0.29816333, 1.51659960]]
```

Se compara RMG con tolerancia absoluta 5e-12 m y L con 5e-9 mH/km, rtol=0,
correspondientes al redondeo de las cifras proporcionadas. Se prueba también
invariancia de los resultados equilibrados al cambiar d_0, en vez de exigir
igualdad de las matrices referidas que, por definición, no son únicas.
