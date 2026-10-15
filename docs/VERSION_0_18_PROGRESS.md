# AulaOS 0.18 — recuperación de trabajo en edición

Este incremento prioriza recuperación ante cierres inesperados, tras revisar los riesgos de fiabilidad. La integración conversacional amplia, matrículas de importación y migraciones de esquema formalizadas siguen pendientes; no se declaran completadas en 0.18.

## Implementado

Los editores de borradores y documentos con plantilla guardan una copia de trabajo local cada 10 segundos cuando detectan cambios. No crean una versión aprobada, no modifican el Word original y no envían contenido a la API. Cada ventana usa una sesión distinta, para conservar trabajos paralelos sin sobrescribirlos entre sí.

«Recuperar trabajo» lista copias de sesiones anteriores del mismo documento y grupo, con fecha y revisión base, y permite revisar el contenido antes de cargarlo. Las ventanas activas de esta instancia de la aplicación no aparecen como sesiones recuperables. Para borradores nuevos sin guardar, se entra desde Nuevo borrador y luego Recuperar trabajo; se admiten título o texto incompletos.

Recuperar reemplaza el texto abierto solo después de confirmarlo. El texto queda en el editor; no se aplica automáticamente a una versión guardada. Se mantiene la revisión base original, de modo que el control de concurrencia rechaza un guardado si otra ventana ya guardó una versión posterior. Se puede revisar el contenido y usar Guardar copia.

Al guardar una versión correctamente se eliminan las copias de trabajo de esa ventana y las copias recuperadas que respaldaban ese guardado. Las sesiones ajenas se conservan. Cerrar y descartar elimina solo la copia de trabajo de esa ventana; una copia anterior recuperada sigue disponible mientras no se guarde o descarte explícitamente desde el selector.

La tabla recovery_snapshots es persistente, forma parte del respaldo SQLite y conserva las copias después de cerrar inesperadamente el proceso. Un error de autoguardado aparece en el estado del editor; el temporizador sigue intentando en los ciclos posteriores.

## Límites

- Cobertura inicial: borradores y documentos con plantilla. No cubre todavía revisiones de propuestas IA, proyectos, evidencias ni paquetes de clase.
- El intervalo es periódico, no espera a que el docente deje de escribir. Puede perderse el texto posterior a la última copia; también puede haber más retraso si la interfaz está ocupada o falla el almacenamiento.
- Recuperación local no sustituye un respaldo externo ni protege frente a pérdida del disco o corrupción del archivo SQLite.
- Las copias se muestran como texto/JSON en el selector, sin vista visual de Word.
- La protección de sesiones activas es de esta instancia de la aplicación; no hay coordinación de ventanas entre dos procesos abiertos del programa.
- Las copias no se eliminan por antigüedad: el docente puede revisarlas y descartarlas. Los respaldos previos pueden conservar copias que se hayan descartado después.
- No hay envío automático al chat, clasificación de contenido ni restauración silenciosa.

## Verificación

252 pruebas en Linux: 251 pasan y una de DPAPI se omite por requerir Windows. Once pruebas nuevas cubren separación respecto de versiones aprobadas, sesiones simultáneas, aislamiento de grupos, borradores incompletos, campos de plantilla válidos, revisión base obsoleta, reapertura y respaldo, validación atómica, temporizador y filtrado de sesiones activas, errores visibles y limpieza después de guardar o descartar.

La lógica del controlador se prueba con un editor simulado; no se declara una prueba de interfaz gráfica ni un apagón físico en Windows. Compilación sintáctica correcta. Las comprobaciones Windows/PC básica/instalador siguen previstas para 1.0.
