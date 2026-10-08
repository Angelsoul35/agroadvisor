# 02 — El motor determinista

Todo el fondo de la recomendación se calcula aquí (`engine.py`), con aritmética
explícita y unidades claras. Mismas entradas, mismos números, siempre. Sin red,
sin clave de API.

## 1) Riego: demanda menos lluvia efectiva

La demanda hídrica del cultivo es la **evapotranspiración del cultivo**:

```
ETc = Kc · ET0        (mm/día)
```

donde `ET0` es la evapotranspiración de referencia (del clima) y `Kc` es el
coeficiente de la etapa. No toda la lluvia aprovecha: parte se pierde por
escorrentía y percolación. Modelamos eso con una fracción efectiva (0,8 por
defecto):

```
lluvia_efectiva = lluvia · fracción_efectiva
riego_neto      = max(0, ETc − lluvia_efectiva)   (mm/día)
```

El `max(0, …)` es clave: si la lluvia cubre la demanda, el riego neto es **cero**,
no un número negativo. Y como **1 mm sobre 1 m² es 1 litro**, el riego en mm/día
es directamente litros por metro cuadrado.

Ejemplo (maíz vegetativo, `Kc = 0,70`): con `ET0 = 6,5` y lluvia `2,0`:
`ETc = 0,70 · 6,5 = 4,55`; `lluvia_efectiva = 2,0 · 0,8 = 1,6`;
`riego_neto = max(0, 4,55 − 1,6) = 2,95` mm/día.

## 2) Fertilización: objetivo menos suelo

Para cada nutriente (N, P, K), el abono a añadir es lo que falta para llegar al
objetivo de la etapa:

```
déficit = max(0, objetivo_etapa − análisis_suelo)   (kg/ha)
```

De nuevo `max(0, …)`: si el suelo ya supera el objetivo, el déficit es cero (no se
abona). Ejemplo (maíz vegetativo, objetivos N=120, P=40, K=60; suelo 50/15/30):
déficits **N=70, P=25, K=30** kg/ha.

## 3) Riesgo de plaga/enfermedad: conteo de condiciones

Cada cultivo tiene una enfermedad clave con una banda climática que la favorece:
un rango de temperatura, una humedad mínima y unas horas mínimas de hoja mojada.
El motor comprueba las **tres condiciones** de forma independiente y cuenta
cuántas se cumplen (0 a 3):

```
cumplidas = 3  → ALTO
cumplidas = 2  → MODERADO
cumplidas ≤ 1  → BAJO
```

Los umbrales (2 y 3) son ajustables por configuración. Cada condición se reporta
con la comparación exacta que la produjo (por ejemplo `95% >= 90%`), y los
umbrales son **inclusivos** (27 °C entra en `18–27`, 6 h cumple `>= 6`).

## La recomendación estructurada

El motor no devuelve solo números: devuelve, con cada cifra, **la regla que la
produjo** (`net = max(0, Kc*ET0 - rainfall*0.8)`, etc.). Así cualquiera —una
persona, un test, o la prosa del asesor— puede rastrear de dónde salió cada
número. Los tests no "confían" en el motor: **recalculan la aritmética a mano** y
comprueban que coincide.
