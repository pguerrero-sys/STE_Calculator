# Etapa 7A: impedancia serie con retorno por tierra de resistividad finita

## Fuentes consultadas y correcciones

- Presentación `Carson.pdf`, 18 diapositivas, fechada 29-09-2026: 4-8
  (hipótesis, ecuaciones originales y modificadas), 9 (primitiva), 10-11
  (Kron, NO implementado), 17 (referencias). Se extrajo su texto y se
  inspeccionaron las diapositivas 5-8 renderizadas.
- `Cap 4 Kersting - Ecuaciones Carson.pdf`, copia local de Kersting,
  *Distribution System Modeling and Analysis*, CRC Press, 2002. Páginas
  impresas 81-85, PDF 5-9: §4.1.3-4.1.4, ecs. (4.20)-(4.42).
  Páginas 92-93, PDF 16-17: ejemplo 4.1 y figura 4.7. La misma copia
  contiene §5: impresa 114, PDF 38, diámetros y alturas del ejemplo 5.1.
  Se extrajeron estas páginas y se revisaron las ecuaciones y el ejemplo
  visualmente. Las páginas son las de esta copia local; la presentación
  cita una tercera edición de 2012, que no se usa para trasladar numeración.
- `Notas clase STE 01-10-26.pdf`, PDF 1-2: hipótesis de suelo uniforme,
  geometría real/imagen y remisión a las ecuaciones del material de clase.
  Revisión visual. `Notas clase STE 29-09-26.pdf`, PDF 1: resistencia de
  subconductores y R/n; no se adoptan los datos EAGLE como propiedades generales.

La diapositiva 6 difiere de Kersting (4.23)-(4.24): imprime k² y factores
incorrectos en los primeros términos. Se usa la página impresa 83 de Kersting.
En p.84 (4.37) falta una j en una línea impresa; la expresión propia debe
ser compleja, coherente con (4.29), (4.39) y (4.41). En p.84 la remisión
al P de (4.27) debe ser (4.26). La matriz particionada de p.94 tiene una
errata en un término bc; se contrasta la primitiva simétrica de p.93.

## Alcance de los métodos implementados

Solo líneas aéreas. Suelo homogéneo, plano e infinito, ρ constante,
permeabilidad de modelo μ0=4π·10^-7 H/m, sin efectos de extremos ni
corrientes de desplazamiento del suelo. R es la resistencia AC suministrada
para la frecuencia y condiciones de trabajo; no se calcula a partir de
material, temperatura o diámetro. RMG es un dato inductivo documentado,
no el radio capacitivo. ACSR nunca se sustituye automáticamente por macizo.

Método 1: **Carson modificado**, (4.26)-(4.27), simplificado en (4.37)-(4.40).
Método 2: **expresiones P/Q finitas de Kersting (4.23)-(4.24)**, con términos
de P hasta k² ln(k) y de Q hasta k. Es otra aproximación, no la evaluación
de toda la serie de Carson. Las fuentes locales no proporcionan un algoritmo
completo con criterio de convergencia; no se implementa ni se anuncia una
solución integral/completa, ni una equivalencia exacta con PSCAD.

Dominio: entradas finitas, f>0, ρ>0, R_AC≥0 y RMG>0; conductores por encima
del suelo, centros distintos. Si se dispone de radio exterior, se valida
también contacto/solapamiento y RMG≤radio mediante la geometría existente.
Se informa k máximo. Como política preventiva de software, k>0.1 genera
aviso y k≥1 bloquea estas aproximaciones de pequeño k. Estos umbrales NO
son una cota de error de Kersting ni garantizan una precisión porcentual.
Fuera de 50-60 Hz se advierte que no se ha validado la aproximación para
esa frecuencia. No se extrapola ρ→0 como si el truncamiento fuese exacto.

## Convenciones SI y fórmulas

Fasores exp(+jωt), impedancia inductiva +jX. Simetría Z=Zᵀ, no Z=Zᴴ.
1 ft=0.3048 m; 1 mile=1609.344 m; 1 mile=1.609344 km, exactos.
G_milla=0.1609344·10^-3 y g=G_milla/1609.344=10^-7 H/m.
El rótulo Ω/mile de G en las fuentes es dimensionalmente incompleto:
al multiplicarse por ω, el factor debe interpretarse con dimensión inductiva.

Para cada par, incluyendo el propio:

```text
Dij = hypot(xi-xj, hi-hj)                        [m]
Sij = hypot(xi-xj, hi+hj)                        [m]
cos θij = (hi+hj)/Sij
kij = 8.565e-4 · (Sij/0.3048) · sqrt(f_Hz/ρ_ohm_m)
dii = RMGi; dij = Dij para i≠j
ω = 2πf
```

La constante 8.565e-4 de (4.25) requiere S en PIES. Introducir S en metros
sin convertirla produce otro modelo. f y ρ en los logaritmos son valores
numéricos expresados en Hz y Ω·m, las unidades de calibración del libro.

Ensamblaje propio y mutuo de (4.29)-(4.30), convertido a Ω/m:

```text
Zbase,ij = δij R_AC,i/1000 + j 2ωg ln(Sij/dij)
ΔZtierra,ij = 4ωg (Pij + j Qij)
Zij = Zbase,ij + ΔZtierra,ij                    [Ω/m]
Z_ohm_km = 1000 Z_ohm_m
```

Zbase es la referencia geométrica con imágenes de suelo ideal MÁS la
resistencia del conductor. ΔZtierra es su corrección por retorno finito.
La separación reactiva depende de esta referencia; no es una asignación
única de inductancia intrínseca al material del suelo. Se muestran además
Rconductores diagonal y jXgeom. El flujo interno ya está incluido en RMG;
no se suma otra inductancia interna.

Carson modificado:

```text
Pij = π/8
2Qij = 7.6786 - ln(Sij_ft) + 0.5 ln(ρ/f)
Zii = R_AC,i/1000 + π² f g
      + j 4π f g [ln(0.3048/RMGi_m)+7.6786+0.5 ln(ρ/f)]
Zij = π² f g
      + j 4π f g [ln(0.3048/Dij_m)+7.6786+0.5 ln(ρ/f)], i≠j
```

7.6786 es el redondeo publicado. Se usa esta convención para contrastar
los ejemplos; no se mezclan silenciosamente coeficientes de distinta precisión.
A 60 Hz y ρ=100 Ω·m, el libro redondea adicionalmente los factores a
0.09530, 0.12134 y 7.93402 en Ω/mile, ecs. (4.41)-(4.42).
En el método modificado S cancela del total: variar alturas a iguales
distancias reales cambia la descomposición pero no Z. Es una limitación
de la aproximación, no una propiedad exacta del retorno por tierra.

P/Q de (4.23)-(4.24), sin añadir términos no publicados:

```text
Pij = π/8 - kij cosθij/(3√2)
      + kij² cos(2θij)/16 · [0.6728 + ln(2/kij)]
Qij = -0.0386 + 0.5 ln(2/kij) + kij cosθij/(3√2)
```

Estos P y Q son reales; lo complejo es Z. Las series originales completas
tienen más términos. Las pequeñas diferencias entre el límite modificado
de estas expresiones y la forma 7.6786 provienen también del redondeo de
las constantes publicadas, no de una supuesta corrección física adicional.
P y Q de Carson son funciones de retorno por tierra: no son la matriz
electrostática de coeficientes de potencial, también llamada P en las etapas
capacitivas. No se intercambian ni se usa P_Carson para calcular C.

## Geometrías existentes, haces y exclusiones

Se admiten tres o seis fases, con todas sus mutuas. En modo centros se
usa un conductor por fase y se validan las posiciones, sin inferir un radio
físico a partir del RMG. En modo Haces se expande la configuración ya
validada (1-4 subconductores por fase), preservando el radio exterior.

Zfase=TᵀZsubT, T[u,p]=E[u,p]/n_p. Hipótesis explícita de corrientes iguales,
Rfase=Rindividual/n_p para resistencias idénticas del haz. No es Kron ni
una solución de reparto real de corrientes. La API primitiva también permite
comprobar cuatro conductores del ejemplo del libro sin eliminar ninguno.

No se añaden/eliminan cables de guarda o neutros en la interfaz y NO se
implementa Kron. No se calculan secuencias, transposición nueva de Z,
cables subterráneos, resistencias por materiales, piel/proximidad ni propagación.
Las asignaciones y modelos de transposición anteriores permanecen separados;
Carson evalúa la geometría transversal seleccionada, sin aplicar su promedio.

## Caso de contraste: Kersting, ejemplo 4.1, pp.92-93

f=60 Hz, ρ=100 Ω·m. Fases a,b,c: GMR=0.0244 ft y R_AC=0.306 Ω/mile.
Coordenadas de figura 4.7: (0,29), (2.5,29), (7,29) ft. Distancias
2.5, 4.5 y 7 ft. El bloque primitivo de fases es 3×3 y no incluye efecto
de eliminación del neutro; NO se compara con el resultado reducido de p.94.

Para contraste adicional del motor se usa el neutro del ejemplo en (4,25) ft,
GMR=0.00814 ft y R=0.592 Ω/mile. Se comprueba toda la primitiva 4×4 de
p.93 sin Kron. Los radios opcionales proceden del ejemplo 5.1, p.114:
diámetros 0.721 in (fase) y 0.563 in (neutro). Son datos de comprobación
bibliográfica, no una ficha vigente de fabricante ni propiedades universales ACSR.

Las matrices del libro están redondeadas a cuatro decimales en Ω/mile.
Se compara con tolerancia absoluta 6e-5 Ω/mile, rtol=0; esta tolerancia
incluye el redondeo de coeficientes de (4.41)-(4.42).

## Advertencia sobre capacitancia y transposición

Carson se aplica SOLO a impedancia serie. No modifica C ni sustituye
los modelos electrostáticos de suelo ideal/sin suelo.

Sea B_t=P_fase,t/(2πε0), V_t=B_t q_t y C_t=B_t^-1.
Si V es común entre tramos electrostáticos equipotenciales:
q_total/L = Σwt C_t V; por tanto C_equiv,V = Σwt C_t.
Si se impone q de fase común como referencia entre tramos:
V_prom = (Σwt B_t) q; por tanto C_equiv,q = (Σwt B_t)^-1.

En general ambas matrices difieren. A potencial común se promedian C
(elementos shunt en paralelo); a carga común se promedian coeficientes
de potencial. En una línea distribuida V(x) e I(x) varían: una cascada de
tramos requiere sus condiciones de borde y no se reemplaza universalmente
por una de esas operaciones. En una homogenización de primer orden de
las ecuaciones de telegrafistas se promedian Z e Y=jωC bajo las condiciones
de esa aproximación, no se justifica por ello invertir automáticamente P media.

Las etapas 5-6 conservan, por petición y referencias del curso, el cálculo
didáctico a carga común (promedio P antes de invertir) y muestran el promedio
C como otro procedimiento. Sus comprobaciones validan el álgebra del
modelo elegido, no demuestran que sea el equivalente shunt físico general
de una línea transpuesta. No se cambian las matrices históricas; se añade
esta distinción explícita y se prueba la conservación de resultados.
