# Construcción interna Windows x64

No son instrucciones para el docente. El instalador incluye el intérprete y dependencias; el usuario final no instala Python. Esta receta prepara candidatos de prueba, no una entrega 1.0.

En un equipo de construcción Windows con Python 3.12 x64 e Inno Setup 6:

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r packaging/requirements-build.txt
.\packaging\build_windows.ps1 -Python .\.venv\Scripts\python.exe
```

El script ejecuta las pruebas, genera una carpeta PyInstaller, prueba el ejecutable y después compila el instalador. Si falla una fase, se detiene. El diagnóstico usa bases temporales y datos sintéticos, comprueba SQLite/respaldo, DOCX, XLSX, el recurso PPTX incluido, carga de PortAudio, DPAPI y arranque básico de Tk. No graba audio ni consume API. Un JSON fallido o ausencia del informe bloquea el instalador.

`dist/installer/` contiene el candidato; `dist/packaged-check.json`, inventario de dependencias y SHA-256 acompañan el resultado. El workflow Windows candidate ejecuta la misma receta en windows-2022. Sus artefactos son internos, duran 14 días y no se publican como Release. El éxito de CI no sustituye probar instalación, actualización o desinstalación en una PC limpia.

Los binarios van a LOCALAPPDATA/Programs/AulaOS. Los datos conservan la ruta anterior LOCALAPPDATA/AulaOSLab, o AULAOS_DATA_DIR si se configuró. El instalador no modifica ni elimina esa carpeta y usa un AppId estable para futuras actualizaciones. Las migraciones ocurren al abrir la aplicación. El desinstalador conserva los datos; no hay limpieza automática de registros del docente. Cerrar AulaOS antes de actualizar sigue siendo necesario. Windows x86/ARM nativo no están validados.

No se firma digitalmente este candidato. Las dependencias de aplicación conservan rangos de compatibilidad: el inventario registra lo resuelto, pero aún no es una compilación bit a bit reproducible. Antes de 1.0 deben revisarse licencias, fijar dependencias validadas y decidir firma/distribución.

Referencias técnicas: [PyInstaller: recursos en ejecución](https://pyinstaller.org/en/stable/runtime-information.html), [Inno Setup: privilegios](https://jrsoftware.org/ishelp/topic_setup_privilegesrequired.htm), [AppId](https://jrsoftware.org/ishelp/topic_setup_appid.htm), [desinstalación](https://jrsoftware.org/ishelp/topic_uninstalldeletesection.htm).
