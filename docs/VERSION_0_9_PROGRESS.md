# AulaOS 0.9 — avance guardado, versión sin cerrar

14 de octubre de 2026. Este incremento continúa la 0.8; no declara terminada la 0.9 ni entrega un instalador.

## Bloque completado: propuestas para formatos propios

Desde el editor de documento con plantilla se puede pedir contenido indicando tema, grado, sesiones y requisitos. Se guarda primero la versión local. Tras confirmación de envío, OpenAI recibe la petición y la ubicación/texto actual de los párrafos editables. Esos textos pueden contener información personal: se informa antes de enviar. No se adjuntan rutas, archivo Word, imágenes, expedientes, historial de chat u otras fuentes.

La IA debe devolver un objeto JSON con cambios por ID y notas sobre información faltante. Se rechazan respuestas incompletas, claves repetidas, campos inexistentes, textos inválidos y contenido fuera de límites. La solicitud puede generar consumo incluso si la propuesta se rechaza por formato. No hay reintento automático. Reutiliza perfil, credencial, tokens máximos y límite mensual actuales.

La propuesta se guarda aparte, con petición, revisión de origen, texto nuevo, notas y estado. El docente ve antes/después de todos los campos y puede aplicarla completa o descartarla. Aplicar crea una nueva revisión del documento y conserva anteriores; aplicar dos veces no duplica versiones. Si el documento cambió durante o después de la consulta, la propuesta no sobrescribe esos cambios. Las propuestas sobreviven al reinicio y se reabren desde el mismo botón.

No se impone un número de columnas. Los campos omitidos mantienen su contenido. No se agregan filas ni se reconstruye el formato. El renderizador y las restricciones de 0.7 siguen vigentes. Se puede exportar la versión aprobada e importarla como material para revisarla en el chat.

## Límites del avance

- Generación por campos implementada, calidad semántica y pedagógica todavía no evaluada con un modelo real.
- Las instrucciones al modelo piden no inventar hechos ni requisitos; no son garantía de exactitud.
- Hasta 18 KB de petición + campos y 6000 caracteres de petición. El límite de respuesta del perfil puede ser insuficiente para formatos grandes; se rechaza JSON incompleto sin modificar documentos.
- Se aplica o descarta la propuesta completa. La selección/edición de cambios individuales aún no está implementada; después de aplicar se puede editar o recuperar una revisión anterior.
- No consulta internet en este flujo ni usa adjuntos. El docente debe aportar datos necesarios en su petición.
- No ejecuta acciones escolares ni comandos del sistema. El lenguaje libre para registrar tareas/observaciones aún requiere el formato explícito de 0.6.
- No hay autoguardado ante cierre forzado de una petición todavía no enviada.

## Verificación de este bloque

146 pruebas totales: 145 pasan en Linux y una de DPAPI queda omitida por requerir Windows. Trece nuevas cubren revisión sin escritura, aplicación idempotente, descarte persistente, aislamiento, cambios concurrentes, JSON inválido/duplicado/campos inexistentes, propuesta sin cambios, exclusión de expedientes/rutas, límites antes de llamar al proveedor, conservación de ediciones anteriores, rollback atómico, formatos variables y flujo propuesta → versión → Word → material → chat.

Proveedores simulados. No se hizo una llamada real a OpenAI. Se verificó compilación y diferencias. No se cambió el motor de renderizado; la comprobación visual de formatos permanece en 0.7. No se probó la nueva interfaz en Windows.

## Próximo punto de reanudación

1. Ampliar las peticiones naturales hacia propuestas de tareas/observaciones sin perder revisión, identidad y alcance por grupo.
2. Integrar fuentes seleccionadas e investigación en la preparación de materiales, manteniendo procedencia y límites visibles.
3. Evaluar con API real generación, mapeo de campos, errores de formato, duración y consumo; probar transcripción real cuando haya credencial/hardware disponible.
4. Revisar visualmente documentos resultantes de propuestas reales y formatos representativos. Corregir cortes y problemas de distribución.
5. Completar la revisión integral de flujos y requisitos pendientes antes de cerrar 0.9. Windows, dispositivos, PC básica e instalador siguen en 1.0.

La numeración no garantiza que todos los requisitos quepan en un solo incremento; si hace falta, se documentarán incrementos adicionales en lugar de declarar listo algo sin validar.
