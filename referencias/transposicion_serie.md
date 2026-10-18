# Etapa 7D: transposición de impedancias serie Carson

## Ecuaciones y fuentes

Se reutilizan las ecuaciones ya documentadas en `secuencias.md` y el registro
de transposición del proyecto. Se volvió a consultar Kersting, *Distribution
System Modeling and Analysis*, CRC Press, 2002, §4.1.7, página impresa 91
(PDF 15 de `Cap 4 Kersting - Ecuaciones Carson.pdf`), (4.68)-(4.72), y p.95
(PDF 19), continuación del ejemplo 4.1. La presentación `Carson.pdf`,
diapositivas 12-13, documentada en etapas anteriores, utiliza los mismos
promedios de términos propios y mutuos. No se aplica este promedio a C.

Una fase ocupa cada posición física una vez en tres secciones de igual longitud.
Las asignaciones, en orden de fases ABC, son [A,B,C], [B,C,A], [C,A,B].

```text
St = matriz de asignación: columna p es la posición física de la fase p
Zt = Stᵀ Zoriginal St
Zprom = (Z0 + Z1 + Z2)/3
Zpropio = (ZAA + ZBB + ZCC)/3                         (4.68)
Zmutuo = (ZAB + ZBC + ZCA)/3                         (4.69)
Zprom = [[Zpropio,Zmutuo,Zmutuo], ...]                (4.70)
```

Las dos últimas expresiones escalares corresponden a un bloque trifásico
recíproco. Para seis fases se usan permutaciones sincronizadas
St=diag(St3,St3). Los bloques entre circuitos se promedian completos, conservando
las seis fases. No se sustituyen por un solo mutuo ni por un equivalente 3×3.
Otro calendario relativo de los circuitos produciría otros promedios; no se
afirma que tres ciclos sincronizados equivalgan a nueve combinaciones independientes.

Se comprueba simetría compleja por transposición, no por conjugación. La matriz
original siempre queda disponible y el selector solo cambia el resultado principal.
No se fuerzan ceros en fase o secuencia. El promedio es invariante bajo ciclos
simultáneos de las etiquetas y preserva traza y unidades.

## Condiciones físicas y auxiliares

El promedio de matrices de posiciones fijas supone fases eléctricamente
equivalentes dentro de cada circuito. La interfaz comprueba R_AC, RMG, radio
si está disponible, número de subconductores y distancias internas del haz.
Se rechaza promediar resistencias de conductores de fase diferentes mediante
simple cambio de etiquetas. Cada circuito puede utilizar otro conductor.
Se conserva la aproximación previa de corrientes iguales I_fase/n en haces.

Con auxiliares se exige la misma declaración explícita de ΔVn=0 de Kron.
Las guardas/neutros permanecen en posiciones fijas y se reduce cada tramo
ANTES de promediar. Por permutación de fases, manteniendo los auxiliares fijos:

```text
Zred,t = Stᵀ [Zpp-Zpn inversa(Znn) Znp] St
Zprom = Σt Zred,t/3
```

Esto NO equivale en general a aplicar Kron al promedio de la primitiva.
Se incluyen pruebas que distinguen ambas operaciones. No se eliminan auxiliares
aislados ni de conexión desconocida. Con guardas que cambien de posición o
conexiones por tramo se necesitaría otro modelo de entrada.

El promedio serie supone corriente de fase continua a través de tramos y
cruces de longitud despreciable. No reemplaza una cascada distribuida exacta
con tensiones/corrientes variables. Capacitancia e inductancia ideal conservan
sus modelos, incluyendo sus procedimientos de transposición independientes.

## Fuentes del caso DOVE y validación en orden

Los tres archivos suministrados se encontraron, sin moverlos ni modificarlos, en:
`referencias/Datos_DOVE_PSCAD_para_Codex/referencias/comparacion_pscad/`.

- `ste_carson.json`: entradas y resultados SIN transposición; 12 subconductores,
  cuatro por fase; 60 Hz y ρ=100 Ω·m; método `kersting_pq_finite`.
  NO se cambia este método por Carson modificado para ajustar resultados.
- `DOVE_220kV_SinTransposicion_Prueba.txt`: resultados PSCAD sin transposición.
- `DOVE_220kV_ConTransposicion_Prueba.txt`: resultados PSCAD con transposición.
- `LEEME.txt` y aclaración del usuario: configuración y resistencia DC de PSCAD.

Se validó primero el caso sin transposición: recálculo de los 12 subconductores
y agregación por I/n idénticos a la matriz exportada, residuo máximo 0 Ω/m.
Después se calculó el promedio de las tres permutaciones de esa matriz.
No se utilizaron las matrices guardadas ni los valores esperados como salidas fijas.

Entradas del JSON: A=(-3,13), B=(3,13), C=(0,9) m; haz cuadrado de lado
0.4572 m; radio exterior 0.011765 m; RMG individual 0.00954024 m.
R_AC individual=0.1859 Ω/milla=0.11551290463692038 Ω/km, fuente declarada
en el JSON: «Kersting, Appendix A», datos bibliográficos a 60 Hz.
No se aplica R exp(-1/4) al ACSR.

Promedio esperado proporcionado por el usuario y comprobado desde entradas:

```text
Zpropio = 0.0863981565 + j0.6358520847 Ω/km
Zmutuo  = 0.0575147177 + j0.3845045830 Ω/km
```

La prueba usa tolerancia absoluta 5e-11 Ω/km, rtol=0, por redondeo a diez
decimales. La matriz completa se calcula, no se rellena con esas constantes.

## Lectura de PSCAD y comparación coherente

Se extrae únicamente el bloque exacto `SERIES IMPEDANCE MATRIX (Z) [ohms/m]`
dentro de PHASE DOMAIN DATA a 60 Hz. Cada par M,N representa M+jN.
Se convierte Ω/m a Ω/km multiplicando por 1000. NO se utilizan las impedancias
totales [Ohms] del bloque LOAD FLOW, matrices modales/de secuencias, ni
LONG-LINE CORRECTED SERIES IMPEDANCE MATRIX [ohms]. Por ello la longitud
100 km del ensayo PSCAD no interviene en el cálculo por unidad de longitud.
El parser exige el tamaño completo y no recorta seis fases a tres.

Los dos estados PSCAD se leen de sus respectivos TXT, independientemente.
No se fabrica el resultado PSCAD transpuesto a partir de STE o del TXT sin
transponer. El promedio cíclico de la Z PSCAD sin transponer coincide con el
TXT transpuesto dentro de su redondeo; se prueba como control adicional.

Para cada elemento i,j de ambos estados:

```text
Error_R [%] = 100 |R_STE - R_PSCAD| / |R_PSCAD|
Error_X [%] = 100 |X_STE - X_PSCAD| / |X_PSCAD|
```

Si una referencia es cero el porcentaje correspondiente es indefinido, incluso
si STE también da cero. Datos ausentes quedan vacíos, sin errores cero supuestos.
La tabla exporta los 18 elementos (nueve por estado); para doble circuito, 72.

PSCAD utiliza R_DC=0.102 Ω/km por subconductor según el usuario/LEEME.
STE utiliza R_AC=0.11551290463692038 Ω/km. No se convierten ni sustituyen
automáticamente y no se supone que los modelos internos de conductor sean
idénticos. Se desconocen aquí los detalles completos de las correcciones
internas AC de PSCAD, por lo que las diferencias no constituyen un error puro
del algoritmo ni una certificación de equivalencia física.

Con transposición, PSCAD suministra Zpropio=0.0841586314+j0.644676406 Ω/km
y Zmutuo=0.0579044283+j0.389821698 Ω/km. Las diferencias del caso dado son:

| Elemento transpuesto | Error R [%] | Error X [%] |
|---|---:|---:|
| Propio | 2.661076 | 1.368799 |
| Mutuo | 0.673024 | 1.363986 |

Sin transposición las diferencias de R propias son 2.626559-2.729735 %,
las mutuas 0.643444-0.732422 %, y las de X 1.352601-1.387563 %.

## Importación y exportación

La opción DOVE lee los archivos originales de referencias en cada ejecución.
No cambia Geometría ni los módulos previos. Otra opción recalcula desde los
controles actuales de Carson y, si se selecciona, de Kron. Se puede cargar
directamente otro JSON exportado por 7A, incluyendo agrupación inequívoca
de subconductores A-1...C-4 o A'-1...C'-4. No se deducen conexiones desde JSON
con auxiliares no declarados. Una matriz guardada discrepante genera aviso.

Para una referencia PSCAD genérica se admite JSON con `source`, `labels`,
`resistance_type` (AC/DC/unknown), y `sin_transposicion` / `con_transposicion`,
cada una con `real`, `imag`, `unit` (Ω/m, Ω/km u Ω/mile). Los estados pueden
estar incompletos; no se deriva el que falte. El CSV es UTF-8 con BOM para Excel.
El PDF separa tablas comparativas R/X, repite encabezados y muestra originales,
promedios, tres matrices intermedias, ecuaciones, fuentes y condiciones AC/DC.
