# AulaOS 0.8 — carpetas elegidas y voz revisable

14 de octubre de 2026. Continúa los formatos variables de 0.7; las seis columnas siguen siendo una preferencia particular y no una restricción del programa.

## Carpetas y búsqueda local

- Elegir carpetas por grupo, recordar esas ubicaciones y actualizar su catálogo sin volver a elegir cada archivo.
- Buscar por fragmento del nombre/ruta desde la ventana o con `/buscar planeación` en el chat. Esa ruta funciona incluso con el modo online seleccionado, sin llamada a OpenAI.
- Catálogo de TXT, MD, CSV, DOCX y XLSX. La búsqueda consulta nombres y metadatos, no un índice semántico del contenido.
- Leer un resultado, revisar su contenido y guardar una copia para adjuntarla. Los archivos originales no se modifican. Si cambia el contenido tras revisarlo, se exige otra vista previa. Los adjuntos anteriores no cambian.
- Desvincular quita el catálogo, no los archivos ni las copias ya guardadas.
- Escaneo explícito y acotado: 5000 entradas, profundidad 12 y límite de tiempo revisado de 15 segundos. No es un límite duro frente a una llamada del sistema de archivos bloqueada. El resultado informa cuando es parcial o hay rutas inaccesibles.
- Se omiten enlaces simbólicos, puntos de redirección de Windows, archivos ocultos por nombre, temporales de Office y archivos mayores a 10 MB. No se escanea el resto del equipo. Una carpeta desconectada conserva su catálogo previo y el error queda visible.
- Archivos disponibles solo en la nube pueden requerir descarga por el cliente de sincronización; no se promete acceso offline a esos originales. Las copias ya importadas sí son locales.

## Voz

- Grabar hasta 30 segundos en memoria con micrófono, detener antes del límite y guardar el audio como archivo nuevo si se desea.
- Elegir audio MP3, MP4, MPEG, MPGA, M4A, WAV o WebM hasta 25 MB. No se convierten ni fragmentan audios grandes automáticamente.
- Pulsar Transcribir y confirmar el envío a OpenAI. Idioma automático, español o inglés. Se utiliza `gpt-4o-mini-transcribe` con respuesta JSON.
- Solo se envían los bytes del audio, modelo, formato y preferencia de idioma; no el nombre original del archivo, rutas, expedientes escolares, adjuntos o historial del chat.
- Cada intento de transcripción comparte el límite mensual local. El costo queda sin estimación confirmada para no aplicar tarifas de texto al audio. Errores también cuentan; no hay reintentos automáticos.
- Transcripción original persistente por grupo; texto editable para revisar nombres, fechas y números, guardar como material o añadir al cuadro del chat. No se envía el texto automáticamente ni se ejecutan acciones escolares por reconocer una frase.
- Los procesos usan trabajadores y conexiones SQLite propias. No se puede cerrar una ventana con una solicitud activa; detener una grabación no envía audio. Se pregunta antes de descartar una grabación no guardada o cambios de texto.
- El antiguo botón de grabación abre el nuevo flujo de voz. Ya no crea automáticamente una observación por el simple hecho de grabar.

## Límites

No hay reconocimiento offline, voz en tiempo real, respuesta hablada, detección de hablantes ni garantía de transcripción exacta. Se necesita internet y una clave API para transcribir. Grabar y guardar audio no requieren una llamada online. No se reproduce audio desde esta interfaz; el archivo puede guardarse y escucharse con el reproductor del equipo.

No hay escaneo permanente ni selección autónoma de fuentes: la búsqueda encuentra nombres y el docente revisa qué archivo compartir. La indexación semántica y la adaptación automática de contenido a campos de plantilla siguen pendientes. El componente de micrófono puede no estar disponible en algunos entornos; importar un audio es una alternativa.

Las transcripciones y el catálogo están en SQLite y su respaldo. Las grabaciones en memoria se pierden ante cierre forzado; los archivos de audio guardados por el usuario son externos al respaldo SQLite. Desvincular carpetas no borra transcripciones, materiales o mensajes previos.

## Validación

133 pruebas: 132 pasan en Linux y una DPAPI se omite por requerir Windows. Dieciocho pruebas nuevas: búsqueda por nombre normalizado, subcarpetas, aislamiento, desvinculación sin borrar originales, modificación tras vista previa, archivos borrados, enlaces/rutas fuera del ámbito, límites de escaneo, carpeta desconectada, búsqueda local sin proveedor, multipart sin ruta original, entradas/respuestas inválidas, transcripción persistida sin ejecutar acciones, fallos sin reintento, límite mensual compartido, captura acotada, cancelación y conservación del audio original.

Compilación sintáctica y diferencias revisadas. Transcripción HTTP y captura se prueban con dobles; no se hizo una llamada real de voz ni se probó un micrófono físico. Windows, dispositivos, rendimiento de PC básica e instalador permanecen como requisitos de 1.0. La versión 0.9 deberá integrar los flujos y abordar requisitos pendientes antes de declarar el producto listo.

Referencia oficial consultada para endpoint, multipart, modelo, idioma y respuesta JSON:
https://developers.openai.com/api/reference/resources/audio/subresources/transcriptions/methods/create
