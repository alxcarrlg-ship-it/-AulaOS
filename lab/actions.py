"""Explicit local chat actions. No model output or attachment is executable."""
import datetime as dt
import json
import re
from core import now, today, normalize
from drafts import Drafts

HELP = '''Acciones locales (sin consumo online):
/tarea Título | AAAA-MM-DD (fecha opcional)
/observacion Nombre completo o #ID | Hechos | AAAA-MM-DD (fecha opcional: hoy)
/borrador Título | Contenido
También: «crea tarea: …», «registra observación: …», «crea borrador: …».
Nada se guarda en los registros hasta confirmar en «Acciones». Para corregir una propuesta, cancélala y envía otra.'''


def command(text):
    match=re.match(r'^\s*(/(?:tarea|observacion|observación|borrador|acciones)\b|crea tarea:|registra observación:|registra observacion:|crea borrador:)\s*(.*)$',text,re.I|re.S)
    if not match:return None
    head=normalize(match[1]);kind='help' if head=='/acciones' else 'task' if 'tarea' in head else 'event' if 'observacion' in head else 'draft'
    return kind,match[2].strip()


class Actions:
    def __init__(self,store):
        self.store=store
        self.drafts=Drafts(store)
        store.con.executescript('''CREATE TABLE IF NOT EXISTS action_proposals(
          id INTEGER PRIMARY KEY, group_id INTEGER REFERENCES groups(id), kind TEXT NOT NULL,
          payload TEXT NOT NULL, scope TEXT NOT NULL, state TEXT NOT NULL DEFAULT 'pending'
          CHECK(state IN ('pending','applied','cancelled')), result_id INTEGER,
          created_at TEXT NOT NULL, resolved_at TEXT, request_id INTEGER UNIQUE);
        CREATE INDEX IF NOT EXISTS actions_group ON action_proposals(group_id,id);''')

    def scope(self,gid):
        if gid is None:return 'General'
        row=self.store.con.execute('SELECT s.name school,g.name FROM groups g JOIN schools s ON s.id=g.school_id WHERE g.id=?',(gid,)).fetchone()
        if row is None:raise ValueError('Grupo inexistente')
        return row['school']+' / '+row['name']

    def propose(self,gid,text,request_id=None):
        parsed=command(text)
        if not parsed:return None
        if request_id is not None:
            existing=self.store.con.execute('SELECT id FROM action_proposals WHERE request_id=? AND group_id IS ?',(request_id,gid)).fetchone()
            if existing:return self.preview(gid,existing['id'])
        kind,body=parsed
        if kind=='help':return HELP
        if kind=='task':
            parts=body.split('|')
            if len(parts)>2:raise ValueError('Usa /tarea Título | AAAA-MM-DD')
            title=parts[0].strip();due=parts[1].strip() if len(parts)==2 else ''
            if not title or len(title)>200:raise ValueError('Título obligatorio, máximo 200 caracteres.')
            if due:due=dt.date.fromisoformat(due).isoformat()
            data={'title':title,'due':due or None}
        elif kind=='event':
            if gid is None:raise ValueError('Selecciona el grupo del alumno primero.')
            parts=[p.strip() for p in body.split('|')]
            if len(parts) not in (2,3) or not parts[0] or not parts[1] or len(parts[1])>10000:
                raise ValueError('Usa /observacion Nombre completo o #ID | Hechos (máximo 10000 caracteres) | AAAA-MM-DD opcional')
            target=parts[0]
            hits=[s for s in self.store.students(gid) if (target==f"#{s['id']}" if target.startswith('#') else normalize(target)==normalize(s['name']))]
            if len(hits)!=1:
                candidates=self.store.find_student(gid,target) if not target.startswith('#') else []
                raise ValueError('No hay una identidad única. Usa el nombre completo o #ID del grupo. '+', '.join(f"{s['name']} (#{s['id']})" for s in candidates[:15]))
            day=dt.date.fromisoformat(parts[2] if len(parts)==3 and parts[2] else today()).isoformat()
            data={'student_id':hits[0]['id'],'student_name':hits[0]['name'],'detail':parts[1],'day':day}
        else:
            if '|' not in body:raise ValueError('Usa /borrador Título | Contenido')
            title,content=Drafts.validate(*body.split('|',1));data={'title':title,'content':content}
        scope=self.scope(gid)
        with self.store.con:
            aid=self.store.con.execute('INSERT INTO action_proposals(group_id,kind,payload,scope,created_at,request_id) VALUES(?,?,?,?,?,?)',(gid,kind,json.dumps(data,ensure_ascii=False),scope,now(),request_id)).lastrowid
        return self.preview(gid,aid)

    def get(self,gid,aid):
        row=self.store.con.execute('SELECT * FROM action_proposals WHERE id=? AND group_id IS ?',(aid,gid)).fetchone()
        if row is None:raise ValueError('Acción no disponible en este grupo.')
        return dict(row)

    def list(self,gid):
        return [dict(r) for r in self.store.con.execute('SELECT * FROM action_proposals WHERE group_id IS ? ORDER BY id DESC',(gid,))]

    def preview(self,gid,aid):
        row=self.get(gid,aid);p=json.loads(row['payload'])
        detail=(f"Tarea: {p['title']}\nVence: {p['due'] or 'sin fecha'}" if row['kind']=='task' else
                f"Observación: {p['student_name']} (#{p['student_id']})\nFecha: {p['day']}\nHechos: {p['detail']}" if row['kind']=='event' else
                f"Borrador: {p['title']}\n{p['content']}")
        state={'pending':'Por confirmar; todavía no aplicado','applied':'Aplicado','cancelled':'Cancelado'}[row['state']]
        return f"Acción #{aid} — {state}\nDestino: {row['scope']}\n{detail}\n\nRevisa esta propuesta en «Acciones»."

    def resolve(self,gid,aid,apply=False):
        con=self.store.con;con.execute('BEGIN IMMEDIATE')
        try:
            row=self.get(gid,aid)
            if row['state']!='pending':
                if apply and row['state']=='applied':con.commit();return row['result_id']
                raise ValueError('Esta propuesta ya fue resuelta.')
            result=None;stamp=now()
            if apply:
                if self.scope(gid)!=row['scope']:raise ValueError('Cambió el nombre del grupo o escuela. Cancela y prepara otra propuesta.')
                p=json.loads(row['payload'])
                if row['kind']=='task':
                    result=con.execute('INSERT INTO tasks(group_id,title,due,created_at) VALUES(?,?,?,?)',(gid,p['title'],p['due'],stamp)).lastrowid
                elif row['kind']=='event':
                    student=con.execute('SELECT * FROM students WHERE id=? AND group_id=? AND active=1',(p['student_id'],gid)).fetchone()
                    if student is None or student['name']!=p['student_name']:raise ValueError('Cambió la identidad o el estado del alumno. Cancela y prepara otra propuesta.')
                    result=con.execute('INSERT INTO events(group_id,student_id,day,category,detail,created_at) VALUES(?,?,?,?,?,?)',(gid,p['student_id'],p['day'],'Observación',p['detail'],stamp)).lastrowid
                else:
                    result=con.execute('INSERT INTO drafts(group_id,current_revision,created_at,updated_at) VALUES(?,1,?,?)',(gid,stamp,stamp)).lastrowid
                    con.execute('INSERT INTO draft_revisions VALUES(?,1,?,?,?,NULL)',(result,p['title'],p['content'],stamp))
            con.execute('UPDATE action_proposals SET state=?,result_id=?,resolved_at=? WHERE id=?',('applied' if apply else 'cancelled',result,stamp,aid))
            con.commit();return result
        except Exception:
            con.rollback();raise
