# AulaOS

Asistente docente para Windows, en desarrollo. Incremento interno **0.6**: acciones locales desde el chat, con vista previa, confirmación e historial. No hay un instalador validado ni se exige que el usuario final instale Python.

## Funciones implementadas

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

Los originales no se modifican. Se guarda el texto extraído en SQLite; no se preserva el diseño Word/Excel ni se ejecutan macros o fórmulas. Los archivos se eligen manualmente: no hay exploración automática del disco. Importar no envía documentos a OpenAI. Enviar una consulta online incluye los adjuntos seleccionados y el historial online del grupo, que puede contener información de documentos previamente usados. Los registros escolares se incluyen solo al activar su opción en la interfaz.

Credencial de sesión o guardado opcional mediante DPAPI de Windows; no se distribuye una clave compartida. `store: false` en la solicitud no promete retención cero del proveedor. El límite local cuenta intentos, no garantiza un máximo de dinero. Los fallos con consumo desconocido se muestran como tal.

El modo sin conexión permite consultar registros, leer y guardar materiales. No resume documentos con IA. La investigación web usa una solicitud independiente: solo la pregunta actual, sin registros, adjuntos ni historial. El docente debe incluir el tema y el nivel en esa pregunta. La exportación 0.5 crea documentos nuevos; no reproduce plantillas originales, logos ni diseños complejos. Transcripción, edición DOCX/PPTX preservando formato y acciones arbitrarias en lenguaje libre no están implementadas. Los borradores requieren guardar: se avisa antes de cerrar con cambios, pero no hay autoguardado ante un cierre forzado.

## Verificación

101 pruebas de lógica/datos/exportación: 100 pasan en Linux y 1 de DPAPI queda omitida por requerir Windows. Incluyen aislamiento entre grupos, fuentes seleccionadas, persistencia, reintentos, errores, costos simulados, formatos documentales, investigación con fuentes migración desde 0.3, borradores versionados, conflictos entre conexiones y protección de archivos exportados. Compilación sintáctica correcta. Word sintético de dos páginas renderizado y revisado visualmente en Linux, incluidos tablas, encabezados repetidos, márgenes y enlaces; no sustituye la validación en Word para Windows. Las llamadas a OpenAI se simulan; falta validación real con credencial. No se declara calidad pedagógica evaluada ni protección absoluta ante instrucciones maliciosas en documentos.

Por acuerdo del usuario, las comprobaciones de Windows, interfaz en ese sistema, rendimiento en PC básica e instalador quedan como requisitos de la versión **1.0**. No bloquean los incrementos de desarrollo 0.x.

## Desarrollo interno

Python, tkinter, SQLite, openpyxl y python-docx (exportación Word). Desde `lab/`, con dependencias de `requirements.txt` instaladas: `python -m unittest discover -s tests -v`.

Ver [alcance y comprobaciones de 0.6](docs/VERSION_0_6.md), [alcance de 0.5](docs/VERSION_0_5.md), [incremento 0.4](docs/VERSION_0_4.md), [incremento 0.3](docs/VERSION_0_3.md) y [arquitectura online/offline](docs/ARQUITECTURA_ONLINE_OFFLINE.md). Los datos reales y claves quedan fuera del repositorio.
