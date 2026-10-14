# Arquitectura acordada: online principal, offline básico

Acuerdo del usuario: 13 octubre 2026.

## Decisión

AulaOS debe funcionar en computadoras básicas. Las funciones avanzadas de IA usarán OpenAI en línea. El modo offline cubrirá lo básico cuando no haya internet; no se exige generación avanzada ni un modelo grande instalado. La elección o evaluación de modelos locales deja de bloquear el producto. El adaptador Ollama existente queda como experimento interno opcional, no requisito de instalación ni dependencia del arranque.

## Comportamiento previsto

Online: conversación abierta, análisis de fuentes seleccionadas, preparación de materiales y herramientas docentes, voz e investigación según capacidades integradas y probadas. No se declaran implementadas por este acuerdo.

Offline: consultar datos ya guardados, asistencia, observaciones, pendientes, historial y operaciones documentales básicas disponibles localmente. Identificar claramente el modo y conservar el trabajo. No fingir investigación o generación avanzada.

Al recuperar internet: continuar la conversación desde el historial local. Los mensajes o documentos pendientes no deben enviarse automáticamente a un proveedor ni generar cobros sin una acción de continuación del docente. Un error temporal, falta de crédito o rechazo de autenticación no se debe presentar como ausencia de internet.

## Datos y continuidad

Mantener SQLite e historial por escuela/grupo en el equipo. Leer originales sin reescribirlos por defecto. Enviar al servicio online únicamente contexto necesario para la solicitud. Credenciales fuera del repositorio y del cliente distribuido; no incluir una clave compartida en el ejecutable. Implementado almacenamiento opcional por usuario con DPAPI; su comprobación en Windows y el servicio de distribución quedan pendientes.

## Costos y alcance de OpenAI

La integración propia en línea requiere una vía de acceso soportada por OpenAI. La API tiene facturación propia; no asumir que la suscripción ChatGPT del usuario cubre uso de una aplicación externa. El incremento 0.2 incorpora perfiles configurados, estimación por tokens y límite de intentos mensuales. No es un tope monetario garantizado; la facturación real corresponde al proveedor. Antes de activar llamadas reales: acceso válido, estimación y controles de gasto; no realizar llamadas cobradas por este acuerdo de arquitectura.

## Criterios de aceptación

- Arranque y seguimiento local sin modelo grande ni Python instalado por el usuario.
- Sin internet, el trabajo básico sigue disponible y la interfaz explica límites.
- Online, las respuestas usan fuentes y contexto activo; no mezclar escuelas/grupos.
- Un fallo de servicio conserva entradas y ofrece reintento sin duplicar registros.
- Reintentar no envía trabajo pendiente ni genera gasto de forma invisible.
- Validar en un Windows básico de referencia antes de declarar compatibilidad; no exigir al usuario diagnosticar su hardware para continuar desarrollando.

## Estado

Incremento interno 0.5: chat persistente, funciones básicas, materiales locales, adjuntos seleccionados investigación web opcional con fuentes y borradores locales con versiones/exportación Word y HTML. La investigación solo envía la pregunta actual, sin datos escolares, documentos ni historial. Integración OpenAI y gestión de intentos/costos implementadas con pruebas simuladas; falta llamada real. Una falla de conexión activa el modo básico, sin afirmar que diagnostica toda la conectividad del equipo. Por acuerdo del usuario, comprobaciones Windows y empaquetado se reservan para 1.0. Este documento sustituye la prioridad anterior de seleccionar un motor local principal.

Fuentes de implementación a consultar:
- https://developers.openai.com/api/docs/pricing
- https://developers.openai.com/api/reference/resources/responses/methods/create


## Incremento 0.6: acciones locales

`actions.py` reconoce comandos explícitos del docente antes de cualquier llamada al proveedor. Las propuestas conservan destino, contenido y estado en SQLite. La confirmación valida nuevamente la identidad y aplica registro + estado en una única transacción. `actions_ui.py` permite revisar, confirmar o cancelar por grupo. Las propuestas no entran al historial enviado a OpenAI. No hay ejecución automática de texto del modelo o documentos. Ver VERSION_0_6.md.


## Incremento 0.7: plantillas variables

El formato pertenece al docente/centro, no al programa. `templates.py` guarda bytes DOCX originales y un esquema estructural sin número fijo de columnas. Documentos separados guardan cambios por párrafo y revisiones; la exportación parchea solo texto compatible en una copia del paquete. `templates_ui.py` conecta la biblioteca, editor, borradores y selección explícita de estructura para el chat. La comprensión semántica de requisitos y distribución automática revisable del contenido aún no están implementadas. No confundir conservación estructural con garantía de paginación idéntica.


## Incremento 0.8: carpetas y voz

`folders.py` cataloga nombres y metadatos de carpetas elegidas por grupo. `/buscar` es una ruta local del chat separada del historial online. La lectura y el adjunto son explícitos; el contenido revisado se verifica por digest antes de guardar una copia como material. `folders_ui.py` ejecuta escaneo y lectura en trabajadores con conexión SQLite propia.

`voice.py` graba WAV en memoria o lee audio seleccionado y usa el endpoint de transcripción con una solicitud multipart explícita. `voice_ui.py` mantiene revisión humana antes de pasar el texto al cuadro del chat. No interpreta ni ejecuta transcripciones como acciones. El consumo comparte el límite local, con costo desconocido para audio. El audio no se incluye en SQLite; sí las transcripciones. Windows y micrófono real pendientes.
