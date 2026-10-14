# AulaOS 0.11 — perfiles de escuela y docente

14 de octubre de 2026. Incremento de desarrollo; no entrega instalable ni cierre de los pendientes de validación anteriores.

## Disponible

En la ventana de propuestas de plantilla se puede crear, ver o editar un perfil con nombre, docente y requisitos libres (máximo 6000 caracteres). Los perfiles se guardan localmente y se comparten entre grupos de la misma escuela; otra escuela tiene su propia lista. Se permiten variantes para distintos docentes. No son cuentas de usuario ni un mecanismo de autenticación.

La selección empieza en «Sin perfil». Elegir un perfil permite incluir sus requisitos en la solicitud online. La confirmación muestra nombre, docente y texto antes de enviar. Crear, editar o guardar perfiles no consume API. Los requisitos entran en el límite conjunto de contexto de 18 KB, sin recorte oculto.

Cada propuesta guarda la copia exacta del perfil enviado, incluida su versión, y la muestra en el historial. Cambiar el perfil después no cambia propuestas anteriores. Se rechazan ediciones concurrentes y solicitudes cuyo perfil cambió desde la selección. No se exige un número fijo de columnas ni se altera la estructura de la plantilla.

El perfil contiene preferencias declaradas. No acredita normativa ni hechos del grupo. Las instrucciones al modelo piden informar contradicciones en las notas, pero no existe aún un detector determinista de requisitos faltantes o contradictorios. La petición y la plantilla siguen requiriendo revisión docente.

## Alcance y límites

El perfil se usa en propuestas de plantilla, no en todo el chat ni en acciones escolares. No se infiere automáticamente a partir de archivos. No hay sincronización de perfiles, borrado desde interfaz ni historial completo de sus ediciones; las copias usadas en propuestas sí permanecen. No se precargan datos personales del usuario en el repositorio.

Persisten los flujos de aprobación parcial, edición manual, guardado de revisiones incompletas, aplicación versionada y fuentes seleccionadas. La interfaz nueva no se ha probado en Windows. No se ha evaluado el cumplimiento de perfiles con una llamada real a OpenAI.

## Verificación

176 pruebas: 175 pasan en Linux y una se omite por depender de Windows. Cinco adicionales cubren aislamiento entre escuelas y variantes de docente, selección explícita y copias históricas, conflictos antes del envío, validación/límites y recuperación persistente sin imponer columnas. Compilación y revisión de diferencias correctas.

## Sigue pendiente

Detección de información faltante, continuidad entre proyectos y materiales, mejora de recursos web y presentaciones. Se conservan las pruebas reales de API/calidad pendientes; Windows, dispositivos, rendimiento en PC básica e instalador siguen previstos para 1.0.
