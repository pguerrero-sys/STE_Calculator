# Interfaz unificada y selección de resistencia AC

Revisión: 17-10-2026. Se trabaja sobre la versión actual posterior a 7F y a
la corrección de transposición automática, sin sustituir los motores validados.

## Inspección y fuentes

Se inspeccionaron todos los módulos de `ste_calculator/`, sus pruebas y los
registros bibliográficos de geometría, inductancia, capacitancia, haces,
transposición, doble circuito, Carson, Kron, secuencias y comparaciones 7F.

Fuentes nuevas consultadas:

- `Tablas_ACSR.pdf`, dos páginas: p.1, cabeceras resistencia DC20 [Ω/km],
  resistencia AC60Hz [Ω/km] a 25/50/75 °C y capacidad [A]; p.2, diámetro
  nominal [mm], RMG [mm], calibre y construcción. Se extrajo el texto de
  ambas páginas y se inspeccionaron sus imágenes completas. Atribución impresa:
  Y.A.R.R., UTP. Las condiciones térmicas de la capacidad no están especificadas.
- `Notas de sistemas de transmision.pdf`, pp.PDF109–111: contexto de AC/piel,
  criterio de porcentaje de carga y ejercicio de resistencia por fase EAGLE.
  Se extrajeron las páginas y se renderizaron 110–111. Se usa la selección
  tabular; no se implementa un modelo térmico, de piel o de resistividad del material.

Las fronteras de 25 % y 75 % están abiertas en las desigualdades de las notas.
Se adopta expresamente el criterio pedido por el usuario: 25 % y 75 % pertenecen
al intervalo que selecciona 50 °C. No es una nueva ley térmica.
Las frases finales de p.111 sobre comparaciones XL/XC no se utilizan para
deducir temperaturas ni propiedades: no forman parte de este procedimiento.

La transcripción incluye 67 filas con las dos filas originales preservadas en
`acsr_catalog.json`. Se conserva la columna Ω/km de resistencias y la columna
mm de dimensiones. Algunas filas tienen discrepancias entre km/milla o mm/pies:
se etiquetan sin corregirlas silenciosamente. Un RMG con unidades discordantes
no se emplea automáticamente para L: requiere un valor personalizado verificado.
No se identifica la tabla como un catálogo vigente de fabricante.

## Método y dimensiones

```text
S_total [MVA] = P_total [MW]/fp si se ingresa potencia activa
I_total [A] = 1000 S_total [MVA]/(sqrt(3) V_LL [kV])
I_circuito = I_total/Nc
I_sub,fase = I_circuito/n_fase
carga_fase [%] = 100 I_sub,fase/I_nominal_tabla

carga <25: seleccionar R_AC(25 °C)
25 <= carga <=75: seleccionar R_AC(50 °C)
carga >75: seleccionar R_AC(75 °C)
R_fase [Ω/km] = R_AC,subconductor [Ω/km]/n_fase
R_sistema,p [Ω/km] = 1/sum_c(1/R_fase,c,p), solo conexión paralela declarada
```

La potencia MVA ya es aparente y no se divide nuevamente por fp. Se presupone
carga trifásica equilibrada y reparto uniforme entre circuitos/subconductores.
Con haces distintos se informa esa hipótesis; no se resuelve reparto real.
Los valores por fase siguen identificando el circuito; R_sistema es un resultado
distinto y no autoriza reducir matrices L/C ni eliminar acoplamientos.

Nombre del modo: **Selección automática según criterio académico de carga**.
Segundo modo: temperatura tabulada especificada (25/50/75 °C). No se interpola
por defecto. Si falta una resistencia/capacidad necesaria se da un diagnóstico,
sin inventarla. R_AC60Hz no se extrapola a otra frecuencia. Para un personalizado
se debe documentar su propia frecuencia y fuente de resistencia.

## Comprobación DOVE

Tabla p.1, fila DOVE: calibre 556.5 kcmil, 26 Al+7 acero, 725 A;
R_DC20=.1007 Ω/km; R_AC25=.103, R_AC50=.113, R_AC75=.123 Ω/km.

220 kV, 250 MVA totales, fp=.9, 60 Hz:

- I_total=656.0798513518475 A.
- I_sub=164.0199628379619 A, tanto Nc=1,n=4 como Nc=2,n=2.
- Carga=22.6234431500637 %; selecciona 25 °C y .103 Ω/km.
- Nc=1,n=4: R_fase=.02575 Ω/km.
- Nc=2,n=2: R_fase=.05150 Ω/km por circuito.
- Solo al declarar ambos circuitos en paralelo: .02575 Ω/km por fase equivalente.

La página 2 da diámetro DOVE=23.546 mm y RMG=9.57072 mm. Los ensayos históricos
utilizan diámetro 23.530 mm y RMG 9.54024 mm. Se conservan ambas fuentes; el
caso **DOVE C6 · regresión histórica sin suelo** usa entradas individuales
con radio .011765 m y RMG .00954024 m para conservar la comprobación anterior.
La selección de R académica usa la tabla nueva, sin reescribir entradas ni
artefactos históricos. R_DC PSCAD=.102 Ω/km y R_AC STE7F=.1859 Ω/milla siguen
siendo datos separados; no se presenta equivalencia física ACSR completa.

C6 histórica sin suelo, transposición Z3×Z3, n=2: se comprueban dentro de
5e-7 nF/km los coeficientes [10.029643,-2.962967,10.029575,-2.962933,-1.367903].
Conserva simetría, rango 5, C·1≈0, todos los acoplamientos y sus nueve tramos.
Es una regresión del método de potenciales a carga común, no validación universal
de un equivalente shunt distribuido. Véanse `carson.md` y `doble_circuito.md`.

## Arquitectura y conservación

- `conductor_library.py` y `acsr_catalog.json`: datos con fuente por parámetro.
- `resistance.py`: corriente, carga, selección tabular y equivalentes resistivos.
- `study.py`: entradas tipadas, orquestación de motores previos, variantes de
  suelo/transposición, Z/Y, secuencias y comparación con el circuito 1 aislado.
- `workspace_ui.py`: presentación compacta con cuatro secciones; controla
  entradas comunes, resultados y recalculado explícito.
- `study_report.py`: resumen compacto, anexo completo y registro JSON.
- `app.py`: entrada mínima de la nueva presentación.

Permanecen intactos los módulos de geometría, unidades, capacitancia,
inductancia, haces, ecuaciones de Carson, Kron, secuencias y transposición
automática de la entrega anterior. La orquestación reconstruye geometrías por
tramo y reutiliza sus funciones. No se reemplaza equipotencialidad capacitiva
por un radio equivalente ni se aproxima ACSR como macizo automáticamente.

La nueva opción personalizada maciza exige confirmación explícita de conductor
circular, μr=1 y corriente uniforme; usa el resolver RMG existente. Los ACSR
siempre usan un RMG tabulado/documentado.

Carson se calcula separado de L/C; auxiliares fijos y fases/haces completos
siguen las nueve combinaciones cuando se transpone un doble circuito. Kron
solo se aplica con condiciones y justificación ΔVaux=0 confirmadas. Aislados
y conexiones desconocidas aparecen en la primitiva sin eliminación automática.
Se conservan bloques Zpp/Zpn/Znp/Znn y la matriz Z012 con acoplamientos.

Zgeom=diag(R_fase/1000)+j2πfL [Ω/m], Y=j2πfC [S/m]. No se añade a Zgeom la
corrección Carson ni se usa esta última para modificar C. Sin suelo se mantienen
las restricciones de suma cero. Los equivalentes positivos se muestran solo si
la transformación verifica desacoplamiento: una matriz diagonal equivalente
se rotula como operador restringido, nunca como sustituto de la matriz física.

## Navegación y resultados

Únicamente cuatro secciones principales:
Configuración y geometría / Resultados / Desarrollo matemático / Bibliografía y exportación.
Resultados tiene un selector de cinco apartados, no pestañas principales nuevas.
Solo hay una geometría, una frecuencia, un conductor global y una configuración
global de haces; editar por fase es optativo. El gráfico responde a las entradas.
El usuario configura y pulsa Calcular; al cambiar entradas los resultados se
ocultan hasta recalcular, evitando salidas antiguas presentadas como actuales.

Las permutaciones, posiciones internas y fracciones aparecen exclusivamente en
Desarrollo matemático como tabla de solo lectura. No se editan ni se introducen
números de tramos. Los pesos se normalizan internamente con el generador previo.
Se compara con/sin suelo dentro de STE con entradas idénticas. La referencia
PSCAD es un contraste externo con fuente y R/X separados, nunca una medida
automática del efecto suelo. No se compara una referencia 3×3 con seis fases.

El resumen omite las primitivas y la lista de tramos. En el caso exportado tiene
5 páginas. El anexo completo de los dos modelos seleccionados incluye todos los
tramos y sus primitivas: es extenso (229 páginas en el caso de comprobación).
Ese volumen solo se genera al pedir **anexo matemático completo**; la aplicación
no lo genera cuando se solicita un resumen. Los controles de descarga se invalidan
al cambiar el estudio o los modelos para evitar exportaciones obsoletas.

## Pruebas

Suite previa: **481 aprobadas en 89.91 s**, `tmp/pytest-refactor-baseline.log`.
No se detectaron fallos previos automatizados. Se conservan todos los tests.

Las pruebas de UI anteriores verifican los adaptadores previos en
`tests/fixtures/validated_app.py`, copia de la entrada vigente antes de este
cambio, con ruta bibliográfica ajustada. Es un montaje de regresión únicamente,
no una segunda aplicación publicada ni una restauración de cálculos antiguos.
Sus expectativas de siete pestañas no se usan como prueba de la navegación nueva.
Los cuatro archivos de pruebas que definían APP cambian solo esa ruta; sus
aserciones originales permanecen.

`test_workspace_app.py` verifica directamente la nueva `app.py`: cuatro secciones,
calcular explícitamente, invalidación al cambiar entradas, corriente/R DOVE,
doble circuito, paralelo resistivo, ambos suelos, nueve tramos solo en desarrollo,
regresión C6 y exportación resumida. Las otras pruebas nuevas contrastan todos
los modelos con los motores originales, fronteras 25/75, MW/MVA, unidades,
datos ausentes, frecuencia, fuentes, Kron, simetría y PDFs separados.

Primera ejecución completa: **519 aprobadas en 113.91 s**.
La ampliación final añadió cinco comprobaciones. Detectó un fallo nuevo de
serialización JSON de escalares complejos al activar Carson (523 aprobadas,
una fallida); se corrigió la conversión recursiva de escalares NumPy y complejos.
La prueba de interfaz reproduce este caso y conserva las comprobaciones de
auxiliares no especificados. No se retiró ninguna prueba.

Ejecución final completa: **524 aprobadas en 109.04 s**,
`tmp/pytest-refactor-final.log`. Smoke HTTP: health=200 y página=200,
`tmp/smoke-refactor.log`. Se inspeccionó la aplicación real en el navegador,
incluidas las cuatro secciones y la tabla DOVE con Rfase=0.02575000 Ω/km.
Se revisaron visualmente las cinco páginas del resumen y las páginas del anexo
mediante renderización, sin columnas cortadas ni superposición de tablas.
Python ejecutado: 3.12 del entorno local; no se ejecutó por separado Python 3.11.

## Límites pendientes

Solo uno o dos circuitos eléctricos y haces regulares de 1–4 subconductores.
No se habilita triple circuito aunque el generador de planes sea extensible.
No se implementa un modelo térmico, ni se infiere temperatura real de la carga.
No hay interpolación automática de tablas, cálculo de resistencia desde materiales,
reparto desigual real, skin/proximidad propio ni corriente de acero reconstruida.
Carson sigue siendo aproximado (modificado/PQ finito), no integración completa.
Las fuentes de capacidad nominal no describen todas las condiciones ambientales.
No se certifica equivalencia exacta con PSCAD ni diseño térmico de una línea.


## Inventario de la actualización

- `app.py`: entrada mínima de la interfaz vigente.
- Nuevos `ste_calculator/workspace_ui.py`, `study.py`, `resistance.py`,
  `conductor_library.py` y `study_report.py`: presentación, orquestación, resistencia,
  datos con fuente y exportaciones, respectivamente.
- `referencias/acsr_catalog.json`: transcripción de las 67 filas de la tabla local.
- `scripts/unified_dove_case.py`: reproducción numérica y exportaciones DOVE.
- Nuevos `tests/test_resistance.py`, `test_study.py`, `test_workspace_app.py`
  y `test_study_report.py`; fixture de presentación anterior y ajuste de ruta APP
  en los cuatro adaptadores históricos, sin borrar sus aserciones.
- `README.md`: instrucciones vigentes. La guía anterior queda en
  `referencias/registro_interfaz_previa.md`.
- Nuevas salidas `output/ste_estudio_unificado_dove.json`,
  `output/pdf/ste_resumen_dove.pdf`, `output/pdf/ste_anexo_dove.pdf`
  y `output/ste_interfaz_unificada.png`.

La comparación SHA-256 de 71 archivos existentes del inventario previo
(módulos matemáticos, entrada y resultados históricos) encuentra cambiado
únicamente `app.py`: `tmp/refactor_integrity_final.json`. La documentación
histórica de etapas anteriores conserva su fecha y alcance; no describe la
navegación vigente. Las matrices y los resultados exportados de 7A–7F no se
reescriben al generar los informes nuevos.
