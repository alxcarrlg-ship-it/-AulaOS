# Incremento 0.3 · Materiales y contexto seleccionado

Fecha: 13 octubre 2026. Continúa la base existente; incluye el incremento online 0.2 que aún no se había guardado en GitHub. No es una entrega instalable.

## Flujo implementado

1. Elegir escuela/grupo o conversación general.
2. Abrir Materiales, importar un archivo y revisar el texto extraído y sus avisos.
3. Seleccionar hasta tres materiales para la próxima consulta. Selección independiente por grupo.
4. En modo online, enviar una pregunta; las fuentes seleccionadas se incluyen como datos y se pide citarlas con identificadores M. Sin conexión, se muestran las referencias y se conserva la lectura local.
5. Guardar la última respuesta como material; encontrarla por título, leerla sin internet o exportarla a Markdown.

La selección se consume al enviar, sin adjuntar archivos automáticamente a la siguiente pregunta. El historial online sí continúa y puede contener información derivada de fuentes anteriores. Un reintento utiliza los mismos materiales del mensaje original, aunque cambie la selección de la interfaz; se muestra un aviso de nueva solicitud/costo. Los adjuntos asociados al mensaje quedan registrados.

## Límites explícitos

- Importación: 10 MB por archivo, 40 MB descomprimidos, 120000 caracteres de texto. XLSX: hasta 100000 celdas leídas en total; también se rechazan dimensiones declaradas mayores por hoja.
- Contexto de adjuntos: hasta tres materiales y 18000 bytes serializados. Se rechaza antes de solicitar IA si no cabe; nunca se recorta silenciosamente. Puede seleccionarse un fragmento de la vista previa y guardarlo como material independiente.
- DOCX: párrafos y texto de tablas del cuerpo. No imágenes, OCR, encabezados/pies ni fidelidad visual.
- XLSX: todas las hojas dentro del límite, nombres y coordenadas. Fórmulas como texto, sin cálculo. No XLS/XLSM como adjuntos de esta versión.
- El importador de materiales CSV está separado del importador de alumnos: guardar un documento no altera listas, asistencia o calificaciones.
- Los materiales son instantáneas de texto; no copias completas del archivo binario, ni sincronización con sus cambios posteriores. Se deduplican por huella dentro del mismo grupo.
- Las citas se solicitan al modelo, no se validan semánticamente. No hay herramientas que ejecuten instrucciones de documentos ni escritura autónoma de archivos.

## Evidencia

Suite completa: 49 pruebas, 48 correctas en Linux, 1 omitida (DPAPI en Windows). Quince casos nuevos de documentos cubren DOCX, XLSX, CSV, reinicio, aislamiento, selección explícita, reintento, límites y archivos inválidos. Las pruebas de OpenAI usan respuestas simuladas, sin cargos ni claves reales. Compilación sintáctica de módulos correcta.

## Pendientes para 1.0

Prueba de API real y calidad de resultados; validación Windows, DPAPI, interfaz, accesibilidad y rendimiento en PC básica; empaquetado e instalador sin Python para el usuario; cumplir las capacidades pendientes de investigación, voz, documentos y herramientas adaptables antes de declarar la aplicación completa.
