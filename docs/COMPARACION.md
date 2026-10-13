# Referencias funcionales y brechas de AulaOS

Fecha de consulta: 13 octubre 2026. Comparación documental de fuentes oficiales; no es una evaluación práctica de productos ni una medición de paridad.

| Referencia | Capacidad documentada | Criterio de AulaOS | Estado actual |
|---|---|---|---|
| Claude Cowork | Acceso a archivos locales y trabajo prolongado con varias herramientas | Procesar documentos de una carpeta elegida; tareas recuperables con progreso, cancelación y resultado verificable | Pendiente; laboratorio limitado a Excel/CSV y seguimiento |
| Copilot en Excel | Preguntas en lenguaje natural sobre tablas y rangos y preguntas sucesivas contextualizadas | Consultar datos escolares con evidencia de hoja/celda; no inferir cero desde celdas vacías | Importador existente; análisis abierto y citas pendientes |
| Ollama API chat | Mensajes, selección de modelo y respuesta conversacional | Proveedor local reemplazable, sin API pagada obligatoria | Adaptador implementado y contrato HTTP probado; modelo real y calidad pendientes |

## Fuentes oficiales

- https://claude.com/resources/guides/claude-cowork-product-guide/product-overview
- https://support.microsoft.com/en-us/excel/get-direct-answers-to-your-data-analysis-questions
- https://docs.ollama.com/api/chat

## Decisiones de este incremento

Mantener el laboratorio y datos compatibles mientras se evalúa la arquitectura definitiva. El chat es la pantalla inicial, sin quitar funciones anteriores. Aislar conversaciones y datos por el identificador del grupo, que ya pertenece a una escuela. Guardar mensajes en SQLite local. Proveedor local opcional para este incremento; no descargar ni seleccionar un modelo sin medir sus requisitos y calidad. El campo manual de modelo pertenece al laboratorio interno, no es la experiencia final de instalación.

La IA recibe registros de lectura del grupo activo y no puede ejecutar cambios de asistencia, archivos ni navegación en este incremento. El prompt pide distinguir hechos de sugerencias; todavía no hay comprobación automática de veracidad ni resistencia medida a instrucciones maliciosas dentro de las fuentes. No afirmar paridad con Cowork/Copilot por disponer de un adaptador.

## Evidencia de pruebas

17/17 pruebas pasan en Linux: 11 de seguimiento y 6 de chat. Se comprueban persistencia al reabrir SQLite, aislamiento de contexto e historial entre escuelas/grupos, fallos del proveedor sin respuestas ficticias, pendientes por grupo, rechazo de servidores remotos en el adaptador local y contrato HTTP de chat con un servidor de ensayo. Sintaxis de interfaz y chat compilada correctamente.

Sin prueba interactiva de interfaz ni modelo real. No hay instalador validado. Voz, investigación web, generación documental, rendimiento con listas grandes, restauración y migraciones completas siguen pendientes. Comparación de costos, licencias, modelos, latencia y requisitos de hardware pendiente antes de fijar el motor distribuido.
