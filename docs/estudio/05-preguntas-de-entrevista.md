# 05 — Preguntas de entrevista

Preguntas típicas sobre este proyecto y cómo responderlas.

### "¿No es esto un envoltorio de un LLM más?"
No, y esa es la tesis del proyecto. El LLM **no calcula nada**: todo el fondo
(riego, fertilización, riesgo) sale de un motor determinista con aritmética
explícita. El modelo solo **redacta** los números ya calculados, con prohibición
de inventar. Si quitas el modelo, una plantilla offline da la misma sustancia.

### "¿Por qué un motor determinista y no dejar que el modelo razone?"
Porque sobre estos números se **actúa**: agua, fertilizante, un tratamiento. Una
cifra alucinada tiene coste real. El determinismo me da reproducibilidad y
auditoría: puedo recalcular a mano `max(0, Kc·ET0 − lluvia·0,8)` y comprobar que
el sistema coincide. Eso es justo lo que hacen los tests.

### "¿Cómo garantizas que la prosa no inventa un número?"
Dos mecanismos. Uno, la recomendación **estructurada** se devuelve siempre junto a
la prosa, así que la fuente de verdad son los números, no el texto. Dos, para la
plantilla offline hay un test que extrae todos los números que imprime y verifica
que cada uno lo calculó el motor; si inventara una cifra, el test falla.

### "¿Qué pasa si no hay clave de API?"
El sistema funciona igual. La cascada de proveedores prueba cada uno; sin clave,
todos lanzan `LLMError`, y el asesor cae a la plantilla determinista. Es
**offline-first** por defecto: no hace falta red ni configuración.

### "¿De dónde salen los coeficientes Kc y los objetivos NPK?"
Son valores **ilustrativos**: los Kc, redondeados de los rangos del FAO-56; los
objetivos NPK y las bandas de enfermedad, cifras plausibles de orden de magnitud.
No están calibrados para ninguna región real. Lo digo con todas las letras en el
README y en un ADR. El proyecto demuestra la *arquitectura*, no sustituye a un
agrónomo.

### "¿Por qué z... perdón, por qué un conteo de condiciones para el riesgo?"
Porque quería un riesgo **explicable** y determinista. Muchas enfermedades
foliares necesitan una ventana de temperatura, humedad alta y horas de hoja
mojada. Cuento cuántas de las tres se cumplen y lo mapeo a BAJO/MODERADO/ALTO,
reportando cada comparación. Un agricultor ve *por qué* y puede anularlo. Es
simple a propósito; no es un modelo epidemiológico validado, y lo digo.

### "¿Cómo lo llevarías a producción?"
Datos calibrados localmente (Kc, presupuestos de nutrientes) revisados por un
agrónomo; un balance hídrico de suelo y un método de lluvia efectiva como el de la
USDA-SCS en lugar de una fracción plana; modelos de enfermedad validados con datos
de campo; persistencia e histórico por parcela. La arquitectura —núcleo
determinista, LLM en un papel presentacional— no cambiaría; cambiarían los datos y
la fidelidad de los modelos.

### "¿Qué es lo que más te gusta del diseño?"
Que la fiabilidad es una propiedad verificable, no una promesa: el reparto
"motor calcula / LLM redacta" está respaldado por un test que impide que el texto
introduzca un número que el motor no produjo.
