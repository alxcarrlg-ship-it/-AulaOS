# AulaOS 0.12 — alcance de implementación completado

14 de octubre de 2026 (hora de México). Código y pruebas automatizadas del alcance de aclaraciones completados. Esto no equivale a validación con API real, calidad pedagógica ni entrega de Windows.

## Revisión local, sin consumo de API

Cada perfil puede definir hasta ocho datos requeridos de hasta 100 caracteres por etiqueta. No hay datos impuestos; los perfiles anteriores funcionan sin nuevas preguntas. Se buscan respuestas explícitas «Dato: respuesta», ignorando mayúsculas. Vacíos o marcadores como «pendiente» y «por definir» se solicitan en una ventana conjunta. Las respuestas confirmadas se añaden a la petición visible. Cancelar con respuestas escritas pide confirmar su descarte y conserva la petición anterior.

Si aparecen dos respuestas no vacías distintas para el mismo dato requerido, se bloquea la generación y se pide aclararlo. Es una comparación textual: «3» y «tres» pueden marcarse como distintos; el docente debe dejar una respuesta clara. Las respuestas añadidas tras un marcador vacío/pendiente no se tratan como contradicción.

## Revisión semántica online opcional

«Revisar texto libre y contradicciones con IA» abre un flujo separado. Tras confirmar el envío, se transmiten solo la petición actual y el perfil seleccionado (máximo conjunto 18 KB; petición hasta 6000 caracteres). No se incluyen Word, materiales, listas de alumnos ni historial. Usa el proveedor y límite mensual existentes; consume API además de la generación posterior. No hay reintentos automáticos.

El modelo puede reconocer datos expresados en prosa y señalar posibles contradicciones dentro de la petición o con requisitos del perfil. Debe devolver JSON estricto con respuestas para etiquetas conocidas, valores breves y evidencia literal de la petición. Cada duda debe aportar citas literales de la petición o requisitos. Se rechazan claves repetidas, etiquetas ajenas, respuestas duplicadas, texto excesivo, evidencia inexistente y contenido incompleto.

El informe se guarda por grupo junto con la petición y perfil exactos. «Abrir última revisión de este grupo» permite consultarlo sin una nueva llamada. Los informes anteriores permanecen en la base; la interfaz solo reabre el más reciente. No modifica documentos ni genera una planeación.

«Usar respuestas interpretadas» muestra la petición resultante y pide confirmación. Solo añade respuestas a datos aún pendientes, nunca reemplaza una respuesta explícita existente. Si hay dudas del informe o respuestas duplicadas incompatibles, exige corregir la petición y revisarla de nuevo. Si cambió la petición o perfil, se rechaza usar un análisis obsoleto. La petición resultante sigue siendo editable y pasa por la confirmación de generación habitual.

## Límites explícitos

La evidencia literal demuestra procedencia, no que la interpretación sea correcta. El modelo puede omitir contradicciones o señalar alguna inexistente. La revisión semántica es opcional y orientativa; no bloquea por sí misma la generación desde el flujo separado. No verifica normativa ni la verdad de los datos; tampoco extrae información desde plantillas o materiales en esta etapa. No hay comprensión semántica offline, fusión automática de instrucciones ni ejecución de acciones.

## Verificación y cierre de código

193 pruebas: 192 pasan en Linux y una de DPAPI se omite por requerir Windows. Se cubren respuestas en prosa, persistencia y aislamiento, exclusión de expedientes, JSON y evidencia inválidos, versiones obsoletas, dudas sin resolución, error de proveedor sin reintentos, límites antes del envío, protección de respuestas explícitas, conflictos locales y flujo revisión → petición aprobada → propuesta → versión aplicada. Compilación y diferencias correctas.

Proveedor simulado. Quedan pendientes las comprobaciones con API real, interfaz gráfica y casos pedagógicos reales. No se declara eficacia semántica evaluada. Windows, dispositivos, rendimiento en PC básica e instalador se mantienen para 1.0.

Siguiente alcance propuesto: 0.13, continuidad de proyectos distinguiendo planeado, realizado y pendiente. No se inició en este cierre.
