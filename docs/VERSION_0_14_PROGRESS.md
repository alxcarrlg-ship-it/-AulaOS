# AulaOS 0.14 — investigar, comparar y adaptar recursos

14 de octubre de 2026, hora de México. Incremento implementado; calidad de investigación/adaptación y comportamiento gráfico pendientes de evaluación real.

## Recorrido disponible

«Recursos web» abre un historial por grupo. El docente escribe tema, objetivo, nivel, minutos y materiales disponibles. Puede limitar la búsqueda con dominios públicos opcionales. Solo se envía esa petición: no se incorporan automáticamente expedientes, proyectos, perfiles, archivos ni historial del chat.

La investigación reutiliza la búsqueda de 0.4 y su control de consumo. Solicita hasta cinco recursos comparados por pertinencia, nivel, tiempo estimado, materiales/tecnología y limitaciones. Pide distinguir hechos de estimaciones, señalar costo/licencia/disponibilidad no comprobados y recomendar una alternativa sin pantalla cuando proceda. Son instrucciones al modelo; el formato y calidad de la comparación aún no están evaluados con API real.

El texto y las fuentes recibidas se guardan localmente. Solo los metadatos de citas del proveedor alimentan la lista seleccionable, no enlaces que aparezcan simplemente en el texto. Una búsqueda incompleta, sin citas o sin metadatos suficientes se conserva marcada como no confirmada y no habilita adaptación. «Con fuentes» no garantiza exactitud de las afirmaciones ni que el recurso sea adecuado.

Sobre una investigación completa, se eligen de una a tres fuentes citadas y se escribe la petición de adaptación. Esta segunda consulta, confirmada por separado, recibe la petición, resumen completo de la investigación y fuentes seleccionadas. No busca de nuevo ni descarga páginas. Solicita una propuesta propia con objetivo, pasos, tiempos, materiales, evaluación, adecuación y límites. La salida debe usar exactamente los identificadores seleccionados; se rechazan referencias o enlaces explícitos ajenos, JSON inválido y textos fuera de límites. La validación de identificadores no comprueba semánticamente cada afirmación.

El resumen puede mencionar otras fuentes, aunque se instruye al modelo para usar solo las elegidas. No existe extracción independiente del texto íntegro de cada fuente. La adaptación queda identificada como propuesta de AulaOS basada en un resumen y conserva los enlaces de procedencia. No se declara copia del material original ni permiso para reutilizarlo íntegramente.

## Reutilización y control

«Guardar resultado como material» conserva la petición, el resultado y su procedencia en el grupo. Guardar dos veces el mismo resultado reutiliza el material existente. Puede seleccionarse después desde Materiales para el chat o una propuesta de plantilla; no se adjunta automáticamente ni se modifica una planeación, avance o registro escolar.

Leer el historial y guardar como material son operaciones locales. Buscar y adaptar son consultas online separadas, contabilizadas con los límites existentes. No hay reintentos automáticos. Se conserva la última respuesta estructurada en el proveedor medido para obtener citas sin cambiar el contrato textual del chat; se borra antes de una nueva solicitud para no reutilizar citas tras un fallo.

Petición de hasta 6000 caracteres; contexto de adaptación hasta 18 KB sin recorte oculto. Resultados guardados hasta 100000 caracteres. Una investigación extensa puede requerir una búsqueda más acotada antes de adaptar. La petición aún no enviada no tiene autoguardado; los resultados completados sí se conservan.

## Verificación

216 pruebas totales: 215 pasan en Linux y una de Windows queda omitida. Once pruebas nuevas cubren procedencia y relación búsqueda/adaptación, exclusión de registros, aislamiento, resultados incompletos/no confirmados, ausencia de metadatos, fuentes solo consultadas, selecciones y respuestas inválidas, material reutilizable, límite antes de llamar, fallos sin reintento y conservación/limpieza de metadatos con registro de consumo. Compilación y diferencias correctas.

Proveedores simulados. No se evaluó calidad real, gratuidad/licencia de recursos específicos ni interfaz gráfica. No se añadió descarga de PDF, análisis de páginas completas, generación de presentaciones ni investigación autónoma prolongada. Se mantienen los pendientes de API real, Windows, hardware e instalador.

## Siguiente alcance propuesto

0.15: materiales de clase conectados con la planeación y presentaciones. Antes de declararlos listos requerirán contenido coherente y comprobación visual de los archivos exportados.
