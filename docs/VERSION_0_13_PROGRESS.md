# AulaOS 0.13 — continuidad de proyectos

14 de octubre de 2026, hora de México. Incremento implementado de continuidad explícita; las validaciones de API real, interfaz y calidad pedagógica siguen pendientes.

## Registro de avance

«Proyectos» permite crear y editar registros dentro del grupo seleccionado, sin necesitar una plantilla ni conexión a internet. Cada registro separa título, planeado, realizado, pendiente y siguiente paso. Son declaraciones del docente, no hechos inferidos del chat. Un campo vacío significa sin registrar; generar, guardar o aplicar una planeación no modifica lo realizado.

Cada guardado con cambios crea una revisión inmutable. El historial permite consultar revisiones anteriores. Dos ventanas no pueden sobrescribir silenciosamente sus cambios: se compara la revisión esperada y se conserva la edición local si hay conflicto. Guardar sin cambios no crea otra revisión. Al cerrar con cambios se pide confirmar su descarte. No hay autoguardado ni recuperación de texto no guardado tras cierre forzado.

Se pueden vincular hasta 20 referencias de documentos de plantilla del mismo grupo a una versión específica. El selector muestra la versión guardada disponible al abrir el editor. Actualizar el documento después no mueve el vínculo. Quitar un vínculo y guardar crea otra revisión del proyecto; no borra documentos ni su historial. Son referencias, no importación del contenido ni prueba de que se impartió una clase.

## Uso en la siguiente planeación

La ventana de propuestas permite elegir un proyecto del grupo, crear uno o registrar avances. Empieza en «Sin proyecto». Se muestra el avance completo en una ventana desplazable antes de confirmar el envío online. Solo se incluye el proyecto elegido, no otros grupos, historial completo ni expedientes. Los nombres/versiones de documentos vinculados pueden enviarse como referencias; sus textos no se añaden automáticamente.

La propuesta conserva la copia exacta del proyecto y su revisión junto a la petición, perfil y fuentes. Las instrucciones al modelo distinguen lo planeado de lo realizado y solicitan continuidad según pendientes y siguiente paso. No garantizan razonamiento pedagógico correcto; la propuesta se revisa antes de aplicar.

Si cambió el proyecto después de seleccionarlo, se bloquea la solicitud antes de llamar al proveedor. Si cambió después de generar, se bloquea aplicar la propuesta antigua: hay que revisar el avance actual y generar otra. Aplicar no registra una clase como impartida ni cambia el avance. El límite conjunto de petición, campos, perfil, proyecto y fuentes sigue siendo 18 KB, sin truncado oculto. El avance admite hasta 10000 caracteres, pero puede requerir abreviarse al combinarlo con otros contextos.

## Verificación

205 pruebas: 204 pasan en Linux y una se omite por Windows. Doce nuevas cubren separación de estados, historia persistente, guardado sin cambios, aislamiento incluso entre grupos de la misma escuela, conflictos de edición, validación sin creación parcial, vínculos de versión sin marcar avance, rollback, selección explícita, copias históricas, bloqueo ante avance obsoleto, generación/aplicación sin alterar progreso y límite de contexto. Compilación y revisión de diferencias correctas.

No se probó la interfaz gráfica ni la continuidad pedagógica con API real. La revisión semántica opcional de 0.12 sigue analizando solo petición y perfil; no incluye este proyecto. No existe seguimiento automático de evidencias ni traslado conversacional de actividades entre estados. No se han añadido calendario, sincronización, gestión de evaluaciones ni análisis de desempeño del alumnado.

## Siguiente paso propuesto

0.14: investigación de recursos y adaptación al grupo, conservando fuentes y revisión docente. Se mantienen los pendientes de validación real y las pruebas de Windows/PC básica/instalador previstas para 1.0.
