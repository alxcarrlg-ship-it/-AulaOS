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

Incremento interno 0.4: chat persistente, funciones básicas, materiales locales, adjuntos seleccionados e investigación web opcional con fuentes. La investigación solo envía la pregunta actual, sin datos escolares, documentos ni historial. Integración OpenAI y gestión de intentos/costos implementadas con pruebas simuladas; falta llamada real. Una falla de conexión activa el modo básico, sin afirmar que diagnostica toda la conectividad del equipo. Por acuerdo del usuario, comprobaciones Windows y empaquetado se reservan para 1.0. Este documento sustituye la prioridad anterior de seleccionar un motor local principal.

Fuentes de implementación a consultar:
- https://developers.openai.com/api/docs/pricing
- https://developers.openai.com/api/reference/resources/responses/methods/create
