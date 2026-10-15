# AulaOS 0.21 — recuperación y diagnóstico

## Implementado

Copias locales recuperables cada 10 segundos cuando hay cambios en proyectos, evidencias nuevas y existentes, contenido de paquetes de clase, perfiles docentes y revisiones de propuestas. Se suman a borradores y documentos con plantilla. Admiten texto incompleto durante la edición; no crean versiones aprobadas ni aplican propuestas. Recuperar requiere selección y confirmación. Guardar sigue siendo explícito y conserva las comprobaciones de concurrencia del servicio correspondiente.

Las copias se separan por grupo, tipo, destino y sesión de ventana. Una recuperación conserva la revisión base: no permite sobrescribir silenciosamente una versión más nueva. Un cierre inesperado conserva la última copia; cerrar confirmando descartar elimina la copia de esa ventana. Pueden perderse los últimos segundos de escritura. La exclusión de ventanas activas es por proceso, no entre varias instancias de la aplicación.

La ventana de propuestas permite medir localmente el contexto de la planeación guardada y las fuentes seleccionadas frente al límite de 18,000 bytes UTF-8. No envía una consulta, no cuenta tokens ni estima facturación. Mantiene las validaciones de fuentes y requisitos; no resume ni recorta contenido silenciosamente. La generación conserva el límite anterior.

Texto y transcripción distinguen timeout, fallo de conexión y error TLS, incluidos errores envueltos por urllib. No se reintenta automáticamente; un timeout no prueba que el proveedor no haya procesado la solicitud o cobrado consumo.

## Verificación y límites

281 pruebas ejecutadas: 280 correctas en Linux y una de DPAPI omitida porque requiere Windows. Siete pruebas nuevas cubren recuperación de los cinco tipos ampliados, aislamiento, texto incompleto sin alterar datos aprobados, selección de campos, propuestas ya resueltas, límite de contexto y clasificación de errores sin duplicar solicitudes. Compilación sintáctica y revisión de espacios correctas.

No se probó la interfaz gráfica en esta entrega. Las llamadas de API son simuladas: no había credencial disponible para una evaluación real de calidad, latencia o costos. No se declara completada esa validación. Las peticiones nuevas de IA, aclaraciones, consultas de recursos y otros cuadros auxiliares siguen fuera de la recuperación automática. El paquete de clase debe existir para recuperar su contenido; su petición de generación no se recupera.

Ver [requisitos de cierre y revisión con Copilot](RELEASE_READINESS.md). Este incremento completa el alcance de código descrito, no certifica una versión de producción.
