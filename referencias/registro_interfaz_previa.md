# Registro técnico anterior a la interfaz unificada

Este documento conserva la guía previa como trazabilidad histórica. La interfaz vigente está descrita en README.md y resistencia_y_refactorizacion.md.

# STE Calculator · Parámetros de líneas de circuito sencillo y doble

Aplicación local en español para explorar la geometría de líneas de transmisión
y calcular capacitancias e inductancias de tres conductores. La etapa 3 añade
inductancia con suelo ideal y análisis sin suelo restringido a corrientes de suma cero.
La etapa 4 incorpora haces regulares de 1 a 4 subconductores por fase, medias
geométricas y capacitancia matricial con subconductores equipotenciales.
La etapa 5 agrega transposición ideal completa en tres tramos iguales, con
promedio inductivo y promedio de potenciales antes de invertir para capacitancia.
La etapa 6 añade seis fases independientes de doble circuito, acoplamiento mutuo,
haces, modelos con/sin suelo, tramos configurables e informes PDF ajustados.
La etapa 7A añade impedancia serie compleja de Carson con suelo de resistividad
finita, separada de los modelos anteriores. Se ofrecen dos aproximaciones
documentadas; no una solución completa de Carson ni una equivalencia PSCAD.
La etapa 7B incorpora neutros y cables de guarda con datos independientes,
primitiva completa y reducción de Kron condicionada a ΔV auxiliar nula.
La etapa 7C incorpora la matriz completa de componentes simétricas y un
contraste independiente para dos guardas, también en doble circuito.
La etapa 7D añade transposición de impedancias serie Carson, conserva la Z
original y compara el caso DOVE con archivos PSCAD suministrados, con CSV/PDF.
Requiere Windows y Python 3.11 o posterior. Se usa Streamlit, NumPy, SciPy y Plotly;
Pandas sirve de soporte para el editor de coordenadas y Pytest para las pruebas.

## Ejecutar en Windows

Abre PowerShell en esta carpeta. Si el entorno ya está preparado:

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Abre [STE Calculator local](http://127.0.0.1:8501) en el navegador. Detén el servidor
con `Ctrl+C` en la terminal. También puedes hacer doble clic en `iniciar.bat`.
No hace falta activar el entorno ni cambiar la política de ejecución de PowerShell.
La aplicación escucha exclusivamente en la interfaz local `127.0.0.1`.

## Instalación desde cero

Si no existe `.venv`, instala Python 3.11+ con el lanzador para Windows y ejecuta:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Si `py` no está disponible, usa `python -m venv .venv` o la ruta completa a tu
Python 3.11+. Los entornos virtuales no son portables: al mover este proyecto
a otro equipo, vuelve a crear `.venv` e instala las dependencias.
`requirements.txt` define rangos compatibles; `requirements-lock.txt`, cuando esté
presente, registra las versiones exactas verificadas con Python 3.12 en esta entrega.
Puedes instalarlas con `python -m pip install -r requirements-lock.txt` dentro del entorno.
Con Python 3.11, usa `requirements.txt` para que el instalador resuelva versiones
compatibles con ese intérprete; esa combinación no se ha probado en esta entrega.

## Validación de secuencias y discrepancias (etapa 7E)

Esta etapa prioriza el análisis y el informe independiente. La aplicación,
sus entradas y todos los resultados de etapa 7D permanecen intactos.

```powershell
.\.venv\Scripts\python.exe scripts\sequence_discrepancy_case.py
.\.venv\Scripts\python.exe -m pytest -q
```

Se calculan Z012 desde las matrices de fase transpuestas de STE y PSCAD y se
contrastan independientemente Z0=Zpropio+2Zmutuo y Z1=Z2=Zpropio-Zmutuo.
El diagnóstico explica el **10.014532 %** de diferencia en R1: las diferencias
de propia y mutua tienen signos opuestos y se suman al restarlas, sobre un
denominador R1 mucho menor. La transformación no introduce esa discrepancia.

La sensibilidad temporal con R_DC=.102 Ω/km por subconductor conserva otro
escenario con R_AC=.1859 Ω/milla. Modifica únicamente una copia de la diagonal
real de Zsub, manteniendo RMG, geometría y retorno por tierra. R1 queda por
debajo de PSCAD y su diferencia absoluta es **2.852840 %**; esto no reproduce
su modelo interno AC ni constituye un ajuste del conductor original.

Se estudia también un equivalente auxiliar que admite reparto desigual con
gradiente longitudinal común por fase. Bajo esas hipótesis y con la misma
primitiva, R1 AC cambia aproximadamente **+0.228568 %** respecto a I/n y no
explica el desacuerdo inicial. Se documentan las condiciones de conexión,
excitación y limitaciones; el modelo I/n de la aplicación no se sustituye.

Se generan:

- `output/pdf/ste_secuencias_discrepancias_dove.pdf`: matrices completas,
  secuencias, verificaciones, errores, sensibilidad y conclusiones físicas.
- `output/ste_secuencias_discrepancias_dove.csv`: 12 comparaciones, cuatro
  escenarios por tres secuencias, con R/X y errores separados.
- `output/ste_corrientes_subconductores_dove.csv`: 96 observaciones de
  corrientes normalizadas, para excitación positiva y cero del primer tramo.
- `output/ste_secuencias_discrepancias_dove.json`: matrices y datos completos.

Las ecuaciones, cifras y diferencias de modelos se documentan en
[referencias/discrepancias_secuencia.md](referencias/discrepancias_secuencia.md).

## Transposición serie Carson y comparación DOVE/PSCAD (etapa 7D)

1. En **Inductancia**, desplázate hasta **Transposición de impedancia serie ·
   Carson · etapa 7D**. No cambia los módulos anteriores ni sus entradas.
2. Pulsa **Cargar caso DOVE · JSON y PSCAD**. El caso se carga exclusivamente
   en 7D desde los tres archivos originales dentro de referencias, incluyendo
   carpetas anidadas. No reemplaza las coordenadas compartidas de Geometría.
3. La aplicación recalcula primero la matriz sin transposición desde los doce
   subconductores del JSON y muestra el residuo frente al resultado exportado.
   En este caso es **0 Ω/m**. Conserva su método **P/Q finitos de Kersting**,
   f=60 Hz y ρ=100 Ω·m; no lo sustituye por Carson modificado.
4. Activa **Activar transposición ideal de Carson** para seleccionar el promedio
   de tres secciones iguales, con asignaciones ABC, BCA y CAB. Desactívala
   para recuperar la original. Ambas matrices siguen disponibles para comparar.
5. En **Tres tramos, asignaciones y desarrollo matemático** consulta las matrices
   intermedias y las ecuaciones Zt=Stᵀ Zoriginal St, Zprom=(Z0+Z1+Z2)/3.
6. La tabla STE/PSCAD contiene todos los elementos de ambos estados en Ω/km,
   con errores absolutos porcentuales de **R y X separados**. Se toman las
   matrices del dominio de fases por unidad de longitud de los TXT; se excluyen
   valores modales, totales y corregidos por efecto de línea larga.
7. Descarga **CSV**, **JSON** y, activando **Preparar informe PDF Carson
   transpuesto**, el **PDF** con tablas R/X, ecuaciones, tres tramos y fuentes.
8. Para otro caso selecciona **Controles actuales de Carson** o importa un
   JSON exportado de 7A. Si usas auxiliares, selecciona **Usar fases reducidas
   por Kron en cada tramo · 7D** y declara su condición ΔVn=0 en Kron. Se reduce
   cada tramo antes de promediar, no el promedio de la primitiva.
9. Con doble circuito se conservan las seis fases y las mutuas entre circuitos.
   Esta versión utiliza ciclos sincronizados en ambos circuitos. Se requieren
   fases eléctricamente equivalentes dentro de cada circuito para el promedio
   por permutaciones; no se promedian resistencias de conductores diferentes.

Resultado DOVE calculado [Ω/km]:

| Término transpuesto | STE Calculator | PSCAD | Error R | Error X |
|---|---|---|---|---|
| Propio | 0.086398156502 + j0.635852084706 | 0.0841586314 + j0.644676406 | 2.661076 % | 1.368799 % |
| Mutuo | 0.057514717708 + j0.384504582967 | 0.0579044283 + j0.389821698 | 0.673024 % | 1.363986 % |

**Entradas de resistencia distintas:** STE usa R_AC bibliográfica de **0.1859
Ω/milla = 0.115512904637 Ω/km**, y PSCAD usa R_DC declarada de **0.102 Ω/km**,
ambas por subconductor. No se supone que los modelos sean idénticos. Estos
porcentajes miden diferencias entre resultados con dichas entradas, no el
error aislado del algoritmo de Carson.

```powershell
.\.venv\Scripts\python.exe scripts\series_transposition_case.py
.\.venv\Scripts\python.exe -m pytest -q
```

El script valida primero el caso original y después genera
`output/ste_carson_transposicion_dove.csv`, `output/ste_carson_transposicion_dove.json`
y `output/pdf/ste_carson_transposicion_dove.pdf`, leyendo los archivos reales.
Las referencias y condiciones están en
[referencias/transposicion_serie.md](referencias/transposicion_serie.md).

## Componentes simétricas y validación de dos guardas (etapa 7C)

1. En **Inductancia**, carga el ejemplo 4.1 completo de Kersting y declara
   la condición ΔVn=0 del neutro. Después de la reducida aparece **Componentes
   simétricas · etapa 7C**. Sin una reducción válida no se muestra una matriz
   de secuencias que pueda confundirse con el resultado reducido.
2. Convención: fasores exp(jωt), a=exp(j120°), fases ABC y secuencias **0,1,2**.
   Vabc=A V012, Iabc=A I012, Z012=A^-1 Zabc A. Se muestran A, su inversa,
   la matriz compleja completa, sus partes R/X y las diagonales Z0/Z1/Z2.
3. Elige **Ω/mile** en la unidad de Kron para comparar con Kersting p.94.
   Resultados calculados desde coordenadas, R_AC y RMG:

   ```text
   Z0 = .773513109+j1.937278418 Ω/milla
   Z1 = .306069982+j.627008922 Ω/milla
   Z2 = .306069982+j.627008922 Ω/milla
   ```

   La matriz mantiene sus seis términos fuera de la diagonal. La igualdad
   Z1=Z2 no demuestra transposición ni permite descartar esos acoplamientos.
4. Para comprobar varios auxiliares pulsa **Cargar ensayo algebraico · dos
   guardas**. Conserva el número de circuitos (uno o dos), sustituye la geometría
   común por el ensayo y deja la declaración ΔVn=0 desmarcada para su revisión.
   Los datos R/RMG de las guardas reutilizan el neutro del libro; la geometría
   es sintética. No es una ficha comercial ni validación de una puesta a tierra.
5. Declara ΔVn=0 para obtener el contraste independiente de ambos cálculos.
   SciPy resuelve las restricciones de corriente y tensión en el sistema
   completo; la comprobación no llama al complemento de Schur del programa.
   Puedes consultar sus matrices y residuos. Cambiar una guarda a aislada o
   conexión desconocida retira la reducida y las secuencias; conserva la primitiva.
6. Para doble circuito, selecciona **Número de circuitos=2** antes de cargar
   el ensayo. La transformación usa B=diag(A,A) y muestra la matriz **6×6**,
   en orden 0 C1,1 C1,2 C1,0 C2,1 C2,2 C2. Conserva los bloques entre circuitos.
7. JSON y PDF de Kron incluyen ahora las secuencias completas con unidades,
   convención y fuentes. El PDF separa R/X y presenta ecuaciones por pasos,
   con encabezados de secuencia/circuito y tablas anchas paginadas.

```powershell
.\.venv\Scripts\python.exe scripts\sequence_case.py
.\.venv\Scripts\python.exe -m pytest -q
```

El script genera `output/ste_secuencias_validacion.json` con el ejemplo del
libro y los ensayos de dos guardas de uno/dos circuitos, además del informe
`output/pdf/ste_secuencias_kersting.pdf`. Todas las matrices se recalculan.
La comparación independiente valida álgebra, no la exactitud de Carson ni
las conexiones físicas. No se añade transposición a Carson/Kron ni se
modifican capacitancia o inductancia con suelo ideal. La fuente detallada,
convención, tolerancias y condiciones están en
[referencias/secuencias.md](referencias/secuencias.md).

## Neutros, guardas y reducción de Kron (etapa 7B)

1. En **Inductancia**, busca **Neutros y cables de guarda · Kron · etapa 7B**
   dentro del panel de Carson. Los módulos anteriores conservan sus controles.
2. Para reproducir el libro pulsa **Cargar ejemplo 4.1 completo de Kersting ·
   con neutro**. Carga las tres fases y el neutro de p.93, f=60 Hz y ρ=100 Ω·m.
   Consulta la primitiva completa y los bloques Zpp, Zpn, Znp y Znn. No necesitas
   ingresar longitud ni frecuencia general para estas matrices por unidad de longitud.
3. Revisa la conexión y su justificación. Marca **Declaro ΔVn = 0 en todos los
   auxiliares eliminados** para aplicar la hipótesis multitierra ideal de p.87.
   Aparecen Zreducida, R/X, respuesta de corriente auxiliar y residuo numérico.
4. Cambia la unidad a **Ω/mile** para comparar con la matriz publicada en p.94.
   Resultado calculado, redondeado a seis decimales:

   ```text
   [[.457552+j1.078048, .155951+j.501679, .153485+j.384938],
    [.155951+j.501679, .466628+j1.048177, .158007+j.423653],
    [.153485+j.384938, .158007+j.423653, .461473+j1.065071]] Ω/milla
   ```

5. Para tu geometría elige uno o dos circuitos y configura las fases en Carson.
   Aumenta **Número de conductores auxiliares · Kron**. Cada auxiliar necesita
   etiqueta única, tipo, X, altura, R_AC en Ω/km, RMG en metros y fuente técnica.
   ACSR requiere datos documentados; no se deducen de un cilindro macizo.
6. Las conexiones **aislada** y **desconocida** conservan la primitiva y bloquean
   Kron con una causa específica. Desmarcar la declaración también retira el
   resultado reducido. Cambios de datos recalculan las matrices en cada ejecución.
7. Con haces se reutilizan todos los subconductores y el reparto I_fase/n del
   modelo anterior. Se distingue la agregación por corrientes iguales de Kron.
   Con doble circuito la reducida conserva **seis fases** y sus acoplamientos.
8. Descarga JSON y activa **Preparar informe PDF Kron**. El informe incluye
   entradas, condiciones, fórmulas y bloques, con tablas R/X separadas, unidades
   coherentes y columnas paginadas. Las fórmulas se ajustan como texto, sin
   capturas anchas; en pantalla las ecuaciones extensas se muestran por pasos.

```powershell
.\.venv\Scripts\python.exe scripts\kron_case.py
.\.venv\Scripts\python.exe -m pytest -q
```

El script regenera `output/ste_kron_kersting.json` y
`output/pdf/ste_kron_kersting.pdf` directamente desde los datos bibliográficos.
Las matrices publicadas solo se usan para comparar, nunca como salidas fijas.
Se resuelve Znn Y=Znp y se calcula Zpp-Zpn Y. La reducción supone ΔVn=0 en
todos los auxiliares eliminados; no modela electrodos finitos, guardas aisladas,
conexión en un solo extremo ni tierras discretas. No añade transposición de
Carson ni reduce dos circuitos a uno. Capacitancia e inductancia ideal permanecen
independientes. Fuentes, erratas, hipótesis y tolerancias: [referencias/kron.md](referencias/kron.md).

## Impedancia serie Carson (etapa 7A)

1. Abre **Inductancia → Impedancia serie · Carson · etapa 7A**. Se conservan
   las siete pestañas; este panel se encuentra después del módulo inductivo anterior.
2. Selecciona **Carson modificado** o **P/Q finitos de Kersting**, ambos aproximados.
   El segundo conserva los términos impresos en (4.23)-(4.24), no toda la serie.
   La diapositiva 6 contiene discrepancias; se priorizó la página original del libro.
3. Ingresa **Frecuencia Carson [Hz]**, resistividad en Ω·m, R_AC y RMG individual
   de cada fase y su fuente técnica. La frecuencia es propia de este módulo y
   no cambia la frecuencia general ni las matrices capacitivas. R_AC puede
   ingresarse en Ω/km, Ω/m o Ω/mile. RMG siempre se ingresa en metros.
4. Para ACSR usa datos del fabricante, con sus condiciones de frecuencia y
   temperatura. No se calcula RMG como R exp(−1/4), ni resistencia por material,
   ni corrección DC/AC o térmica. El usuario debe aportar R_AC aplicable a la
   frecuencia/temperatura analizadas; cambiar f no corrige ese dato automáticamente.
5. Usa los **centros de Geometría** para un conductor por fase, o selecciona
   **Subconductores configurados en Haces** para expandir los haces existentes
   de uno o dos circuitos. Con haces se supone I_sub=I_fase/n y Zfase=TᵀZsubT.
   No se resuelve la redistribución real de corrientes. No se aplica el promedio
   de transposición de los otros paneles: se evalúa la sección transversal original.
6. Consulta Z compleja y sus partes R y X en Ω/km o Ω/m. Las contribuciones
   se muestran separadas: R_AC diagonal, X geométrica con imágenes ideales y
   corrección ΔZ de retorno por tierra. La descomposición reactiva depende de
   esa referencia; no es una propiedad inductiva intrínseca única de la tierra.
7. Elige un elemento para ver distancias, k, P/Q, sustituciones y unidades.
   El k de Kersting usa S en **pies**, convertido explícitamente desde metros.
   Se muestra el k máximo: k>0.1 genera aviso y k≥1 se rechaza por criterio
   preventivo de software. Esos umbrales no garantizan precisión bibliográfica.
   Fuera de 50-60 Hz se advierte que no se validó la precisión de la aproximación.
8. Pulsa **Cargar fases del ejemplo 4.1 de Kersting · sin Kron** para comprobar
   el bloque primitivo de tres fases. Sustituye las coordenadas compartidas,
   pero no los radios capacitivos. Son datos del ejemplo, no una ficha vigente.
   No contiene la eliminación del neutro ni debe compararse con la matriz
   reducida de p.94. El motor se contrasta además con la primitiva 4×4 de p.93.
9. Descarga JSON con matrices y entradas. Activa **Preparar informe PDF Carson**
   para obtener fórmulas, fuentes, sustituciones, contribuciones y primitivas
   completas con el formato de tablas ajustadas.

Reproducción independiente de la interfaz desde PowerShell:

```powershell
.\.venv\Scripts\python.exe scripts\carson_case.py
```

Genera `output/ste_carson_kersting.json` con ambos métodos y la primitiva
de cuatro hilos sin eliminar ninguno, y `output/pdf/ste_carson_kersting.pdf`
con el método modificado. El caso usa 60 Hz, ρ=100 Ω·m, fases en (0,29),
(2.5,29), (7,29) ft, R_AC=0.306 Ω/mile y RMG=0.0244 ft.
Su bloque de fases da Z_AA≈0.249357+j0.878177 Ω/km y
Z_AB≈0.059218+j0.529124 Ω/km. Los valores se calculan; no son salidas fijas.

El panel de etapa 7A conserva su cálculo sin Kron. Neutros y guardas se añaden
en el módulo separado 7B descrito arriba; las secuencias de la reducida se
calculan en 7C. No se implementan líneas subterráneas,
suelo estratificado ni serie/integral completa de Carson. No hay comparación
independiente con PSCAD. La presentación, las notas y el capítulo consultados,
con páginas, ecuaciones y erratas, se documentan en
[referencias/carson.md](referencias/carson.md).

**Revisión de capacitancia:** a potencial común entre tramos se promedia C;
a carga común se promedian los coeficientes de potencial antes de invertir.
En general son resultados distintos. Las etapas 5-6 conservan su procedimiento
didáctico a carga común, sin certificarlo como equivalente shunt universal de
una línea distribuida. Carson no cambia ninguna de esas matrices. La derivación
y las condiciones de borde están en la última sección del registro bibliográfico.

## Doble circuito y PDF (etapa 6)

1. Actualiza las dependencias del entorno existente:
   `.\.venv\Scripts\python.exe -m pip install -r requirements.txt`.
   Se añadieron ReportLab para los informes y pypdf para comprobarlos.
2. Inicia la aplicación con el comando de Windows indicado arriba. Abre
   **Haces → Cargar caso reproducible de doble circuito**. Carga dos circuitos,
   sus seis coordenadas y el modelo sintético macizo. Si ya hay dos circuitos,
   el panel **Doble circuito · etapa 6** aparece primero en Haces.
3. En **Geometría** edita las seis posiciones: C1-A/B/C son A/B/C y C2-A/B/C
   son A'/B'/C'. En Haces configura por separado los seis radios, cantidades
   de 1 a 4 subconductores, separaciones y rotaciones. Las coordenadas son
   compartidas; las opciones eléctricas de doble circuito tienen claves `dc_*`
   propias, independientes de los módulos anteriores de circuito sencillo.
4. Para ACSR selecciona el modelo de fabricante, ingresa seis RMG y su fuente
   técnica. No se aplica la expresión de conductor macizo al trenzado. Si falta
   RMG, la geometría y capacitancia continúan disponibles.
5. Elige suelo para L y C independientemente. Los resultados principales son
   **L6** en H/m, µH/m o mH/km y **C6** en F/m y nF/km. Los gráficos muestran
   cada subconductor y, opcionalmente, sus imágenes. Frecuencia y longitud
   no son requisitos de las matrices; frecuencia positiva permite X6 en Ω/km.
6. Sin suelo se requiere **ΣI de las seis fases=0** para L y **Σq=0** para C;
   los operadores principales tienen rango 5 y no fijan el potencial común.
   El apartado de equilibrio separado de cada circuito restringe L a rango 4
   y muestra cuatro lazos; no conecta terminales ni crea un equivalente 3×3.
7. En **Transposición de doble circuito** elige **Sin transposición** o
   **Transposición ideal completa automática**. El plan completo genera las
   nueve combinaciones independientes de los ciclos de los dos circuitos,
   cada una con peso interno 1/9. La tabla de fracciones y posiciones es de
   solo lectura; no se introducen número de tramos ni asignaciones manuales.
   Cada haz completo viaja con su fase, dentro de su propio circuito.
   Para circuito sencillo se generan tres tramos iguales. El generador puede
   extenderse a N circuitos; el motor eléctrico sigue admitiendo solo uno o dos.
8. Consulta **Matrices intermedias**, **Primitivas de subconductores**, los
   bloques por circuito y el desarrollo de cualquier elemento. La matriz de
   seis terminales se distingue de la primitiva de hasta 24 subconductores.
   C se obtiene de cargas equipotenciales; en transposición se promedia P
   efectiva antes de invertir. No se reduce a tres fases automáticamente.
9. Activa **Preparar informe PDF de doble circuito** y descarga el informe.
   El generador usa A4 horizontal, tablas de hasta seis columnas numéricas
   por bloque, etiquetas repetidas y control de paginación. Así conserva todas
   las columnas y evita superposiciones. Incluye entradas, fórmulas, sustituciones,
   distancias, matrices primitivas e intermedias. Para las etapas anteriores
   está **Preparar informe PDF de haces y transposición**. Usa estos informes
   para imprimir: el Ctrl+P del navegador puede recortar los canvas de Streamlit.

Caso sintético reproducible: A=(-4,15), B=(-4,11), C=(-4,7), A'=(4,15),
B'=(4,11), C'=(4,7) m, un subconductor por fase, radio 0.011765 m,
modelo macizo no magnético uniforme, suelo ideal, sin transposición.
Para regenerar las matrices numéricas completas y el PDF desde PowerShell:

```powershell
.\.venv\Scripts\python.exe scripts\double_circuit_case.py
```

Produce `output/ste_doble_circuito.json` y
`output/pdf/ste_doble_circuito.pdf`. Por ejemplo, L_AA=1.618764728 mH/km,
L_AA'=0.271220821 mH/km, C_AA=7.810906938 nF/km y
C_AA'=−0.892482542 nF/km. Son salidas calculadas del caso sintético,
no propiedades comerciales ni resultados fijados en el código.

La corrección automática y la verificación DOVE de dos subconductores por fase
se documentan en [referencias/correccion_transposicion_automatica.md](referencias/correccion_transposicion_automatica.md).
Se comprueban simetría, carga global cero, acoplamientos independientes y una
matriz transpuesta distinta de la original. Se conservan los modelos físicos
por tramo y las etapas 7A-7F.

Los bloques diagonales de C no representan circuitos aislados: con suelo,
C11 relaciona q1 con V1 cuando V2=0. El otro circuito flotante implica otras
condiciones. No hay conexión paralela ni reducción de Kron automática.
Fuentes, inconsistencias de los apuntes y derivación en
[referencias/doble_circuito.md](referencias/doble_circuito.md).

## Utilizar transposición ideal (etapa 5)

Si una sesión abierta desde una versión anterior muestra Haces calculados pero
Transposición no recibe el contexto, detén ese servidor con `Ctrl+C` y vuelve
a ejecutar el comando de inicio. Recargar solo la página puede conservar el
proceso y sus módulos antiguos. La versión corregida construye las entradas
desde los widgets actuales mediante `bundle_inputs.py`, sin depender del
retorno de la función que dibuja Haces. No se guardan matrices ni geometrías
derivadas en `st.session_state`; las claves `haz_*` contienen las entradas.
Un dato inválido identifica su campo y fase. Frecuencia y longitud no bloquean
las matrices por unidad de longitud: solo afectan reactancia y tabla de longitudes.

1. Ejecuta la aplicación y abre **Haces**. Baja a **Transposición ideal · etapa 5**
   y pulsa **Cargar caso obligatorio de transposición**. Carga los centros
   A=(−3,13), B=(3,13), C=(0,9) m, cuatro subconductores cuadrados por fase,
   separación 0.4572 m, radio individual 0.011765 m y modelo macizo con suelo ideal.
2. En **Tratamiento de la línea**, selecciona **Transposición ideal completa**
   o **Sin transposición**. El segundo modo reproduce el tramo inicial de Haces.
   El gráfico longitudinal y la tabla muestran dónde está cada fase en los
   tres tercios. La longitud de Configuración permite mostrar sus longitudes
   en metros; no es necesaria para los coeficientes por unidad de longitud.
3. En el caso obligatorio, L en mH/km tiene diagonales **0.961802** y términos
   mutuos **0.298262**. C en nF/km tiene diagonales **13.803851** y términos
   mutuos **−3.300067**. Las cifras son una comprobación numérica del modelo.
4. Expande cada tramo para ver su permutación, posiciones de subconductores,
   matrices L, P efectiva y C. Activa sus casillas para ver geometría y matrices
   primitivas completas. Las propiedades de los conductores viajan con la fase.
5. La capacitancia se obtiene resolviendo primero los subconductores
   equipotenciales de cada fase. Luego se recupera P efectiva de fases, se
   promedia y se invierte: **C_trans = 2πε₀ (Σ P_fase,t/3)⁻¹**.
   La comparación con el promedio directo de C está separada y no alimenta
   el resultado principal. En general ambos procedimientos dan valores distintos.
6. Los controles de suelo de Haces siguen siendo independientes para L y C.
   Sin suelo, L solo describe **IA+IB+IC=0**; C solo describe **Σq_fase=0**,
   sin potencial común definido. Se opera en el subespacio de suma cero;
   las matrices proyectadas no son matrices absolutas para entradas arbitrarias.
7. Consulta el desarrollo de cada elemento y el registro
   [referencias/transposicion.md](referencias/transposicion.md), con páginas,
   discrepancias de las notas y deducción. Las unidades principales son
   H/m, µH/m y mH/km para L; F/m y nF/km para C.

Se promedian los enlaces o potenciales por longitud bajo corrientes o cargas
de fase comunes entre tramos. Es una homogenización ideal, con cruces de
longitud nula, no una solución exacta en cascada de líneas distribuidas.
Se conservan las hipótesis de corriente I_fase/n y carga lineal de Haces.
Carson se calcula aparte en la etapa 7A; no se implementa reducción de doble circuito.

## Utilizar conductores en haz (etapa 4)

1. Abre **Haces**. Las coordenadas de **Geometría** son los centros de las fases.
   Puedes pulsar **Cargar comparación sin haz (n=1)**: carga la geometría y radio
   del caso anterior y el modelo macizo de ensayo. No es un diseño validado.
2. Selecciona de 1 a 4 subconductores por fase. Para n>1 ingresa la separación
   entre vecinos en metros. n=2 es horizontal; n=3, triangular; n=4, cuadrado.
   Puedes cambiar la rotación adicional por fase. n=1 ignora la separación.
3. Ingresa el radio exterior individual por fase. El gráfico muestra cada
   subconductor; usa **Vista de subconductores → A/B/C** para ampliar un haz.
   La tabla enumera sus coordenadas y radios físicos.
4. Para inductancia, selecciona el modelo macizo y confirma sus condiciones,
   o **ACSR/trenzado: RMG del fabricante**, que exige RMG individual por fase
   y fuente técnica. No se aplica R exp(−1/4) a un ACSR automáticamente.
   La geometría y capacitancia funcionan aunque falte el RMG inductivo.
5. Los modelos de suelo para L y C se eligen independientemente. Con suelo
   ideal se muestran C de fases, P de todos los subconductores, respuesta
   individual de cargas y residuo de equipotencialidad. La matriz principal
   usa radios individuales; no usa los radios equivalentes del haz.
6. Sin suelo, C se calcula solo para **carga neta total cero**, con potencial
   común indeterminado y rango 2. Para L se mantiene **IA+IB+IC=0** y se
   muestran matriz proyectada y lazos. No se solicita d₀.
7. La tabla distingue RMG inductivo equivalente y radio capacitivo equivalente.
   El desarrollo sustituye los valores de cada fase en sus medias geométricas.
   Consulta **Distancias geométricas equivalentes y primitivas** para DMG
   entre haces e imágenes, calculadas con todas las posiciones.
8. L usa corrientes iguales I_fase/n: es una hipótesis del modelo agregado,
   no una solución de redistribución de corrientes. Con frecuencia positiva
   ingresada en Configuración se obtiene también X en Ω/km.
9. La comparación capacitiva de un círculo equivalente por fase está en un
   apartado separado, rotulado como aproximación. Puede diferir de la solución
   matricial explícita; para n=1 ambas reproducen el módulo individual.

Las fuentes, correcciones y derivaciones están en
[referencias/haces.md](referencias/haces.md). El panel de etapa 5 añade la
transposición de circuito sencillo; el panel de etapa 6 añade doble circuito.
Carson está separado en el panel de etapa 7A. La formulación explícita conserva la aproximación de
cargas lineales y radios circulares; no resuelve carga superficial exacta,
hebras ACSR, piel/proximidad, corona ni corrientes de reparto reales.

## Utilizar y verificar el módulo de inductancia (etapa 3)

1. Abre **Inductancia** y pulsa **Cargar caso obligatorio de inductancia**.
   Se cargan las coordenadas compartidas A=(−3,13), B=(3,13), C=(0,9) m,
   radios inductivos de 0.011765 m y el modelo circular macizo no magnético
   con corriente uniforme y suelo ideal. Se conservan los radios capacitivos,
   la frecuencia y la longitud. Las ediciones posteriores se recalculan.
2. Comprueba la tabla de RMG: aproximadamente **0.009162591213 m** por fase.
   Expande las distancias: D_AB=6 m, D_AC=D_BC=5 m, S_AA=S_BB=26 m,
   S_CC=18 m. El gráfico identifica fases reales e imágenes de corriente opuesta.
3. La matriz en mH/km debe mostrar, a ocho decimales:

   ```text
   [[1.59014456, 0.29845590, 0.29816333],
    [0.29845590, 1.59014456, 0.29816333],
    [0.29816333, 0.29816333, 1.51659960]]
   ```

   También se presenta en H/m y µH/m. La conversión de H/m a cualquiera
   de las otras dos unidades es **10^6**.
4. Para reactancia, ingresa una frecuencia positiva en **Configuración**.
   Se muestran X=2πfL en Ω/m y Ω/km; sin frecuencia válida, L y RMG siguen
   disponibles. La longitud longitudinal no interviene en estos resultados.
5. Consulta el ensayo equilibrado ABC. El valor inicial de 1 A es un ensayo
   explícito, no una corriente del proyecto. Puedes cambiar su amplitud para
   revisar enlaces propios, mutuos, totales y diferencias respecto de C.
   Con frecuencia válida se muestran diferencias de caída inductiva en V/m.
6. En el desarrollo de la misma sección, elige LAA, LAB, etc. para ver la fórmula,
   sustitución numérica, unidades, RMG usado y fuente bibliográfica.

Para un **RMG conocido del fabricante**, cambia el modelo, ingresa radio exterior
y RMG de cada fase y una referencia técnica. Ese RMG se usa directamente;
no se multiplica otra vez por exp(−1/4). La expresión para conductor macizo
requiere confirmar sus hipótesis y no se aplica a ACSR trenzado por defecto.

Para **sin efecto suelo**, selecciona ese modo. No necesitas introducir d₀:
los resultados principales son la **matriz proyectada de media cero (3×3)**
y la **matriz de lazos A−C/B−C (2×2)**, ambas en H/m, µH/m y mH/km.
El ensayo principal muestra enlaces proyectados y diferencias de lazos.
La restricción **IA + IB + IC = 0** permanece explícita: la proyección tiene
rango 2, no se invierte ni describe secuencia cero o corrientes arbitrarias.

Para explorar la deducción, abre **Avanzado · deducción con distancia de referencia**
y activa **Mostrar deducción con referencia d₀**. Prueba 10, 1000 y 2000 m:
la matriz auxiliar L_ref cambia, mientras los resultados principales permanecen
iguales. L_ref no es una matriz absoluta única. Un valor vacío, cero o inválido
en esta opción solo impide la deducción avanzada, sin bloquear el cálculo principal.
Las expresiones originales con d₀ y los coeficientes referidos se muestran allí.

Los modos de suelo y radios de inductancia no modifican los de capacitancia.
Ambos módulos comparten las coordenadas y la frecuencia general.
Las ecuaciones, páginas revisadas, errores detectados y condiciones físicas
están en [referencias/inductancia.md](referencias/inductancia.md).

## Verificar la capacitancia en la interfaz

1. En **Configuración**, pulsa **Cargar caso obligatorio de capacitancia**.
   Se cargan A = (−3,13), B = (3,13), C = (0,9) m y radio exterior
   0.011765 m para cada fase. El botón reemplaza coordenadas y radios.
2. En **Resultados**, baja a **Capacitancia · suelo ideal por imágenes**.
   Revisa P adimensional y C en F/m y nF/km, en orden A, B, C.
   La capacitancia usa coordenadas y radios: no exige frecuencia ni longitud.
3. La matriz en nF/km debe mostrarse, a seis decimales, como:

   ```text
   [[ 7.719800, -1.240982, -1.317160],
    [-1.240982,  7.719800, -1.317160],
    [-1.317160, -1.317160,  8.122161]]
   ```

4. Expande **Distancias reales e imágenes [m]**. Debe verse D_AB = 6 m,
   D_AC = D_BC = 5 m; S_AA = S_BB = 26 m y S_CC = 18 m.
5. En **Comprobación P × C = 2πε₀ I**, comprueba el producto y el objetivo
   en F/m. El máximo residuo normalizado del caso se verificó en 2.22e-16.
   La tolerancia de software es 1e-10; puede haber diferencias por redondeo
   numérico entre plataformas. La matriz de referencia se compara con
   tolerancia absoluta de 0.5e-6 nF/km, al estar redondeada a seis decimales.
6. En **Desarrollo matemático**, elige un elemento AA, AB, etc., para consultar
   las distancias, logaritmos, inversa completa de P, sustitución de C y conversión.
7. En **Bibliografía**, consulta las fuentes y los supuestos registrados en
   [referencias/capacitancia.md](referencias/capacitancia.md).
8. Prueba radio cero, radio igual a la altura, o círculos que se toquen: se bloquea
   la capacitancia. Con más de un circuito solo está disponible la geometría.

ε₀ = 8.8541878128e-12 F/m es el valor indicado por el usuario. No se usa GMR
inductivo ni se representan hebras ACSR. Los datos del caso son una verificación
numérica del modelo, no un diseño eléctrico certificado. Los términos mutuos
negativos son normales en esta matriz de Maxwell.

## Probar la geometría conservada de la primera etapa

1. En **Configuración**, ingresa circuitos, frecuencia positiva en Hz y longitud
   positiva en m o km. La interfaz admite entre 1 y 12 circuitos trifásicos A/B/C.
2. En **Geometría**, ingresa las coordenadas X e Y de cada fase en metros.
   X admite valores negativos; Y debe estar por encima del terreno Y = 0.
   Las posiciones no pueden coincidir. Usa punto para los decimales.
3. Inspecciona el gráfico con desplazamiento y zoom. Las etiquetas `C1-A`, etc.
   identifican circuito y fase. Las escalas de X e Y son iguales.
4. Revisa tabla, matriz y CSV en **Resultados**. Selecciona un par en
   **Desarrollo matemático** para ver fórmula, sustitución numérica y unidades.
5. Prueba una celda vacía, Y = 0, frecuencia negativa o posiciones coincidentes:
   los resultados geométricos se retiran hasta corregir la entrada. La capacitancia
   es independiente de la frecuencia y longitud.
6. Los controles históricos pendientes de Configuración permanecen desactivados;
   usa **Haces** para haces y transposición ideal. Suelo ideal es la hipótesis fija
   del módulo capacitivo individual. Las notas del conductor son metadatos.

**Comprobación manual puramente geométrica:** con un circuito, frecuencia y
longitud positivas elegidas por ti, ingresa A = (−1, 2), B = (2, 6), C = (2, 2) m.
Los pares AB, AC y BC deben medir 5, 3 y 4 m respectivamente, por Pitágoras.
Estos datos son una prueba sintética; no describen un diseño eléctrico validado.
El botón de ejemplo carga otra distribución sintética y la marca explícitamente
como ilustrativa, incluso después de editarla. La app inicia con entradas vacías.

Ejecuta las pruebas automáticas desde esta carpeta:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe scripts\smoke_test.py
```

Las pruebas cubren triángulos conocidos, matriz, pares geométricos entre circuitos,
entradas incorrectas y conversiones de unidades. Para capacitancia cubren el caso
obligatorio, simetría, invertibilidad, definición positiva, identidad matricial en SI,
un modo simétrico analítico, límite de fases muy separadas, escalamiento geométrico,
asociación entre radios y fases y bloqueo de geometrías fuera del alcance.
La etapa 3 agrega el caso obligatorio de inductancia, RMG macizo y de fabricante,
simetría, unidades, alturas distintas, reflexión, flujo interno contado una vez,
reactancia y enlaces equilibrados. Se prueba la invariancia física sin suelo al
cambiar d₀, el caso equilátero sin transposición y el aislamiento de opciones
de capacitancia e inductancia en la interfaz.
Las etapas 4 y 5 añaden haces de 1 a 4 subconductores, comparación con los
modelos individuales, permutaciones de transposición, tres tramos iguales,
promedio de potenciales, solución independiente por restricciones equipotenciales
y conservación de los modelos anteriores al desactivar la transposición.
La prueba de interfaz usa `streamlit.testing.v1.AppTest`, comprueba el estado
inicial, resultados, errores y controles pendientes. No sustituye la revisión
visual del navegador.
El script `smoke_test.py` inicia un servidor temporal en un puerto local libre,
comprueba la página y el estado HTTP y detiene ese servidor al terminar.

## Organización

```text
app.py                      Interfaz Streamlit y conexión entre capas
ste_calculator/
  models.py                 Datos de entrada y validaciones
  units.py                  Conversiones métricas
  geometry.py               Distancias y matriz; sin código de interfaz
  plotting.py               Gráfico Plotly
  capacitance.py            Cálculo independiente de capacitancia, validación y unidades
  capacitance_ui.py         Tablas y desarrollo matemático de capacitancia en Streamlit
  inductance.py             RMG, matrices con/sin suelo, enlaces, unidades y reactancia
  inductance_ui.py          Sección Inductancia, gráfico, entradas y desarrollo
  bundles.py                Geometría de haces, radios y distancias equivalentes
  bundle_electrical.py      L agregada, C equipotencial y modelos sin suelo
  bundle_ui.py              Sección Haces y comparación con aproximación en centros
  bundle_inputs.py          Contrato de entradas y diagnóstico compartido Haces/Transposición
  transposition.py          Tramos, promedio de L y promedio/inversión de P de fases
  transposition_ui.py       Panel de transposición, esquema y matrices intermedias
  double_circuit.py         Seis terminales, acoplamiento, haces y tramos configurables
  double_circuit_ui.py      Geometría, entradas y desarrollo de doble circuito
  printing.py               PDF con tablas ajustadas, partición horizontal y paginación
  carson.py                 Z propia/mutua, dos aproximaciones y agregación de haces
  carson_ui.py              Entradas técnicas, contribuciones y desarrollo independiente
  carson_report.py          JSON y PDF con procedencia y unidades
  kron.py                  Primitiva ampliada, bloques y reducción condicionada
  kron_ui.py               Entradas técnicas y condiciones eléctricas explícitas
  kron_report.py           Matrices y procedimiento Kron exportables
  sequences.py             Transformación completa 3×3/6×6 de fase a secuencias
  sequences_ui.py          Matrices complejas, convención y contraste de guardas
  sequence_report.py       Convención y secuencias exportables
  sequence_examples.py     Ensayo algebraico reproducible de dos guardas
  kron_validation.py       Contraste independiente por sistema completo
  series_transposition.py  Promedio serie por ciclos; 3×3/6×6, sin cambiar L/C
  series_inputs.py         Entradas actuales o JSON exportado, con recálculo
  pscad_series.py          Lectura de Z de fase por longitud en los TXT de PSCAD
  series_comparison.py     Comparación R/X y CSV con referencias explícitas
  series_report.py         Matrices, tramos, tabla comparativa PDF/JSON
  series_transposition_ui.py  Integración independiente de la etapa 7D
tests/                      Pruebas de cálculo, unidades e interfaz
scripts/smoke_test.py        Prueba HTTP con servidor temporal
scripts/double_circuit_case.py Caso reproducible: matrices JSON e informe PDF
scripts/carson_case.py       Caso Kersting: matrices calculadas y PDF sin Kron
scripts/kron_case.py         Ejemplo 4.1 completo: primitiva y reducción del neutro
scripts/sequence_case.py     Secuencias de Kersting y ensayos de dos guardas
scripts/series_transposition_case.py  Caso DOVE: validación original, transposición y PSCAD
referencias/                PDF originales y registros de ecuaciones de cada etapa
.streamlit/config.toml      Tema e inicio local
iniciar.ps1 / iniciar.bat    Lanzadores para Windows
requirements.txt            Dependencias con rangos de versiones
requirements-lock.txt       Versiones instaladas y verificadas
VERIFICACION.md             Evidencia de las comprobaciones de esta entrega
.gitignore                  Exclusión del entorno y archivos temporales
```

## Alcance y supuestos

- Cada fila es una posición de fase en una sección transversal. No se modelan
  cables de guarda, catenarias, flecha ni terreno irregular. Solo se contempla
  variación longitudinal mediante los tres tramos uniformes de transposición ideal.
- Se calculan todos los pares de posiciones, dentro y entre circuitos,
  con `Dij = sqrt((xj − xi)² + (yj − yi)²)`, en metros. NumPy `hypot`
  evalúa esta expresión de forma numéricamente estable y SciPy organiza la matriz.
- Se conserva la precisión interna de punto flotante; se redondea solo al mostrar.
- La frecuencia y longitud son entradas registradas: no intervienen en las
  distancias transversales ni C por unidad de longitud. La longitud usa únicamente
  conversiones métricas; no se calcula capacitancia total ni admitancia.
- En los modelos individuales los marcadores representan posiciones de fase.
  En Haces se expanden los subconductores y los círculos representan sus radios;
  los marcadores siguen identificando centros.
- En el módulo individual de capacitancia se implementa C = 2πε₀ P⁻¹ para un circuito A/B/C,
  con Pii = ln(2hi/ri) y Pij = ln(Sij/Dij). P es adimensional; C está en F/m.
  El suelo es un plano infinito a 0 V y el aire tiene permitividad relativa 1.
  Se usa la aproximación de carga lineal y radio exterior circular de las fuentes,
  sin resolver exactamente la distribución superficial de cilindros gruesos próximos.
- Los radios deben ser positivos, menores que las alturas, y los círculos no
  pueden tocarse ni solaparse. P debe ser definida positiva y tener número de
  condición <= 1e12 (criterio numérico de software, no norma física).
- En Haces la capacitancia principal resuelve cargas con fases equipotenciales.
  El modelo sin suelo restringe la carga total a cero y no fija el potencial común.
  El círculo equivalente en centros es una comparación aproximada separada.
- No se implementan Carson completo, equivalentes automáticos de doble circuito
  ni propiedades de materiales. Kron solo está disponible bajo la condición
  explícita ΔVn=0 del módulo 7B. No se comprueban límites
  reglamentarios ni seguridad de una instalación.
- El módulo individual de inductancia admite un circuito, un conductor por fase, de gran longitud
  y geometría uniforme. En suelo ideal se usan imágenes con corrientes opuestas.
  Sin suelo solo se admiten corrientes de suma cero; no existe aquí un modelo
  de retorno para secuencia cero ni una matriz absoluta única.
- El módulo de inductancia ideal no implementa piel, proximidad, hebras ACSR,
  permeabilidad del alma ni retorno de resistividad finita (este último está
  separado en Carson), ni equivalentes automáticos de doble circuito.
  La hipótesis de corriente uniforme limita la fórmula maciza. Un dato de
  fabricante debe corresponder al conductor y condiciones que se analizan.
- Haces agrega inductancias bajo corriente I_fase/n por subconductor, incluyendo
  todas las distancias reales e imágenes. No resuelve su reparto de corrientes.
- La reactancia es por longitud, sin resistencia ni impedancia total. Los ensayos
  fasoriales no son cálculos de carga ni validaciones de seguridad de la línea.
- No hay guardado de proyectos en disco: los datos viven en la sesión de la app.
  El CSV exporta la tabla de distancias y su contexto (ejemplo ilustrativo o
  entradas del usuario, siempre sin validación de diseño). No es un formato de proyecto.

Las fuentes y la diferencia entre P adimensional y los coeficientes dimensionales
de Kersting se registran en `referencias/capacitancia.md`. Las próximas ecuaciones
deben incorporarse después de revisar sus fuentes específicas.
