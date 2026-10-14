# AulaOS 0.6 — acciones revisables desde el chat

Incremento interno del 14 de octubre de 2026. Continúa sobre 0.5 sin reemplazar registros existentes.

## Qué funciona

- `/tarea Revisar cuadernos | 2026-10-20`: propuesta de pendiente, fecha opcional.
- `/observacion Ana Pérez | Participó en la lectura | 2026-10-14`: observación con nombre completo o `#ID`; la fecha omitida se resuelve al día local de la propuesta y queda visible antes de confirmar.
- `/borrador Guía de lectura | Contenido del borrador`: nuevo documento editable con versión 1; el contenido se conserva, no se genera con IA offline.
- Alternativas: `crea tarea:`, `registra observación:`, `crea borrador:` seguidas del mismo formato. `/acciones` muestra ayuda.
- Acciones disponibles con cualquier modo seleccionado, sin llamada online, sin enviar adjuntos ni registros. Las consultas abiertas siguen el flujo online existente.
- Vista previa con escuela/grupo, alumno e identificador, fecha y texto exacto. Botón «Acciones» con pendientes, aplicadas y canceladas. La propuesta se abre tras la respuesta si quedan acciones por confirmar.
- Confirmar crea el registro. Cancelar conserva el historial y no crea registros. Para corregir: cancelar y enviar una propuesta nueva. Al confirmar un borrador se abre el editor de 0.5.

## Integridad

Los nombres parciales o ambiguos no se seleccionan automáticamente. Se ofrecen coincidencias del grupo con ID; antes de guardar se vuelve a verificar identidad, actividad y nombre del grupo/escuela. No se alteran asistencias, registros previos, Excel originales ni archivos del disco.

El registro objetivo y el estado aplicado se guardan en una sola transacción SQLite. Confirmar de nuevo devuelve el resultado previo sin duplicarlo, incluso desde otra conexión. Los reintentos del mismo mensaje recuperan su propuesta mediante ID del mensaje. Dos solicitudes nuevas idénticas sí son propuestas independientes que requieren confirmación propia.

Las propuestas sobreviven al reinicio y están incluidas en el respaldo SQLite. El historial de Acciones es la referencia actual de su estado; la respuesta original del chat conserva la vista previa histórica. No hay deshacer de una acción aplicada en esta versión.

## Límites y comprobaciones

Esto es un intérprete local de formatos explícitos, no ejecución general de herramientas por IA ni comprensión arbitraria del lenguaje natural. No interpreta «mañana» como fecha; requiere AAAA-MM-DD y muestra errores antes de preparar cambios. Una observación no evalúa ni inventa hechos del alumno. Los borradores se crean con texto suministrado; la generación avanzada sigue siendo online y puede guardarse con el flujo de 0.5.

101 pruebas: 100 pasan y una de DPAPI se omite en Linux. Las 15 nuevas cubren propuesta sin escritura, cancelación persistente, aislamiento, homónimos, cambios de identidad/destino, creación de borradores, entradas inválidas, ámbito general, ruta sin proveedor, comandos explícitos, recuperación, rollback y doble confirmación entre conexiones. Se conserva la suite previa de chat, materiales, web y exportación. Compilación sintáctica y revisión de diferencias realizadas.

No se ejecutaron llamadas reales a OpenAI. La interfaz de Windows, rendimiento en equipos básicos e instalador se mantienen para 1.0. Próximo alcance propuesto: 0.7, plantillas y calidad visual de materiales.
