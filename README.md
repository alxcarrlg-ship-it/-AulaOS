# AulaOS

Asistente docente inteligente para Windows, en desarrollo.

## Estado verificable

Se recuperó AulaOS Lab 0.1 y se incorporó su núcleo y su interfaz al repositorio. La base es un laboratorio interno, no una entrega final. La implementación anterior de 0.2 no se localizó; las correcciones actuales continúan desde la 0.1 real.

Se conservan asistencia, observaciones, pendientes, lectura Excel/CSV, conflictos, exportación HTML y respaldo SQLite. Corregidos dos errores de integridad: escrituras entre grupos y reasignación de identidad al ordenar CSV. Las 11 pruebas del núcleo pasan en Linux.

Faltan IA conversacional, conversación persistente contextual, transcripción, acceso documental ampliado, investigación web, herramientas adaptables y validación del instalador en Windows. El usuario final no deberá instalar Python. No existe una versión instalable validada.

La auditoría y criterios de aceptación están en docs/AUDITORIA.md. El código recuperado se conserva en lab/. La base de datos real permanece local, fuera del repositorio.

## Desarrollo interno

El laboratorio usa Python, tkinter y SQLite. Esto no impone Python al usuario final ni fija la arquitectura definitiva. Para verificar el núcleo en un entorno de desarrollo: instalar lab/requirements.txt y ejecutar desde lab/: `python -m unittest discover -s tests -v`.
