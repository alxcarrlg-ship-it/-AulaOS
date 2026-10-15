# AulaOS 0.19 — identidad al importar y migraciones del núcleo

## Matrícula opcional

Las importaciones CSV/Excel reconocen una columna Matrícula, ID alumno, Identificador, Student ID o Número de control (sin distinguir mayúsculas o acentos en encabezados). Tener varias columnas de identificador bloquea la importación para no elegir una arbitrariamente. La CURP no es obligatoria ni se reconoce automáticamente como matrícula.

La matrícula se guarda como texto, conservando ceros iniciales; se recortan espacios exteriores y se normaliza a mayúsculas. Admite hasta 80 letras ASCII, números y los signos . _ / -. Una celda numérica de Excel se rechaza: hay que convertir correctamente los identificadores a texto antes de importar, sin suponer que ceros ya perdidos pueden recuperarse.

La matrícula es única dentro del grupo y puede repetirse en otro grupo. El ID interno existente del alumno sigue siendo el vínculo de asistencias, observaciones y demás registros. Si coincide la matrícula, cambiar el nombre o la posición en la lista conserva ese ID interno. Los homónimos con matrículas diferentes pueden importarse en una lista nueva y actualizarse después sin intercambiar sus historiales.

Sin matrícula se mantiene la correspondencia por nombre único y se rechazan ambigüedades. Una matrícula nueva puede asociarse a un nombre único previamente registrado sin matrícula. Si el nombre tiene una matrícula distinta registrada, se bloquea la importación completa. Si hay homónimos existentes sin identificar, el docente debe asignar primero sus matrículas en la lista local.

En Asistencia aparece la matrícula y una opción para asignarla, corregirla o quitarla al alumno seleccionado. Se confirma el nombre y el ID interno antes del cambio. Un valor repetido en el grupo o una modificación concurrente se rechaza. Los identificadores no se añadieron al contexto online de registros escolares.

CSV y Excel resuelven todas las correspondencias antes de modificar alumnos. El guardado es transaccional: si se detecta un conflicto, no se aplica parte de la lista. Se conservan los criterios previos de asistencia manual y conflictos con Excel; las fuentes no se modifican.

## Migraciones

Se establece la versión 1 del esquema del núcleo mediante PRAGMA user_version y una bitácora schema_migrations. Esta versión añade la columna de matrícula y su índice único. Es independiente del número comercial 0.19.

Al abrir una base anterior sin versión registrada, se verifica su integridad con quick_check y se crea un respaldo SQLite consistente en migration_backups antes de ejecutar cambios de esquema. También se verifica el respaldo. Si falla esta preparación, la actualización se detiene. Las bases nuevas no necesitan respaldo previo.

La migración de la columna/índice y el cambio de versión se aplican en una transacción. Un fallo revierte esa migración y conserva el respaldo. Reabrir una base ya actualizada no repite la migración ni crea otro respaldo de migración. Una base marcada con una versión superior a la admitida se rechaza antes de ejecutar DDL del núcleo.

Los respaldos de migración son independientes de la rotación normal de 20 respaldos; no se eliminan automáticamente. Para recuperar uno, se debe cerrar AulaOS y sustituir la base por una copia elegida, conservando también la base actual. Todavía no hay asistente gráfico de restauración ni descenso automático de versiones.

## Límites

- Una matrícula errónea aportada por el docente no puede autenticarse frente a una fuente oficial. La correspondencia depende de que el identificador sea correcto y estable.
- No hay identidad universal entre grupos, traslado automático de alumnos ni fusión de historiales. El número de lista no se usa como matrícula.
- Agregar un nuevo homónimo cuyo nombre ya tiene otra matrícula puede requerir crear/asignar su identidad local antes de importar. Se prioriza detener una asociación dudosa.
- Sin identificador, un nombre corregido que ya no coincida puede crear una identidad nueva como antes; no se hace coincidencia difusa.
- Los módulos anteriores conservan sus inicializadores idempotentes. Este incremento establece el registro de migraciones para el núcleo; no reescribe retrospectivamente todas las inicializaciones de tablas opcionales como migraciones numeradas. Los futuros cambios estructurales deben ampliar este registro.
- Verificar SQLite no equivale a certificar la exactitud de los datos docentes ni protege frente a pérdida del disco.

## Verificación

267 pruebas en Linux: 266 pasan y una de DPAPI requiere Windows. Quince pruebas nuevas cubren homónimos, cambio de nombre, orden, matrícula heredada, duplicados, discrepancias, aislamiento por grupo, edición concurrente, celdas numéricas y encabezados ambiguos. Las pruebas de migración cubren datos de alumnos/asistencia/observaciones, borradores, proyectos, evidencias y recuperación; respaldo anterior verificable, reapertura idempotente, base nueva, versión futura, fallo de respaldo y reversión de migración fallida.

Compilación sintáctica y revisión de diferencias correctas. Las pruebas son con datos sintéticos. Windows, interfaz real, equipos básicos e instalador siguen pendientes conforme al plan de 1.0.
