# Incremento 0.4 · Investigación docente con fuentes

13 octubre 2026. Continúa 0.3 y conserva sus funciones. Implementado y probado con simulaciones; todavía sin llamada real a OpenAI ni instalador validado.

## Uso

En el asistente, elegir OpenAI online y activar **Investigar en internet (esta consulta)**. Escribir una pregunta completa (tema, nivel, objetivo, recursos disponibles). Opcionalmente indicar dominios separados por comas, sin prefijo ni rutas. Si hay adjuntos seleccionados, la interfaz solicita quitarlos antes de investigar. El control se desactiva tras enviar: una conversación normal no activa búsquedas ni cargos de herramientas.

La consulta de investigación no utiliza nombres de escuela, estudiantes, registros, adjuntos o historial. Esta separación se aplica también en el servicio, aunque la opción de incluir registros esté activa. Lo escrito explícitamente en la pregunta sí se envía al proveedor y puede usarse para buscar; no introducir datos personales.

La respuesta y sus fuentes quedan en el historial del grupo de origen, aunque el docente cambie de grupo mientras espera. Guardar respuesta crea un material local con el resumen, fecha y enlaces. Se conserva el texto de los hallazgos, no una copia offline de las páginas completas. Los enlaces también funcionan en la vista previa de materiales; se abren en el navegador tras mostrar la URL.

## Fuentes y límites

- Responses API con `web_search`, acceso web activo, `tool_choice: required`, hasta tres llamadas de herramientas por respuesta y fuentes incluidas en el resultado.
- Fuentes procedentes de anotaciones `url_citation`: enlaces junto al texto y lista de referencias; fuentes consultadas pero no citadas se distinguen expresamente.
- Si no hay evidencia de búsqueda completada o citas válidas, se muestra un aviso de investigación sin verificación suficiente. No se valida automáticamente si una cita respalda cada afirmación.
- Se pide priorizar fuentes originales, diferenciar adaptación docente de contenido de la fuente y no inventar licencias, gratuidad ni fechas. Son instrucciones al modelo, no garantías de calidad.
- No es investigación profunda de larga duración: timeout de conexión/lectura de 120 segundos, sin reintento automático, descargas ni navegación autónoma en el equipo.
- Solo enlaces HTTP/HTTPS con estructura pública; se rechazan esquemas ejecutables, credenciales embebidas y direcciones locales comunes. No se hace auditoría DNS ni se promete bloquear toda redirección o página peligrosa; la apertura es manual en el navegador.

## Consumo

Las investigaciones comparten el límite mensual de intentos online con el chat. Cada reintento es otra solicitud, muestra aviso y conserva sus dominios y modo originales. El contador registra por separado búsquedas completadas (`search`) y su estimación a US$0.01 por acción, adicional a los tokens informados por el proveedor. Abrir páginas o buscar texto en ellas no se cuenta como otra acción de búsqueda. Las llamadas fallidas, estados desconocidos o respuestas incompletas dejan el costo web sin confirmar. No es una factura ni un límite monetario garantizado.

La tarifa de referencia se consultó el 13 octubre 2026: US$10 por mil búsquedas, más tokens de contenido a la tarifa del modelo. No se realizaron llamadas cobradas durante este desarrollo.

## Pruebas y migración

65 pruebas: 64 correctas en Linux y una omitida (DPAPI en Windows). Dieciséis casos nuevos verifican contrato de búsqueda, fuentes y enlaces, consumo separado, errores, aislamiento de datos, adjuntos rechazados, persistencia offline, reintentos, dominios, contador compartido y migración idempotente desde 0.3 conservando mensajes y consumo anterior. La compilación sintáctica también pasa.

No se ha validado visualmente la interfaz ni la búsqueda con una cuenta API real. Windows, DPAPI, rendimiento en PC básica y el instalador permanecen pendientes para 1.0 por acuerdo del usuario.

## Documentación oficial utilizada

- https://developers.openai.com/api/docs/guides/tools-web-search
- https://developers.openai.com/api/docs/models/gpt-6-luna
- https://developers.openai.com/api/docs/pricing
- https://developers.openai.com/api/reference/resources/responses/methods/create
