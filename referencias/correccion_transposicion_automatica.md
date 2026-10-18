# Corrección de transposición automática · 17-10-2026

Se trabaja sobre la versión actual con etapas 7A-7F. Se conserva el cálculo
físico de cada tramo, la geometría de los haces, la proyección sin suelo y
el promedio de coeficientes de potencial antes de invertir.

## Causas reproducidas

El panel de etapa 6 permitía elegir tramos manuales, pero cada fila comenzaba
con las fases en sus posiciones originales. Elegir nueve tramos no generaba
las permutaciones: nueve identidades producen la misma matriz sin transposición.
Además, Streamlit conservaba `dc_weight_*` al cambiar `dc_sections`, y podía
mantener fracciones iniciales incompatibles. Nueve entradas redondeadas
0.111111111 suman 0.999999999, fuera de la tolerancia 1e-10 de la API manual.

La UI deja de leer `dc_sections`, `dc_weight_*` y `dc_pos_*`. Se sustituyen sus
controles por dos opciones: Sin transposición / Transposición ideal completa
automática. La sesión antigua se migra antes de crear el radio; todo plan
activado antiguo pasa al plan completo nuevo. El visor de tramo se restablece
al cambiar nueve tramos por uno. La tabla de posiciones y fracciones no permite
edición. El número de circuitos y las coordenadas físicas se siguen editando
en Configuración / Geometría.

## Generador y motor

`automatic_schedule(N, complete)` enumera {0,1,2}^N. Cada combinación contiene
una rotación independiente por circuito, con tres posiciones cíclicas locales.
Un circuito: tres tramos. Dos circuitos: nueve; no se intercambian terminales
entre circuitos. El peso es 1/(3^N), normalizado con `math.fsum`; el cálculo
nunca utiliza la cadena decimal redondeada que aparece en pantalla.

El generador no contiene un caso especial para seis fases y se prueba con
N=1,2,3,4. **El motor eléctrico conserva su límite de uno o dos circuitos**.
No se anuncian ni se calculan líneas de tres circuitos. La antigua API de
planes explícitos se mantiene para sus pruebas y resultados históricos;
la UI automática no permite sobrescribir posiciones ni pesos manualmente.

Cada fase conserva número de subconductores, radio, separación y rotación del
haz al trasladar su centro. El plan no separa sus subconductores. Las pruebas
incluyen haces constructivamente distintos para impedir una permutación ciega
de matrices en ese supuesto.

## Verificación DOVE solicitada

Coordenadas [m]: A=(-3,13), B=(3,13), C=(0,9), A'=(-3,25), B'=(3,25),
C'=(0,21). Dos subconductores por fase, radio 0.011765 m, separación 0.4572 m,
rotación 0° (convención geométrica existente). Capacitancia sin suelo, carga
global cero. No se requiere RMG para este cálculo capacitivo; no se aproxima
ACSR como conductor macizo.

C automática [nF/km], orden A,B,C,A',B',C':

```text
[[10.029643183, -2.962966810, -2.962966810, -1.367903188, -1.367903188, -1.367903188],
 [-2.962966810, 10.029643183, -2.962966810, -1.367903188, -1.367903188, -1.367903188],
 [-2.962966810, -2.962966810, 10.029643183, -1.367903188, -1.367903188, -1.367903188],
 [-1.367903188, -1.367903188, -1.367903188, 10.029575422, -2.962932929, -2.962932929],
 [-1.367903188, -1.367903188, -1.367903188, -2.962932929, 10.029575422, -2.962932929],
 [-1.367903188, -1.367903188, -1.367903188, -2.962932929, -2.962932929, 10.029575422]]
```

Sin transposición, las propias del primer circuito son 10.167310443,
10.167310443 y 9.872611311; las del segundo, 9.732599199, 9.732599199 y
10.731358230 nF/km. La diferencia máxima entre ambas matrices es
0.701782807552 nF/km: la matriz automática no coincide con la original.

Las propias son iguales dentro de cada circuito; no se impone que ambos
circuitos tengan exactamente la misma propia. Los nueve acoplamientos
entre circuitos quedan iguales bajo las rotaciones independientes. La matriz
es simétrica, de rango 5 y C·1≈0; máximo |C·1|=4.04e-27 F/m. Residuo de
Pprom·C/(2πε0)=H6: 2.22e-16. Estos valores usan toda la precisión interna;
el redondeo de la matriz impresa no se utiliza en las verificaciones.

El oráculo de prueba construye independientemente las nueve permutaciones de
P efectiva original y realiza una inversión restringida al subespacio global
de carga cero. No compara con el promedio de capacitancias, que representa
otra hipótesis física. Se conserva la advertencia del modelo didáctico a carga
común de etapas 5-6; no se presenta como equivalente shunt universal de una
línea distribuida. Véanse `doble_circuito.md` y `carson.md`.

Datos completos calculados: `output/ste_dove_transposicion_automatica.json`.
El PDF de comprobación usa la exportación existente y contiene los nueve
tramos y las primitivas: `output/pdf/ste_dove_transposicion_automatica.pdf`.

## Pruebas e interfaz

- Suite inicial de la versión anterior: **463 aprobadas en 136.83 s**,
  `tmp/pytest-auto-transposition-baseline.log`. No se detectaron fallos previos
  automatizados; faltaba cobertura de los errores reales descritos.
- Se conservan todas las pruebas unitarias previas de planes explícitos y
  pesos inválidos. Las pruebas de UI que exigían los controles eliminados
  se actualizan al nuevo contrato; no se eliminan pruebas para ocultar fallos.
- La primera ejecución focalizada detectó un fallo del propio arnés AppTest
  al inyectar una etiqueta antigua después de crear el radio nuevo. Se corrigió
  el montaje para simular la sesión antigua antes del primer render; la prueba
  de migración y de recuperación de radio inválido se conserva.
- Nuevas pruebas: producto cartesiano, pesos, ciclos locales, límite del motor,
  invariancia por rotaciones independientes, suma cero, grupo promedio
  independiente, preservación de haces y comparación con/sin transposición.
- AppTest configura el DOVE solicitado sin frecuencia ni longitud, verifica
  nueve filas distintas de solo lectura, conmuta desde el visor del tramo 9
  a sin transposición y de vuelta y prepara la descarga PDF. Capacitancia
  permanece disponible al elegir ACSR sin introducir RMG.

Pruebas completas posteriores: **481 aprobadas en 167.77 s**, registro
`tmp/pytest-auto-transposition-final.log`. Se conservan las 463 pruebas previas
y se añaden 18 (17 de generador/motor y una de interfaz para el DOVE solicitado).
La exportación completa de comprobación contiene 94 páginas con los nueve
tramos y sus primitivas, renderizadas e inspeccionadas; no hay recortes ni
superposiciones. El servidor local responde `ok` en `/_stcore/health`.

## Archivos de código cambiados

- `ste_calculator/transposition_schedule.py`: generador común y migración de
  la opción antigua; nuevo archivo sin ecuaciones físicas.
- `ste_calculator/double_circuit.py`: entrada `complete` para obtener el plan
  automáticamente; conserva las ecuaciones y la API explícita histórica.
- `ste_calculator/double_circuit_ui.py`: solo dos opciones, tabla de solo
  lectura, rechazo de dependencias del estado manual y reinicio del visor.
- `ste_calculator/transposition.py` y `transposition_ui.py`: reutilización del
  generador para un circuito, etiqueta automática y migración de sesión.
- `ste_calculator/printing.py`: identificación del plan independiente 1/9
  en el PDF, sin cambios de ecuaciones ni de matrices.
- Pruebas nuevas en `tests/test_automatic_transposition.py`; actualización y
  ampliación de las pruebas de interfaz existentes de etapas 5 y 6. Las pruebas
  de motores y validación manual anteriores se conservan.
- `README.md`, `referencias/doble_circuito.md` y este documento: instrucciones,
  alcance, causas, cifras reproducibles y resultados de las pruebas.

Para verificar en Windows: abre `http://localhost:8501`, entra en Haces →
Doble circuito · etapa 6, configura los dos circuitos y sus haces, elige
Sin suelo · carga global cero para C y Transposición ideal completa automática.
La tabla muestra nueve asignaciones, todas las combinaciones de ciclos, y
fracción exacta 1/9. Cambia a Sin transposición: aparece un solo tramo y C
vuelve al resultado original. Frecuencia y longitud no condicionan L/C.

Para arrancar y ejecutar pruebas desde la carpeta del proyecto:

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py
.\.venv\Scripts\python.exe -m pytest -q
```
