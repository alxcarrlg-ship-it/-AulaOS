# Arquitectura acordada: online principal, offline básico

Acuerdo del usuario: 13 octubre 2026.

## Decisión

AulaOS debe funcionar en computadoras básicas. Las funciones avanzadas de IA usarán OpenAI en línea. El modo offline cubrirá lo básico cuando no haya internet; no se exige generación avanzada ni un modelo grande instalado. La elección o evaluación de modelos locales deja de bloquear el producto. El adaptador Ollama existente queda como experimento interno opcional, no requisito de instalación ni dependencia del arranque.

## Comportamiento previsto

Online: conversación abierta, análisis de fuentes seleccionadas, preparación de materiales y herramientas docentes, voz e investigación según capacidades integradas y probadas. No se declaran implementadas por este acuerdo.

Offline: consultar datos ya guardados, asistencia, observaciones, pendientes, historial y operaciones documentales básicas disponibles localmente. Identificar claramente el modo y conservar el trabajo. No fingir investigación o generación avanzada.

Al recuperar internet: continuar la conversación desde el historial local. Los mensajes o documentos pendientes no deben enviarse automáticamente a un proveedor ni generar cobros sin una acción de continuación del docente. Un error temporal, falta de crédito o rechazo de autenticación no se debe presentar como ausencia de internet.

## Datos y continuidad

Mantener SQLite e historial por escuela/grupo en el equipo. Leer originales sin reescribirlos por defecto. Enviar al servicio online únicamente contexto necesario para la solicitud. Credenciales fuera del repositorio y del cliente distribuido; no incluir una clave compartida en el ejecutable. La solución de credenciales y servicio de distribución queda pendiente de implementación.

## Costos y alcance de OpenAI

La integración propia en línea requiere una vía de acceso soportada por OpenAI. La API tiene facturación propia; no asumir que la suscripción ChatGPT del usuario cubre uso de una aplicación externa. Modelo, tarifa, financiación y límites aún por definir y verificar. Antes de activar llamadas reales: acceso válido, estimación y controles de gasto; no realizar llamadas cobradas por este acuerdo de arquitectura.

## Criterios de aceptación

- Arranque y seguimiento local sin modelo grande ni Python instalado por el usuario.
- Sin internet, el trabajo básico sigue disponible y la interfaz explica límites.
- Online, las respuestas usan fuentes y contexto activo; no mezclar escuelas/grupos.
- Un fallo de servicio conserva entradas y ofrece reintento sin duplicar registros.
- Reintentar no envía trabajo pendiente ni genera gasto de forma invisible.
- Validar en un Windows básico de referencia antes de declarar compatibilidad; no exigir al usuario diagnosticar su hardware para continuar desarrollando.

## Estado

Acuerdo y criterios registrados. Chat persistente y funciones básicas locales existen en el laboratorio. Integración OpenAI, detección de conectividad fiable, gestión de costos y empaquetado Windows siguen pendientes. Este documento sustituye la prioridad anterior de seleccionar un motor local principal.

Fuentes de implementación a consultar:
- https://developers.openai.com/api/docs/pricing
- https://developers.openai.com/api/reference/resources/responses/methods/create
