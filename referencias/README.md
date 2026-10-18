# Referencias técnicas

Coloca aquí los libros, apuntes o fichas técnicas que tengas autorización para utilizar.
Ya se revisaron fuentes para el método de las imágenes con suelo ideal.
El registro de ecuaciones, notación, páginas, supuestos y criterio de verificación
está en [capacitancia.md](capacitancia.md).
La etapa 3 registra fuentes, correcciones detectadas, ecuaciones de RMG,
suelo ideal y referencia sin suelo en [inductancia.md](inductancia.md).
La etapa 4 registra geometría, medias geométricas, corriente I/n y agregación
capacitiva equipotencial en [haces.md](haces.md). Se contrastaron los productos
generales de distancias con las formas cerradas para n=1,2,3,4.
La etapa 5 documenta transposición ideal, matrices por tramo, promedio de
potenciales antes de invertir y restricciones sin suelo en
[transposicion.md](transposicion.md). Se revisaron las notas generales PDF
53–57 y 96–98 y las notas de clase del 14-09-26, PDF 2–3; las discrepancias
de notación y de procedimiento se registran allí explícitamente.
La etapa 6 revisa las notas generales PDF 67-75, clase 15-09-26 PDF 6-9,
clase 17-09-26 PDF 1 y clase 24-09-26 PDF 1-2. El registro
[doble_circuito.md](doble_circuito.md) distingue seis fases independientes,
imágenes, haces, bloques por circuito y equivalentes que necesitarían
conexiones adicionales. No se adoptan propiedades FINCH como datos generales.
La etapa 7A registra Carson modificado y las expresiones finitas P/Q de
Kersting en [carson.md](carson.md), con las discrepancias de la diapositiva 6,
unidades SI/pies/millas, ejemplo 4.1 pp.92-93 y exclusión de Kron. Se consultan
la presentación Carson, notas 01-10-26 PDF 1-2 y capítulo Kersting pp.81-85.
También se documenta la diferencia física entre promedio de C a potencial
común e inversión del promedio P a carga común, conservando resultados históricos.
La etapa 7B documenta [kron.md](kron.md): Kersting pp.86-87, ecs.4.45-4.54,
ejemplo 4.1 completo pp.92-94, presentación diapositivas 9-11 y contraste con
notas de clase. La condición ΔVn=0 se declara explícitamente; no se infiere
por tratarse de un neutro o cable de guarda.
La etapa 7C registra [secuencias.md](secuencias.md): Kersting §4.1.7,
pp.89-91, (4.59)-(4.67), ejemplo 4.1 pp.94-95 y presentación Carson
diapositiva 15. Explicita a=exp(j120°), el orden 0/1/2, la conservación de
acoplamientos y el ensayo independiente de dos guardas de uno/dos circuitos.
La etapa 7D registra [transposicion_serie.md](transposicion_serie.md):
promedio de Z por ciclos, Kersting pp.91 y 95 (4.68)-(4.72), archivos reales
DOVE/PSCAD, lectura de Z del dominio de fases en Ω/m y diferencia entre R_AC
bibliográfica y R_DC declarada en PSCAD. No se cambian C ni L con suelo ideal.
La etapa 7E registra [discrepancias_secuencia.md](discrepancias_secuencia.md):
comprobación escalar independiente de Z0/Z1/Z2, amplificación relativa en R1,
sensibilidad DC sin cambiar entradas AC y diagnóstico de reparto desigual
de corrientes con hipótesis explícitas. No altera los modelos de la aplicación.

Antes de incorporar cada modelo, registra:

| Documento | Autor / edición / año | Capítulo y páginas | Ecuación | Unidades y supuestos | Estado de revisión |
|---|---|---|---|---|---|
| Notas de sistemas de transmision.pdf | Sin atribución editorial comprobada | Cap. 3; PDF 81-82 y 94-96 | P por imágenes y C = 2πε₀ P⁻¹ | SI, aire, suelo ideal | Revisadas las páginas citadas |
| Distribution System Modeling and Analysis - Kersting.pdf | W. H. Kersting, CRC Press, 2002 | §5.2; impresas 111-113, PDF 126-128 | (5.3), (5.6)-(5.10), (5.14) | Adaptación de coeficientes dimensionales a P adimensional | Revisadas las páginas citadas |
| Notas de sistemas de transmision.pdf | Sin atribución editorial comprobada | Cap. 2; PDF 37-39 y 43-48 | RMG, enlaces trifásicos e imágenes | Macizo uniforme no magnético o RMG conocido | Revisadas, correcciones registradas |
| Notas clase STE 08-09-26.pdf | Apuntes manuscritos del curso | PDF 1-4 y 7-10 | Enlaces propios/mutuos y matriz con suelo ideal | Tres fases, imágenes opuestas | Revisión visual de páginas citadas |
| Soucion Ejercicio Matriz Inductancia.pdf | Material del curso sin atribución comprobada | PDF 1-4 | L, X=ωL y reactancia total del ejemplo | Se corrige conversión de unidades al implementar | Texto revisado |
| Distribution System Modeling and Analysis - Kersting.pdf | W. H. Kersting, CRC Press, 2002 | §4.1; impresas 77-78, PDF 92-93 | (4.1)-(4.4) | Suma de corrientes cero, GMR | Revisión visual de páginas citadas |

La primera etapa usa únicamente distancia euclidiana (Pitágoras) y conversiones métricas.
Para capacitancia, Y = 0 representa ahora el plano de suelo ideal del método de las imágenes.
La presencia de un archivo en esta carpeta no significa que haya sido revisado o aplicado.
