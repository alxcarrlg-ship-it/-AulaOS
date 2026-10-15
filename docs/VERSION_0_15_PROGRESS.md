# AulaOS 0.15 — materiales derivados de una planeación

## Implementado

Desde el editor de una planeación, «Materiales y presentación desde esta planeación» abre un paquete de clase. El docente describe la sesión, duración, idioma y recursos. Una solicitud online explícita prepara una guía docente (con respuestas o criterios), una actividad para alumnos y entre 2 y 20 diapositivas con notas del docente.

La petición comparte únicamente los textos editables de la planeación guardada y la instrucción del docente. No adjunta expedientes, historial, imágenes ni el archivo original. Se usa la credencial y el límite de intentos configurados. Cada paquete conserva una copia de la versión de origen; no modifica la planeación ni registra la clase como impartida.

Los textos se revisan y editan antes de usar. Cada guardado que cambia contenido crea una revisión inmutable; se bloquean guardados concurrentes obsoletos. Los paquetes se consultan por grupo y planeación. La guía y actividad se exportan por separado a Word. La presentación se exporta a PowerPoint con texto editable y notas separadas; las notas incluyen la identificación de la planeación y la revisión del paquete. Los archivos existentes no se sobrescriben.

La generación es online. Consultar, editar, guardar y exportar paquetes ya creados funciona sin conexión, sin instalar un modelo local. El generador no impone seis columnas ni otro formato docente fijo.

## Límites actuales

- Presentación de diseño sencillo, con texto, sin imágenes generadas. El editor cambia títulos, puntos y notas; todavía no agrega, elimina ni reordena diapositivas. El PPTX puede editarse en una aplicación compatible.
- No importa presentaciones existentes ni reproduce logos o el diseño de la planeación en estos materiales nuevos.
- El historial de revisiones se conserva en la base de datos; esta ventana abre la revisión actual, sin un selector de revisiones anteriores.
- No hay comprobación semántica automática de que las respuestas sean correctas o de que nunca aparezcan en el material del alumno. La revisión docente sigue siendo necesaria.
- Petición más planeación: hasta 18 KB. La respuesta está sujeta al límite de salida configurado; una respuesta incompleta se rechaza y no se reintenta automáticamente.
- Los límites de texto reducen saturación, pero no garantizan que cualquier combinación de palabras o fuente se distribuya correctamente. Revisar el archivo exportado antes de clase.
- No hay autoguardado ante cierre forzado. Se avisa de cambios sin guardar y se conserva lo editado mientras llega una generación nueva.

## Verificación

223 pruebas: 222 pasan en Linux y una de DPAPI se omite por requerir Windows. Las siete nuevas cubren origen inmutable, aislamiento entre grupos, historial y conflictos, validación de contenido, alcance y tamaño del contexto, respuestas incompletas y estructura PPTX con notas y protección contra sobrescritura. Compilación sintáctica correcta.

Una presentación de tres diapositivas generada por el exportador se importó y renderizó con Artifact Tool; se inspeccionaron las tres imágenes. La plantilla incluida se creó con esa herramienta, pero el programa no la requiere al ejecutar: usa lxml y empaquetado ZIP ya disponibles.

No se probaron una llamada real a OpenAI, calidad pedagógica con docentes, la interfaz en Windows ni apertura en PowerPoint para Windows. Las comprobaciones de Windows, PC básica e instalador siguen reservadas para 1.0.
