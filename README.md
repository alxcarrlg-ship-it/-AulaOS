# AulaOS

Asistente docente para Windows, en desarrollo. **0.10 en desarrollo**, sobre los avances de 0.9: propuestas de contenido por campo con fuentes seleccionadas y preparación de acciones en lenguaje natural, siempre revisables. Inicia la continuidad de revisiones; siguen pendientes las validaciones reales de 0.9. No hay un instalador validado ni se exige que el usuario final instale Python.

## Funciones implementadas

- Avance 0.10: guardar y recuperar revisiones manuales de propuestas sin aplicarlas, con protección entre ventanas. [Alcance y pendientes](docs/VERSION_0_10_PROGRESS.md).
- Avance 0.9: propuestas online por campo de plantilla con hasta tres materiales seleccionados; revisión antes/después, selección y edición de campos, fuentes conservadas y aplicación como versión nueva. Aislamiento y bloqueo de cambios concurrentes.
- Preparar una tarea, observación o borrador con tus palabras desde el chat. La interpretación online genera una propuesta; la identificación de alumnos se resuelve localmente y los homónimos piden aclaración. Confirmar sigue siendo obligatorio. Aún sin evaluación pedagógica ni prueba real de API.

- Catálogo local de carpetas por grupo, búsqueda por nombre/ruta desde `/buscar`, lectura previa y copias inmutables para adjuntar. Detecta cambios entre vista previa y adjunto.
- Grabación local hasta 30 segundos, importación de audio y transcripción OpenAI explícita. Revisión editable, historial por grupo y paso al cuadro del chat sin enviar ni ejecutar automáticamente.

- Plantillas DOCX propias: reconocer tablas de diferentes tamaños, celdas combinadas, encabezados, pies y párrafos editables. Las seis columnas son una preferencia particular, no una regla del programa.
- Crear documentos versionados sobre una copia del formato, insertar texto de borradores y exportar conservando logos incrustados, tablas y márgenes. Adjuntar voluntariamente la estructura al chat para orientar el contenido.

- Crear tareas, registrar observaciones de alumnos y guardar borradores desde comandos del chat. Vista previa por escuela/grupo, confirmación explícita, cancelación e historial persistente. Funcionan sin internet; `/acciones` muestra los formatos. No se ejecutan instrucciones de documentos ni respuestas del modelo.

- Asistencia, observaciones, pendientes, importación de listas Excel/CSV, conflictos, exportación HTML y respaldo SQLite.
- Conversaciones persistentes separadas por escuela/grupo; modo básico disponible sin internet ni modelos grandes.
- Integración OpenAI Responses, selección de perfil, límite mensual de intentos, estimaciones por tokens y reintentos manuales. API con facturación independiente de ChatGPT.
- Materiales por grupo: importar TXT, Markdown, CSV, DOCX y XLSX, revisar texto, buscar por título, guardar fragmentos y exportar texto Markdown.
- Adjuntar hasta tres materiales por consulta. Las fuentes se identifican como `[Mnumero]`; el modelo recibe instrucciones de citarlas, sin garantía automática de exactitud.
- Guardar la última respuesta como material y retomarla después. Los textos importados quedan disponibles aunque el archivo original cambie o desaparezca.

- Investigación opcional desde el chat: consulta independiente, filtro por dominios, citas enlazadas y fecha de consulta. Los hallazgos pueden guardarse como materiales para leerlos sin conexión.
- Estimación separada de búsquedas web, límite de tres llamadas de herramienta por consulta y reintentos conservando el modo y los dominios originales.

- Editor offline de borradores desde una respuesta, un material o una página en blanco. Versiones recuperables y detección de cambios simultáneos entre ventanas.
- Exportación de documentos nuevos a Word, HTML imprimible y Markdown, con títulos, negritas, listas, tablas básicas y enlaces. Copias inmutables para adjuntar versiones concretas al chat.

## Privacidad y límites

Los originales no se modifican. En Materiales se guarda el texto extraído en SQLite, sin preservar diseño Word/Excel. En Plantillas se conserva el paquete DOCX completo para crear copias con su estructura. No se ejecutan macros o fórmulas. Los archivos se eligen manualmente o se encuentran en carpetas autorizadas por el docente. El catálogo se actualiza a petición, sin explorar el resto del disco ni enviar archivos al buscar. Importar no envía documentos a OpenAI. Enviar una consulta online incluye los adjuntos seleccionados y el historial online del grupo, que puede contener información de documentos previamente usados. Los registros escolares se incluyen solo al activar su opción en la interfaz.

Las transcripciones se guardan localmente por grupo. El audio solo se envía al pulsar Transcribir y confirmarlo; cada intento comparte el límite mensual del chat. El costo de audio se muestra como no confirmado, sin estimación de tarifa textual. Las grabaciones están en memoria hasta guardarlas; no forman parte del respaldo SQLite.

Credencial de sesión o guardado opcional mediante DPAPI de Windows; no se distribuye una clave compartida. `store: false` en la solicitud no promete retención cero del proveedor. El límite local cuenta intentos, no garantiza un máximo de dinero. Los fallos con consumo desconocido se muestran como tal.

El modo sin conexión permite consultar registros, leer y guardar materiales. No resume documentos con IA. La investigación web usa una solicitud independiente: solo la pregunta actual, sin registros, adjuntos ni historial. El docente debe incluir el tema y el nivel en esa pregunta. La exportación 0.5 crea documentos nuevos; no reproduce plantillas originales, logos ni diseños complejos. Las plantillas 0.7 permiten edición selectiva de texto conservando su estructura; el avance 0.9 añade propuestas de contenido por campo, que requieren revisión y todavía no tienen calidad semántica validada. La transcripción 0.8 es online; no hay reconocimiento de voz offline, conversación de voz en tiempo real, edición PPTX ni acciones arbitrarias en lenguaje libre. Los borradores requieren guardar: se avisa antes de cerrar con cambios, pero no hay autoguardado ante un cierre forzado.

## Verificación

171 pruebas de lógica/datos/exportación: 170 pasan en Linux y 1 de DPAPI queda omitida por requerir Windows. Incluyen aislamiento entre grupos, fuentes seleccionadas, persistencia, reintentos, errores, costos simulados, formatos documentales, investigación con fuentes migración desde 0.3, borradores versionados, conflictos entre conexiones y protección de archivos exportados. Compilación sintáctica correcta. Word sintético de dos páginas renderizado y revisado visualmente en Linux, incluidos tablas, encabezados repetidos, márgenes y enlaces; no sustituye la validación en Word para Windows. Las llamadas a OpenAI y la captura del micrófono se simulan; falta validación real con credencial y hardware. No se declara calidad pedagógica evaluada ni protección absoluta ante instrucciones maliciosas en documentos.

Además, tres formatos sintéticos de 3/6/8 columnas renderizados e inspeccionados en Linux para 0.7.

Por acuerdo del usuario, las comprobaciones de Windows, interfaz en ese sistema, rendimiento en PC básica e instalador quedan como requisitos de la versión **1.0**. No bloquean los incrementos de desarrollo 0.x.

## Desarrollo interno

Python, tkinter, SQLite, openpyxl, python-docx, lxml y sounddevice (micrófono). Desde `lab/`, con dependencias de `requirements.txt` instaladas: `python -m unittest discover -s tests -v`.

Ver [avance y pendientes de 0.9](docs/VERSION_0_9_PROGRESS.md), [alcance de 0.8](docs/VERSION_0_8.md), [alcance de 0.7](docs/VERSION_0_7.md), [alcance de 0.6](docs/VERSION_0_6.md), [alcance de 0.5](docs/VERSION_0_5.md), [incremento 0.4](docs/VERSION_0_4.md), [incremento 0.3](docs/VERSION_0_3.md) y [arquitectura online/offline](docs/ARQUITECTURA_ONLINE_OFFLINE.md). Los datos reales y claves quedan fuera del repositorio.
