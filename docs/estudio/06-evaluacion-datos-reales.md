# 06 — Evaluación con datos reales: el recomendador de cultivo

Este capítulo explica la parte **aprendida** del proyecto y cómo se demuestra, con
números reproducibles, que generaliza. El motor determinista (capítulo 02)
responde a *"dado este cultivo, ¿cómo lo manejo?"*. El recomendador responde a la
pregunta anterior: *"¿qué cultivo conviene en esta parcela?"*, a partir de siete
medidas de suelo y clima. Los dos **conviven y se componen**: primero recomiendas
un cultivo, luego se lo pasas al motor para el plan de manejo. La aritmética
auditada del motor no se toca; esto es una capacidad añadida encima.

Código: `agroadvisor/real_data.py` (datos), `agroadvisor/recommender.py` (modelo)
y `agroadvisor/real_benchmark.py` (evaluación). Reproducir el informe:

```bash
python -m agroadvisor.real_benchmark
```

## 1) El problema y el conjunto de datos

Es un problema de **clasificación multiclase**: a partir de un vector de siete
características agronómicas, predecir **cuál de 22 cultivos** es el adecuado. Los
datos son el conjunto público `randalakab/Crop-recommendation` (Hugging Face):
**2200 filas reales**, perfectamente balanceadas en **100 filas por cultivo**.

Las siete características (`features()` las entrega en este orden fijo) y su
sentido agronómico:

| Característica | Qué mide                       | Unidad | Por qué importa |
| ------------- | ------------------------------ | ------ | --------------- |
| `N`           | nitrógeno del suelo            | kg/ha  | crecimiento vegetativo, hoja |
| `P`           | fósforo del suelo              | kg/ha  | raíz, floración, cuaje |
| `K`           | potasio del suelo              | kg/ha  | vigor, resistencia a estrés |
| `temperature` | temperatura del aire           | °C     | ventana térmica del cultivo |
| `humidity`    | humedad relativa               | %      | demanda hídrica y enfermedad |
| `ph`          | acidez del suelo               | —      | disponibilidad de nutrientes |
| `rainfall`    | precipitación                  | mm     | agua disponible sin riego |

Los tres macronutrientes **reutilizan** el `SoilTest` del motor (`engine.py`): una
fila es un `AgroSample` que contiene un `SoilTest(N, P, K)` más clima, pH y la
etiqueta. Así la parte aprendida no inventa un modelo de datos nuevo, se apoya en
el que ya existe.

> Nota de datos reales: la humedad llega a ~101,4 % en alguna fila. No es un error
> de carga, es el **ruido de medición** propio de datos de campo reales. El test
> `test_dataset_values_are_in_plausible_agronomic_ranges` fija cotas que respetan
> ese ruido pero que detectarían un volcado corrupto.

## 2) El modelo

Un **`Pipeline`** de scikit-learn: `StandardScaler` seguido de una **regresión
logística multinomial**.

- La **estandarización** es imprescindible: las características viven en escalas muy
  distintas (pH ~6 frente a lluvia ~200 mm). Restar la media y dividir por la
  desviación típica de cada columna evita que una característica domine solo por su
  unidad. La media y la desviación se aprenden **dentro de cada partición de
  entrenamiento**, nunca sobre el test (eso sería fuga de datos).
- La **regresión logística** se elige a propósito para un proyecto de portafolio:
  es **interpretable** (un peso por característica y por clase), da probabilidades
  razonables y —a diferencia de un bosque que puede memorizar el entrenamiento y
  marcar un 100 % de acierto en él— deja una **brecha train/test legible**, que es
  justo lo que usamos para demostrar que generaliza.

## 3) Las métricas, con fórmulas

Sea `N` el número de ejemplos y `C = 22` el número de clases. La predicción del
ejemplo `i` es `ŷ_i` y la verdad es `y_i`.

**Exactitud (accuracy)** — fracción de aciertos:

```
accuracy = (1/N) · Σ_i  1[ ŷ_i = y_i ]
```

Es intuitiva, pero en problemas desbalanceados puede engañar: un modelo que
siempre predice la clase mayoritaria puede tener alta exactitud sin saber nada de
las clases raras.

**Macro-F1** — mide el equilibrio **clase por clase**. Para cada cultivo `c`:

```
precision_c = TP_c / (TP_c + FP_c)      (de lo que predije como c, cuánto acerté)
recall_c    = TP_c / (TP_c + FN_c)      (de los c reales, cuántos encontré)
F1_c        = 2 · precision_c · recall_c / (precision_c + recall_c)   (su media armónica)
```

y la **macro-F1** es la media simple de las 22:

```
macro-F1 = (1/C) · Σ_c  F1_c
```

La clave del *macro*: promedia **sin ponderar por tamaño**, así que cada cultivo
pesa igual. Aunque este conjunto esté balanceado (100 por clase), reportar macro-F1
junto a la exactitud es lo correcto, porque garantiza que el acierto está repartido
entre los 22 cultivos y no concentrado en unos pocos. Que accuracy (0,9382) y
macro-F1 (0,9375) casi coincidan es señal de que ningún cultivo se queda atrás.

**Nivel de azar (chance)** — un clasificador que adivina a ciegas, con clases
balanceadas, acierta:

```
chance = 1 / C = 1 / 22 ≈ 0,0455
```

Este es el listón mínimo: cualquier modelo útil tiene que superarlo con holgura.

## 4) Sobreajuste y subajuste: qué son y cómo los vemos

El dilema **sesgo–varianza**:

- **Subajuste (underfitting, sesgo alto).** El modelo es demasiado simple para
  captar la señal. Rinde **mal en entrenamiento y mal en test** a la vez, con poca
  diferencia entre ambos. Síntoma: la exactitud de test apenas supera el azar.
- **Sobreajuste (overfitting, varianza alta).** El modelo memoriza el
  entrenamiento, incluido su ruido. Rinde **muy bien en entrenamiento y claramente
  peor en datos nuevos**. Síntoma: una **brecha train/test grande**.
- **Buen ajuste (well-fit).** Exactitud de test alta **y** brecha pequeña.

La **brecha de generalización** es la herramienta de diagnóstico:

```
gap = accuracy_entrenamiento − accuracy_test
```

Un `gap` grande grita sobreajuste. Un `gap` pequeño con exactitud de test alta es
buen ajuste. Un `gap` pequeño con exactitud de test cercana al azar es subajuste.
El código lo decide en `classify_fit`: si `gap > 0,10` → `overfit`; si no, y la
exactitud de test no supera `4 × chance` → `underfit`; en otro caso → `well-fit`.

## 5) El método de evaluación: validación cruzada + partición retenida

Medimos de **dos formas independientes** y comprobamos que coinciden.

**Validación cruzada estratificada de 5 particiones (k-fold, k=5).** Se parte el
conjunto en 5 bloques del mismo tamaño que conservan la proporción de cada clase
(eso es *estratificada*). Se entrena 5 veces, cada una dejando fuera un bloque como
test, y se promedian las 5 exactitudes y macro-F1. Ventaja: cada ejemplo actúa como
test exactamente una vez, así que el número no depende de una partición
afortunada, y la **desviación típica** entre bloques mide la estabilidad.

**Partición retenida (held-out) 75 / 25.** Un corte único y estratificado: se
entrena con el 75 % y se mide en el 25 % restante. Aquí sí comparamos la exactitud
de **entrenamiento** con la de **test** para leer la brecha.

¿Por qué las dos? La validación cruzada da una media robusta; la partición retenida
da la brecha train/test. Si **ambas coinciden**, la cifra es creíble: no es un
corte con suerte. Las semillas están fijadas (`random_state`), así que el informe
es reproducible al decimal.

## 6) Ejemplo trabajado con los números reales

Salida de `python -m agroadvisor.real_benchmark` sobre las 2200 filas:

```
Stratified 5-fold cross-validation
  accuracy : 0.9341 +/- 0.0041
  macro-F1 : 0.9333 +/- 0.0048

Held-out split (75% train / 25% test, stratified)
  train accuracy : 0.9412
  test  accuracy : 0.9382
  test  macro-F1 : 0.9375
  train-test gap : 0.0030

verdict: WELL-FIT  (gap 0.0030 <= 0.1; test accuracy 20.6x chance)
```

Leamos cada pieza:

1. **Supera el azar con holgura.** `chance = 1/22 ≈ 0,0455`. La exactitud de test es
   `0,9382`, es decir `0,9382 / 0,0455 ≈ 20,6` **veces el azar**. El modelo ha
   aprendido señal real, no adivina.
2. **No hay subajuste.** Tanto entrenamiento (`0,9412`) como test (`0,9382`) son
   altos; el modelo capta bien la relación suelo-clima → cultivo.
3. **No hay sobreajuste.** La brecha es
   `gap = 0,9412 − 0,9382 = 0,0030`. Es diminuta (muy por debajo del umbral 0,10):
   el modelo rinde casi igual en datos vistos y no vistos.
4. **Las dos mediciones concuerdan.** La media de validación cruzada (`0,9341`) y la
   exactitud retenida (`0,9382`) difieren en `0,0041`. El número no depende de un
   corte afortunado.
5. **Veredicto: `well-fit`.** Brecha pequeña **y** exactitud muy por encima del azar.

Que el modelo **no** llegue a `1.0` es lo esperable y lo correcto con 22 clases
reales: un `1.0` perfecto sería la señal de alarma (memorización o fuga de datos),
no de éxito.

### Una predicción concreta

Para una parcela cálida, húmeda y muy lluviosa, con suelo ligeramente ácido —
`N=82, P=50, K=48, temperatura=22 °C, humedad=84 %, pH=5,8, lluvia=198 mm` — el
recomendador predice **rice** (arroz), que coincide con la etiqueta real de esa
observación. Encaja con la agronomía: el arroz pide mucha agua y tolera suelo
ácido. El método `ranked(sample, k=3)` además devuelve los tres cultivos más
probables con su probabilidad, por si se quiere ofrecer alternativas.

## 7) El control de etiquetas barajadas

Un buen número de exactitud puede ser mentira si la evaluación **filtra**
información del test al entrenamiento (fuga de datos). El control lo descarta.

La idea: **barajar las etiquetas** al azar, rompiendo el vínculo entre las
características y el cultivo, y volver a evaluar **con exactamente el mismo
procedimiento**. Si al destruir toda la señal el modelo sigue puntuando alto, es que
el procedimiento filtra; si puntúa al azar, el procedimiento es limpio.

Resultado:

```
Shuffled-label control
  CV accuracy on permuted labels : 0.0409  (collapses to chance 0.0455)
```

`0,0409` está prácticamente sobre `1/22 = 0,0455`. Sin relación real entre entrada
y salida, el modelo no puede hacer más que adivinar. **Por tanto el `0,9382` del
modelo de verdad mide señal real, no un artefacto de la evaluación.** Es la prueba
de que todo el montaje está **libre de fuga de datos**.

## 8) Cómo encaja en el proyecto

- `real_data.py` descarga (con reintentos y *backoff* por el límite de peticiones) y
  carga los datos en objetos `AgroSample` que reutilizan `SoilTest`.
- `recommender.py` define `CropRecommender`: `train`, `recommend`, `recommend_many`
  y `ranked`.
- `real_benchmark.py` ejecuta la evaluación completa (validación cruzada, partición
  retenida, control barajado) y la imprime.
- Los tests en `tests/test_real_benchmark.py` son **funcionales y a prueba de
  mutaciones**: comprueban las 2200 filas y los 22 cultivos, que el modelo supera el
  azar, que la brecha es pequeña (buen ajuste), que el control barajado cae al azar,
  y cubren la ruta de descarga con un `urlopen` sustituido.

La moraleja es la misma que la del motor determinista: una afirmación fuerte
("generaliza", "supera el azar", "está libre de fuga de datos") vale cuando es
**verificable**, y aquí lo es, con números que cualquiera puede reproducir.
