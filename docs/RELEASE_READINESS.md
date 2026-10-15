# Cierre hacia AulaOS 1.0

## 0.22 candidata

Congelar funciones y corregir problemas de uso. Recorrer con datos sintéticos: escuela/grupo → lista con homónimos → proyecto → formato propio → propuesta revisada → evidencia → exportación. Preparar el instalador y documentar una instalación y actualización reproducibles. No cambiar de interfaz o añadir motores offline grandes durante este cierre.

## Revisión de calidad antes de 1.0

El 15 de octubre de 2026 el usuario retiró Copilot como requisito y autorizó comenzar las pruebas en su PC con la candidata 0.22. Se mantienen las comprobaciones funcionales y la corrección de hallazgos; no se declara realizada una revisión con Copilot.

Prioridades para revisar:

- Aislamiento por escuela/grupo en consultas, recuperación, fuentes, rutas y exportaciones.
- Conflictos de revisión: recuperar texto antiguo, editar desde dos ventanas y resolver propuestas no debe sobrescribir datos posteriores.
- Migraciones: respaldos, interrupciones y rechazo de esquemas futuros; revisar también las tablas inicializadas fuera del núcleo numerado.
- Privacidad: datos efectivamente enviados, claves fuera de logs, adjuntos e instrucciones no confiables.
- Errores de API: timeout, cuota y red; consumo desconocido, límites locales y ausencia de reintentos automáticos duplicados.
- DOCX/PPTX: conservar formato, validar referencias, impedir sobrescritura accidental de originales.

## Puertas de salida para 1.0 (pendientes)

1. Evaluación con API real y datos sintéticos: varios formatos docentes, coherencia pedagógica, referencias, latencia y consumo observado. Registrar modelo y fecha; no convertir pruebas simuladas en promesas de calidad.
2. Windows limpio: instalación, apertura, DPAPI, micrófono real, exportación en Word/PowerPoint, actualización y desinstalación conservando los datos según la decisión del usuario.
3. PC básica: medir arranque, memoria y respuesta con una carga representativa, incluida operación básica sin internet.
4. Recuperación tras cierre forzado, guardado concurrente, respaldo/restauración y migración desde una base 0.x conservada para pruebas.
5. Resolución de hallazgos críticos y recorrido docente de aceptación en su PC.

La numeración no sustituye estas comprobaciones: 0.22 puede requerir correcciones adicionales antes de publicar 1.0.
