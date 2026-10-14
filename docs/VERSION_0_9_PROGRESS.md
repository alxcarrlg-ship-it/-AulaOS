# AulaOS 0.9 — avance guardado, versión sin cerrar

14 de octubre de 2026. Este incremento continúa la 0.8; no declara terminada la 0.9 ni entrega un instalador.

## Bloque completado: propuestas para formatos propios

Desde el editor de documento con plantilla se puede pedir contenido indicando tema, grado, sesiones y requisitos. Se guarda primero la versión local. Tras confirmación de envío, OpenAI recibe la petición y la ubicación/texto actual de los párrafos editables. Esos textos pueden contener información personal: se informa antes de enviar. No se adjuntan rutas, archivo Word, imágenes, expedientes ni historial de chat. Ahora pueden incluirse materiales seleccionados explícitamente, como se describe abajo.

La IA debe devolver un objeto JSON con cambios por ID y notas sobre información faltante. Se rechazan respuestas incompletas, claves repetidas, campos inexistentes, textos inválidos y contenido fuera de límites. La solicitud puede generar consumo incluso si la propuesta se rechaza por formato. No hay reintento automático. Reutiliza perfil, credencial, tokens máximos y límite mensual actuales.

La propuesta se guarda aparte, con petición, revisión de origen, texto nuevo, notas y estado. El docente ve antes/después de todos los campos y puede aplicarla completa o descartarla. Aplicar crea una nueva revisión del documento y conserva anteriores; aplicar dos veces no duplica versiones. Si el documento cambió durante o después de la consulta, la propuesta no sobrescribe esos cambios. Las propuestas sobreviven al reinicio y se reabren desde el mismo botón.

No se impone un número de columnas. Los campos omitidos mantienen su contenido. No se agregan filas ni se reconstruye el formato. El renderizador y las restricciones de 0.7 siguen vigentes. Se puede exportar la versión aprobada e importarla como material para revisarla en el chat.

## Límites del avance

- Generación por campos implementada, calidad semántica y pedagógica todavía no evaluada con un modelo real.
- Las instrucciones al modelo piden no inventar hechos ni requisitos; no son garantía de exactitud.
- Hasta 18 KB de petición + campos y 6000 caracteres de petición. El límite de respuesta del perfil puede ser insuficiente para formatos grandes; se rechaza JSON incompleto sin modificar documentos.
- Se aplica o descarta la propuesta completa. La selección/edición de cambios individuales aún no está implementada; después de aplicar se puede editar o recuperar una revisión anterior.
- No consulta internet en este flujo. Puede usar hasta tres materiales seleccionados del mismo grupo, dentro del límite total de 18 KB.
- Las propuestas de plantilla no ejecutan acciones escolares ni comandos del sistema. La interpretación natural de tareas/observaciones está disponible mediante el flujo separado descrito abajo; no ejecuta acciones por el mero envío de una conversación normal.
- No hay autoguardado ante cierre forzado de una petición todavía no enviada.

## Verificación de este bloque

162 pruebas totales: 161 pasan en Linux y una de DPAPI queda omitida por requerir Windows. Trece nuevas cubren revisión sin escritura, aplicación idempotente, descarte persistente, aislamiento, cambios concurrentes, JSON inválido/duplicado/campos inexistentes, propuesta sin cambios, exclusión de expedientes/rutas, límites antes de llamar al proveedor, conservación de ediciones anteriores, rollback atómico, formatos variables y flujo propuesta → versión → Word → material → chat.

Proveedores simulados. No se hizo una llamada real a OpenAI. Se verificó compilación y diferencias. No se cambió el motor de renderizado; la comprobación visual de formatos permanece en 0.7. No se probó la nueva interfaz en Windows.

## Segundo bloque completado: lenguaje natural y fuentes

**Acciones con tus palabras.** Desde el cuadro del chat, «Preparar acción con IA» permite pedir una tarea, observación o borrador sin escribir comandos con separadores. El botón de interpretación indica el envío online y el consumo. Se transmiten solo la petición y la fecha local; las listas de alumnos, materiales y conversaciones quedan fuera. El texto dictado de 0.8 puede pasarse al chat y usarse como petición, sin envío ni ejecución automáticos.

El modelo devuelve una sola operación admitida o una pregunta aclaratoria. Se validan tipo, claves, tamaños y fechas. Para observaciones, el nombre o #ID devuelto debe estar escrito en la petición; la búsqueda se realiza localmente dentro del grupo capturado al abrir la ventana. Si no hay una única coincidencia, se pide nombre completo/ID. La propuesta conserva petición original, notas de la interpretación y destino; sigue pasando por «Acciones» para confirmar/cancelar. El registro objetivo solo se crea al confirmar. Las fechas interpretadas también necesitan revisión. Una tarea es un pendiente, no una alarma.

La aplicación no garantiza entender correctamente cualquier frase, ni maneja listas de acciones múltiples. El flujo normal del chat sigue conversando; el docente elige expresamente cuándo preparar una acción. Para aclarar, se modifica la petición y se pide otra interpretación; no existe una conversación autónoma de herramientas entre varios turnos. Los comandos offline anteriores continúan disponibles.

**Fuentes para el formato.** En las propuestas de plantilla se puede marcar «Usar los materiales seleccionados para el chat de este grupo». Se muestran los títulos antes de confirmar el envío. El contexto combina petición, campos y hasta tres fuentes, con límite conjunto de 18 KB. La propuesta guarda el texto de las fuentes utilizadas y las muestra en su revisión; un cambio posterior del archivo original no altera esas copias. Se rechazan referencias `[Mnumero]` a materiales que no fueron enviados. Esto verifica la identidad de la cita, no su exactitud semántica. Los identificadores M son internos: una bibliografía o referencias externas adecuadas deben revisarse antes de entregar el Word.

Una investigación web guardada como material se puede seleccionar como fuente. No se realiza una búsqueda nueva durante la propuesta de plantilla. Se conserva el contenido y enlaces de ese material dentro de la copia de procedencia; no se garantiza que el modelo incorpore todas sus referencias al texto final.

Dieciséis pruebas adicionales cubren confirmación antes de escritura, identificación local, homónimos, alumnos inventados, IDs de otro grupo, exclusión de listas en la solicitud, tipos/fechas/campos no admitidos, borradores con texto literal, identidad cambiada, compatibilidad offline, fuentes seleccionadas, rechazo de fuentes de otro grupo, citas desconocidas y procedencia persistente.

No hay clave API configurada en este entorno: interpretación, redacción y uso real de fuentes siguen sin evaluarse contra el servicio. No se declara terminada la 0.9.

## Próximo punto de reanudación

1. Evaluar y pulir las peticiones naturales ya implementadas, especialmente aclaraciones, fechas y nombres ambiguos.
2. Evaluar la adaptación de fuentes a los campos y mejorar la revisión de cambios individuales y referencias de salida.
3. Evaluar con API real generación, mapeo de campos, errores de formato, duración y consumo; probar transcripción real cuando haya credencial/hardware disponible.
4. Revisar visualmente documentos resultantes de propuestas reales y formatos representativos. Corregir cortes y problemas de distribución.
5. Completar la revisión integral de flujos y requisitos pendientes antes de cerrar 0.9. Windows, dispositivos, PC básica e instalador siguen en 1.0.

La numeración no garantiza que todos los requisitos quepan en un solo incremento; si hace falta, se documentarán incrementos adicionales en lugar de declarar listo algo sin validar.
