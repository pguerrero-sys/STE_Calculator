# Verificación de STE Calculator

Fecha: 16 de octubre de 2026, contexto del usuario en Colombia.

Entorno preparado dentro de la carpeta del proyecto: `.venv`, con Python 3.12.14
de 64 bits en Windows. Dependencias instaladas correctamente desde `requirements.txt`.
Las versiones exactas están en `requirements-lock.txt`.

## Etapa 7E: secuencias y análisis de discrepancias, resultado actual

```text
python -m pytest -q
446 passed in 110.85s (0:01:50)
python -m pytest tests/test_sequence_discrepancy.py -q
16 passed in 2.26s
python -m compileall -q ste_calculator scripts tests
Sin errores
python scripts/sequence_discrepancy_case.py
PDF, JSON y dos CSV nuevos, sin cambiar datos o resultados 7D
```

Se conservan las 430 pruebas anteriores y se añaden 16. Tras ajustar la
presentación del informe se repitieron las 16 pruebas del análisis, aprobadas.
El primer conjunto completo también aprobó 446 pruebas en 118.79 s.

Se transforman las matrices de fase transpuestas de STE y PSCAD, manteniendo
el método P/Q finito del JSON. Se contrastan independientemente Z0=Zs+2Zm,
Z1=Z2=Zs-Zm. Se rechaza aplicar los escalares a la geometría original no
transpuesta. Los residuos son menores de 1e-18 Ω/m; no se fuerzan ceros.
El contraste adicional con la Zsq publicada en PSCAD difiere hasta 2e-9 Ω/km
por redondeo textual, conservando la transformación desde fase como resultado.

Resultados principales con I/n [Ω/km]:

| Escenario | Secuencia | R | X | Error R [%] | Error X [%] |
|---|---|---:|---:|---:|---:|
| AC original | 0 | .201427591918 | 1.404861250640 | .730171 | 1.366164 |
| AC original | 1 y 2 | .028883438794 | .251347501739 | 10.014532 | 1.376159 |
| DC temporal | 0 | .198049365758 | 1.404861250640 | .959217 | 1.366164 |
| DC temporal | 1 y 2 | .025505212635 | .251347501739 | 2.852840 | 1.376159 |

R1_PSCAD=.0262542031 Ω/km. La diferencia original se descompone en
ΔRs=+.002239525102 y ΔRm=-.000389710592 Ω/km. Por resta, ΔR1=.002629235694
Ω/km. Las contribuciones son +8.530158 y +1.484374 puntos porcentuales,
total +10.014532 %. Se verifica esta identidad y el factor de cancelación
5.411059675; no es un fallo del cambio de base ni un promedio de errores.

La sensibilidad DC modifica solo una copia de la diagonal real de Zsub.
Con R_DC=.102 frente a R_AC=.1859/1.609344 Ω/km por subconductor, cada
secuencia se desplaza -.003378226159 Ω/km en R, manteniendo X en el modelo I/n.
La prueba comprueba esta identidad, la invariancia de geometría/RMG/términos
externos, y que la entrada técnica R_AC original permanece intacta.
R1_DC queda por debajo de PSCAD; no se intenta un ajuste para igualarlos.

Se deriva y evalúa un equivalente auxiliar de gradiente longitudinal común:
W=solve(Zsub,E); Zfase=solve(EᵀW,I); Isub=W Zfase Iphase.
Se verifica de manera independiente con el sistema por bloques
[[Zsub,-E],[Eᵀ,0]], con identidades de corrientes, tensión y potencia compleja,
simetría y un caso analítico simétrico que reproduce I/n. Se rechazan
matrices/agrupaciones inválidas y sistemas singulares, sin pseudoinversa.

Con entrada AC, ese diagnóstico produce R1=.028949457130 y X1=.251165794119
Ω/km: errores 10.265991 % y 1.447458 %. R1 aumenta aproximadamente 0.228568 %
respecto a I/n; no explica el desacuerdo inicial. Con entrada DC temporal:
R1=.025565041962, X1=.251160998419 Ω/km, errores 2.624955 % y 1.449339 %.
Para excitación positiva unitaria del primer tramo original, el reparto AC
desigual tiene hasta 5.141945 % de desviación de módulo respecto a 0.25 A y
3.067983 grados de desfase. Se exportan también corrientes de secuencia cero.

Este equivalente no se atribuye a PSCAD: supone sección uniforme, gradiente
común, conexiones ideales y eliminación serie sin shunt. No resuelve hebras,
superficie de corriente ni correcciones internas AC de PSCAD. La resistencia
DC declarada no equivale a su resistencia serie AC efectiva. Se mantienen las
diferencias sin atribuir porcentajes causales únicos a modelos no identificados.

Se preservaron por SHA-256 los 35 módulos Python preexistentes, app.py,
los cuatro archivos técnicos DOVE (JSON, dos TXT y LEEME) y los tres artefactos
DOVE 7D (CSV, JSON, PDF). No hay controles ni cambios en la aplicación.

Archivos nuevos: `ste_calculator/sequence_discrepancy.py`,
`sequence_discrepancy_report.py`, `scripts/sequence_discrepancy_case.py`,
`tests/test_sequence_discrepancy.py`, `referencias/discrepancias_secuencia.md`.
Se actualizan solo la documentación principal, el índice bibliográfico y este
registro; no hay dependencias nuevas. Artefactos nuevos:
`output/pdf/ste_secuencias_discrepancias_dove.pdf` (ocho páginas), JSON completo,
CSV de 12 comparaciones de secuencias y CSV de 96 corrientes de subconductores.
Se renderizaron e inspeccionaron todas las páginas del PDF final: tablas con
R/X y unidades explícitas, matrices completas, ecuaciones, cifras y conclusiones.

## Etapa 7D: transposición serie Carson y DOVE/PSCAD, verificación histórica

```text
python -m pytest -q
430 passed in 81.29s (0:01:21)
python -m compileall -q app.py ste_calculator scripts tests
Sin errores
python scripts/smoke_test.py
OK: servidor local, health=200, pagina=200
python scripts/series_transposition_case.py
Caso original validado antes de calcular transposición; PDF, CSV y JSON generados.
```

Se conservan las 402 pruebas previas y se agregan 28: 23 del cálculo/importación/
comparación, dos de interfaz y tres de informes. Se comprueban ciclos de fases
para matrices 3×3 y 6×6, invariancia al cambiar el origen del ciclo, idempotencia,
simetría, traza, unidades, cambios activado/desactivado, permanencia de
las matrices originales y conservación de acoplamientos entre circuitos.

La prueba de interfaz valida desactivado→activado→desactivado para DOVE,
unidades, carga exclusiva de 7D sin cambiar los controles anteriores, descarga
PDF/CSV, doble circuito con Kron por sección y bloqueo ante una guarda aislada.
También se contrasta reducir cada sección antes de promediar: Kron del promedio
primitivo produce en general otra matriz y se comprueba como contraejemplo.

Se recibieron y leyeron los archivos suministrados por el usuario dentro de
`referencias/Datos_DOVE_PSCAD_para_Codex/referencias/comparacion_pscad/`.
No se movieron ni modificaron. El JSON DOVE corresponde a **P/Q finitos de
Kersting**, no Carson modificado. Se conserva esa selección, con 12
subconductores, R_AC=.1859 Ω/milla, RMG=.00954024 m, f=60 Hz y ρ=100 Ω·m.

Primero se recalculó SIN transposición desde las entradas, incluyendo los
12 subconductores y su agregación I/n. Residuo máximo frente al JSON: **0 Ω/m**.
Después se calcularon y promediaron tres permutaciones cíclicas:

```text
Original [Ω/km]:
[[.086212280240+j.636058390593, .057326501375+j.375545825590, .057608825874+j.388983961656],
 [.057326501375+j.375545825590, .086212280240+j.636058390593, .057608825874+j.388983961656],
 [.057608825874+j.388983961656, .057608825874+j.388983961656, .086769909025+j.635439472934]]

Transpuesta [Ω/km]: propias .086398156502+j.635852084706;
mutuas .057514717708+j.384504582967.
```

La comprobación de TODOS los términos transpuestos usa rtol=0,
atol=5e-11 Ω/km frente a los diez decimales dados por el usuario. No se
codifican esos valores como salidas: se calculan desde geometría, R y RMG.

PSCAD se lee independientemente de cada TXT, bloque exacto SERIES IMPEDANCE
MATRIX (Z) [ohms/m], PHASE DOMAIN DATA a 60 Hz. Se excluyen long-line corrected,
modos, secuencias y datos totales. Se comprueba el redondeo entre promedio
PSCAD sin transponer y archivo PSCAD transpuesto (atol=7e-10 Ω/km).

| Estado/elemento | Error R [%] | Error X [%] |
|---|---:|---:|
| Sin transposición AA/BB | 2.626559 | 1.362439 |
| Sin transposición CC | 2.729735 | 1.381529 |
| Sin transposición AB/BA | 0.732422 | 1.387563 |
| Sin transposición AC/CA/BC/CB | 0.643444 | 1.352601 |
| Transpuesto propio | 2.661076 | 1.368799 |
| Transpuesto mutuo | 0.673024 | 1.363986 |

El denominador de cada porcentaje es el módulo de la componente PSCAD
correspondiente, con numerador absoluto. Referencia cero implica indefinido,
no cero supuesto. Se comprueban datos faltantes y exportación JSON sin NaN.

Discrepancia física documentada: R_AC STE=.1859 Ω/milla=.115512904637 Ω/km
y R_DC PSCAD=.102 Ω/km por subconductor son entradas distintas. No se supone
equivalencia de modelos ni se atribuye toda la diferencia a Carson. No se
inventa una corrección DC→AC ni un RMG de macizo para DOVE. Detalles del
modelo interno de conductor de PSCAD no están documentados completamente.

Artefactos: `output/ste_carson_transposicion_dove.csv` (18 filas de datos,
UTF-8 BOM), JSON de entradas/resultados/tramos/comparación y
`output/pdf/ste_carson_transposicion_dove.pdf` (ocho páginas horizontales).
Se renderizaron e inspeccionaron todas las páginas del PDF final: ecuaciones,
fuentes, columnas completas, R/X separadas y encabezados comparativos unidos
a sus tablas. La prueba adicional exporta las 72 filas de doble circuito.

Archivos nuevos: `series_transposition.py`, `series_inputs.py`,
`pscad_series.py`, `series_comparison.py`, `series_report.py` y
`series_transposition_ui.py` dentro de ste_calculator; script reproducible
`scripts/series_transposition_case.py`; tres archivos tests/test_series_transposition*;
`referencias/transposicion_serie.md` y artefactos de output. Integración en
app.py; README, índice bibliográfico y este registro actualizados.

Se verificaron SHA-256 de 15 módulos anteriores, todos intactos: geometría,
capacitancia, inductancia, haces, cálculo eléctrico de haces, transposición
previa, doble circuito, Carson, Kron, secuencias, UI/informe Carson,
UI/informe Kron e impresión compartida. No se necesitan dependencias nuevas.
La etapa 7D no cambia C ni L con suelo ideal. El modelo de doble circuito
transpuesto usa tres ciclos sincronizados y no sustituye otros calendarios.

## Etapa 7C: componentes simétricas y dos guardas, verificación histórica

```text
python -m pytest -q
402 passed in 84.52s (0:01:24)
python -m compileall -q app.py ste_calculator scripts tests
Sin errores
python scripts/smoke_test.py
OK: servidor local, health=200, pagina=200
python scripts/sequence_case.py
Ejemplo Kersting y ensayos de dos guardas recalculados; PDF y JSON en output/
```

Se conservan las 367 pruebas previas y se agregan 35. La suite completa pasó
también antes del ajuste final de anchos de columnas (402 en 78.18 s).
La ejecución final anterior incluye ese ajuste. Las nuevas pruebas cubren:
convención a=exp(j120°), vectores de secuencia positiva, inversa conjugada/3,
matriz publicada COMPLETA de Kersting, conservación de términos no diagonales,
reconstrucción de fase para corrientes arbitrarias, unidades e invalidación
de resultados al cambiar conexiones o desmarcar ΔVn=0.

Se ensayan dos guardas en uno y dos circuitos, ambos métodos aproximados de
Carson, así como doble circuito con haces de uno/cuatro subconductores.
Las primitivas correspondientes son 5×5, 8×8 y 26×26; las reducidas de doble
circuito siguen siendo 6×6, conservando todos los términos entre circuitos.
También se prueban auxiliares aislados/desconocidos y bloques Znn nulos,
singulares y con cond>10^12. No hay pseudoinversa ni eliminación automática.

Kersting ejemplo 4.1 [Ω/milla], orden 0,1,2:

```text
[[ .773513109+j1.937278418, .025560580+j.011493522, -.032085729+j.015893188],
 [-.032085729+j.015893188, .306069982+j.627008922, -.072251431-j.006027345],
 [ .025560580+j.011493522, .072303906-j.005897591, .306069982+j.627008922]]
```

Las partes R/X de los nueve elementos coinciden con p.94 dentro de
6e-5 Ω/milla, teniendo en cuenta su redondeo a cuatro decimales. Se mantiene
la errata histórica de p.94 documentada, sin usarla en cálculos. No se detectó
una discrepancia adicional con la convención de pp.89-90. El residuo de
reconstrucción de fase es aproximadamente 3.987e-16.

Contraste independiente de dos guardas: SciPy resuelve el sistema completo
con Ip=I y ΔVn=0, y obtiene las caídas de fase mediante la primitiva. No llama
a reduce_kron ni a su complemento de Schur. Error relativo: 6.2853e-17 para
un circuito y 1.3239e-16 para dos; residuos de frontera 2.4896e-17 y 1.5177e-17.
Las pruebas agregan otra vía independiente: fórmula de Carson en pies/millas
y eliminación con inversa 2×2 por determinante. Descartar las mutuas entre
guardas produce un resultado distinto y se verifica expresamente.

Las geometrías de dos guardas son sintéticas: las propiedades eléctricas son
las del neutro del libro, reutilizadas explícitamente para ensayar álgebra.
No son modelos comerciales ni validaciones físicas de puesta a tierra.
Z1=Z2 no demuestra transposición; Z012 no es en general simétrica ni diagonal.
La representación de fases y las de secuencias son cambios de base del mismo
modelo, no nuevas aproximaciones electromagnéticas.

PDF `output/pdf/ste_secuencias_kersting.pdf`: nueve páginas horizontales.
Se renderizaron e inspeccionaron todas; se revisó además a mayor escala la
página de convención y ecuaciones. Recuadro por pasos, A y A^-1 explícitas,
unidades en cada tabla, etiquetas de secuencia/circuito, R/X separadas y
términos no diagonales completos. Se verifica en pruebas la exportación de
doble circuito, dos guardas y matrices anchas de las etapas anteriores.

Se mantienen idénticos los SHA-256 de los nueve módulos numéricos previos:
geometría, capacitancia, inductancia, haces, cálculo eléctrico de haces,
transposición, doble circuito, Carson y Kron. No hay dependencias nuevas.

Archivos nuevos: `ste_calculator/sequences.py`, `sequences_ui.py`,
`sequence_report.py`, `sequence_examples.py`, `kron_validation.py`,
`scripts/sequence_case.py`, `tests/test_sequences.py`, `test_sequences_app.py`,
`test_sequences_report.py`, `referencias/secuencias.md` y los artefactos PDF,
JSON y PNG de etapa 7C en output/. Se actualizan `app.py`, `kron_ui.py`,
`kron_report.py`, `printing.py`, README, índice bibliográfico y este registro.
Las instrucciones de reproducción están en README y las fuentes en
`referencias/secuencias.md`.
La aplicación real se reinició en 127.0.0.1:8501. Se cargó el ejemplo, se
declaró ΔVn=0 y se comprobó la presencia de la convención A/A^-1 y de la
matriz compleja completa: `output/ste_secuencias_interfaz.png`. Salud HTTP=200.

## Etapa 7B: reducción de Kron, verificación histórica

```text
python -m pytest -q
367 passed in 82.06s (0:01:22)
python -m pytest tests/test_kron.py tests/test_kron_app.py tests/test_kron_report.py -q
38 passed in 13.11s
python -m compileall -q app.py ste_calculator scripts tests
Sin errores
python scripts/smoke_test.py
OK: servidor local, health=200, pagina=200
python scripts/kron_case.py
Ejemplo completo recalculado; PDF y JSON generados en output/
```

Se conservan las 329 pruebas anteriores y se agregan 38. La primera ejecución
completa detectó una expectativa textual incorrecta de una prueba PDF nueva;
se corrigió esa expectativa, y la ejecución completa final pasó. Tras explicitar
ΔV/ℓ en la presentación de ecuaciones por unidad de longitud se volvieron a
ejecutar las 38 pruebas de etapa 7B, también aprobadas.

Pruebas nuevas: referencia publicada de Kersting p.94, comparación escalar
independiente para un neutro, simetría compleja, conversión de unidades que
conmuta con el complemento de Schur, reconstrucción de las ecuaciones de
tensión con corrientes arbitrarias, varios auxiliares acoplados, permutación
de índices, bloque singular/mal condicionado y propiedades auxiliares inválidas.
Se ensaya doble circuito con haces de 1, 2, 3 y 4 subconductores, manteniendo
seis fases; no se descartan términos entre circuitos ni entre auxiliares.

En AppTest se verifica que la carga del ejemplo muestra primero la primitiva,
que la declaración ΔVn=0 habilita Kron y que conexiones aisladas/desconocidas
lo bloquean sin ocultar la primitiva. Cambiar resistencia actualiza los resultados;
se prueban unidades, mensajes específicos, descarga PDF y ausencia de dependencia
de longitud/frecuencia general. Las propiedades electromagnéticas previas no cambian.

Kersting ejemplo 4.1, completo, f=60 Hz, ρ=100 Ω·m, Carson modificado:

```text
Zreducida [Ω/milla], desde coordenadas y datos originales, sin resultados fijos:
[[.457551750+j1.078048248, .155950722+j.501679027, .153485488+j.384937852],
 [.155950722+j.501679027, .466628267+j1.048176587, .158006917+j.423652617],
 [.153485488+j.384937852, .158006917+j.423652617, .461473056+j1.065071426]]

Zreducida [Ω/km]:
[[.284309476+j.669868125, .096903286+j.311728895, .095371460+j.239189292],
 [.096903286+j.311728895, .289949363+j.651306736, .098180947+j.263245532],
 [.095371460+j.239189292, .098180947+j.263245532, .286746063+j.661804702]]
cond(Znn)=1; residuo normalizado=2.1112107453e-17.
```

Comparación bibliográfica por componente R/X: tolerancia absoluta 6e-5 Ω/milla
frente al redondeo a cuatro decimales de pp.93-94. No se usa la errata de la
partición de p.94 ni se altera Carson para ajustar resultados. No se certifica
equivalencia PSCAD. La derivación, referencias y condiciones están en
`referencias/kron.md`.

PDF final `output/pdf/ste_kron_kersting.pdf`: ocho páginas horizontales;
se renderizaron e inspeccionaron todas y se volvió a revisar la primera tras
la aclaración ΔV/ℓ. Fórmulas completas y sustituciones ajustadas como texto,
tablas numéricas R/X sin superposición. También se comprueba automáticamente
la exportación de 26 subconductores/guardas y de una fórmula sin espacios
que necesita varios renglones. Evidencia de interfaz real:
`output/ste_kron_interfaz.png`; servidor local reiniciado en 127.0.0.1:8501.
La prueba real muestra las matrices R/X de la reducida y la hipótesis declarada.

Se verificaron SHA-256 antes/después de ocho módulos numéricos: `geometry.py`,
`capacitance.py`, `inductance.py`, `bundles.py`, `bundle_electrical.py`,
`transposition.py`, `double_circuit.py` y `carson.py`. Todos idénticos.

Archivos nuevos: `ste_calculator/kron.py`, `kron_ui.py`, `kron_report.py`,
`scripts/kron_case.py`, `tests/test_kron.py`, `test_kron_app.py`,
`test_kron_report.py`, `referencias/kron.md` y los tres artefactos de ejemplo
JSON, PDF y PNG en `output/`. Integración/presentación actualizada en
`app.py`, `ste_calculator/carson_ui.py`, `printing.py`, `README.md`,
`referencias/README.md` y este registro. No se necesitan dependencias nuevas.

Limitaciones: todos los auxiliares añadidos deben cumplir ΔVn=0 para reducir;
no se realiza selección parcial implícita. No se modelan electrodos finitos,
tierras discretas ni conexiones en un solo extremo; los haces conservan I/n.
No se aplica transposición automática a Carson/Kron ni se fusionan circuitos.

## Etapa 7A: impedancia serie Carson, verificación histórica

```text
python -m pytest -q
329 passed in 66.09s (0:01:06)
python -m pytest tests/test_printing.py tests/test_carson_report.py -q
8 passed in 8.73s
python -m compileall -q app.py ste_calculator scripts tests
Sin errores
python scripts/smoke_test.py
OK: servidor local, health=200, pagina=200. Servidor temporal detenido al finalizar.
```

Se conservan las 276 pruebas anteriores sin editarlas y se añaden 53:
44 de cálculo/validación, 5 de interfaz y 4 de exportación/contraste C-P.
Después del ajuste textual de advertencias en los informes históricos se
repitieron las ocho pruebas pertinentes de PDF y exportación. No se añadió
ninguna dependencia. Los SHA256 de los siete módulos numéricos previos
`geometry.py`, `capacitance.py`, `inductance.py`, `bundles.py`,
`bundle_electrical.py`, `transposition.py` y `double_circuit.py` coinciden
con los registrados antes de esta etapa.

### Métodos, contraste y límites

Se implementan únicamente dos aproximaciones identificadas: Carson
modificado, Kersting (4.37)-(4.40), y P/Q finitos impresos en (4.23)-(4.24).
Se corrigieron las discrepancias de k y sus factores en la diapositiva 6,
priorizando la página impresa 83 del capítulo. No se calcula una serie
infinita completa ni se afirma precisión exacta frente a PSCAD.

El contraste independiente usa la primitiva 4×4 de Kersting ejemplo 4.1,
p.93, sin eliminar el neutro. Todas las partes reales e imaginarias coinciden
con los valores impresos a cuatro decimales dentro de 6e-5 Ω/mile, rtol=0,
incluyendo el redondeo/truncamiento de los coeficientes publicados. No se
confunde esta matriz con la reducida de p.94. Otro ensayo evalúa directamente
las ecuaciones en pies y Ω/milla mediante bucles escalares y las contrasta
con el ensamblaje SI por imágenes/P/Q.

Las pruebas cubren simetría Z=Zᵀ (no hermítica), suma de contribuciones,
pasividad resistiva de los casos de ensayo, Ω/m↔Ω/km↔Ω/mile, escalamiento
f/ρ, modificación del modo común al cambiar ρ y cancelación de alturas solo
en Carson modificado. Se comprueba la expresión P/Q con ángulo no nulo y
se detecta que la expresión discrepante de la diapositiva no produce el
mismo valor. También se ensayan uno/dos circuitos, n=1,2,3,4, todas las
mutuas, Rfase=Rindividual/n y Xgeom=ωLideal del módulo anterior.

R_AC y RMG se usan como datos documentados, sin convertir un ACSR a macizo.
Se rechazan fuentes ausentes, datos negativos/no finitos, centros coincidentes,
contactos conocidos y métodos inexistentes. k>0.1 genera aviso y k≥1 se
bloquea por política preventiva explícita de software, no por una cota
normativa o de error del libro. Fuera de 50-60 Hz se advierte que no se
validó la precisión de las aproximaciones. No se extrapola ρ→0 como una
solución exacta de suelo perfecto.

La regresión de interfaz comprueba igualdad bit a bit de la matriz C al
cambiar f de Carson, ρ y método. La frecuencia general no se modifica.
La referencia geométrica de imágenes ideales y ΔZtierra se muestran
separadas; la separación reactiva es dependiente de la referencia elegida.

### Caso reproducible, calculado y sin Kron

Kersting, ejemplo 4.1: tres fases A/B/C en (0,29), (2.5,29), (7,29) ft,
R_AC=0.306 Ω/mile, RMG=0.0244 ft; f=60 Hz y ρ=100 Ω·m. Es un bloque
primitivo de fases, no la matriz reducida de un circuito con neutro.
Son datos bibliográficos de comprobación, no una ficha vigente del fabricante.

Carson modificado, Z=R+jX, Ω/km:

```text
R = [[0.249357211, 0.059217626, 0.059217626],
     [0.059217626, 0.249357211, 0.059217626],
     [0.059217626, 0.059217626, 0.249357211]]
X = [[0.878177057, 0.529123779, 0.451492304],
     [0.529123779, 0.878177057, 0.484805709],
     [0.451492304, 0.484805709, 0.878177057]]
```

P/Q finitos de (4.23)-(4.24), Ω/km:

```text
R = [[0.248054049, 0.057914332, 0.057913425],
     [0.057914332, 0.248054049, 0.057914035],
     [0.057913425, 0.057914035, 0.248054049]]
X = [[0.879544999, 0.530491721, 0.452860246],
     [0.530491721, 0.879544999, 0.486173651],
     [0.452860246, 0.486173651, 0.879544999]]
```

k máximo del caso de tres fases: 0.03875887265581907. Los datos precisos,
fuentes, primitivas y las contribuciones se regeneran con
`scripts/carson_case.py` en `output/ste_carson_kersting.json`.
El PDF `output/pdf/ste_carson_kersting.pdf`, de cinco páginas A4 horizontales,
contiene el método modificado, entradas, fórmulas, dos sustituciones,
R/X en ambas unidades y contribuciones. Se renderizaron y revisaron todas
sus páginas y la tabla principal a tamaño legible, sin columnas cortadas
ni textos superpuestos. Los informes para 24 subconductores conservan
la partición horizontal de tablas; su contenido también tiene prueba automática.
Se reinició el servidor local y se verificaron en el navegador la carga del
caso, la matriz Z compleja de tres fases, R/X en Ω/km y el botón de descarga
PDF. El residuo de simetría mostrado fue cero; el de suma de contribuciones,
5.790e-20 Ω/m. La comprobación HTTP de salud respondió 200.

### Bibliografía y revisión de capacitancia

El registro `referencias/carson.md` identifica notas 01-10-26 PDF 1-2,
presentación Carson diapositivas 4-9, y Kersting pp.81-85 y 92-93 con
ecuaciones (4.20)-(4.42), errores detectados y convenciones de unidades.

Se documentan dos condiciones distintas: potencial común ⇒ promedio C;
carga común ⇒ invertir el promedio de coeficientes de potencial. No son
intercambiables ni universales para una cascada distribuida. Se conservan
las matrices históricas, incluido el caso obligatorio de transposición,
y se aclara el carácter didáctico a carga común de las etapas 5-6 en la
interfaz, sus informes y las notas. P/Q de Carson no son la matriz
electrostática P. No se implementó Kron, guardas, secuencias, transposición
nueva de Z ni reemplazo del modelo capacitivo por suelo de Carson.

## Etapa 6: doble circuito e impresión PDF

Ejecución final con Python 3.12.14 en Windows:

```text
python -m pytest -q
276 passed in 59.02s
python -m compileall -q app.py ste_calculator scripts tests
Sin errores
python scripts/smoke_test.py
OK: servidor local, health=200, pagina=200. Servidor temporal detenido al finalizar.
```

Se conservan las 232 pruebas existentes sin editarlas. Se añaden 35 pruebas
numéricas, 5 de interfaz y 4 de PDF. Las versiones instaladas nuevas son
ReportLab 4.5.1 y pypdf 6.20.1; quedaron registradas en requirements-lock.txt.

Los SHA256 de `geometry.py`, `capacitance.py`, `inductance.py`, `bundles.py`,
`bundle_electrical.py` y `transposition.py` permanecen iguales. La extensión
se implementa en archivos independientes. Se mantienen las siete pestañas;
el panel de doble circuito está en Haces y aparece primero al elegir dos
circuitos. Los módulos anteriores siguen disponibles para un circuito.

### Verificaciones nuevas

- Seis fases independientes, n=1,2,3,4, contactos entre circuitos,
  posiciones y distancias reales/imágenes. Acoplamientos cruzados no nulos.
- Matrices simétricas y energía positiva en el espacio aplicable; con suelo
  rango 6 y sin suelo rango 5. La restricción inductiva separada por circuito
  tiene rango 4 y cuatro lazos, sin unir fases homólogas.
- Caso n=1 mediante bucles escalares independientes de Pitágoras/logaritmos,
  resolución NumPy independiente y comprobación P C/(2πε₀)=I6.
- Comparación con los módulos anteriores para cada n y modelo de suelo.
  L conserva los bloques físicos del circuito; sin suelo se compara tras
  la proyección correspondiente. C del conjunto no se confunde con la C
  aislada del primer circuito. Con seis conductores sencillos, imponer Q2=0
  mediante eliminación algebraica recupera el resultado aislado de referencia.
- Equipotencialidad por fase, neutralidad global sin suelo, radio exterior
  separado del RMG y RMG del fabricante sin multiplicar por exp(-1/4).
- Tramos simultáneos, opuestos y personalizados; permutaciones explícitas,
  pesos positivos que suman 1 y propiedades que viajan con la fase.
  Se promedian coeficientes efectivos de potencial antes de invertir.
  Cambiar el ciclo relativo cambia los acoplamientos entre circuitos.
- Invariancia inductiva sin suelo al cambiar referencias 10, 1000 y 2000 m;
  unidades H/m, µH/m, mH/km, F/m, nF/km y X=2πfL.
- Interfaz sin frecuencia/longitud, cambio de haces y tramos, controles de
  suelo independientes, RMG incompleto sin bloquear C, edición compartida
  de coordenadas y mensajes de entrada no válida.

### Caso numérico calculado, no diseño validado

Orden A/B/C/A'/B'/C'. Centros (-4,15), (-4,11), (-4,7), (4,15), (4,11),
(4,7) m; un subconductor por fase; R=0.011765 m; macizo no magnético uniforme;
suelo ideal; sin transposición. RMG=0.009162591212835 m.

L [mH/km], redondeada solo para mostrar:

```text
[[1.618765, 0.374360, 0.202320, 0.271221, 0.222462, 0.145425],
 [0.374360, 1.556734, 0.300815, 0.222462, 0.214739, 0.157898],
 [0.202320, 0.300815, 1.466337, 0.145425, 0.157898, 0.140180],
 [0.271221, 0.222462, 0.145425, 1.618765, 0.374360, 0.202320],
 [0.222462, 0.214739, 0.157898, 0.374360, 1.556734, 0.300815],
 [0.145425, 0.157898, 0.140180, 0.202320, 0.300815, 1.466337]]
```

C [nF/km]:

```text
[[ 7.810907,-1.574317,-0.593568,-0.892483,-0.581697,-0.316704],
 [-1.574317, 8.259586,-1.364206,-0.581697,-0.573525,-0.419235],
 [-0.593568,-1.364206, 8.357108,-0.316704,-0.419235,-0.479819],
 [-0.892483,-0.581697,-0.316704, 7.810907,-1.574317,-0.593568],
 [-0.581697,-0.573525,-0.419235,-1.574317, 8.259586,-1.364206],
 [-0.316704,-0.419235,-0.479819,-0.593568,-1.364206, 8.357108]]
```

El residuo normalizado de P C/(2πε₀)−I6 es 2.220446049250313e-16.
El script `scripts/double_circuit_case.py` regenera estas matrices, el JSON
en output/ y el PDF en output/pdf/ a partir de las ecuaciones. No contiene
matrices esperadas codificadas como resultados.

### PDF y fuentes

El informe final `output/pdf/ste_doble_circuito.pdf` tiene ocho páginas A4
horizontales. Se renderizaron todas las páginas, se revisó la hoja de
contacto y las sustituciones en tamaño legible. Se corrigieron símbolos
faltantes usando una fuente Unicode disponible en Windows. Las tablas
numéricas respetan el ancho útil y mantienen título y tabla juntos.

La prueba de 24 columnas verifica que se conservan las 576 celdas, la
anchura de cada texto y los encabezados repetidos. Para el caso máximo de
24 subconductores y tres tramos opuestos se generó además un informe
temporal de 71 páginas y se inspeccionó su bloque Psub de columnas 19-24,
con todas las etiquetas de fila, sin recortes ni superposición. El mismo
generador se aplica al informe de Haces y Transposición de circuito sencillo.
El Ctrl+P de los canvas del navegador no es el mecanismo de exportación.
Se reinició el servidor de 127.0.0.1:8501 y se comprobó el panel real en el
navegador: carga del caso, seis controles de haz, matrices L6/C6, reactancia
a 60 Hz y disponibilidad del botón de descarga del informe. El estado HTTP
de salud del servidor es 200.

Fuentes y discrepancias: `referencias/doble_circuito.md`. Se distingue la
matriz de tres conductores reales más sus imágenes de las seis fases reales
de doble circuito. No se adopta automáticamente la agrupación trifásica de
las notas ni el RMG comercial de su ejemplo FINCH.

Se conservan las aproximaciones de cargas lineales, corrientes I/n y tramos
uniformes con cruces sin longitud. Sin suelo se respetan suma global cero
y potencial común indeterminado. No hay Carson, pérdidas de tierra,
redistribución inductiva, propagación distribuida exacta ni reducción 3×3.

## Corrección de transferencia Haces → Transposición

Se reprodujo el fallo en el servidor de 127.0.0.1:8501, con el caso obligatorio
cargado: Haces calculaba y Transposición recibía `bundle_context=None`. La
condición que disparaba el mensaje era `if context is None` en
`render_transposition_panel`. El proceso había arrancado a las 16:25, antes
de los cambios de `bundle_ui.py` de las 18:00, y seguía ejecutando el
renderizador anterior sin retorno de contexto. No era una ausencia de radios,
coordenadas, frecuencia ni longitud. Una ejecución nueva de AppTest con los
archivos de disco no tenía ese fallo.

La prueba de regresión envuelve el renderizador para que dibuje correctamente
pero devuelva `None`: falló antes del cambio y pasó después. Ahora `app.py`
obtiene las entradas de los widgets `haz_*` actuales y los conductores actuales
del editor de Geometría mediante el contrato independiente de Streamlit
`build_bundle_context`. Haces usa el mismo validador. El retorno del renderizador
ya no condiciona Transposición, y no se conserva una geometría derivada obsoleta
en `st.session_state`. Una geometría inválida lleva su error concreto al panel;
un radio ausente identifica, por ejemplo, `Radio exterior individual B [m]
(haz_r_B)`. Un fallo de RMG solo bloquea la inductancia.

Se conservan todas las pruebas anteriores y se añaden siete regresiones:
retorno ausente, cuatro combinaciones de frecuencia/longitud vacías o no
positivas, radio de fase ausente y recuperación, cambios de separación y
número de circuitos sin resultados obsoletos. Se alterna transposición
activada/desactivada y se comprueban las matrices obligatorias.

```text
python -m pytest -q
232 passed in 40.27s
python -m compileall -q app.py ste_calculator tests
Sin errores
python scripts/smoke_test.py
OK: servidor local, health=200, pagina=200. Servidor temporal detenido al finalizar.
```

No se modificaron las ecuaciones ni los archivos `geometry.py`,
`capacitance.py`, `inductance.py`, `bundles.py`, `bundle_electrical.py` o
`transposition.py`; los SHA256 coinciden con los anteriores. No se añadieron
dependencias. Se reinició el servidor local para descargar el código antiguo.
Después del reinicio se comprobó en el navegador el caso obligatorio a 60 Hz,
con longitud vacía, alternando ambos modos. Aparecieron los resultados de
tramo único y de tres tramos respectivamente, sin el aviso genérico. La
capacitancia transpuesta muestra 13.803851 nF/km en las diagonales y
−3.300067 nF/km en los mutuos, con residuo normalizado 2.220e-16.
La captura local de comprobación está en `tmp/transposicion-corregida.png`.

## Etapa 5: resultado actual — transposición ideal completa

Ejecución final en el entorno local Windows, sin dependencias nuevas:

```text
python -m pytest -q
225 passed in 30.33s
python -m compileall -q app.py ste_calculator tests
Sin errores
python scripts/smoke_test.py
OK: servidor local, health=200, pagina=200. Servidor temporal detenido al finalizar.
```

Se conservan las 196 pruebas existentes. Se añaden 25 pruebas de cálculo
y 4 de interfaz, sin modificar las anteriores. AppTest comprueba la carga
del caso, tres tramos y longitudes iguales, las matrices, cambio de modo,
vistas primitivas y geometría, controles independientes de suelo y
capacitancia disponible sin fuente de RMG. No se realizó inspección visual
manual del navegador; el gráfico se ejecutó mediante AppTest.

Se verificaron por SHA256, sin cambios, los módulos `geometry.py`,
`capacitance.py`, `inductance.py`, `bundles.py` y `bundle_electrical.py`.
La integración solo añade módulos de transposición y un contexto de salida
al panel existente de Haces; se conservan las siete pestañas y sus resultados.

### Caso obligatorio y comprobación independiente

Centros A=(−3,13), B=(3,13), C=(0,9) m; cuatro subconductores cuadrados por
fase, separación de vecinos 0.4572 m, radio 0.011765 m y RMG=R exp(−1/4).
Suelo ideal, ε₀=8.8541878128e-12 F/m, μ₀=4π×10^-7 H/m.

| Resultado transpuesto | Diagonal | Términos mutuos | Unidad |
|---|---:|---:|---|
| L | 0.96180211 | 0.29826156 | mH/km |
| C, promediando P efectiva antes de invertir | 13.80385067 | −3.30006686 | nF/km |
| Promedio directo de C, solo comparación | 13.83011609 | −3.30873057 | nF/km |

Las dos matrices solicitadas coinciden con las referencias redondeadas del
usuario, con tolerancia absoluta 0.5e-6 y relativa cero en las unidades de
la tabla. No se usan esos valores como salidas constantes del cálculo.
El residuo máximo de P_prom C/(2πε₀)−I es 2.22e-16 en esta ejecución.

Además del cálculo completo por tramos, una prueba independiente resuelve
el sistema aumentado `[P_sub, E; Eᵀ, 0]` con cargas totales de fase impuestas,
recupera P efectiva, promedia sus diagonales y mutuos y aplica la inversa
analítica de `(a−b)I+b11ᵀ`. Para L se arma independientemente la matriz
logarítmica primitiva con distancias reales/imágenes y RMG. Las soluciones
coinciden con el módulo a tolerancia relativa 1e-13.

También se comprueban n=1,2,3,4, permutaciones, simetría, unidades,
reactancia y conservación del modelo previo al elegir sin transposición,
con suelo y sin suelo. El caso con haces distintos por fase verifica que
las propiedades viajan con la fase y no se imponen diagonales iguales.
Sin suelo, los operadores anulan el vector común, tienen rango 2 y
P_prom C/(2πε₀)=H, con H=I−11ᵀ/3; no se invierte una matriz singular.

### Alcance físico y fuentes

El registro completo está en `referencias/transposicion.md`: notas generales
PDF 53–57 y 96–98, clase 14-09-26 PDF 2–3 y Kersting, con discrepancias
de índices y de procedimiento explicitadas. Se promedian potenciales para
una misma carga de fase de referencia; no se confunde con el promedio de
cargas a potencial local fijo. Se conserva equipotencialidad capacitiva y
corriente inductiva I/n. Sin suelo solo son aplicables las restricciones
de suma cero correspondientes. Los cruces tienen longitud idealizada nula;
no se resuelve propagación distribuida, redistribución inductiva, Carson
ni doble circuito. Estas comprobaciones validan el software respecto del
modelo, no certifican el diseño de una instalación.

## Etapa 4: verificación conservada — conductores en haz

Se ejecutó la suite completa al finalizar la etapa:

```text
python -m pytest -q
196 passed in 19.74s
```

Se conservan las 146 pruebas anteriores y se añaden 43 de cálculo de haces
y 7 de interfaz. También pasaron la compilación de módulos con `compileall`
y `scripts/smoke_test.py` (página y salud HTTP 200). El servidor temporal se
detuvo al terminar. Se usó el mismo entorno Python 3.12.14 en Windows, sin
agregar dependencias. La interfaz se ejecutó con AppTest; no se realizó
inspección visual manual del navegador.

### Cobertura nueva

- Haces regulares de n=1,2,3,4, separación de vecinos, rotación, centros,
  alturas reales, radios y contacto/solapamiento. También se ensayan cantidades
  diferentes por fase y reordenamiento de entradas.
- RMG y radio capacitivo equivalentes por las n² distancias, comparados con
  formas cerradas independientes. En el cuadrado se incluye la diagonal √2 s.
- Para n=2, comprobación independiente de DMG_AB como raíz cuarta de
  6×6×5.6×6.4 y de S_AA como sqrt(26×hypot(26,0.4)); ninguna se sustituye
  automáticamente por una distancia entre centros.
- n=1 reproduce los módulos verificados de inductancia con/sin suelo y
  capacitancia con suelo dentro de tolerancia numérica. Sin suelo, el caso
  capacitivo equilátero se contrasta con C=(2πε₀/ln(D/R))H.
- Para cada n y modelo de suelo: simetría, energía positiva en el espacio
  aplicable y agregación de cargas o corrientes. El modelo sin suelo mantiene
  el rango 2 y las restricciones correspondientes.
- Capacitancia con suelo: P W=E con residuo <1e-12. Sin suelo:
  P0 W−E es común, la carga total es cero y C anula el potencial común.
  Se comprueba invariancia ante escala geométrica común y traslación sin suelo.
- Las cargas explícitas dentro de una fase pueden diferir; se contrasta que
  la aproximación de círculo equivalente puede dar otra matriz. La respuesta
  principal no se reemplaza por esa aproximación.
- L coincide con Tᵀ L_sub T bajo corrientes iguales y con la formulación por
  medias geométricas, incluidas las imágenes propias del haz completo.
- El RMG de fabricante se usa sin factor macizo adicional; su ausencia o falta
  de fuente bloquea únicamente el cálculo inductivo, no el capacitivo.
- Interfaz para los cuatro n, vista ampliada de cada fase, fuente ACSR,
  restricciones sin suelo, frecuencia y controles independientes. Se rechazan
  separaciones inválidas y circuitos múltiples.

### Datos sintéticos de comprobación, no de un diseño validado

Se usan los centros del caso anterior, R=0.011765 m y subconductor macizo
no magnético uniforme. Para n>1 se eligió s=0.4 m exclusivamente como dato
de prueba, sin declararlo óptimo ni cargarlo como separación predeterminada.

| n | Radio equivalente capacitivo [m] | RMG equivalente inductivo [m] |
|---|---|---|
| 1 | 0.011765000000 | 0.009162591213 |
| 2 | 0.068600291545 | 0.060539544804 |
| 3 | 0.123472612721 | 0.113600287694 |
| 4 | 0.180643244873 | 0.169698623943 |

Las formas cerradas se comparan con rtol=1e-13. La comparación n=1 contra
los módulos existentes usa rtol=1e-14, atol=1e-21 H/m y atol=1e-25 F/m.

### Conservación y alcance

No se modificaron `geometry.py`, `capacitance.py` ni `inductance.py`.
Sus SHA256 antes y después coinciden:

```text
geometry.py     FFB6A3FE4AF18E3967AA9B85DFFE7C02A05D45BFB33654DCC69EBDCCC7454DC3
capacitance.py  FBA63D8CBFFEEEFF43D4C1BAC7BE23246F6FAF977F3DB6FE49AE21DB90C44B8C
inductance.py   94F6D85574DBC1C99AFFFCA1E131C0A62E89C6451065939A3E7C5635A989E7E6
```

Los archivos nuevos son `bundles.py`, `bundle_electrical.py`, `bundle_ui.py`,
`tests/test_bundles.py`, `tests/test_bundle_app.py` y `referencias/haces.md`.
Se actualizó la interfaz principal, su prueba de navegación y la documentación.

Fuentes, correcciones y ecuaciones: `referencias/haces.md`, registrado antes
de la implementación. La solución capacitiva explícita impone equipotencialidad
por fase dentro del modelo de cargas lineales; no resuelve carga superficial
exacta. La inductancia supone I/n, sin resolver redistribución. Sin suelo:
carga neta total cero para C y suma de corrientes cero para L. Sin Carson,
resistividad finita, transposición, doble circuito, hebras ACSR, piel/proximidad
ni validación reglamentaria de distancias.

## Ajuste de interfaz sin suelo: verificación anterior

Se eliminó la solicitud de d_0 del cálculo principal de la interfaz. Se muestran
primero la proyección 3x3 de media cero y los lazos A-C/B-C, en H/m, microH/m
y mH/km. Se conserva explícitamente IA+IB+IC=0 y el rango 2 de la proyección.
La matriz dependiente de referencia solo aparece al activar la deducción avanzada.

Suite completa ejecutada tras el cambio:

```text
python -m pytest -q
146 passed in 14.32s
```

Se añadieron tres casos parametrizados de invariancia para 10, 1000 y 2000 m
y una prueba de interfaz que verifica que la opción avanzada vacía o inválida
no bloquee el resultado principal. Para cada referencia se contrastan las
matrices con fórmulas directas de lazos y proyección, con rtol=1e-14 y
atol=1e-21 H/m, y se comprueban enlaces y reactancia.
La prueba de interfaz conserva exactamente las tablas principales, incluyendo
reactancia y ensayo, al cambiar o desactivar la referencia. L_ref cambia según
lo esperado y solo se presenta como matriz auxiliar no única.

Las fórmulas y la comparación con las notas están en `referencias/inductancia.md`.
No se modificó ningún módulo numérico, ni la interfaz de capacitancia.
En particular, el SHA256 de `ste_calculator/inductance.py` se mantuvo:
`94F6D85574DBC1C99AFFFCA1E131C0A62E89C6451065939A3E7C5635A989E7E6`.
Las huellas de geometría y capacitancia coinciden con las registradas abajo.

## Etapa 3: verificación anterior

Se ejecutó la suite completa tras integrar inductancia:

```text
python -m pytest -q
142 passed in 11.28s
```

Composición: 37 pruebas originales de geometría/unidades, 32 de capacitancia,
7 de la interfaz existente, 61 del cálculo de inductancia y 5 de su interfaz.
También pasaron `python -m compileall -q app.py ste_calculator tests` y
`python scripts/smoke_test.py`: servidor iniciado, página HTTP 200 y salud
HTTP 200 con respuesta `ok`. El servidor temporal se detuvo al terminar.
No se agregaron dependencias para esta etapa.

### Caso obligatorio de inductancia

A=(-3,13), B=(3,13), C=(0,9) m; radio exterior 0.011765 m por fase;
conductor circular macizo, mu_r=1, corriente uniforme; suelo ideal sin
transposición. Se usó mu_0=4 pi 10^-7 H/m según el modelo solicitado.

```text
RMG calculado = 0.00916259121283508 m

L [mH/km], redondeada a ocho decimales:
[[1.59014456, 0.29845590, 0.29816333],
 [0.29845590, 1.59014456, 0.29816333],
 [0.29816333, 0.29816333, 1.51659960]]

X a 60 Hz [ohm/km], ensayo de conversión (frecuencia elegida para la prueba):
[[0.599470375751, 0.112515222524, 0.112404929106],
 [0.112515222524, 0.599470375751, 0.112404929106],
 [0.112404929106, 0.112404929106, 0.571744580524]]
```

La comparación de RMG contra 0.00916259121 m pasó con atol=5e-12 m y rtol=0.
La matriz L pasó con atol=5e-9 mH/km y rtol=0, coherente con los ocho decimales
de la referencia. La frecuencia de 60 Hz es un dato del ensayo, no se inserta
automáticamente como entrada de la aplicación.

### Cobertura y condiciones verificadas

- Simetría, energía positiva en el espacio físico aplicable y enlace interno
  incorporado exactamente una vez mediante RMG.
- Distancias reales, imágenes reflejadas, distancias entre imágenes iguales a
  las reales y alturas diferentes. En el caso obligatorio: D_AB=6 m,
  D_AC=D_BC=5 m, S_AA=S_BB=26 m y S_CC=18 m.
- RMG macizo, RMG de fabricante sin nueva corrección, fuente obligatoria y
  asociación por fase al reordenar entradas.
- Conversión H/m a microH/m y mH/km con factor 1e6; X=2 pi f L en SI y
  conversión a ohm/km. Consistencia entre j omega lambda y j X I.
- Sin suelo: L_ref cambia al variar d_0 según k ln(a) 11^T, mientras los
  enlaces para suma de corrientes cero y las matrices reducidas son invariantes.
  En una comprobación adicional d_0=1 frente a 1000 m, la diferencia máxima
  entre matrices de lazos calculadas fue 0 H/m. La implementación obtiene
  las reducciones con la forma canónica para evitar cancelaciones de ln(d_0).
- Caso equilátero analítico sin transposición; invariancia frente a escala
  geométrica común y traslación vertical cuando no hay efecto suelo.
- Entradas no finitas, frecuencias/radios/RMG inválidos, falta de referencia,
  falta de fuente, contacto/solapamiento, circuitos múltiples y corrientes
  con componente de suma no nula se rechazan.
- Interfaz: carga del caso, confirmación del modelo macizo, alternativa de
  fabricante, cambio de referencia, controles independientes de capacitancia,
  reactancia solo con frecuencia válida y L disponible sin frecuencia.

Los módulos protegidos no se modificaron. SHA256 antes y después:

```text
ste_calculator/geometry.py
FFB6A3FE4AF18E3967AA9B85DFFE7C02A05D45BFB33654DCC69EBDCCC7454DC3

ste_calculator/capacitance.py
FBA63D8CBFFEEEFF43D4C1BAC7BE23246F6FAF977F3DB6FE49AE21DB90C44B8C
```

Fuentes, páginas, inconsistencias corregidas y derivación de la representación
de suma cero: `referencias/inductancia.md`. La revisión incluyó páginas
renderizadas de las notas, el manuscrito del 08-09-26 y Kersting. La interfaz
se verificó con AppTest y arranque HTTP; no se realizó inspección visual manual
del navegador. Las pruebas verifican software y casos del modelo, no certifican
un diseño eléctrico. No se implementaron Carson, piel, proximidad, hebras ACSR,
retorno por tierra de resistividad finita, haz, transposición ni doble circuito.

Versiones principales verificadas:

| Componente | Versión instalada |
|---|---|
| Streamlit | 1.66.0 |
| NumPy | 2.5.4 |
| SciPy | 1.18.1 |
| Plotly | 6.9.0 |
| Pandas | 2.3.3 |
| Pytest | 9.1.1 |

## Etapa 2: resultados históricos

| Comprobación | Resultado |
|---|---|
| Compilación de los módulos Python (`compileall`) | Correcta |
| `python -m pytest -q` | 76 pruebas aprobadas: 37 originales de geometría/unidades, 32 de capacitancia y 7 de interfaz |
| `python scripts/smoke_test.py` | Servidor iniciado; página HTTP 200; salud HTTP 200 con respuesta `ok` |
| `python -m pip check` | Sin dependencias incompatibles |

En estos comandos, `python` corresponde a `.venv\Scripts\python.exe`.
El servidor temporal se detuvo al finalizar. Para usar la aplicación, vuelve a
iniciarla según el README.

Las pruebas originales cubren distancias de un triángulo conocido, matriz simétrica,
pares entre circuitos, traslaciones y reordenamiento, conversiones métricas,
datos inválidos y desbordamiento. Las pruebas de Streamlit comprueban el inicio
vacío, los resultados conocidos, su retirada ante errores, el marcado de ejemplos,
el cambio de circuitos y los controles pendientes desactivados. Se añadieron pruebas
de capacitancia en la interfaz para el caso obligatorio, radio inválido y bloqueo
capacitivo de circuitos múltiples manteniendo sus distancias geométricas.

## Caso obligatorio de capacitancia ejecutado

Coordenadas A=(-3,13), B=(3,13), C=(0,9) m, radio exterior 0.011765 m en
las tres fases, epsilon_0=8.8541878128e-12 F/m, según la solicitud del usuario.

```text
P [adimensional], redondeada:
[[7.70072279, 1.49227949, 1.49081667],
 [1.49227949, 7.70072279, 1.49081667],
 [1.49081667, 1.49081667, 7.33299801]]

C [nF/km], redondeada a seis decimales:
[[ 7.719800, -1.240982, -1.317160],
 [-1.240982,  7.719800, -1.317160],
 [-1.317160, -1.317160,  8.122161]]
```

La matriz calculada coincide con la referencia del usuario dentro de 0.5e-6 nF/km
por elemento (rtol=0). La identidad PC=2 pi epsilon_0 I se comprobó con C en F/m:
el factor es aproximadamente 5.56325028e-11 F/m y el residuo normalizado máximo
es 2.220446049250313e-16. Los términos fuera de la diagonal del producto son
del orden de 1e-27 F/m, compatibles con redondeo de punto flotante.

Las pruebas nuevas cubren además simetría, definición positiva, rango completo,
un caso simétrico analítico, límite de conductores muy separados, invariancia
ante escalado geométrico común y traslación horizontal, orden de fases y radios,
conversión F/m a nF/km (factor 1e12, conservando signos) y entradas no admisibles.

Los archivos `geometry.py`, `units.py` y `models.py` no se modificaron. En particular,
el SHA256 de `ste_calculator/geometry.py` se mantuvo antes y después del cambio:
`FFB6A3FE4AF18E3967AA9B85DFFE7C02A05D45BFB33654DCC69EBDCCC7454DC3`.
Las ecuaciones, páginas de las fuentes y supuestos se registraron primero en
`referencias/capacitancia.md`; después se implementó el módulo independiente.

La interfaz se ejecutó mediante AppTest. No se realizó una inspección visual manual
del navegador. Python 3.11 no se ejecutó en esta verificación.

Estas comprobaciones verifican el software y el caso numérico del modelo de imágenes.
No certifican un diseño de transmisión ni extienden la validez del modelo a Carson,
transposición, haces o doble circuito capacitivo. Los datos de prueba son sintéticos.


## Actualización de interfaz unificada · 17 de octubre de 2026

El registro anterior corresponde a sus etapas y fechas originales. La interfaz
vigente tiene cuatro secciones; se verificó también en el navegador real.
Baseline previo a la refactorización: 481 pruebas aprobadas. Suite final vigente:
524 aprobadas en 109.04 s, sin borrar pruebas. Los adaptadores anteriores se
prueban mediante una fixture preservada; la app vigente se prueba directamente
en `tests/test_workspace_app.py`. Detalles y alcance de cada prueba, fuentes,
casos numéricos y límites: `referencias/resistencia_y_refactorizacion.md`.

Se conservan las ecuaciones de los motores previos y las salidas 7A–7F.
Informe resumido DOVE: 5 páginas; anexo completo solicitado: 229 páginas.
Los informes son comprobaciones del software y sus modelos, no una validación
física completa frente a PSCAD ni una certificación térmica de diseño.
