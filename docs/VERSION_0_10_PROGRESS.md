# AulaOS 0.10 — continuidad del trabajo, en desarrollo

14 de octubre de 2026. Primer incremento de 0.10. La numeración no cierra ni sustituye las validaciones pendientes de 0.9; no es una entrega instalable.

## Implementado

En la revisión por campos aparece «Guardar para continuar después». Conserva localmente la selección y todos los textos editados, incluso los excluidos, sin cambiar el documento ni consumir API. Al reabrir la revisión de la misma propuesta se recupera la copia guardada. Cerrar con cambios ofrece guardar, cerrar sin guardar esos cambios o cancelar el cierre. No hay autoguardado: un cierre forzado puede perder lo escrito desde el último guardado.

Una revisión tiene su propio contador de versiones. Guardar desde una ventana antigua o aplicar después de que otra guardó se rechaza; las correcciones permanecen en la ventana para copiarlas antes de cerrar. Las propuestas resueltas no admiten nuevos guardados. La copia manual queda conservada, pero el historial de aprobación sigue siendo la autoridad sobre lo efectivamente aplicado. Una copia manual no es un historial completo de cada edición: guardar reemplaza la copia anterior.

Si cambió la versión del documento, todavía puede guardarse el trabajo manual para recuperarlo, pero no aplicarse sobre el documento cambiado. Hay que generar una nueva propuesta sobre la versión actual; no existe fusión automática entre versiones. Los borradores pertenecen a su propuesta y grupo. Se validan campos y límites de texto. Las citas se validan al aplicar, permitiendo guardar texto incompleto mientras se revisa.

## Verificación

171 pruebas totales: 170 aprobadas en Linux y una omitida por depender de Windows. Cinco pruebas nuevas cubren recuperación desde otra conexión, conservación de campos excluidos, conflictos al guardar/aplicar, aislamiento y datos inválidos, propuestas resueltas y documentos modificados. No se probó la interfaz con ventanas reales ni Windows en este incremento. No se hizo una llamada real a OpenAI.

## Próximos objetivos, aún no implementados

- Detectar información faltante antes de generar, respetando requisitos variables por docente.
- Preferencias explícitas por escuela/docente y su reutilización con revisión.
- Continuidad de proyectos entre planeaciones, actividades y materiales sin inventar avances del grupo.
- Mejor selección y adaptación de recursos encontrados en línea, con procedencia y revisión.
- Presentaciones y materiales de clase: requieren diseño y exportación propios, todavía pendientes.
- Completar validación con API real, documentos representativos y calidad pedagógica.

Windows, micrófono, rendimiento en PC básica e instalador se mantienen para 1.0. No se fija un número de versiones intermedias como garantía de estar listo.
