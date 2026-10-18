# Etapa 6: dos circuitos trifásicos independientes

**Revisión física de etapa 7A:** el promedio P de los tramos mantiene el
modelo didáctico a carga común de etapa 5. No equivale al promedio directo
de C a potencial común ni es un equivalente shunt universal. Véase
`carson.md` para las condiciones de borde y el contraste con el modelo
distribuido. No se cambian los resultados históricos ni las capacitancias
de cada sección; Carson se calcula solo como impedancia serie independiente.

## Documentos contrastados

- Notas de sistemas de transmision.pdf, PDF 67-75: geometrías de doble
  circuito, transposición y medias geométricas propias/mutuas. Se extrajo el
  texto completo del intervalo y se inspeccionó PDF 68 renderizada.
- Notas clase STE 15-09-26.pdf, PDF 6-9, inspección visual: configuraciones
  plana vertical/barril/hexagonal y ejemplo equivalente con conductores FINCH.
- Notas clase STE 17-09-26.pdf, PDF 1: estructuras con haces y doble circuito.
- Notas clase STE 24-09-26.pdf, PDF 1-2: imágenes, coeficientes de potencial,
  inversión matricial y tramos. Ambas páginas se inspeccionaron visualmente.
- Las ecuaciones primitivas son las de las etapas 3-5, contrastadas con
  Kersting, Distribution System Modeling and Analysis, CRC Press 2002,
  §4.1 y §5.1-5.2; ver inductancia.md, haces.md y transposicion.md.

Correcciones: PDF 68 de las notas generales repite Ia donde corresponde Ic
en la suma de corrientes del primer circuito. PDF 73 escribe La=λa/La: debe
ser λa/Ia. En PDF 71 desaparecen algunos ln en pasos intermedios; se conserva
ln(producto)=suma de ln. La clase 24-09-26 PDF 2 escribe una inversión de
vector en un paso de C: se usa la relación matricial q=C V e inversa de P,
nunca una inversa de vector. El ejemplo FINCH contiene un RMG de ejemplo;
no se adopta como propiedad de otro conductor ni se infiere un radio exterior.
La matriz 6×6 de clase 24-09-26 PDF 1 representa tres reales y sus tres
imágenes, NO dos circuitos reales. Aquí hay seis fases reales y seis grupos
de imágenes; se extiende la misma relación de potencial por superposición
y se eliminan las imágenes analíticamente mediante ln(S/D).

## Terminales y geometría

Orden fijo: A, B, C, A', B', C'. Cada terminal es una fase independiente.
La matriz primitiva de seis terminales NO es un equivalente trifásico.
Si hay haces, se distingue de las primitivas de N subconductores, N=6..24.
Se reutiliza la geometría regular validada de cada circuito; se construyen
TODAS las distancias entre subconductores, incluidos los de circuitos distintos.
Se rechaza cualquier contacto/solapamiento cruzado y contacto con el suelo.

Duv = hypot(xu-xv, hu-hv); Suv = hypot(xu-xv, hu+hv), en metros.
E[u,p]=1 si u pertenece a p. T[u,p]=E[u,p]/n_p.
Las distancias equivalentes y radios se calculan por medias de logaritmos
con las mismas distancias propias de las etapas anteriores.

## Matrices con suelo ideal

k=μ0/(2π), F=2πε0; μ0=4π·10^-7 H/m, ε0=8.8541878128·10^-12 F/m.

Lsub,uu=k ln(2hu/RMG_u); Lsub,uv=k ln(Suv/Duv) [H/m].
L6=Tᵀ Lsub T. Se presupone I_sub=I_fase/n; no se resuelve reparto de corrientes.
RMG=R exp(-1/4) solo para macizo no magnético con corriente uniforme.
ACSR exige RMG documentado del fabricante; no se inventa su geometría.

Psub,uu=ln(2hu/Ru); Psub,uv=ln(Suv/Duv), adimensional.
W=Psub^-1 E; C6=F Eᵀ W [F/m]; Pfase=(C6/F)^-1.
Se impone equipotencialidad por haz; las cargas individuales pueden diferir.
No se reemplaza Psub por un círculo capacitivo equivalente.
Comprobaciones: Psub W=E y Pfase C6/F=I6.

## Sin suelo: espacio de suma cero, no retorno arbitrario

La representación auxiliar canónica usa dref=1 m:
L0,uu=k ln(dref/RMG_u), L0,uv=k ln(dref/Duv).
P0,uu=ln(dref/Ru), P0,uv=ln(dref/Duv).
Esta referencia cancela en los resultados restringidos; no es retorno físico.
H6=I6-11ᵀ/6; resultado inductivo principal Lproj=H6 (TᵀL0 T) H6.
Solo vale para IA+IB+IC+IA'+IB'+IC'=0. Tiene rango 5.
Si se exige además suma cero en cada circuito, Hcc=diag(H3,H3),
Lcc=Hcc Lproj Hcc (rango 4); Bcc=diag(B3,B3),
B3=[[1,0],[0,1],[-1,-1]], y L_lazos=BccᵀLproj Bcc [H/m].
Esto define cuatro corrientes de lazo; no une terminales ni reduce a 3 fases.

Para capacitancia Z es una base ortonormal de 1ᵀq_sub=0:
W=Z (ZᵀP0 Z)^-1 Zᵀ E; C6=F EᵀW (rango 5).
Se impone SOLO carga total de los dos circuitos igual a cero, no neutralidad
individual por circuito. El potencial común es indeterminado. No son seis
capacitancias absolutas a tierra. Se verifica neutralidad y equipotencialidad
salvo una constante común.

## Transposición ideal completa automática · corrección 17-10-2026

La interfaz permite únicamente **Sin transposición** y **Transposición ideal
completa automática**. No hay entradas de número de tramos, fracciones ni
asignaciones P1-P6. La tabla de tramos es de solo lectura. La geometría de
entrada conserva sus posiciones físicas editables.

Para N circuitos se enumeran las combinaciones (k1,...,kN) de {0,1,2}^N.
Cada fase local i ocupa la posición 3c+(i+kc) mod 3 de su mismo circuito c
(índices desde cero). Hay 3^N tramos, con pesos internos normalizados mediante
`math.fsum`, iguales a 1/(3^N). Un circuito usa tres ciclos; dos circuitos,
las nueve combinaciones independientes. Sin transposición, solo identidad
y peso 1. Los decimales mostrados nunca se releen para calcular los pesos.

El generador combinatorio se prueba también con tres y cuatro circuitos;
**los motores eléctricos y la interfaz siguen limitados a uno o dos**.
Las antiguas sesiones manuales activadas migran al plan automático, sin leer
sus pesos ni asignaciones guardadas. El visor de tramos se restablece al pasar
de nueve tramos a uno si su selección ya no existe.

Cada tramo especifica internamente la posición física ocupada por cada fase.
Se conservan las permutaciones dentro de cada circuito y sus tres terminales.
Las propiedades y el haz viajan con la fase. Se reconstruye la geometría,
no se permutan matrices a ciegas cuando las construcciones difieren.

L_prom=Σ wt Lt; P_prom=Σ wt Pfase,t; C_prom_modelo=F P_prom^-1.
Sin suelo, Q es base de suma cero de seis fases:
Pfase,t=Q [Qᵀ(Ct/F)Q]^-1 Qᵀ;
C=F Q (QᵀP_prom Q)^-1 Qᵀ y P_prom C/F=H6.
Es el promedio de potenciales a carga de fase de referencia común de etapa 5,
no promedio directo de C ni cascada exacta de líneas distribuidas.
Tres ciclos simultáneos no garantizan igualar TODOS los acoplamientos
entre circuitos: el ciclo relativo importa. La nueva opción completa usa las
nueve combinaciones; se muestran los seis terminales y todos sus acoplamientos.
Los planes explícitos históricos permanecen en la API para conservar sus
pruebas y cálculos previos; no se ofrecen como transposición completa en UI.

## Bloques y límites

L=[[L11,L12],[L21,L22]], λ1=L11 I1+L12 I2, λ2=L21 I1+L22 I2.
C=[[C11,C12],[C21,C22]], q1=C11 V1+C12 V2.
Los bloques diagonales son partes del operador completo, NO circuitos aislados.
C11 con suelo describe q1 ante V2=0, no el otro circuito flotante.
No hay reducción automática, conexión paralela ni reducción de Kron.
Sin suelo los bloques se interpretan junto con la restricción global.

Conversión: H/m→µH/m o mH/km: 10^6; F/m→nF/km: 10^12.
X=2πfL, Ω/m; Ω/km=X·1000. Frecuencia y longitud no condicionan L/C.
Aire con εr=1, línea larga y horizontal por tramos, cargas lineales,
suelo ideal plano si se activa. Sin Carson, resistividad finita, piel/proximidad,
flecha, cruces de longitud finita, cables de guarda ni propagación distribuida.

## Caso reproducible sintético, no diseño validado

Un subconductor por fase; A=(-4,15), B=(-4,11), C=(-4,7),
A'=(4,15), B'=(4,11), C'=(4,7), en metros. Radio 0.011765 m por fase,
modelo macizo no magnético uniforme, suelo ideal, sin transposición.
La frecuencia de ensayo puede ser 60 Hz; no se asigna una corriente o tensión
de operación. Los resultados se calculan y se exportan, nunca se codifican.
