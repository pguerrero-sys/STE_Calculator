# STE Calculator · Interfaz unificada

Aplicación local para parámetros de líneas aéreas trifásicas de circuito sencillo
y doble circuito. Python 3.11+, Streamlit, NumPy, SciPy y Plotly.

## Ejecutar en Windows

Desde PowerShell, en esta carpeta:

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Abre http://localhost:8501. También puedes usar `iniciar.bat` o `iniciar.ps1`.
Para detener el servidor, pulsa Ctrl+C en su terminal. El servidor local existente
usa 127.0.0.1:8501.

Si falta el entorno:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## Flujo de trabajo vigente

1. **Configuración y geometría**: introduce tensión, frecuencia, longitud,
   potencia total MVA o MW, fp y carga. Selecciona uno o dos circuitos, conductor
   de biblioteca o personalizado, haces globales y coordenadas. La figura se
   actualiza con las entradas. La edición por fase es opcional.
2. Elige **Sin transposición** o **Transposición ideal completa automática**:
   tres ciclos para un circuito, nueve combinaciones independientes para dos.
   No se editan tramos ni fracciones. Pulsa **Calcular parámetros**.
3. **Resultados**: el selector muestra Inductancia, Capacitancia, Resistencia,
   Impedancia y admitancia o Comparaciones. Puedes comparar suelo ideal y sin
   suelo manteniendo las mismas entradas. Las matrices conservan todas las fases.
4. **Desarrollo matemático**: desplegables de corriente/resistencia, tabla de
   tramos de solo lectura, distancias/imágenes, primitivas y Carson/Kron/secuencias.
5. **Bibliografía y exportación**: consulta fuentes, descarga el estudio JSON,
   prepara un informe resumido o solicita explícitamente el anexo completo.

El resumen omite primitivas y tramos; el ejemplo DOVE produce 5 páginas.
El anexo incluye los cálculos disponibles de todos los tramos de los modelos
solicitados y puede ser extenso. Nunca se genera por defecto.

Si cambias las entradas, los resultados se ocultan hasta volver a calcular.
Cambiar unidades o la vista de resultados no requiere repetir las entradas.

## Biblioteca y resistencia AC

Se transcriben 67 conductores de `referencias/Tablas_ACSR.pdf`, con fuente por
fila y unidad. Se conservan las filas originales en `referencias/acsr_catalog.json`.
Las discrepancias entre columnas publicadas se señalan; no se corrigen con datos
inventados. RMG discordante requiere un dato personalizado verificado para L.

**Selección automática según criterio académico de carga**:

- I_total=S_total/(√3 V_LL); para MW, S=P/fp.
- I_sub=I_total/(N_circuitos·n_subconductores_por_fase), reparto uniforme.
- Carga=100 I_sub/I_nominal.
- <25 %: R_AC25; 25–75 % inclusive: R_AC50; >75 %: R_AC75.

Es un criterio didáctico de las notas pp.PDF109–111, no una predicción térmica.
La segunda opción usa una temperatura tabulada especificada: 25, 50 o 75 °C.
No se interpola por defecto ni se extrapolan los datos de 60 Hz a otra frecuencia.
La capacidad nominal tabulada no constituye un análisis térmico de diseño.

R_haz=R_AC/n. El equivalente resistivo del sistema se calcula solo al declarar
circuitos en paralelo; esa declaración no reduce automáticamente las matrices L/C.

DOVE: 220 kV, 250 MVA totales, fp=0.9, 60 Hz da I_total=656.07985 A e
I_sub=164.01996 A para sencillo con n=4 o doble con n=2. Carga=22.62344 %,
R_AC25=0.103 Ω/km; R_fase=0.02575 y 0.05150 Ω/km respectivamente. Doble en
paralelo: 0.02575 Ω/km por fase equivalente.

La tabla nueva da diámetro DOVE=23.546 mm y RMG=9.57072 mm. El caso histórico
C6 conserva su radio 0.011765 m y RMG 0.00954024 m mediante entradas por fase
con fuente explícita. Sus capacitancias verificadas permanecen intactas.
R_DC20 de tabla=0.1007 Ω/km, R_DC PSCAD histórica=0.102 Ω/km y R_AC histórica
7F=0.1859 Ω/milla son fuentes diferentes y se mantienen separadas.

## Modelos y límites

- L/C: motores anteriores conservados; suelo ideal o proyección de suma global
  cero sin suelo. Sin suelo C es singular y no es capacitancia absoluta a tierra.
- Haces regulares de 1 a 4 subconductores, equipotencialidad capacitiva y
  reparto uniforme inductivo. ACSR utiliza RMG documentado. El modelo macizo
  requiere confirmación explícita en el conductor personalizado.
- Capacitancia transpuesta: promedio de P efectiva antes de invertir, bajo la
  hipótesis didáctica de carga común. No es un equivalente shunt universal.
- Z geométrica=diag(R_fase)+jωL; Y=jωC. Se identifican unidades por metro/km
  y restricciones del modelo. Los equivalentes positivos solo se muestran cuando
  la transformación verifica desacoplamiento; no reemplazan las matrices completas.
- Carson modificado y P/Q finito siguen separados. Kron requiere ΔVaux=0
  confirmado y justificado. Se conservan aislados/desconocidos en la primitiva,
  sin reducirlos automáticamente. Se muestran matrices Z012 completas.
- Contrastes externos PSCAD disponibles o JSON suministrado: R/X, errores y
  secuencias por separado. Las referencias DOVE son 3×3 y no se comparan con 6×6.
- No hay triple circuito eléctrico, integración exacta de Carson propia, cálculo
  térmico, reparto real entre subconductores, propagación distribuida ni equivalencia
  física completa con ACSR PSCAD. El generador combinatorio es extensible a N.

## Pruebas y reproducción

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe scripts\smoke_test.py
.\.venv\Scripts\python.exe scripts\unified_dove_case.py
```

El último comando genera `output/ste_estudio_unificado_dove.json`,
`output/pdf/ste_resumen_dove.pdf` y `output/pdf/ste_anexo_dove.pdf` con datos
calculados, sin utilizar salidas esperadas como constantes del motor.

Los módulos matemáticos y los scripts históricos 7A–7F se conservan. Las pruebas
de los adaptadores de la presentación previa se ejecutan sobre
`tests/fixtures/validated_app.py` (solo pruebas, sin publicarlo como aplicación).
`tests/test_workspace_app.py` prueba directamente la nueva `app.py` de cuatro
secciones. No se eliminan pruebas antiguas ni se presentan las del adaptador
histórico como evidencia de la navegación nueva.

Detalles técnicos y resultados de validación:
[resistencia_y_refactorizacion.md](referencias/resistencia_y_refactorizacion.md).
La guía previa se conserva como registro en `referencias/registro_interfaz_previa.md`.
