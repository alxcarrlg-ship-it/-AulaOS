"""Local project evidence and follow-up; no inferred achievement or automatic sharing."""
import datetime as dt
import json
from core import now
from drafts import RevisionConflict
from projects import Projects,describe as describe_project
from materials import Materials

STATES=('Por revisar','Revisada','Requiere seguimiento','Retirada')
FIELDS=('title','day','observation','next_step','due','status')

class Evidence:
    def __init__(self,store):
        self.store=store;self.projects=Projects(store);self.materials=Materials(store)
        store.con.executescript('''CREATE TABLE IF NOT EXISTS project_evidence(
            id INTEGER PRIMARY KEY,project_id INTEGER NOT NULL REFERENCES teaching_projects(id),
            project_revision INTEGER NOT NULL,student_json TEXT,source_json TEXT NOT NULL,
            current_revision INTEGER NOT NULL,created_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS project_evidence_revisions(
            evidence_id INTEGER NOT NULL REFERENCES project_evidence(id),revision INTEGER NOT NULL,
            content_json TEXT NOT NULL,created_at TEXT NOT NULL,PRIMARY KEY(evidence_id,revision));''')
    def validate(self,content):
        if not isinstance(content,dict) or set(content)!=set(FIELDS) or any(not isinstance(content[k],str) for k in FIELDS):raise ValueError('Campos de evidencia inválidos.')
        clean={k:content[k].strip() for k in FIELDS}
        if not clean['title'] or len(clean['title'])>160:raise ValueError('Título obligatorio, hasta 160 caracteres.')
        if not clean['observation'] or len(clean['observation'])>8000 or len(clean['next_step'])>4000:raise ValueError('Observación obligatoria (hasta 8000 caracteres); seguimiento hasta 4000.')
        if clean['status'] not in STATES:raise ValueError('Estado de revisión inválido.')
        for key in ('day','due'):
            if key=='due' and not clean[key]:continue
            try:
                if dt.date.fromisoformat(clean[key]).isoformat()!=clean[key]:raise ValueError()
            except ValueError as exc:raise ValueError('Fechas en formato AAAA-MM-DD.') from exc
        if clean['status']=='Requiere seguimiento' and not clean['next_step']:raise ValueError('Describe el siguiente paso para el seguimiento.')
        if any(not(c in '\n\r\t' or 0x20<=ord(c)<=0xD7FF or 0xE000<=ord(c)<=0xFFFD or 0x10000<=ord(c)<=0x10FFFF) for c in ''.join(clean.values())):raise ValueError('Caracteres no admitidos.')
        return clean
    def observations(self,gid):
        self.projects.group(gid)
        return [dict(r) for r in self.store.con.execute('SELECT e.*,s.name FROM events e JOIN students s ON s.id=e.student_id WHERE e.group_id=? AND s.group_id=? ORDER BY e.day DESC,e.id DESC',(gid,gid))]
    def source(self,gid,kind,source_id):
        if kind=='Sin adjunto':
            if source_id is not None:raise ValueError('Referencia inesperada.')
            return {'kind':kind},None
        if type(source_id) is not int:raise ValueError('Selecciona una fuente válida.')
        if kind=='Material':
            row=self.materials.get(gid,source_id)
            if len(row['content'])>20000:raise ValueError('El material supera 20000 caracteres. Guarda un fragmento revisado en Materiales.')
            return dict(kind=kind,id=row['id'],title=row['title'],content=row['content'],digest=row['digest']),None
        if kind=='Observación':
            row=self.store.con.execute('SELECT * FROM events WHERE id=? AND group_id=?',(source_id,gid)).fetchone()
            if row is None:raise ValueError('Observación no disponible en este grupo.')
            self.store._require_membership(gid,row['student_id'])
            if len(row['detail'])>20000:raise ValueError('Observación demasiado extensa.')
            return dict(kind=kind,id=row['id'],day=row['day'],category=row['category'],content=row['detail']),row['student_id']
        raise ValueError('Tipo de fuente inválido.')
    def create(self,gid,pid,project_revision,content,student_id=None,kind='Sin adjunto',source_id=None):
        con=self.store.con;con.execute('BEGIN IMMEDIATE')
        try:
            project=self.projects.snapshot(gid,pid,project_revision)
            if project is None:raise ValueError('Selecciona un proyecto.')
            clean=self.validate(content);source,owner=self.source(gid,kind,source_id)
            if owner is not None:
                if student_id is not None and student_id!=owner:raise ValueError('La observación pertenece a otro alumno.')
                student_id=owner
            student=None
            if student_id is not None:
                if type(student_id) is not int:raise ValueError('Alumno inválido.')
                self.store._require_membership(gid,student_id)
                student=dict(con.execute('SELECT id,name FROM students WHERE id=?',(student_id,)).fetchone())
            eid=con.execute('INSERT INTO project_evidence(project_id,project_revision,student_json,source_json,current_revision,created_at) VALUES(?,?,?,?,1,?)',(pid,project_revision,json.dumps(student,ensure_ascii=False),json.dumps(source,ensure_ascii=False),now())).lastrowid
            con.execute('INSERT INTO project_evidence_revisions VALUES(?,1,?,?)',(eid,json.dumps(clean,ensure_ascii=False),now()));con.commit();return eid
        except Exception:con.rollback();raise
    def get(self,gid,eid,revision=None):
        row=self.store.con.execute('SELECT e.* FROM project_evidence e JOIN teaching_projects p ON p.id=e.project_id WHERE e.id=? AND p.group_id=?',(eid,gid)).fetchone()
        if row is None:raise ValueError('Evidencia no disponible en este grupo.')
        rev=row['current_revision'] if revision is None else revision
        saved=self.store.con.execute('SELECT * FROM project_evidence_revisions WHERE evidence_id=? AND revision=?',(eid,rev)).fetchone()
        if saved is None:raise ValueError('Revisión inexistente.')
        return dict(row,revision=rev,content=json.loads(saved['content_json']),student=json.loads(row['student_json']),source=json.loads(row['source_json']),updated_at=saved['created_at'])
    def list(self,gid,pid,status=None):
        self.projects.get(gid,pid)
        if status is not None and status not in STATES:raise ValueError('Filtro inválido.')
        rows=[self.get(gid,r[0]) for r in self.store.con.execute('SELECT id FROM project_evidence WHERE project_id=? ORDER BY id DESC',(pid,))]
        return [r for r in rows if status is None or r['content']['status']==status]
    def save(self,gid,eid,content,expected_revision):
        con=self.store.con;con.execute('BEGIN IMMEDIATE')
        try:
            row=self.get(gid,eid);clean=self.validate(content)
            if row['current_revision']!=expected_revision:raise RevisionConflict('Otra ventana cambió la evidencia; vuelve a abrirla.')
            if clean==row['content']:con.commit();return expected_revision
            rev=expected_revision+1
            con.execute('INSERT INTO project_evidence_revisions VALUES(?,?,?,?)',(eid,rev,json.dumps(clean,ensure_ascii=False),now()))
            con.execute('UPDATE project_evidence SET current_revision=? WHERE id=?',(rev,eid));con.commit();return rev
        except Exception:con.rollback();raise
    def history(self,gid,eid):
        self.get(gid,eid)
        return [r[0] for r in self.store.con.execute('SELECT revision FROM project_evidence_revisions WHERE evidence_id=? ORDER BY revision DESC',(eid,))]
    def report(self,gid,pid,status=None):
        project=self.projects.get(gid,pid);rows=self.list(gid,pid,status)
        group=next(g for g in self.store.groups() if g['id']==gid)
        text=f"Escuela: {group['school']} · Grupo: {group['name']}\n\n"+describe_project(project)
        text+='\n# Evidencias y seguimiento\n\nFiltro: '+(status or 'Todos los estados')+'\n\n'
        text+='Registro docente; una evidencia o su estado de revisión no demuestra por sí solo logro ni realización del proyecto.\n\n'
        for state in STATES:text+=f"{state}: {sum(r['content']['status']==state for r in rows)}\n"
        for row in rows:text+='\n## '+row['content']['title']+'\n\n'+describe(row)+'\n'
        return text

def describe(row):
    c=row['content'];s=row['source'];student=row['student']
    text=c['title']+'\n'+f"Evidencia #{row['id']} · revisión {row['revision']} · vinculada al proyecto v{row['project_revision']}\n"
    text+='Alumno: '+(student['name']+f" (#{student['id']})" if student else 'Grupo')+'\n'
    text+=f"Fecha: {c['day']} · Estado: {c['status']}\n\nObservación del docente:\n{c['observation']}\n\nSiguiente paso:\n{c['next_step'] or '(Sin registrar)'}\nFecha de seguimiento: {c['due'] or '(Sin fijar)'}\n"
    text+='\nFuente: '+s['kind']+(f" #{s['id']}" if 'id' in s else '')+'\n'
    if 'content' in s:text+=(s.get('title') or s.get('category',''))+'\n'+s.get('day','')+'\n'+s['content']+'\n'
    return text
