# Etapa 7B: eliminación de neutros y cables de guarda

## Fuentes revisadas antes de implementar

- Kersting, *Distribution System Modeling and Analysis*, CRC Press, 2002,
  copia `Cap 4 Kersting - Ecuaciones Carson.pdf`: §4.1.5-4.1.6,
  páginas impresas 86-87 (PDF 10-11), ecuaciones (4.45)-(4.54), figura 4.5.
  Ejemplo 4.1, impresas 92-94 (PDF 16-18), figura 4.7. Extracción de texto
  y revisión visual de la derivación y los resultados publicados.
- Presentación del curso `Carson.pdf`, diapositivas 9-11: matriz primitiva,
  neutro multitierra con Vng=V'ng=0 y eliminación algebraica. Se revisó el texto.
- `Notas de Clase/Notas de Clase/Notas clase STE 01-10-26.pdf`, páginas PDF
  3-6, revisión visual: matrices ampliadas y parámetros de neutros de cables
  concéntricos; la página 6 deja un ejemplo sin terminar. No es el ejemplo
  aéreo 4.1 ni justifica aplicar parámetros de cables subterráneos a guardas.
- Notas del 06-10-26, páginas PDF 1-2, revisión visual: separación de parámetros
  por unidad de longitud y parámetros totales; el equivalente monofásico
  allí supuesto requiere equilibrio/transposición, no se aplica a esta matriz.

Las correcciones de Carson de etapa 7A permanecen en `carson.md`. La errata
de p.94 en la partición (término bc impreso con dos j y 0.0943) no se utiliza:
se toma la primitiva simétrica de p.93 y las distancias físicas de fig.4.7.
La afirmación de la presentación sobre acoplamiento «exacto» se refiere a la
eliminación algebraica del modelo elegido: no vuelve exacto a Carson modificado.

## Ecuaciones y condición eléctrica

Todos los Z son complejos por unidad de longitud, en una única unidad coherente.
Las fases p se conservan; los auxiliares n se eliminan conjuntamente, incluyendo
los acoplamientos entre auxiliares. No hay conjugación en las transpuestas.

```text
Z = [[Zpp, Zpn], [Znp, Znn]]                         (4.45)-(4.48)
ΔVp / longitud = Zpp Ip + Zpn In                     (4.49)
ΔVn / longitud = Znp Ip + Znn In                     (4.50)
Si ΔVn=0: In = -inversa(Znn) Znp Ip                  (4.51)
Zreducida = Zpp - Zpn inversa(Znn) Znp               (4.52)-(4.54)
```

En interfaz y reportes se muestra ΔV/ℓ, con ℓ la longitud del tramo uniforme,
cuando Z está por unidad de longitud. La hipótesis del libro es neutro multitierra ideal, a potencial
de tierra en ambos extremos de cada sección. Una guarda puede eliminarse
solamente si esa misma condición eléctrica está justificada. El tipo de
conductor no establece su conexión. Cada auxiliar necesita conexión y
justificación declaradas, además de una declaración explícita global.

Un conductor aislado no tiene por qué satisfacer ΔVn=0. Si su condición es
In=0, las fases utilizan Zpp bajo esa condición, no el complemento de Schur.
Conexiones desconocidas bloquean solo Kron: la primitiva continúa disponible.
La primera versión requiere que TODOS los auxiliares añadidos satisfagan la
condición de eliminación; no realiza eliminaciones parciales implícitas.
Resistencias de electrodos, elevación de potencial de torre, tierras discretas,
capacitancia de guardas, conexiones en un solo extremo y corrientes de fuga
requieren un modelo de frontera distinto, no implementado.

## Ensamblaje e implementación numérica

Se reutiliza Carson sin cambiar sus ecuaciones ni sus umbrales. R_AC y RMG
de cada auxiliar son entradas técnicas independientes, con fuente obligatoria.
No se infieren propiedades por material, ni RMG a partir de radio para ACSR.
Cuando el radio exterior no está disponible solo se comprueba coincidencia de
centros; no se certifica ausencia de contacto físico a partir del RMG.

La primitiva resuelve todos los subconductores reales y auxiliares.
Con haces se conserva la aproximación previa I_sub=I_fase/n:

```text
A = diag(T, Iaux); Zterminal = Aᵀ Zsub A
Znn Y = Znp; corrección = Zpn Y; Zred = Zpp - corrección
```

Esta agregación previa de haces no es una resolución del reparto de corrientes
por equipotencialidad longitudinal. Es distinta de Kron y se identifica como
aproximación. No se promedian tramos ni se aplica la transposición de otros
paneles. Para dos circuitos se conservan seis fases y todos sus acoplamientos;
no hay equivalente 3×3 ni conexiones entre circuitos inferidas.

Se utiliza `numpy.linalg.solve`, no la inversa explícita. Se rechaza Znn singular
o con cond>10^12 (política numérica del software, no condición física). Se informa
el residuo de Znn Y=Znp. Simetría compleja significa Z=Zᵀ, no Z=Zᴴ.
Ω/m→Ω/km: ×1000; Ω/m→Ω/milla: ×1609.344. Y y la respuesta In/Ip no tienen unidades.
No se necesita longitud de línea para matrices por unidad de longitud.

## Ejemplo reproducible 4.1 completo

f=60 Hz; ρ=100 Ω·m; Carson modificado; sin transposición.
Coordenadas en pies convertidas exactamente con 1 ft=0.3048 m:

| Conductor | X [ft] | h [ft] | R_AC [Ω/milla] | RMG [ft] |
|---|---:|---:|---:|---:|
| A | 0 | 29 | 0.306 | 0.0244 |
| B | 2.5 | 29 | 0.306 | 0.0244 |
| C | 7 | 29 | 0.306 | 0.0244 |
| n | 4 | 25 | 0.592 | 0.00814 |

Las fases son ACSR Linnet 336400 26/7 del ejemplo. Son datos bibliográficos,
no una ficha vigente ni validación de una instalación. Los radios físicos
opcionales del constructor previo proceden del ejemplo 5.1 p.114; no afectan
la fórmula de Carson modificada ni se utilizan como RMG.

Primitiva publicada p.93 [Ω/milla]:

```text
[[.4013+j1.4133, .0953+j.8515, .0953+j.7266, .0953+j.7524],
 [.0953+j.8515, .4013+j1.4133, .0953+j.7802, .0953+j.7865],
 [.0953+j.7266, .0953+j.7802, .4013+j1.4133, .0953+j.7674],
 [.0953+j.7524, .0953+j.7865, .0953+j.7674, .6873+j1.5465]]
```

Reducida publicada p.94 [Ω/milla]:

```text
[[.4576+j1.0780, .1560+j.5017, .1535+j.3849],
 [.1560+j.5017, .4666+j1.0482, .1580+j.4236],
 [.1535+j.3849, .1580+j.4236, .4615+j1.0651]]
```

Las pruebas contrastan componentes real e imaginaria con tolerancia absoluta
6×10^-5 Ω/milla por redondeo publicado a cuatro decimales y constantes truncadas.
Los valores publicados son referencias de contraste, nunca salidas fijas.
El script `scripts/kron_case.py` calcula nuevamente desde coordenadas, R y RMG.
La comparación se limita a las matrices primitivas y reducidas solicitadas,
sin añadir transformación de secuencias ni afirmar equivalencia PSCAD.

## PDF y separación de modelos

Las fórmulas se dividen en pasos lógicos; el exportador PDF escribe texto
ajustable y tablas R/X independientes con partición de columnas. No captura
fórmulas LaTeX como imágenes anchas. El estilo de impresión del navegador
también permite contenido matemático visible, aunque los informes descargables
son la vía reproducible para matrices completas. Kron solo modifica el resultado
serie correspondiente: capacitancia, promedios P/C e inductancia ideal conservan
sus modelos y sus resultados. No se introduce Kron en sus ecuaciones.
