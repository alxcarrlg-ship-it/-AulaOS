# AulaOS 0.16 — reconocer y nombrar campos del formato docente

## Implementado

El reconocimiento local de plantillas DOCX añade pistas de significado sin modificar el archivo: etiquetas seguidas de dos puntos, etiquetas en la celda anterior, encabezados candidatos de la primera fila y secciones reconocidas por estilos de título o nivel de esquema. La correspondencia de columnas considera el ancho de las celdas combinadas horizontalmente y el inicio de cuadrícula de cada fila. Las tablas anidadas usan sus propios encabezados.

El editor muestra el nombre sugerido junto a la ubicación y el texto de cada campo. «Nombrar este campo» permite corregirlo para esa plantilla del grupo; «Volver a la pista automática» elimina la corrección. El nombre no sustituye el contenido del Word. Las correcciones se guardan localmente y se protegen contra cambios simultáneos desde otra ventana.

Las nuevas propuestas de contenido y los paquetes de clase reciben las etiquetas, distinguiendo nombres asignados por el docente y pistas automáticas. Se conserva una copia del contexto de campos en las nuevas propuestas; las anteriores tienen ese registro vacío, sin inventar retrospectivamente lo enviado. Los paquetes conservan su copia de origen como antes. No se envía nada por importar, reconocer o nombrar campos.

Las plantillas ya importadas se reconocen al consultarlas desde los bytes originales guardados. Se mantienen IDs de campo, documentos, revisiones y originales. No es necesario volver a importarlas. Los documentos siguen usando su propia cantidad de columnas.

El resumen de importación avisa de filas con altura fija, combinaciones verticales y cuadros de texto, para ayudar a detectar posibles problemas al rellenar.

## Alcance y pendientes

- Son heurísticas estructurales, no comprensión universal del formato. Una primera fila corta puede ser contenido en vez de encabezado; por eso las pistas se presentan como automáticas y corregibles. Sin pista suficiente, el campo queda sin identificar.
- Los nombres personalizados se aplican a una plantilla dentro de su grupo; no se propagan a otras variantes, escuelas o grupos. Se guardan al confirmar el diálogo, por separado del contenido del documento.
- No hay OCR de formatos escaneados, reconocimiento visual por IA, importación de Excel como plantilla ni detección de campos dentro de imágenes.
- Las combinaciones verticales se conservan y se advierten; no se reconstruye su significado. No se editan párrafos complejos que el importador anterior ya excluía.
- Las pistas se basan en la plantilla original. Cambiar el texto de una instancia no recalcula sus nombres automáticamente; el docente puede corregirlos.
- No se rediseña el documento ni se ajustan automáticamente las alturas, anchos o paginación. Un aviso de altura fija no garantiza detectar todos los riesgos de desbordamiento.
- El contexto online mantiene su límite de 18 KB y envía una representación compacta de los campos. Las etiquetas son datos orientativos, no instrucciones para cambiar el protocolo del modelo.

## Verificación

231 pruebas ejecutadas en Linux: 230 pasan y una de DPAPI requiere Windows. Ocho pruebas nuevas cubren formatos de 3/6/8 columnas, columnas combinadas, etiquetas locales, encabezados incompletos, tablas anidadas y alturas fijas, aislamiento y conflictos, compatibilidad con esquemas antiguos y conservación del contexto enviado. Las pruebas anteriores de preservación de partes y geometría DOCX siguen pasando. Compilación sintáctica y revisión de diferencias correctas.

No se declara validación visual nueva en Word, calidad de reconocimiento sobre formatos reales de distintas escuelas, ni evaluación con una llamada real a OpenAI. Windows, rendimiento en PC básica e instalador siguen pendientes para 1.0.
