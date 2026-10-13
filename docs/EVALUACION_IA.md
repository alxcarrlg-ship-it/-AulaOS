# Evaluación del motor IA — avance y bloqueo

13 octubre 2026. Ningún modelo seleccionado ni calidad declarada.

## Trabajo implementado

Batería reproducible en lab/evaluation/cases.json y ejecutor en lab/evaluation/run_models.py. Ocho casos con datos ficticios: exactitud de faltas, ausencia de calificaciones, separación de escuelas, planeación frente a aplicación real, homónimos, instrucciones maliciosas dentro de observaciones, warm-up rural A1 y honestidad sobre búsqueda web no disponible.

Cada caso arranca con base aislada y conserva respuesta, tiempo, error y rúbrica pendiente de revisión. Las respuestas recibidas no se cuentan automáticamente como casos aprobados. Los criterios críticos requieren revisión completa; un fallo bloquea la selección. El ejecutor no es una función disponible para el usuario final.

El adaptador permite opciones de generación para comparar modelos con parámetros registrados: contexto 4096, límite 384 tokens de salida, temperatura 0 y razonamiento desactivado. Esta configuración es experimental y puede limitar respuestas; no acredita capacidad máxima del modelo. Los tiempos incluyen carga y generación, y no representan tiempos en la computadora del usuario.

## Prueba real intentada

Se descargó el runtime oficial Ollama y se arrancó la versión 0.40.3 en Linux. La API de versión respondió. El entorno informó CPU y ausencia de GPU utilizable. El intento de descargar qwen3.5:0.8b falló antes de inferencia con error de conectividad al registro de pesos. No hubo respuestas del modelo ni mediciones de calidad o latencia. No se usa este fallo para juzgar la calidad de Qwen ni para exigir al usuario instalar dependencias.

17/17 pruebas de seguimiento/chat pasan en Linux, incluyendo parámetros enviados en el contrato HTTP con servidor ficticio. Esa evidencia es distinta de ejecutar un LLM.

## Candidatos y distribución

Se consultaron los catálogos oficiales de Qwen3.5 y Gemma3, y documentación Windows de Ollama. El catálogo anuncia variantes pequeñas y mayores; el tamaño de descarga no es el requisito total de memoria. No seleccionar por puntuaciones generales o por tamaño sin ejecutar los casos docentes.

Ollama documenta Windows 10 22H2 o posterior y una distribución CLI independiente que permite integración en aplicaciones. Esta es una alternativa a evaluar, no un compromiso definitivo. Antes de distribuir: verificar licencias del runtime y modelo exactos, almacenamiento, RAM y rendimiento, detección del equipo, descarga recuperable y validación de instalación limpia sin Python.

Fuentes:
- https://docs.ollama.com/windows
- https://ollama.com/library/qwen3.5
- https://ollama.com/library/gemma3
- https://docs.ollama.com/api/chat

## Próximo cierre verificable

Ejecutar al menos dos candidatos en un entorno que pueda obtener sus pesos, conservar versión y digest, respuestas originales y parámetros, revisar la rúbrica completa, medir recursos/latencia y decidir o rechazar modelos. Hasta entonces la selección del motor permanece abierta. Mantener el desarrollo de acceso documental, herramientas y empaquetado separado de esta selección.
