# 03 — LLM que redacta, no que decide

## El reparto riguroso de responsabilidades

La mayoría de las demos de "IA para el campo" dejan que un modelo de lenguaje
invente los números: cuántos milímetros regar, cuántos kilos de nitrógeno. Ese es
justo el lugar equivocado para un modelo que puede alucinar. AgroAdvisor lo
invierte:

- **La sustancia** (riego, déficits, nivel de riesgo) la calcula el motor
  determinista (`engine.py`).
- **El modelo** solo se encarga de la **redacción**: recibe las cifras ya
  calculadas y las expresa en prosa clara, con la instrucción de no inventar, no
  cambiar y no omitir ningún valor.

Quita el modelo por completo y la recomendación **no cambia**: la plantilla
offline redacta los mismos números. El modelo hace la salida más agradable de
leer; nunca decide *cuál* es la salida.

## Cómo se le pide al modelo que se limite

El `prompt` lleva todas las cifras calculadas, una por línea (Kc, ET0, ETc, lluvia
efectiva, riego neto, cada déficit, el nivel de riesgo). El `system` le dice, con
todas las letras, que use **solo** esos números y ese nivel, sin inventar, cambiar
ni omitir, y que si un valor es cero (no hace falta riego, un nutriente ya
cubierto) lo diga claramente.

El resultado registra su **origen** (`source`): `"llm"` si lo redactó el modelo,
`"template"` si lo hizo la plantilla offline. Quien llama siempre sabe qué camino
produjo el texto.

## La garantía de que no se inventa nada

Como la salida del LLM es no determinista, **no** es la fuente de verdad: por eso
la recomendación estructurada (los números del motor) se devuelve **siempre** al
lado de la prosa. El contrato es la estructura; la prosa es una comodidad.

Y para la plantilla offline lo garantizamos con un test
(`test_template_invents_no_numbers`): extrae **todos** los números que imprime la
plantilla y comprueba que cada uno es un número que el motor calculó. Si la
plantilla imprimiera una cifra inventada, el test falla. Es una garantía
verificable del proyecto convertida en una aserción ejecutable.
