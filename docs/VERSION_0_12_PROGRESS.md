# AulaOS 0.12 — primer avance: aclaraciones configurables

14 de octubre de 2026. Incremento parcial, sin declarar terminada la 0.12.

El editor de perfiles permite definir hasta ocho datos requeridos, uno por línea (máximo 100 caracteres por etiqueta, sin dos puntos). Ninguno viene impuesto. Los perfiles antiguos conservan una lista vacía; siguen funcionando sin nuevas preguntas.

Antes de generar, se buscan respuestas explícitas en líneas «Dato: respuesta» de la petición. Se ignoran diferencias de mayúsculas. Valores vacíos o marcadores como «pendiente», «por definir» o «no sé» siguen pendientes. Si faltan datos, la interfaz muestra los datos faltantes juntos y añade las respuestas confirmadas a la petición visible. Cancelar no envía la solicitud y conserva la petición anterior; si se escribieron respuestas, pide confirmar su descarte. El docente puede explicar que un dato no aplica.

El servicio también bloquea solicitudes incompletas antes de llamar al proveedor. El perfil, sus etiquetas y la petición quedan conservados en la propuesta. Se mantienen selección explícita, revisión de versión del perfil y límite conjunto de contexto. Crear etiquetas o responder preguntas no consume API; la generación posterior sí.

## Límites y siguiente punto

Es una comprobación de presencia de respuestas, no comprensión semántica: puede volver a preguntar si la información estaba en prosa, plantilla o fuentes. No verifica que una respuesta sea verdadera o suficiente, no detecta contradicciones y no descubre automáticamente los requisitos de una institución. No convierte estos datos en campos obligatorios del Word. El formulario integrado permite revisar todas las aclaraciones juntas. Quedan pendientes la detección semántica y la revisión de contradicciones.

179 pruebas totales: 178 pasan y una depende de Windows. Tres nuevas cubren bloqueo antes del proveedor, aceptación y procedencia, validación/preservación de etiquetas y reconocimiento explícito. Proveedor simulado; interfaz y API real aún sin validar. Windows y equipos básicos siguen previstos para 1.0.
