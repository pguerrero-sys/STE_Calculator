# Etapa 7F: validación controlada del retorno por tierra y ACSR

Actualización: referencia PSCAD de integración numérica confirmada por el usuario.
Análisis independiente y reproducible. No se
modifican módulos, entradas, interfaz ni artefactos de etapas anteriores.

## Reproducción en Windows

Desde la carpeta del proyecto, con el entorno existente:

```powershell
.\.venv\Scripts\python.exe scripts\earth_validation_case.py
.\.venv\Scripts\python.exe -m pytest -q
```

Salidas nuevas, sin sobrescribir informes 7A-7E:

- `output/pdf/ste_validacion_tierra_acsr_dove.pdf`: informe actualizado de siete páginas.
- `output/ste_validacion_tierra_acsr_dove.json`: entradas, P/Q, k, distancias,
  primitivas de 12×12, contribuciones por fase, matrices de fase y secuencia
  completas de ocho escenarios, referencias PSCAD y auditoría de fuentes.
- `output/ste_validacion_tierra_acsr_pscad.csv`: 144 comparaciones elemento a
  elemento (fase y secuencia), AC/DC, dos métodos y dos estados de transposición.
- `output/ste_validacion_tierra_acsr_metodos.csv`: 72 comparaciones controladas
  P/Q menos modificado, usando exactamente las mismas entradas.
- `output/ste_validacion_tierra_acsr_pscad_numerica.csv`: 72 comparaciones con la
  nueva referencia PSCAD de integración numérica, exclusivamente transpuesta.

El informe y las salidas 7F anteriores se conservan en
`output/archivo_7f_pre_integracion_numerica/`. Las salidas 7A-7E permanecen intactas.

R/X, diferencias firmadas, diferencias absolutas y errores porcentuales se
exportan por separado, en Ω/km. Las matrices internas del JSON están en Ω/m.
La interfaz conserva la etapa 7D; este diagnóstico se ejecuta por script.

## Entradas y controles experimentales

Se leen los archivos originales de
`Datos_DOVE_PSCAD_para_Codex/referencias/comparacion_pscad/`:
`ste_carson.json`, `LEEME.txt` y ambos TXT PSCAD. Se utilizan las doce coordenadas
exactas del JSON (no una nueva orientación del cuadrado), RMG=0.00954024 m,
radio exterior=0.011765 m, separación=0.4572 m, cuatro subconductores por fase,
centros A=(-3,13), B=(3,13), C=(0,9) m, f=60 Hz, ρ=100 Ω·m, sin guardas.
Longitud declarada=100 km; no se utiliza para matrices por unidad de longitud.

Los dos métodos reciben **la misma tupla de conductores**, f y ρ. Las resistencias
originales de esos conductores siempre conservan su valor AC documentado:

```text
R_AC = 0.1859 Ω/milla / 1.609344 km/milla = 0.11551290463692038 Ω/km
R_DC = 0.102 Ω/km por subconductor, declarado por el usuario para PSCAD
Zsub_DC = copia(Zsub_AC) + diag((R_DC-R_AC)/1000)   [Ω/m]
```

DC es una sensibilidad explícita. No se reinterpreta el campo AC del JSON, no se
calcula RMG a partir del radio, no se cambia la temperatura ni se ajusta una
resistencia para reproducir la salida PSCAD. RMG y términos externos permanecen
idénticos en los escenarios AC/DC. Las contribuciones conductor, referencia
geométrica con suelo ideal y corrección de tierra se conservan por separado.

## Ecuaciones contrastadas

Se volvió a consultar Kersting, *Distribution System Modeling and Analysis*,
CRC 2002, capítulo 4 local: pp.82-84, PDF6-8, especialmente p.83 renderizada,
ecs.(4.23)-(4.30). Se preservan las fórmulas verificadas en `carson.md` y sus
correcciones de la presentación `Carson.pdf` (diap.5-8). Las notas STE
01-10-26, pp.PDF1-2, establecen la geometría real/imagen y suelo uniforme.

Para fasores exp(+jωt), g=10^-7 H/m, ω=2πf:

```text
Dij = hypot(xi-xj, hi-hj)
Sij = hypot(xi-xj, hi+hj)
dii = RMGi; dij = Dij (i≠j)
cosθij = (hi+hj)/Sij
kij = 8.565e-4 (Sij/0.3048) sqrt(f/ρ)
Zsub,ij = δij R_i/1000 + j 2ωg ln(Sij/dij) + 4ωg(Pij+jQij)   [Ω/m]

Modificado:
Pij = π/8
Qij = [7.6786-ln(Sij/0.3048)+0.5 ln(ρ/f)]/2

P/Q finito:
Pij = π/8 - kij cosθij/(3sqrt(2))
      + kij² cos(2θij)/16 [0.6728+ln(2/kij)]
Qij = -0.0386 + 0.5 ln(2/kij) + kij cosθij/(3sqrt(2))
```

Los coeficientes publicados se conservan con su redondeo. S está en pies en
la expresión original de k; aquí se convierte explícitamente desde metros.
Estos P/Q son términos finitos de una expansión, **no la integral exacta ni una
serie completa con control de convergencia**. k va de 0.038184485 a 0.059278333
en DOVE. Los umbrales preventivos de software no garantizan error bibliográfico.

Reducción de haz bajo corrientes iguales y promedio serie por transposición:

```text
T[u,p]=1/4 si el subconductor u pertenece a la fase p; 0 en otro caso
Zfase=Tᵀ Zsub T
Ztr=(Zfase+Πᵀ Zfase Π+(Π²)ᵀ Zfase Π²)/3
a=exp(j2π/3); A=[[1,1,1],[1,a²,a],[1,a,a²]]
Z012=A^-1 Zabc A; orden de secuencias 0,1,2
```

Se transforman también las matrices sin transposición y se conservan sus
acoplamientos de secuencia, sin forzarlos a cero. Para una matriz idealmente
transpuesta se verifican independientemente Z0=Zpropio+2Zmutuo y
Z1=Z2=Zpropio-Zmutuo. Las diagonales de Z012 son invariantes al promedio cíclico;
eso no elimina los acoplamientos presentes en la geometría original.

En cada CSV, Δ=STE-referencia, |Δ| se presenta además por separado y
error_R=100|ΔR|/|Rref| (análogo X). Referencia=PSCAD en el primer CSV,
Carson modificado con las mismas entradas en el segundo. Si |referencia|
no supera 10^-12 del máximo de su componente R/X, se omite el porcentaje
(campo vacío y bandera de interpretabilidad falsa), conservando valores y Δ.
Es una política de presentación de residuos de máquina, no una modificación
de matrices ni un criterio de validación física.

## Resultados reproducibles, transposición ideal [Ω/km]

Z2=Z1 en las matrices transpuestas. PSCAD se transforma desde las matrices de
fase de los TXT, no desde datos modales ni valores de línea larga.

| Método / escenario | Z0 | Z1=Z2 | Error R1 [%] | Error X1 [%] |
|---|---|---|---:|---:|
| PSCAD | .199967488+j1.424319802 | .0262542031+j.254854708 | — | — |
| Modificado / AC | .206531105379+j1.399444947365 | .028878226159+j.251347501739 | 9.994678 | 1.376159 |
| P/Q finito / AC, original 7D | .201427591918+j1.404861250641 | .028883438794+j.251347501739 | 10.014532 | 1.376159 |
| Modificado / DC temporal | .203152879220+j1.399444947365 | .025500000000+j.251347501739 | 2.872695 | 1.376159 |
| P/Q finito / DC temporal | .198049365758+j1.404861250641 | .025505212635+j.251347501739 | 2.852840 | 1.376159 |

A entradas fijas, P/Q menos modificado:

```text
ΔZ0 = -0.005103513461270 + j0.005416303275776 Ω/km
ΔZ1 = ΔZ2 = +0.000005212634644 + j≈0 Ω/km
```

La diferencia afecta principalmente al modo cero. En el truncamiento Q:

```text
Qfin-Qmod = c + β(hi+hj)
c = -0.0386 + 0.5 ln(2/0.0008565) - 7.6786/2
β = (0.0008565/0.3048) sqrt(f/ρ)/(3sqrt(2))
J = I - 11ᵀ/3
J Tᵀ (Qfin-Qmod) T J = 0
```

Por eso ΔX1=ΔX2≈0 entre estas dos aproximaciones. No demuestra que los términos
omitidos o una integral exacta den el mismo resultado. El cambio de método
no explica el error AC de aproximadamente 10 % en R1. La cancelación
propia-mutuamente acoplada ya cuantificada en 7E se conserva.

La sustitución DC desplaza cada impedancia diagonal de secuencia en
-0.003378226159230 Ω/km, sin cambiar X. Persiste un residuo frente a PSCAD,
que no se puede atribuir de manera única a retorno por tierra, impedancia
interna, RMG, reparto del haz o detalles internos del cálculo PSCAD no identificados.

## Nueva referencia PSCAD: integración numérica directa

Procedencia: valores y selección de métodos confirmados por el usuario en la
interfaz PSCAD, registrados sin alteración en
`Datos_DOVE_PSCAD_para_Codex/referencias/comparacion_pscad/pscad_integracion_numerica_confirmada.json`.
Los parámetros de entrada y resultados fueron suministrados por el usuario;
la procedencia se conserva en el JSON de referencia. Se confirma para este caso:

- Método original: Deri-Semlyen, EarthImpedanceFormula=0.
- Nuevo método: Direct numerical integration, EarthImpedanceFormula=2.
- ρ=100 Ω·m; permitividad relativa final=1; f=60 Hz; transposición activada;
  cuatro DOVE por fase y sin cables de guarda.

Matriz nueva [Ω/km]: diagonal 0.0838480984+j0.639290544; elementos mutuos
0.0575947846+j0.384430764. Se construye esta matriz como **referencia externa**,
no como una salida calculada de STE. La transformación A^-1 Zabc A y las
fórmulas escalares independientes dan:

```text
Z0 = 0.1990376676 + j1.408152072 Ω/km
Z1 = Z2 = 0.0262533138 + j0.254859780 Ω/km
```

Concuerdan con las secuencias suministradas hasta precisión numérica. No hay
resultados nuevos sin transposición: no se fabrican por inversión del promedio.
La matriz Y completa de la nueva simulación también fue suministrada [S/m]:

```text
[[1e-11+j5.20392911e-9, -j1.24409590e-9,       -j1.24409590e-9],
 [-j1.24409590e-9,      1e-11+j5.20392911e-9, -j1.24409590e-9],
 [-j1.24409590e-9,     -j1.24409590e-9,        1e-11+j5.20392911e-9]]
```

Se contrastó elemento a elemento con el TXT original transpuesto,
`DOVE_220kV_ConTransposicion_Prueba.txt`, bloque SHUNT ADMITTANCE MATRIX (Y)
[mhos/m], líneas 63-66: máximo |ΔY|=0 S/m a la precisión suministrada.
Se compara Y por unidad de longitud, sin correcciones de línea larga.
No se cambia C ni se utiliza esta igualdad como prueba de equivalencia de Z.

### Parámetros de entrada conocidos y detalle interno pendiente

Los valores suministrados del archivo de entrada PSCAD son:

| Campo PSCAD | Valor conocido |
|---|---:|
| Sag | 0 m |
| Strand Radius | 0.001858 m |
| Number of Outer Strands | 16 |
| Total Number of Strands | 26 |
| Conductor Relative Permeability | 1 |
| DCResistance | 0.102 Ω/km |
| GroundWires | 0 |
| GroundPermittivity final | 1 |
| EarthImpedanceFormula, Deri-Semlyen | 0, comprobado en interfaz |
| EarthImpedanceFormula, integración numérica | 2, comprobado en interfaz |

Se corrigen expresamente las afirmaciones anteriores de ausencia de sag,
parámetros de hebras, permeabilidad o matriz Y nueva. Son datos conocidos,
no valores por defecto ni aproximaciones inventadas. Se conservan los nombres
de los campos sin inferir otra composición de materiales o un RMG equivalente.

Lo aún desconocido es el **detalle del cálculo interno**: RMG efectivo e
impedancia interna AC que PSCAD obtiene de esas entradas, tratamiento exacto
de las hebras, correcciones internas de frecuencia y reducción efectiva del
haz. Esos detalles no se deducen únicamente de que las entradas sean conocidas.

Comparación con la integración numérica, sin modificar ninguna matriz STE:

| Método / R | Error R0 [%] | Error X0 [%] | Error R1=R2 [%] | Error X1=X2 [%] |
|---|---:|---:|---:|---:|
| Modificado / AC | 3.764834 | 0.618337 | 9.998404 | 1.378122 |
| Modificado / DC temporal | 2.067554 | 0.618337 | 2.869405 | 1.378122 |
| P/Q finito / AC | 1.200740 | 0.233698 | 10.018259 | 1.378122 |
| P/Q finito / DC temporal | 0.496540 | 0.233698 | 2.849549 | 1.378122 |

Respecto a Deri-Semlyen, el cambio PSCAD numérica menos original es:

```text
ΔZ0 = -0.0009298204 - j0.0161677300 Ω/km
ΔZ1 = ΔZ2 = -0.0000008893 + j0.0000050720 Ω/km
```

Así se aísla el cambio de método en el ensayo PSCAD reportado: afecta sobre
todo a Z0. Para P/Q finito, el error X0 baja de 1.366164 % a 0.233698 %,
mientras el error R1 AC pasa de 10.014532 % a 10.018259 %: no desaparece.
La sensibilidad DC tampoco elimina el residuo de R1 ni X1 y no reproduce
la impedancia interna de un ACSR. No se ajustan resistencias, RMG ni geometría.

## Investigación documental PSCAD y límites demostrados

Fuentes oficiales consultadas en línea el 16-10-2026:

1. [Ground Plane](https://www.pscad.com/webhelp/Master_Library_Models/Transmission_Lines_Cables/ground_plane.htm),
   secciones Description / Input Parameters: diferencia aproximación analítica
   e integración numérica; para líneas aéreas, la primera es Deri-Semlyen.
2. [Mutual Impedance with Earth Return](https://www.pscad.com/webhelp-v5-ol/EMTDC/Transmission_Lines/Mutual_Impedance_with_Earth_Return.htm),
   Aerial Lines, ecs.(8-26)-(8-29): Deri-Semlyen es la opción predeterminada.
3. [Segment Input File](https://www.pscad.com/webhelp-v5-ol/PSCAD/Transmission_Lines_and_Cables/Line_Constants_Files/Input_File.htm),
   ejemplo Line Constants Ground Data: imprime EarthImpedanceFormula=0,
   pero no incluye una correspondencia explícita código-etiqueta.
4. [Conductor Library](https://www.pscad.com/webhelp/Master_Library_Models/Transmission_Lines_Cables/Transmission_Line_Models/Using_Maintaining_a_Conductor_Library.htm),
   formatos conductor.clb y conductor_stranded.clb.
5. [Conductor Elimination](https://www.pscad.com/webhelp-pscad-v5.1.0-ol/EMTDC/Transmission_Lines/Conductor_Elimination.htm),
   Conductor Bundling: expansión de subconductores y reducción de haz.

**Selectores confirmados en la interfaz por el usuario:** 0=Deri-Semlyen y
2=integración numérica directa, para el caso ensayado. Esta nueva evidencia
sustituye la conclusión anterior de selector no verificado, conservada en el
informe histórico. No se presenta como tabla universal para todas las versiones.
La documentación inicial por sí sola no permitía deducir la correspondencia.

La ayuda de bibliotecas se conserva como referencia general. Para este caso,
los campos de hebras, radio y permeabilidad sí se conocen y figuran en la tabla
anterior. No se confunde la documentación genérica de formatos con los datos
efectivamente suministrados. Continúan sin identificarse el RMG efectivo y la
impedancia interna calculados, ni el tratamiento interno exacto de las hebras.

Geometría, resistividad, número de subconductores y R_DC PSCAD están declarados
en LEEME/conversación; f y matrices Z están efectivamente impresos en los TXT.
El JSON especifica los datos STE, no demuestra los parámetros internos PSCAD.
No se convierten los valores por defecto de la ayuda en entradas comprobadas.

La ayuda de reducción de haz menciona corrientes iguales, tensión común y Kron.
Esto no basta para demostrar la identidad algebraica de su algoritmo concreto
con TᵀZT. El escenario de reparto desigual de 7E conserva sus hipótesis de
gradiente longitudinal común; no se rebautiza como algoritmo de PSCAD.

Para cerrar las cuestiones físicas restantes serían útiles la versión de
PSCAD/LCP y la descripción de sus algoritmos internos o sus resultados
intermedios. No se vuelven a solicitar como desconocidos los datos de entrada
ya suministrados. No se declara equivalencia con ninguno de los dos métodos STE.

## Pruebas y conservación

`tests/test_earth_validation.py`: 16 casos automatizados, incluyendo
parametrizaciones. Comprobación escalar independiente en unidades inglesas de
ambos métodos (con alturas y RMG diferentes), suma explícita de los 16 pares
de cada par de haces, DFT independiente, invariancia cíclica, simetría,
conversión exacta de longitudes, cambio DC exclusivamente diagonal, identidad
del ΔQ proyectado, conservación exacta de 7D/7E, errores por componente,
serialización y PDF completo de siete páginas. Se añaden la verificación
independiente de las secuencias numéricas suministradas y la conservación de
ambas referencias, con comprobación de todos los errores nuevos.

Suite completa actualizada: **462 pruebas aprobadas en 136.52 s**; registro
`tmp/pytest-earth-numerical-full.log`. Las 16 pruebas focalizadas también pasan
(4.65 s). Se revisaron las siete páginas del PDF renderizado, sin cortes.
Los ocho escenarios STE y las matrices de referencia PSCAD originales son
exactamente iguales a los del JSON 7F archivado. Solo cambian las comparaciones,
los metadatos de confirmación y la presentación; no las ecuaciones de Carson.

Esta corrección documental posterior conserva además todos los valores de
comparaciones y errores de la actualización de integración numérica: modifica
solo trazabilidad de entradas conocidas, documentación y representación de Y.
Se aprobaron **17 pruebas focalizadas en 2.84 s**, incluido el contraste
elemento a elemento de la Y suministrada con el TXT transpuesto original.
Registro: `tmp/pytest-earth-traceability.log`. Se verificó la igualdad exacta
de las matrices, escenarios, errores y CSV con su versión anterior a esta
corrección. Los módulos físicos conservan sus hashes; las siete páginas del
PDF regenerado fueron revisadas visualmente.
Se conserva un inventario SHA-256 de archivos existentes antes de la etapa en
`tmp/earth_validation_baseline.json`: **129 archivos previos sin cambios**,
incluidos módulos, pruebas, datos e informes. Las pruebas
no sustituyen la verificación del modelo físico de PSCAD.
