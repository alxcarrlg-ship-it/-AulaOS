"""Explicit, versioned teaching progress. Planning never implies completion."""
import json
from core import now
from drafts import RevisionConflict
from templates import Templates

FIELDS=('title','planned','completed','pending','next_step')
LABELS={'title':'Proyecto','planned':'Planeado','completed':'Realizado (declarado por el docente)','pending':'Pendiente','next_step':'Siguiente paso'}

class Projects:
    def __init__(self,store):
        self.store=store;self.templates=Templates(store)
        store.con.executescript('''CREATE TABLE IF NOT EXISTS teaching_projects(
            id INTEGER PRIMARY KEY,group_id INTEGER NOT NULL REFERENCES groups(id),
            current_revision INTEGER NOT NULL,created_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS teaching_project_revisions(
            project_id INTEGER NOT NULL REFERENCES teaching_projects(id),revision INTEGER NOT NULL,
            content_json TEXT NOT NULL,created_at TEXT NOT NULL,PRIMARY KEY(project_id,revision));''')
    def group(self,gid):
        if self.store.con.execute('SELECT 1 FROM groups WHERE id=?',(gid,)).fetchone() is None:raise ValueError('Grupo inexistente.')
    def get(self,gid,pid,revision=None):
        row=self.store.con.execute('SELECT * FROM teaching_projects WHERE id=? AND group_id=?',(pid,gid)).fetchone()
        if row is None:raise ValueError('Proyecto inexistente o de otro grupo.')
        rev=row['current_revision'] if revision is None else revision
        saved=self.store.con.execute('SELECT * FROM teaching_project_revisions WHERE project_id=? AND revision=?',(pid,rev)).fetchone()
        if saved is None:raise ValueError('Revisión de proyecto inexistente.')
        return dict(id=pid,revision=rev,current_revision=row['current_revision'],created_at=saved['created_at'],**json.loads(saved['content_json']))
    def list(self,gid):
        self.group(gid)
        ids=[r['id'] for r in self.store.con.execute('SELECT id FROM teaching_projects WHERE group_id=? ORDER BY id DESC',(gid,))]
        return [self.get(gid,pid) for pid in ids]
    def history(self,gid,pid):
        self.get(gid,pid)
        return [dict(r) for r in self.store.con.execute('SELECT revision,created_at FROM teaching_project_revisions WHERE project_id=? ORDER BY revision DESC',(pid,))]
    def validate(self,gid,content):
        self.group(gid)
        if not isinstance(content,dict) or set(content)!=set(FIELDS)|{'documents'}:raise ValueError('Campos de proyecto inválidos.')
        if any(not isinstance(content[k],str) for k in FIELDS):raise ValueError('Los datos del proyecto deben ser texto.')
        cleaned={k:content[k].strip() for k in FIELDS}
        if not cleaned['title'] or len(cleaned['title'])>160:raise ValueError('Escribe un título de hasta 160 caracteres.')
        if sum(len(cleaned[k]) for k in FIELDS)>10000:raise ValueError('Máximo 10000 caracteres por registro de avance.')
        refs=content['documents']
        if not isinstance(refs,list) or len(refs)>20:raise ValueError('Máximo 20 referencias de documentos por proyecto.')
        documents=[];seen=set()
        for ref in refs:
            if not isinstance(ref,dict) or not {'id','revision'}<=set(ref) or set(ref)-{'id','revision','title'}:raise ValueError('Referencia de documento inválida.')
            if type(ref['id']) is not int or type(ref['revision']) is not int:raise ValueError('Referencia de documento inválida.')
            key=(ref['id'],ref['revision'])
            if key in seen:raise ValueError('Referencia duplicada.')
            seen.add(key);doc=self.templates.document(gid,*key)
            documents.append(dict(id=doc['id'],revision=doc['revision'],title=doc['title']))
        return dict(cleaned,documents=documents)
    def save(self,gid,content,pid=None,expected_revision=0):
        con=self.store.con;con.execute('BEGIN IMMEDIATE')
        try:
            content=self.validate(gid,content)
            if pid is None:
                if expected_revision!=0:raise RevisionConflict('El proyecto nuevo no tiene revisión anterior.')
                revision=1
                pid=con.execute('INSERT INTO teaching_projects(group_id,current_revision,created_at) VALUES(?,1,?)',(gid,now())).lastrowid
            else:
                current=self.get(gid,pid)
                if current['revision']!=expected_revision:raise RevisionConflict('Otro editor actualizó este proyecto. Abre la revisión actual antes de guardar.')
                if {k:current[k] for k in (*FIELDS,'documents')}==content:con.commit();return pid,current['revision']
                revision=current['revision']+1
                con.execute('UPDATE teaching_projects SET current_revision=? WHERE id=?',(revision,pid))
            con.execute('INSERT INTO teaching_project_revisions VALUES(?,?,?,?)',(pid,revision,json.dumps(content,ensure_ascii=False),now()))
            con.commit();return pid,revision
        except Exception:con.rollback();raise
    def snapshot(self,gid,pid,expected_revision=None):
        if pid is None:return None
        row=self.get(gid,pid)
        if expected_revision is not None and row['revision']!=expected_revision:raise RevisionConflict('El avance del proyecto cambió. Revisa la versión actual antes de continuar.')
        return {k:row[k] for k in ('id','revision',*FIELDS,'documents')}


def describe(project):
    if not project:return 'Sin proyecto seleccionado.'
    text='Proyecto #'+str(project['id'])+' · revisión '+str(project['revision'])+'\n\n'
    for key in FIELDS:text+=LABELS[key]+'\n'+(project[key] or '(Sin registrar; no se supone completado)')+'\n\n'
    text+='Documentos vinculados (solo referencias, no contenido)\n'
    for doc in project['documents']:text+=doc['title']+' · #'+str(doc['id'])+' v'+str(doc['revision'])+'\n'
    return text
