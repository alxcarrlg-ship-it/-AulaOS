# AulaOS

Asistente docente para Windows, en desarrollo. Incremento interno **0.4**: investigación web opcional, con fuentes y hallazgos locales. No hay un instalador validado ni se exige que el usuario final instale Python.

## Funciones implementadas

- Asistencia, observaciones, pendientes, importación de listas Excel/CSV, conflictos, exportación HTML y respaldo SQLite.
- Conversaciones persistentes separadas por escuela/grupo; modo básico disponible sin internet ni modelos grandes.
- Integración OpenAI Responses, selección de perfil, límite mensual de intentos, estimaciones por tokens y reintentos manuales. API con facturación independiente de ChatGPT.
- Materiales por grupo: importar TXT, Markdown, CSV, DOCX y XLSX, revisar texto, buscar por título, guardar fragmentos y exportar texto Markdown.
- Adjuntar hasta tres materiales por consulta. Las fuentes se identifican como `[Mnumero]`; el modelo recibe instrucciones de citarlas, sin garantía automática de exactitud.
- Guardar la última respuesta como material y retomarla después. Los textos importados quedan disponibles aunque el archivo original cambie o desaparezca.

- Investigación opcional desde el chat: consulta independiente, filtro por dominios, citas enlazadas y fecha de consulta. Los hallazgos pueden guardarse como materiales para leerlos sin conexión.
- Estimación separada de búsquedas web, límite de tres llamadas de herramienta por consulta y reintentos conservando el modo y los dominios originales.

## Privacidad y límites

Los originales no se modifican. Se guarda el texto extraído en SQLite; no se preserva el diseño Word/Excel ni se ejecutan macros o fórmulas. Los archivos se eligen manualmente: no hay exploración automática del disco. Importar no envía documentos a OpenAI. Enviar una consulta online incluye los adjuntos seleccionados y el historial online del grupo, que puede contener información de documentos previamente usados. Los registros escolares se incluyen solo al activar su opción en la interfaz.

Credencial de sesión o guardado opcional mediante DPAPI de Windows; no se distribuye una clave compartida. `store: false` en la solicitud no promete retención cero del proveedor. El límite local cuenta intentos, no garantiza un máximo de dinero. Los fallos con consumo desconocido se muestran como tal.

El modo sin conexión permite consultar registros, leer y guardar materiales. No resume documentos con IA. La investigación web usa una solicitud independiente: solo la pregunta actual, sin registros, adjuntos ni historial. El docente debe incluir el tema y el nivel en esa pregunta. Transcripción, edición DOCX/PPTX preservando formato y herramientas de escritura automáticas no están implementadas.

## Verificación

65 pruebas de lógica/datos: 64 pasan en Linux y 1 de DPAPI queda omitida por requerir Windows. Incluyen aislamiento entre grupos, fuentes seleccionadas, persistencia, reintentos, errores, costos simulados, formatos documentales, investigación con fuentes y migración desde 0.3. Compilación sintáctica correcta. Las llamadas a OpenAI se simulan; falta validación real con credencial. No se declara calidad pedagógica evaluada ni protección absoluta ante instrucciones maliciosas en documentos.

Por acuerdo del usuario, las comprobaciones de Windows, interfaz en ese sistema, rendimiento en PC básica e instalador quedan como requisitos de la versión **1.0**. No bloquean los incrementos de desarrollo 0.x.

## Desarrollo interno

Python, tkinter, SQLite y openpyxl. Desde `lab/`, con dependencias de `requirements.txt` instaladas: `python -m unittest discover -s tests -v`.

Ver [alcance y comprobaciones de 0.4](docs/VERSION_0_4.md), [incremento 0.3](docs/VERSION_0_3.md) y [arquitectura online/offline](docs/ARQUITECTURA_ONLINE_OFFLINE.md). Los datos reales y claves quedan fuera del repositorio.
