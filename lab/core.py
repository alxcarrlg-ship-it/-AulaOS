"""AulaOS Lab 0.1 — local-only storage and Excel read-only importer.
No school/student data leaves this computer. MIT prototype, not production.
"""
from __future__ import annotations
import csv
import datetime as dt
import html
import os
import re
import sqlite3
from pathlib import Path
from typing import Optional
from migrations import prepare,upgrade
from roster_identity import identifier,header_index,resolve

STATUS = {'A':'Asistencia','F':'Falta','R':'Retardo','J':'Justificada'}


def now(): return dt.datetime.now().astimezone().isoformat(timespec='seconds')
def today(): return dt.date.today().isoformat()
def normalize(s):
    import unicodedata
    return ''.join(c for c in unicodedata.normalize('NFKD', str(s or '').lower()) if not unicodedata.combining(c)).strip()

class Store:
    def __init__(self, db_path):
        self.db_path = str(db_path)
        Path(self.db_path).parent.mkdir(parents=True,exist_ok=True)
        self.con=sqlite3.connect(self.db_path)
        self.con.row_factory=sqlite3.Row
        self.con.execute('PRAGMA foreign_keys=ON')
        self.con.execute('PRAGMA busy_timeout=5000')
        try:self.migration_backup=prepare(self.con,self.db_path)
        except Exception:self.con.close();raise
        self.con.executescript('''
        CREATE TABLE IF NOT EXISTS schools(id INTEGER PRIMARY KEY,name TEXT NOT NULL UNIQUE);
        CREATE TABLE IF NOT EXISTS groups(id INTEGER PRIMARY KEY,school_id INTEGER NOT NULL REFERENCES schools(id),name TEXT NOT NULL,source_path TEXT,source_stamp TEXT, UNIQUE(school_id,name));
        CREATE TABLE IF NOT EXISTS students(id INTEGER PRIMARY KEY,group_id INTEGER NOT NULL REFERENCES groups(id),name TEXT NOT NULL,source_row INTEGER,active INTEGER NOT NULL DEFAULT 1, UNIQUE(group_id,source_row));
        CREATE TABLE IF NOT EXISTS attendance(id INTEGER PRIMARY KEY, group_id INTEGER NOT NULL REFERENCES groups(id),student_id INTEGER NOT NULL REFERENCES students(id),day TEXT NOT NULL,status TEXT NOT NULL CHECK(status IN ('A','F','R','J')),origin TEXT NOT NULL,updated_at TEXT NOT NULL,UNIQUE(student_id,day));
        CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY,group_id INTEGER NOT NULL REFERENCES groups(id),student_id INTEGER NOT NULL REFERENCES students(id),day TEXT NOT NULL,category TEXT NOT NULL,detail TEXT NOT NULL,created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS tasks(id INTEGER PRIMARY KEY,group_id INTEGER REFERENCES groups(id),title TEXT NOT NULL,due TEXT,done INTEGER NOT NULL DEFAULT 0,created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS conflicts(id INTEGER PRIMARY KEY,group_id INTEGER NOT NULL,student_id INTEGER NOT NULL,day TEXT NOT NULL,local_status TEXT NOT NULL,excel_status TEXT NOT NULL,created_at TEXT NOT NULL,resolved INTEGER NOT NULL DEFAULT 0, UNIQUE(student_id,day,local_status,excel_status));
        CREATE INDEX IF NOT EXISTS idx_att_group ON attendance(group_id,day);
        CREATE INDEX IF NOT EXISTS idx_event_student ON events(student_id,day);
        ''')
        self.con.commit()
        try:upgrade(self.con)
        except Exception:self.con.close();raise
    def backup(self):
        """Consistent SQLite backup; rotate last 20 copies. Never sync live WAL DB."""
        out=Path(self.db_path).parent/'backups';out.mkdir(exist_ok=True)
        dst=out/f'aulaos_{dt.datetime.now().strftime("%Y%m%d_%H%M%S_%f")}.sqlite3'
        conn=sqlite3.connect(dst)
        try:self.con.backup(conn)
        finally:conn.close()
        for old in sorted(out.glob('aulaos_*.sqlite3'),reverse=True)[20:]:old.unlink(missing_ok=True)
        return dst
    def close(self): self.con.close()
    def group(self,school,name):
        school=school.strip();name=name.strip()
        if not school or not name: raise ValueError('Escuela y grupo son obligatorios')
        with self.con:
            self.con.execute('INSERT OR IGNORE INTO schools(name) VALUES (?)',(school,))
            sid=self.con.execute('SELECT id FROM schools WHERE name=?',(school,)).fetchone()['id']
            self.con.execute('INSERT OR IGNORE INTO groups(school_id,name) VALUES(?,?)',(sid,name))
            return self.con.execute('SELECT id FROM groups WHERE school_id=? AND name=?',(sid,name)).fetchone()['id']
    def groups(self):
        return list(self.con.execute('SELECT g.id, s.name school,g.name,g.source_path,g.source_stamp FROM groups g JOIN schools s ON s.id=g.school_id ORDER BY s.name,g.name'))
    def add_student(self,gid,name,row=None):
        name=name.strip()
        if not name: raise ValueError('Nombre vacío')
        with self.con:
            if row is not None:
                self.con.execute('INSERT INTO students(group_id,name,source_row) VALUES(?,?,?) ON CONFLICT(group_id,source_row) DO UPDATE SET name=excluded.name,active=1',(gid,name,row))
                return self.con.execute('SELECT id FROM students WHERE group_id=? AND source_row=?',(gid,row)).fetchone()['id']
            # Manual students use an assigned negative row to avoid colliding with Excel row numbers.
            n=self.con.execute('SELECT COALESCE(MIN(source_row),0) FROM students WHERE group_id=?',(gid,)).fetchone()[0]
            row=min(-1,n-1)
            return self.add_student(gid,name,row)
    def students(self,gid): return list(self.con.execute('SELECT * FROM students WHERE group_id=? AND active=1 ORDER BY CASE WHEN source_row>0 THEN 0 ELSE 1 END,source_row,name',(gid,)))
    def _require_membership(self,gid,sid):
        row=self.con.execute('SELECT group_id FROM students WHERE id=?',(sid,)).fetchone()
        if row is None or row['group_id'] != gid:
            raise ValueError('El alumno no pertenece al grupo seleccionado')
    def mark(self,gid,sid,day,status,origin='manual'):
        self._require_membership(gid,sid)
        if status not in STATUS: raise ValueError('Estado no válido')
        dt.date.fromisoformat(day)
        with self.con:
            self.con.execute('''INSERT INTO attendance(group_id,student_id,day,status,origin,updated_at) VALUES (?,?,?,?,?,?)
                ON CONFLICT(student_id,day) DO UPDATE SET status=excluded.status,origin=excluded.origin,updated_at=excluded.updated_at''',(gid,sid,day,status,origin,now()))
    def marks(self,gid,day): return {r['student_id']:r['status'] for r in self.con.execute('SELECT student_id,status FROM attendance WHERE group_id=? AND day=?',(gid,day))}
    def attendance_counts(self,sid): return {r['status']:r['n'] for r in self.con.execute('SELECT status,COUNT(*) n FROM attendance WHERE student_id=? GROUP BY status',(sid,))}
    def log_event(self,gid,sid,day,category,detail):
        self._require_membership(gid,sid)
        if not detail.strip():raise ValueError('Descripción obligatoria')
        dt.date.fromisoformat(day)
        with self.con:
            return self.con.execute('INSERT INTO events(group_id,student_id,day,category,detail,created_at) VALUES(?,?,?,?,?,?)',(gid,sid,day,category.strip() or 'Observación',detail.strip(),now())).lastrowid
    def events(self,sid):return list(self.con.execute('SELECT day,category,detail,created_at FROM events WHERE student_id=? ORDER BY day,id',(sid,)))
    def create_task(self,title,gid=None,due=None):
        if not title.strip():raise ValueError('Título vacío')
        if due:dt.date.fromisoformat(due)
        with self.con:
            return self.con.execute('INSERT INTO tasks(group_id,title,due,created_at) VALUES(?,?,?,?)',(gid,title.strip(),due,now())).lastrowid
    def tasks(self):return list(self.con.execute('''SELECT t.id,t.title,t.due,t.done,g.name grupo,s.name escuela FROM tasks t LEFT JOIN groups g ON g.id=t.group_id LEFT JOIN schools s ON s.id=g.school_id ORDER BY done,CASE WHEN due IS NULL THEN 1 ELSE 0 END,t.due,t.id'''))
    def task_done(self,tid,value=True):
        with self.con:self.con.execute('UPDATE tasks SET done=? WHERE id=?',(int(value),tid))
    def student_summary(self,sid):
        stu=self.con.execute('SELECT st.name,g.name grupo,s.name escuela FROM students st JOIN groups g ON g.id=st.group_id JOIN schools s ON s.id=g.school_id WHERE st.id=?',(sid,)).fetchone()
        if not stu:return 'No se encontró el estudiante.'
        c=self.attendance_counts(sid);out=[f"{stu['name']} — {stu['escuela']} / {stu['grupo']}",f"Asistencias: {c.get('A',0)} · Faltas: {c.get('F',0)} · Retardos: {c.get('R',0)} · Justificadas: {c.get('J',0)}",'','OBSERVACIONES REGISTRADAS:']
        out.extend([f"{e['day']} | {e['category']}: {e['detail']}" for e in self.events(sid)] or ['Sin observaciones registradas.'])
        return '\n'.join(out)
    def export_html(self,sid,path):
        raw=self.student_summary(sid)
        safe='<br>'.join(html.escape(s) for s in raw.splitlines())
        body=f'<!doctype html><html lang="es"><head><meta charset="utf-8"><title>Historial AulaOS</title><style>body{{font:16px/1.6 Segoe UI,Arial;margin:3rem;max-width:850px;color:#233044}}h1{{color:#205988}}.note{{font-size:12px;color:#777}}</style></head><body><h1>Historial docente</h1><p>{safe}</p><p class="note">Registro generado desde AulaOS Lab. Revisar fuentes y exactitud antes de utilizar en una reunión. No sustituye procedimientos institucionales.</p></body></html>'
        Path(path).write_text(body,encoding='utf-8')
    def import_csv(self,gid,path):
        with open(path,'r',encoding='utf-8-sig',newline='') as f:
            reader=csv.DictReader(f)
            if not reader.fieldnames:raise ValueError('CSV sin encabezado')
            key=next((x for x in reader.fieldnames if normalize(x) in ['nombre','alumno','nombre del alumno','nombre del alumno(a)']),None)
            if key is None:raise ValueError('El CSV necesita columna Nombre o Alumno')
            index=header_index(reader.fieldnames,normalize);id_key=reader.fieldnames[index] if index is not None else None
            roster=[dict(row=i,name=(row.get(key) or '').strip(),external_id=identifier(row.get(id_key)) if id_key else None,marks=[]) for i,row in enumerate(reader,start=2) if (row.get(key) or '').strip()]
        if not roster:raise ValueError('CSV sin alumnos; no se aplicaron cambios')
        self.con.execute('BEGIN IMMEDIATE')
        try:
            known=[dict(r) for r in self.con.execute('SELECT * FROM students WHERE group_id=?',(gid,))]
            resolved=resolve(known,roster,normalize)
            self.con.execute('UPDATE students SET source_row=NULL WHERE group_id=? AND source_row>0',(gid,))
            for item in resolved:self._apply_roster_student(gid,item)
            self.con.commit()
        except Exception:self.con.rollback();raise
        return f'Importados {len(roster)} alumnos; matrícula cuando está disponible (CSV de solo lectura).'
    def _apply_roster_student(self,gid,item):
        if item['student_id'] is None:
            return self.con.execute('INSERT INTO students(group_id,name,source_row,external_id) VALUES(?,?,?,?)',(gid,item['name'],item['row'],item['external_id'])).lastrowid
        self.con.execute('UPDATE students SET name=?,source_row=?,external_id=?,active=1 WHERE id=? AND group_id=?',(item['name'],item['row'],item['external_id'],item['student_id'],gid))
        return item['student_id']
    def set_student_identifier(self,gid,sid,value,expected=None):
        self._require_membership(gid,sid);value=identifier(value)
        self.con.execute('BEGIN IMMEDIATE')
        try:
            old=self.con.execute('SELECT external_id FROM students WHERE id=?',(sid,)).fetchone()[0]
            if old!=expected:raise ValueError('La matrícula cambió en otra ventana; actualiza la lista.')
            self.con.execute('UPDATE students SET external_id=? WHERE id=?',(value,sid));self.con.commit()
        except sqlite3.IntegrityError as exc:self.con.rollback();raise ValueError('Esa matrícula ya pertenece a otro alumno del grupo.') from exc
        except Exception:self.con.rollback();raise
    def import_excel(self,gid,path,force=False):
        try:
            import openpyxl
        except ImportError as exc:
            raise RuntimeError('Para importar Excel instala openpyxl (requirements.txt).') from exc
        p=Path(path).expanduser().resolve()
        if not p.exists():raise FileNotFoundError(str(p))
        stat=p.stat();stamp=f'{stat.st_mtime_ns}:{stat.st_size}'
        record=self.con.execute('SELECT source_stamp FROM groups WHERE id=?',(gid,)).fetchone()
        if not force and record and record['source_stamp']==stamp:return 'Sin cambios desde la última lectura.'
        wb=openpyxl.load_workbook(p,read_only=True,data_only=True)
        try:
            sheet=next((sh for sh in wb if normalize(sh.title)=='asistencia'),wb.active)
            iterator=sheet.iter_rows(values_only=True)
            header=None
            for i,row in enumerate(iterator,start=1):
                texts=[normalize(v) for v in row]
                name_col=next((j for j,t in enumerate(texts) if 'nombre' in t and ('alumno' in t or t=='nombre')),None)
                if name_col is not None:
                    header=(i,row,name_col);break
                if i>=35:break
            if header is None:raise ValueError('No encontré el encabezado de alumnos (primeras 35 filas).')
            nhead,values,name_col=header
            id_col=header_index(values,normalize)
            dates=[]
            for j,val in enumerate(values):
                if j<=name_col:continue
                try:
                    if isinstance(val,dt.datetime):day=val.date().isoformat()
                    elif isinstance(val,dt.date):day=val.isoformat()
                    elif isinstance(val,str):
                        txt=val.strip()
                        try:day=dt.datetime.strptime(txt,'%d/%m/%Y').date().isoformat()
                        except ValueError:day=dt.date.fromisoformat(txt).isoformat()
                    else:continue
                    dates.append((j,day))
                except (ValueError,TypeError):continue
            rosters=[]
            for row_idx,values in enumerate(iterator,start=nhead+1):
                name=values[name_col] if name_col<len(values) else None
                if not isinstance(name,str) or not name.strip():continue
                marks=[]
                for col,day in dates:
                    val=str(values[col] if col<len(values) and values[col] is not None else '').strip().upper()
                    if val in STATUS:marks.append((day,val))
                external=identifier(values[id_col] if id_col<len(values) else None) if id_col is not None else None
                rosters.append(dict(row=row_idx,name=name.strip(),marks=marks,external_id=external))
        finally:wb.close()
        if not rosters:raise ValueError('No encontré estudiantes; no se aplicaron cambios.')
        used=set();marked=0;conflicts=0;new_people=0;identity_warnings=0
        self.con.execute('BEGIN IMMEDIATE')
        try:
            known=[dict(r) for r in self.con.execute('SELECT * FROM students WHERE group_id=?',(gid,))]
            resolved=resolve(known,rosters,normalize)
            self.con.execute('UPDATE students SET source_row=NULL WHERE group_id=? AND source_row>0',(gid,))
            for item in resolved:
                if item['student_id'] is None:new_people+=1
                sid=self._apply_roster_student(gid,item);used.add(sid);marks=item['marks']
                for day,val in marks:
                    old=self.con.execute('SELECT status,origin FROM attendance WHERE student_id=? AND day=?',(sid,day)).fetchone()
                    if old and old['origin']=='manual':
                        if old['status']!=val:
                            self.con.execute('INSERT OR IGNORE INTO conflicts(group_id,student_id,day,local_status,excel_status,created_at) VALUES(?,?,?,?,?,?)',(gid,sid,day,old['status'],val,now()))
                            conflicts+=1
                        continue
                    if not old or old['status']!=val:
                        self.con.execute('''INSERT INTO attendance(group_id,student_id,day,status,origin,updated_at) VALUES (?,?,?,?,?,?)
                            ON CONFLICT(student_id,day) DO UPDATE SET status=excluded.status,origin=excluded.origin,updated_at=excluded.updated_at''',(gid,sid,day,val,'excel',now()))
                        marked+=1
            for old in known:
                if old['id'] not in used and (old['source_row'] or 0)>0:
                    self.con.execute('UPDATE students SET active=0 WHERE id=?',(old['id'],))
                    identity_warnings+=1
            self.con.execute('UPDATE groups SET source_path=?,source_stamp=? WHERE id=?',(str(p),stamp,gid))
            self.con.commit()
        except Exception:self.con.rollback();raise
        warning=f' Avisos de identidad: {identity_warnings}; revisa nombres cambiados/homónimos.' if identity_warnings else ''
        return f'{len(rosters)} alumnos; {new_people} identidades nuevas; {marked} marcas nuevas/actualizadas; {conflicts} conflictos de asistencia.{warning} Excel NO modificado.'
    def unresolved_conflicts(self,gid):
        return list(self.con.execute('''SELECT c.id,st.name,c.day,c.local_status,c.excel_status FROM conflicts c JOIN students st ON st.id=c.student_id WHERE c.group_id=? AND c.resolved=0 ORDER BY day,name''',(gid,)))
    def resolve_conflict(self,cid,choose_excel=False):
        c=self.con.execute('SELECT * FROM conflicts WHERE id=? AND resolved=0',(cid,)).fetchone()
        if not c:return
        if choose_excel:self.mark(c['group_id'],c['student_id'],c['day'],c['excel_status'],'excel')
        with self.con:self.con.execute('UPDATE conflicts SET resolved=1 WHERE id=?',(cid,))
    def find_student(self,gid,query):
        q=normalize(query)
        hits=[s for s in self.students(gid) if q in normalize(s['name'])]
        return hits
    def consult(self,gid,message):
        """Transparent offline command helper, not an LLM and not an AI simulation."""
        x=normalize(message)
        if any(k in x for k in ['pendiente','tarea','recordatorio']):
            ts=[t for t in self.tasks() if not t['done']];return 'Pendientes:\n'+'\n'.join(f"• {t['title']} ({t['due'] or 'sin fecha'})" for t in ts) if ts else 'No hay pendientes.'
        if gid is None:return 'Selecciona un grupo para consultar a sus alumnos.'
        prefix=re.sub(r'^(oye|asistente|aulaos)[,\s:]+','',x)
        for marker in ['cuantas faltas lleva','cuantos retardos lleva','historial de','resumen de','faltas de','retardos de']:
            if marker in prefix:
                target=prefix.split(marker,1)[1].strip(' ?.,:')
                hits=self.find_student(gid,target)
                if not hits:return f'No encontré a «{target}» en el grupo seleccionado.'
                if len(hits)>1:return 'Encontré varias coincidencias; elige un nombre más específico:\n'+'\n'.join(f"• {h['name']}" for h in hits)
                h=hits[0]
                if 'historial' in marker or 'resumen' in marker:return self.student_summary(h['id'])
                c=self.attendance_counts(h['id']);k='F' if 'falta' in marker else 'R'
                return f"{h['name']} tiene {c.get(k,0)} {'faltas' if k=='F' else 'retardos'} registrados en AulaOS (incluyendo Excel importado)."
        return 'Puedo consultar: «¿Cuántas faltas lleva [nombre]?», «Historial de [nombre]» o «Pendientes». Todavía no tengo IA conversacional; esta prueba funciona sin internet.'
