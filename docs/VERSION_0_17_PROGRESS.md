# AulaOS 0.17 — evidencias y seguimiento de proyectos

## Implementado

En Proyectos, «Evidencias y seguimiento» abre los registros del proyecto seleccionado. Cada evidencia tiene título, fecha, observación docente, siguiente paso, fecha opcional de seguimiento y estado: Por revisar, Revisada, Requiere seguimiento o Retirada. «Requiere seguimiento» exige describir el siguiente paso. Las fechas usan AAAA-MM-DD.

Puede referirse al grupo completo o a un alumno elegido por nombre e ID. Opcionalmente se vincula un material del grupo o una observación escolar ya registrada. Una observación individual determina su alumno; una selección incompatible se rechaza. La fuente puede revisarse antes de guardar.

Se guarda una copia del texto de la fuente y de la identidad del alumno, junto a la revisión del proyecto vigente al crear el registro. Los cambios posteriores en la fuente no alteran esa copia. Las correcciones de observación, estado y seguimiento crean revisiones inmutables. El historial se consulta desde la interfaz; una edición concurrente obsoleta se rechaza. Retirar un registro conserva su historial. Fuente, destinatario y proyecto quedan fijos: para corregir una asociación equivocada se retira el registro y se crea otro.

El listado permite filtrar por estado. El informe local exportable a Word, Markdown o HTML incluye escuela, grupo, avance actual declarado del proyecto, filtro aplicado, conteos por estado y registros con su fuente. Advierte que contiene nombres y texto de fuentes antes de preparar la copia. No sobrescribe archivos existentes. El avance mostrado es el actual; cada evidencia identifica la revisión del proyecto a la que se vinculó.

Todo este flujo funciona sin conexión y utiliza el respaldo SQLite existente. No registra automáticamente clases realizadas, calificaciones, tareas ni observaciones escolares nuevas. Tampoco incorpora evidencias o nombres de alumnos automáticamente al contexto online del proyecto.

## Límites y decisiones

- El estado «Revisada» significa revisión del registro, no aprobación del alumno ni logro demostrado. No hay diagnóstico pedagógico automático ni inferencia de resultados.
- La fecha de seguimiento es un dato local. No crea avisos, recordatorios o eventos de calendario.
- Las fuentes son copias de texto previamente guardado en Materiales o de observaciones; no almacena fotos, audio ni archivos binarios como evidencia. Máximo 20000 caracteres por fuente, sin recortes ocultos.
- Los nombres corresponden a la copia guardada al registrar; un cambio posterior en la lista no reescribe esa identidad histórica.
- No hay envíos a familias, reportes automáticos con IA ni procesamiento de expedientes en línea. El docente decide si exporta y comparte el informe.
- Se puede retirar una asociación incorrecta y crear otra, pero no hay borrado definitivo desde esta ventana. Los datos siguen en el historial y los respaldos.
- La calidad del contenido registrado depende de lo observado y escrito por el docente. El programa no autentica materiales como prueba de autoría o aprendizaje.

## Verificación

241 pruebas ejecutadas en Linux: 240 pasan y una de DPAPI se omite por requerir Windows. Diez pruebas nuevas cubren separación entre evidencia y avance, copia estable de fuentes, identidad del alumno, aislamiento entre grupos, historial/conflictos/retiro, vínculo a revisión del proyecto, validación y reversión de errores, persistencia en respaldo, exclusión del contexto online implícito, filtros/exportación y límite de fuente.

Compilación sintáctica y revisión de diferencias correctas. El exportador de documentos existente se reutiliza; no se declara una nueva revisión visual del informe en Word ni prueba de interfaz en Windows. Windows, PC básica e instalador continúan pendientes para 1.0.
