# Etapa 7C: componentes simétricas y contraste de dos guardas

## Fuentes y convención

Se consultaron antes de programar las páginas impresas 89-91 del capítulo 4
de Kersting, *Distribution System Modeling and Analysis*, CRC Press, 2002,
§4.1.7, ecuaciones (4.59)-(4.67), y el ejemplo 4.1 pp.94-95. En la copia
`Cap 4 Kersting - Ecuaciones Carson.pdf` son PDF 13-15 y 18-19.
Se extrajo el texto y se inspeccionaron visualmente PDF 13,14,18 para comprobar
el operador, los exponentes y los signos de los acoplamientos publicados.
La presentación del curso `Carson.pdf`, diapositivas 13-15, confirma la misma
convención y distingue línea transpuesta y redes de secuencia acopladas.
Las notas del 06-10-26 PDF 1-2 mantienen separados los parámetros por longitud
y los totales; su equivalente monofásico exige equilibrio/transposición.
No se impone ese equivalente en este módulo. Las hipótesis de neutros y los
ejemplos incompletos de las notas del 01-10-26 se registran en `kron.md`.

Convención fasorial exp(jωt), orden de fases ABC y operador a=exp(j2π/3),
rotación de +120 grados. 1+a+a²=0 y a³=1.

```text
Vabc=A V012; Iabc=A I012                    (4.59)-(4.62)
A = [[1,1,1], [1,a²,a], [1,a,a²]]          (4.61)
A^-1=(1/3)[[1,1,1],[1,a,a²],[1,a²,a]]      (4.64)
Z012=A^-1 Zabc A                          (4.66)
```

Secuencia 0: [1,1,1]; positiva 1: [1,a²,a]; negativa 2: [1,a,a²].
Para esta A, A^-1=A conjugada transpuesta/3; no A transpuesta/3.
Zabc es la impedancia de fases después de una reducción de Kron válida,
no el bloque primitivo Zpp que todavía contiene el efecto de los auxiliares
sin eliminar. La transformación conserva Ω/m, Ω/km u Ω/milla.

## Matriz completa y significado físico

Se guardan y muestran todos los elementos. Z012 NO es en general simétrica
ni hermítica, aun si Zabc=Zabcᵀ. No se simetriza ni diagonaliza el resultado.
Para un bloque trifásico recíproco, Z11=Z22 sin que eso implique transposición.
Los términos Zij con i≠j describen acoplamiento entre secuencias:
ΔVi/ℓ=Σj Zij Ij. No se puede sustituir esta ecuación por ΔVi/ℓ=Zii Ii cuando
hay otras corrientes de secuencia. La igualdad Z1=Z2 no prueba desacoplamiento.

Kersting pp.91 y 95 explica que una matriz de fase idealmente transpuesta,
con propias iguales y mutuas iguales, se transforma en diagonal. En el ejemplo
sin transponer sus diagonales coinciden con las del promedio idealizado de
p.95, pero los acoplamientos no desaparecen. Esta etapa NO añade transposición
a Carson/Kron ni altera la transposición inductiva o capacitiva de otras etapas.

Para doble circuito se usa B=diag(A,A), con entradas A,B,C,A',B',C' y salidas
0 C1,1 C1,2 C1,0 C2,1 C2,2 C2. Cada bloque entre circuitos se transforma como
A^-1 Z12 A y se conserva. No se reduce la matriz de seis fases a tres.
Esta extensión por cambio de base sigue directamente de las ecuaciones
de dos circuitos, sin inferir conexiones eléctricas entre ellos.

## Ejemplo 4.1 de Kersting

Las fases, neutro, coordenadas, R_AC y RMG son los de `kron.md`.
f=60 Hz, ρ=100 Ω·m, Carson modificado y neutro multitierra ideal declarado.
Referencia publicada p.94 [Ω/milla], orden 0,1,2:

```text
[[.7735+j1.9373,  .0256+j.0115, -.0321+j.0159],
 [-.0321+j.0159, .3061+j.6270, -.0723-j.0060],
 [ .0256+j.0115, .0723-j.0059, .3061+j.6270]]
```

No hay discrepancia de convención al utilizar A como se indica arriba.
Las diferencias numéricas restantes corresponden al redondeo de matrices y
constantes del libro. Se comparan las partes real e imaginaria de TODOS los
elementos con tolerancia absoluta 6e-5 Ω/milla; no solo las diagonales.
No se utiliza la errata de la partición primitiva de p.94 ni se alteran
resultados para forzar coincidencia. No se certifica exactitud de Carson
modificado ni equivalencia PSCAD a partir de este contraste algebraico.

## Dos guardas: ensayo algebraico reproducible

El botón y el script de validación construyen geometrías SINTÉTICAS.
Para un circuito, fases del ejemplo 4.1; guardas en (-4,40) y (11,40) ft.
Para dos circuitos, el segundo repite las fases desplazadas +20 ft en X;
guardas en (-4,40) y (31,40) ft. Se reutilizan explícitamente los datos
eléctricos del neutro del libro: R_AC=.592 Ω/milla, RMG=.00814 ft.
No se afirma que sean guardas comerciales, ni que estas configuraciones
aparezcan en Kersting, ni se inventa una ficha de material. La condición
ΔVn=0 es impuesta para probar el álgebra; no valida una puesta a tierra real.

El programa principal conserva su resolución Znn Y=Znp y complemento de Schur.
El contraste independiente NO utiliza esa función ni calcula ese complemento:

```text
K = [[Ip_identidad, 0], [Znp/s, Znn/s]]
K W = [[Ip_identidad], [0]]       (SciPy, LU general)
Vp_por_Ip = (Zterminal W)[filas de fases]
```

s es el máximo módulo de las filas auxiliares, solo para normalización.
Las últimas filas de Zterminal W deben ser nulas. Se contrastan Vp_por_Ip
y la reducida principal, y se informa el error relativo y residuo de frontera.
Las pruebas agregan una segunda comprobación: reconstrucción independiente
de Carson modificado en pies/millas y eliminación mediante la inversa 2×2
escrita con su determinante. Se incluyen ambos acoplamientos de guarda;
una eliminación que descarte las mutuas entre guardas no es equivalente.

Se prueban condiciones aisladas, desconocidas y sin justificación, además de
Znn singular y cond>10^12. El rechazo de estas últimas es una política numérica
existente, no un límite físico universal. Ni el ensayo ni la transformación
de secuencias evitan las condiciones de aplicación de Kron de `kron.md`.

## Exportación y separación de métodos

JSON conserva números complejos por partes real/imaginaria, matrices de cambio
de base, orden y unidades. PDF presenta ecuaciones por pasos en recuadros
ajustables y matrices R/X completas, con encabezado de secuencia/circuito,
unidades y partición horizontal de tablas anchas. No captura fórmulas como
imágenes recortadas. Se conserva el resultado anterior de Carson/Kron.

Carson modificado y P/Q finitos siguen siendo aproximaciones diferentes.
Suelo ideal, capacitancia y sus promedios de transposición permanecen separados.
Los resultados publicados de este ejemplo corresponden solo a Carson modificado.
