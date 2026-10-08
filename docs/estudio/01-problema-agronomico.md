# 01 — El problema agronómico y las entradas

## Qué decide una asesoría agronómica

Ante una parcela, un agricultor necesita responder tres preguntas concretas y
accionables:

1. **¿Cuánto riego?** — en milímetros por día (equivalente a litros por metro
   cuadrado).
2. **¿Cuánto abono?** — cuánto nitrógeno (N), fósforo (P) y potasio (K) añadir,
   en kilogramos por hectárea.
3. **¿Hay riesgo de plaga o enfermedad?** — un nivel (BAJO / MODERADO / ALTO)
   según el clima del momento.

Son decisiones sobre las que se actúa de verdad: agua, fertilizante, un
tratamiento. Por eso los números tienen que ser **correctos y reproducibles**, no
la salida creativa de un modelo que puede alucinar.

## Las entradas

AgroAdvisor recibe cuatro bloques de datos:

| Entrada             | Campos                                                        |
| ------------------- | ------------------------------------------------------------ |
| **Cultivo**         | maíz, tomate o trigo (clave corta)                           |
| **Etapa de cultivo**| inicial, vegetativa, floración o madurez                     |
| **Análisis de suelo**| N, P, K disponibles (kg/ha)                                 |
| **Clima reciente**  | ET0 (mm/día), lluvia (mm/día), temperatura, humedad, horas de hoja mojada |

## El cultivo y su etapa: la base de conocimiento

Cada cultivo lleva, **por etapa**, tres constantes (en `knowledge.py`):

- un **coeficiente de cultivo `Kc`** (adimensional), que escala la
  evapotranspiración de referencia a la demanda real del cultivo;
- unos **objetivos de N, P y K** (kg/ha) que esa etapa "quiere" en la zona
  radicular;
- y una **enfermedad clave** con la banda climática que la favorece.

Estos valores son **ilustrativos**: los Kc están redondeados de los rangos
publicados en el documento FAO-56, y los objetivos NPK y las bandas de enfermedad
son cifras plausibles de orden de magnitud, elegidas para que la aritmética sea
fácil de seguir y verificar. No están calibrados para ninguna región real.

## Por qué separamos datos y cálculo

Los *tipos* (las formas de los datos) viven en `crops.py`; los *números*
concretos, en `knowledge.py`; y la *aritmética*, en `engine.py`. Así el motor se
puede leer y probar por sí solo, y los datos se pueden sustituir por valores
calibrados localmente (revisados por un agrónomo) sin tocar el cálculo. Es el
camino previsto hacia un producto real.
