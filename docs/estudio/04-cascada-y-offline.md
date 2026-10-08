# 04 — La cascada de proveedores y el modo offline

## Una interfaz, varios proveedores

El asesor no depende de un proveedor concreto, sino de una **interfaz**
(`LLMClient`) con un único método `complete`. Cada proveedor (Anthropic, OpenAI,
Gemini, DeepSeek, un modelo local con Ollama) se envuelve detrás de esa misma
interfaz. El código que necesita un LLM no sabe —ni le importa— cuál hay detrás.

## La cascada: resiliencia por diseño

`build_llm` construye una **cascada** (`CascadeLLM`) sobre una lista de
proveedores configurable (`AA_LLM_SPEC`). La cascada prueba cada uno en orden: si
uno falla (sin clave de API, límite de tasa, error de red, respuesta inválida),
lanza `LLMError` y pasa al siguiente. Si **todos** fallan, el asesor cae a la
**plantilla determinista**.

Esto da dos cosas a la vez:

- **Resiliencia**: que un proveedor esté caído no detiene el sistema.
- **Libertad de coste**: puedes poner primero un modelo barato o local y caer a
  uno más fuerte solo cuando haga falta.

## Por qué es offline-first

El caso por defecto —sin ninguna clave de API— es precisamente "todos los
proveedores fallan": cada adaptador lanza `LLMError` porque no encuentra su clave.
Así que, sin configurar nada, el sistema produce la recomendación completa con la
plantilla offline. **Nada de lo necesario para dar una recomendación correcta
depende de que una llamada de red tenga éxito.**

Cambiar o reordenar proveedores es un cambio de configuración (`AA_LLM_SPEC`), no
de código; añadir uno nuevo es un solo adaptador detrás de la misma interfaz.

## Cómo se prueba sin tocar la red

Como el fallo es un camino normal y esperado, los tests lo ejercitan con dobles:

- `FakeLLM` devuelve un texto prefijado → se prueba el camino "llm".
- `FailingLLM` siempre lanza `LLMError` → se prueba el fallback a plantilla y la
  cascada.

Ningún test hace una llamada de red real. El módulo `llm/` es idéntico en forma al
de otros proyectos del portafolio: es un patrón reutilizable de orquestación
multi-LLM.
