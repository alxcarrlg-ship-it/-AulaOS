# AulaOS

Asistente docente inteligente para Windows, en desarrollo.

## Estado verificable

Se recuperó AulaOS Lab 0.1 y se incorporó su núcleo y su interfaz al repositorio. La base es un laboratorio interno, no una entrega final. La implementación anterior de 0.2 no se localizó; las correcciones actuales continúan desde la 0.1 real.

Se conservan asistencia, observaciones, pendientes, lectura Excel/CSV, conflictos, exportación HTML y respaldo SQLite. Corregidos dos errores de integridad: escrituras entre grupos y reasignación de identidad al ordenar CSV. Las 17 pruebas del núcleo y chat pasan en Linux.

Avance interno 0.2: conversación persistente por grupo, pestaña de asistente como entrada principal, ejecución de respuestas fuera del hilo de interfaz y adaptador de chat local Ollama. El modo básico sigue disponible sin modelo. El adaptador se verificó con servidor de ensayo; no se ha ejecutado un modelo real ni validado la interfaz en Windows. Faltan selección e integración del motor distribuido, calidad conversacional medida, ejecución de herramientas, transcripción, acceso documental ampliado, investigación web, herramientas adaptables y validación del instalador en Windows. El usuario final no deberá instalar Python. No existe una versión instalable validada.

La auditoría y criterios de aceptación están en docs/AUDITORIA.md. El código recuperado se conserva en lab/. La base de datos real permanece local, fuera del repositorio.

## Desarrollo interno

El laboratorio usa Python, tkinter y SQLite. Esto no impone Python al usuario final ni fija la arquitectura definitiva. Para verificar el núcleo en un entorno de desarrollo: instalar lab/requirements.txt y ejecutar desde lab/: `python -m unittest discover -s tests -v`.
