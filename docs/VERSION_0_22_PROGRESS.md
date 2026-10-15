# AulaOS 0.22 — preparación de candidata

Se congela el alcance funcional mientras se prepara la distribución. Se añade un punto de entrada para ejecutable, versión compartida, receta PyInstaller con la plantilla PPTX incluida e instalador Inno Setup por usuario. El workflow de Windows conserva candidatos internos e informes, sin publicar una versión final.

Antes de compilar el instalador se ejecutan las pruebas y un diagnóstico del ejecutable con datos sintéticos: SQLite y respaldo reabierto, plantilla DOCX, Excel, PPTX incluido, DPAPI, carga de PortAudio y arranque básico de Tk. No usa credenciales, micrófono ni registros reales. Ni este diagnóstico ni las pruebas de lógica constituyen validación visual o aceptación docente.

Se corrige un fallo de arranque: JSON válido con tipo incorrecto en settings.json (por ejemplo una lista o null) ahora recupera configuración predeterminada; antes provocaba un error al acceder a sus campos. Los guardados inválidos siguen rechazados.

Cuatro pruebas nuevas cubren diagnóstico sin red ni acceso al directorio del usuario, informe que no sobrescribe archivos, configuración inválida y recorrido integrado: lista con homónimos → proyecto → formato de ocho columnas → propuesta simulada corregida manualmente → evidencia → exportación → respaldo y reapertura. Se comprueba identidad del alumno, aislamiento y conservación del original.

Verificación local: 285 pruebas, 284 correctas y una de DPAPI omitida en Linux; compilación sintáctica y diff correctos. Verificación automatizada adicional: las 285 pruebas pasaron sin omisiones en Windows Server 2022. Se generó el instalador interno y pasaron siete comprobaciones del ejecutable empaquetado. [Ejecución](https://github.com/alxcarrlg-ship-it/-AulaOS/actions/runs/38732602503) y [registro con SHA-256, dependencias y alcance](QA_0_22_WINDOWS.json). La primera ejecución detectó una lectura de prueba con codificación predeterminada de Windows; se corrigió explícitamente a UTF-8. El compilador avisó sobre api-ms-win-core-path-l1-1-0.dll; el diagnóstico ejecutable pasó en ese servidor, sin demostrar compatibilidad con otras ediciones de Windows. API real, instalación/actualización/desinstalación, uso visual, PC básica, micrófono y revisión Copilot siguen pendientes antes de 1.0.

Ver [construcción interna](../packaging/README.md) y [puertas de salida](RELEASE_READINESS.md).
