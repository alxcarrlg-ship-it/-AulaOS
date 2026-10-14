# AulaOS 0.7 — formatos propios por docente y escuela

14 de octubre de 2026. Decisión de producto: **las seis columnas de Alex son un caso particular, no una regla del programa**. AulaOS debe adaptarse a lo que pide cada centro y a los cambios de formato de un mismo docente.

## Implementado

- Biblioteca local de plantillas DOCX del grupo, con nombre de variante y docente. Cada importación guarda el archivo original completo, su huella y estructura. Se pueden conservar varias variantes sin sustituir las anteriores.
- Reconocimiento estructural de tablas, número de columnas de cuadrícula, filas, celdas combinadas, secciones, imágenes, encabezados, pies y párrafos editables. No exige seis columnas ni una nomenclatura de planeación particular.
- Documentos separados de la plantilla, edición de párrafos/celdas, guardado de versiones, recuperación de contenido anterior y detección de conflictos entre ventanas.
- Copias Word basadas en el paquete original. Se mantienen imágenes/logos incrustados, estilos, geometría de tablas, orientación y márgenes. Solo cambian las partes XML que contienen el texto editado; las demás partes se conservan byte a byte.
- El texto nuevo de un párrafo toma las propiedades de su primer tramo. No se promete mantener diferentes negritas/colores dentro del contenido reemplazado. Los párrafos no editados conservan sus tramos originales.
- Insertar texto de un borrador en un campo seleccionado. El contenido se inserta como texto literal: no convierte Markdown a formato Word ni distribuye automáticamente una respuesta entre columnas.
- Adjuntar voluntariamente una copia textual de la estructura al chat para pedir contenido adecuado al formato. Incluye el texto previo de la plantilla, con aviso antes de seleccionarla. Importar, editar y exportar no envían el Word a OpenAI.
- Originales y archivos existentes no se sobrescriben. Los documentos siguen funcionando si se borra el archivo fuente. Plantillas y versiones están incluidas en el respaldo SQLite.

## Flujo

Plantillas → Importar Word → revisar estructura → Crear documento → seleccionar campo → editar o insertar contenido de borrador → Guardar versión → Exportar Word con nombre nuevo.

Para una nueva exigencia escolar: importar el Word actualizado con otro nombre de variante. Los documentos anteriores siguen ligados a su formato original. La etiqueta de docente organiza formatos, no implementa cuentas o autenticación multiusuario.

## Límites expresos

El reconocimiento es estructural, no comprensión pedagógica automática. No detecta por sí solo qué significa cada casilla, no garantiza que una planeación cumpla todos los requisitos institucionales y no llena todo el documento a partir de una orden libre. Esa adaptación semántica revisable sigue siendo un requisito previo al producto final.

La edición conserva la estructura existente: no agrega sesiones/filas ni rediseña tablas. Para ampliar el formato, se importa una variante actualizada. El texto largo puede cambiar páginas o desbordar celdas con altura fija; se debe revisar el Word exportado. No se promete fidelidad visual universal para todos los documentos.

Se conservan sin editar los párrafos con dibujos, enlaces, campos dinámicos, controles de contenido o cambios controlados. Se rechazan paquetes protegidos, con macros, objetos incrustados, firmas digitales o recursos externos vinculados que no sean hipervínculos. Los hipervínculos se conservan, no se visitan. No admite PDF escaneado, OCR, DOC antiguo, XLSX o PPTX como plantillas en esta versión.

Límites: 10 MB por DOCX, 40 MB descomprimidos, 3000 entradas ZIP, 5000 párrafos editables y 120000 caracteres modificados. Adjuntar una estructura al chat conserva los límites de materiales de 0.3; formatos grandes requieren seleccionar un fragmento. Sin autoguardado ante cierre forzado.

## Comprobaciones

115 pruebas: 114 pasan en Linux y una de DPAPI se omite por requerir Windows. Catorce pruebas nuevas verifican formatos de 3, 6 y 8 columnas, celdas combinadas, imágenes, piezas XML no modificadas, estilo inicial, campos vacíos, encabezados/pies, versiones, aislamiento por grupo, conflictos, respaldo, independencia de variantes y protección de originales.

Tres documentos sintéticos (3/6/8 columnas), de una página cada uno, renderizados e inspeccionados visualmente en Linux: texto legible, tablas y fila combinada conservadas, imagen de prueba y pie conservados, orientación vertical/horizontal correcta. No se usaron ni validaron los Word reales de Alex en este incremento. No se realizaron llamadas reales a OpenAI. Windows, rendimiento en PC básica e instalador permanecen para 1.0.
