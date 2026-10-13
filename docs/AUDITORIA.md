# AulaOS — auditoría y tareas verificables

Fecha: 12 de octubre de 2026, hora de México. Estado: auditoría inicial; ninguna versión final ni instalador validado.

## Evidencia localizada

- `AulaOS_Documento_Maestro_v0_1.docx`, versión 1: especificación y arquitectura inicial Python/tkinter, con evolución propuesta a Tauri. Su contenido se leyó completo.
- `AulaOS_Lab_v0.zip`, versión 1, 17,707 bytes: núcleo Python/SQLite, interfaz tkinter, ocho pruebas, importación Excel/CSV, workflow de empaquetado Windows.
- `Memoria_viva_del_ciclo_2026_2027.docx`: leída; aporta casos docentes, distinción entre preparación y aplicación real, criterios por grupo y conservación de XLSM.
- Conversaciones recuperadas: Windows instalable sin Python, chat central, archivos locales, historial contextual, pendientes, voz, investigación y herramientas adaptables. Una respuesta anterior afirmó versión 0.2 y diez pruebas; no se localizaron esos archivos y no se consideran implementación comprobada.
- Workspace inicialmente sin archivos de proyecto. GitHub: búsqueda AulaOS y listado de repositorios accesibles devolvieron cero resultados. No implica que no exista repositorio; no permite identificarlo ni escribir allí. No se ha creado ningún issue, commit o rama en GitHub.

## Estado funcional comprobado

Ejecutado `python3 -m unittest discover -s tests -v`: 8/8 pruebas correctas en Linux. Cubren conteos, eventos, tareas, CSV, conflicto Excel/manual, reordenamiento Excel, respaldo y rechazo de homónimos en Excel. No prueban interfaz Windows, micrófono ni instalador.

Existente: escuelas/grupos, alumnos, asistencia A/F/R/J, observaciones fechadas, pendientes, consultas por reglas, historial HTML, lectura Excel/CSV, conflictos y respaldo SQLite. Grabación WAV opcional declarada, no validada con micrófono. Observación de Excel cada 15 segundos del grupo activo.

Ausente: LLM conversacional, conversación persistente por contexto, Word/PDF/PPTX, transcripción, investigación web, herramientas configurables, restauración verificada, migración y distribución instalable probada. El workflow genera un EXE con PyInstaller, sin evidencia de ejecución ni instalador de distribución.

## Defectos reproducidos con datos ficticios

1. El núcleo acepta asistencia con un alumno de otro grupo: `mark(grupo_B, alumno_de_A, fecha, F)` se guarda. Las claves foráneas no aseguran pertenencia contextual. También debe revisarse `log_event`.
2. CSV identifica por fila: importar Rosa/Mateo, registrar nota de Rosa y reimportar Mateo/Rosa atribuye el identificador de Rosa a Mateo. Riesgo de transferencia de historial.

Otras limitaciones por inspección: campos institucionales y ciclo no modelados; pendientes consultados globalmente; importación Excel con heurísticas de encabezado, sin mapeo configurable ni espera de guardado estable; no existe auditoría histórica de sobrescrituras. Son pendientes, no fallos medidos en Windows.

## Acuerdos que rigen el desarrollo

Aplicación Windows instalable sin instalar Python; asistente conversacional central; datos y funciones esenciales locales; nube y proveedores opcionales; costo bajo; conservación funcional al ampliar; herramientas según docente y contexto. Dropbox sincroniza los documentos por su cuenta: AulaOS lee sus rutas locales. Base SQLite activa fuera de carpetas sincronizadas. Los originales XLSM conservan macros y no se reescriben por defecto.

Tauri/TypeScript con núcleo local y SQLite es la dirección recuperada, pendiente de validar dependencias, hardware y empaquetado antes de fijar implementación. Coordinador con herramientas especializadas es separación lógica, no obligación de ejecutar varios modelos caros. IA propia significa integrada en AulaOS y proveedor reemplazable; no entrenamiento de un modelo desde cero ni dependencia de una sesión ChatGPT. No prometer equivalencia offline con servicios avanzados.

Los formatos ABPC, PDA, recursos por escuela y proyectos de Alex serán contexto importable, no reglas universales de todos los docentes. No inferir clases impartidas de una planeación, ni calificaciones cero de celdas vacías, ni ponderaciones no acordadas.

## Backlog en orden de dependencia

| ID | Tarea | Evidencia de cierre |
|---|---|---|
| A01 | Recuperar repositorio GitHub y código 0.2 si existe | URL y permisos comprobados; árbol, ramas, SHA y pruebas inventariados; comparar con ZIP antes de migrar |
| A02 | Corregir identidad y pertenencia contextual | Reordenamientos Excel/CSV conservan historial; homónimos, renombres y bajas requieren resolución; marcas/eventos entre grupos rechazados sin cambios |
| A03 | Definir compatibilidad de datos y regresión | Fixtures ficticios de base 0.1; migración con respaldo/restauración; matriz con todas las funciones existentes y pruebas que pasan |
| A04 | Construir aplicación Windows centrada en chat | Arranque instalado sin Python; conversación persiste tras reinicio; cambio de escuela/grupo no mezcla datos; herramientas aparecen por necesidad |
| A05 | Integrar acceso documental adaptable | Carpetas elegidas; Excel/XLSM/CSV y DOCX/PDF/PPTX con citas de hoja/celda/página; hashes originales sin cambios; archivos bloqueados/corruptos y cambios externos gestionados |
| A06 | Integrar asistente y ejecución de herramientas | Consultas abiertas sobre fuentes; selección contextual; acciones revisables; cancelar no escribe; manejar ambigüedad, fallo y repetición sin duplicar registros |
| A07 | Seguimiento y pendientes | Asistencia, observaciones, tareas y cronología conservados; contexto y fechas verificables; distinguir hecho, inferencia y preparación; resolver conflictos y recuperar respaldo |
| A08 | Voz local | Grabar y conservar sin internet; transcribir español con ruido y nombres; revisar antes de registrar; cancelar; respuesta oral configurable |
| A09 | Investigación web | Buscar tema, comparar recursos como British Council, mostrar URL/fecha/nivel; distinguir fuente de recomendación; tareas largas cancelables y recuperables |
| A10 | Herramientas adaptables por docente | Crear/configurar por conversación una herramienta y plantilla de otro docente; persistir y versionar sin romper funciones anteriores |
| A11 | Comparar costos y alternativas | Fuentes oficiales actuales, licencias, RAM/CPU, latencia, calidad en español, costo local/remoto y descargas; seleccionar sin imponer suscripciones ni APIs obligatorias |
| A12 | Validar y distribuir | CI de regresión y build Windows; instalación/actualización/desinstalación en Windows limpio; conservación de datos, restauración y jornada docente completa; publicar instalador solo con matriz completa |

Estas tareas están organizadas aquí; todavía no son issues publicados en GitHub. A01 bloquea la integración en el repositorio solicitado. No subir listas, documentos reales, nombres de alumnos, credenciales ni archivos de trabajo a GitHub; usar fixtures ficticios.

## Condición de entrega

Entregar instalador cuando funcionen conversación con IA, archivos, seguimiento, voz, investigación y adaptación; cuando la regresión conserve funciones anteriores; y cuando exista evidencia Windows de instalación, persistencia, recuperación y flujo completo. No entregar laboratorio como producto, no pedir instalar Python y no declarar una capacidad validada solo por contar con código o workflow. Ninguna tarea se cierra sin evidencia.

## Actualización de recuperación — 13 octubre 2026

Código del ZIP recuperado y vuelto a probar: 8/8 pruebas pasan en Linux. No se localizó una implementación anterior de 0.2. El trabajo continúa desde la base real 0.1. SHA-256 del ZIP de procedencia: `6e2522f476db2cdd1cf5cd1336a97c055e32f1948d62bf0d532d7a4bdc66fd05`.

Se corrigieron pertenencia de alumno/grupo en marcas y eventos, e identidad de CSV al reordenar. Se añadieron tres pruebas: rechazo de escrituras entre grupos sin alterar registros, reordenamiento CSV con historial y hash del original conservados, y rechazo atómico de homónimos CSV. Resultado: 11/11 pruebas pasan en Linux, sin omisiones. No acredita Windows ni interfaz, voz o instalador.
