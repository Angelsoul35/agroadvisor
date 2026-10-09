# Guía de estudio — AgroAdvisor

Una guía en español para entender el proyecto a fondo y poder defenderlo en una
entrevista. El código, los comentarios y la documentación técnica están en inglés
(como en un entorno profesional real); esta guía explica el *porqué* de cada
decisión.

## Orden sugerido

1. [01 — El problema agronómico y las entradas](01-problema-agronomico.md)
   Qué datos entran (cultivo, etapa, suelo, clima) y qué se decide con ellos.
2. [02 — El motor determinista](02-motor-determinista.md)
   El cálculo real: riego, fertilización y riesgo, con unidades y fórmulas.
3. [03 — LLM que redacta, no que decide](03-llm-redacta-no-decide.md)
   Por qué el modelo solo expresa en prosa los números ya calculados.
4. [04 — La cascada de proveedores y el modo offline](04-cascada-y-offline.md)
   Cómo funciona el fallback de proveedores y por qué el sistema es offline-first.
5. [05 — Preguntas de entrevista](05-preguntas-de-entrevista.md)
   Preguntas típicas y cómo responderlas con este proyecto.
6. [06 — Evaluación con datos reales](06-evaluacion-datos-reales.md)
   El recomendador de cultivo aprendido: dataset real, métricas (exactitud y
   macro-F1), sobreajuste/subajuste y la brecha, validación cruzada frente a
   partición retenida, y el control de etiquetas barajadas, con números reales.

## La idea en una frase

Un motor agronómico **determinista y auditable** calcula el fondo de la
recomendación (riego, fertilización, riesgo de plaga/enfermedad); un LLM solo
**redacta** esos números en prosa y, si no hay modelo, una plantilla offline
produce la misma sustancia. El modelo nunca inventa una cifra.

## Aviso importante

Los valores agronómicos (coeficientes Kc, objetivos NPK, bandas climáticas de
enfermedad) son **ilustrativos**, no están calibrados para ninguna región real.
El proyecto demuestra la *arquitectura*, no sustituye a un agrónomo.
