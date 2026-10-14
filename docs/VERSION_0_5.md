# Incremento 0.5 · Borradores y documentos exportables

13 octubre 2026, horario de México. Implementación sobre 0.4, sin sustituir datos existentes. No es una entrega instalable.

## Flujo implementado

- **Guardar respuesta** conserva el material y abre una copia editable. **Editar una copia** abre un borrador desde un material. **Borradores** permite crear, buscar por título y abrir los del grupo activo o de la conversación general.
- El editor muestra el grupo de origen, título, contenido y versión guardada. Trabaja sin red y admite texto con Markdown básico.
- Cada cambio guardado produce una versión nueva. Guardar sin cambios no duplica versiones. El historial permite revisar y restaurar versiones; la restauración añade otra versión y conserva las anteriores.
- Si otra ventana guardó antes, se bloquea la escritura desactualizada y se conserva el texto en el editor. Guardar copia permite rescatar esa edición en otro borrador.
- Adjuntar copia al chat crea un material inmutable correspondiente a una versión concreta. Editar después no cambia documentos ya adjuntos ni los usados en reintentos de mensajes.
- Exportar Word, HTML imprimible o Markdown guarda primero la versión que se exportará. Se utiliza el destino elegido por el docente; el diálogo de guardado solicita confirmación para reemplazar archivos existentes. La función de exportación rechaza reemplazos por defecto. Cuando se autoriza reemplazar, prepara el archivo temporal antes de sustituir el anterior.
- Antes de cerrar un editor con cambios se ofrece guardar, descartar o cancelar. El cierre normal de AulaOS respeta esos avisos y respalda SQLite, incluidas las versiones. No hay autoguardado periódico ni recuperación del texto aún no guardado tras un cierre forzado.

## Exportación

DOCX editable de tamaño Carta, tipografía Arial, títulos y encabezados, negritas, viñetas, números explícitos, tablas simples y enlaces externos. Encabezados de tabla repetidos, bordes claros, padding y anchos ajustados al contenido. Los enlaces de las fuentes se conservan mientras el docente mantenga su marcado en el texto. La edición es libre; las referencias no se verifican semánticamente.

HTML autónomo con estilos de impresión, caracteres escapados y política que bloquea scripts y recursos remotos. Se puede abrir en el navegador para imprimir usando sus funciones habituales. AulaOS no tiene un generador PDF propio en este incremento. Markdown exporta el título y el contenido sin depender de Word.

Subset de Markdown: títulos con uno a tres signos #, negrita simple, viñetas, líneas numeradas, enlaces HTTP/HTTPS, bloques de código y tablas rectangulares separadas por barras. Tablas de más de seis columnas se convierten en líneas de texto para conservar el contenido sin forzar columnas ilegibles. No admite tablas anidadas, celdas combinadas, imágenes, ecuaciones, notas al pie ni toda la sintaxis Markdown. No recupera formato de un DOCX importado ni reproduce logos y plantillas institucionales.

Límites: título de 200 caracteres y contenido de 120000. Borradores y materiales se aíslan por grupo. No se envía nada a OpenAI por editar, versionar o exportar. Para pedir una revisión a la IA se adjunta explícitamente una copia guardada al chat normal, con los controles ya existentes.

## Validación

- Suite completa: 86 pruebas; 85 correctas en Linux y una omitida porque requiere DPAPI en Windows.
- 21 casos nuevos cubren persistencia de versiones, restauración sin pérdida, conflictos entre conexiones, aislamiento, respaldo, inmutabilidad de adjuntos, conservación de datos 0.4, archivos Word reabiertos, enlaces, HTML sin ejecución de etiquetas incrustadas, exportación en los tres formatos y fallos de reemplazo sin dañar el archivo anterior.
- Compilación sintáctica y comprobación de diferencias sin errores de espacios.
- Documento sintético de dos páginas exportado con el mismo código de la aplicación, renderizado con LibreOffice y revisado en imágenes. Se verificaron las dos páginas, tablas multipágina con encabezados repetidos, títulos, caracteres en español, márgenes y enlaces. Se eliminó un borde decorativo heredado del estilo Title y se volvió a renderizar.
- Interfaz del editor no validada visualmente en Windows. No se hicieron llamadas API reales ni se generaron cargos de API. Siguen pendientes la prueba online real, plantillas avanzadas, voz y empaquetado/compatibilidad Windows para 1.0.

Dependencia nueva de desarrollo: `python-docx>=1.2,<2`. El usuario final no deberá instalar Python ni estas dependencias cuando exista el instalador.
