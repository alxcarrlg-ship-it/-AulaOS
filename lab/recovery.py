"""Persistent working copies, separate from approved immutable revisions."""
import json
from core import now
from drafts import Drafts
from templates import Templates,validate_changes

class Recovery:
    def __init__(self,store):
        self.store=store;self.drafts=Drafts(store);self.templates=Templates(store)
        store.con.execute('''CREATE TABLE IF NOT EXISTS recovery_snapshots(
            token TEXT PRIMARY KEY,group_id INTEGER REFERENCES groups(id),kind TEXT NOT NULL,
            target_id INTEGER,base_revision INTEGER,payload TEXT NOT NULL,updated_at TEXT NOT NULL)''')
        store.con.commit()
    def validate(self,gid,kind,target,revision,payload):
        if gid is not None and self.store.con.execute('SELECT 1 FROM groups WHERE id=?',(gid,)).fetchone() is None:raise ValueError('Grupo inexistente.')
        if kind=='draft':
            if target is not None:self.drafts.get(gid,target,revision)
            elif revision is not None:raise ValueError('Borrador nuevo sin revisión base.')
            if not isinstance(payload,dict) or set(payload)!={'title','content'} or any(not isinstance(v,str) for v in payload.values()):raise ValueError('Copia de borrador inválida.')
            if len(payload['title'])>200 or len(payload['content'])>120000:raise ValueError('Copia de borrador demasiado extensa.')
        elif kind=='template':
            doc=self.templates.document(gid,target,revision);template=self.templates.get(gid,doc['template_id'])
            validate_changes(json.loads(template['schema_json']),payload)
        elif kind=='project':
            from projects import Projects,FIELDS
            service=Projects(self.store)
            if target is not None:service.get(gid,target,revision)
            if not isinstance(payload,dict) or set(payload)!=set(FIELDS)|{'documents'} or any(not isinstance(payload[k],str) for k in FIELDS):raise ValueError('Copia de proyecto inválida.')
            if sum(len(payload[k]) for k in FIELDS)>10000:raise ValueError('Copia demasiado extensa.')
            if not isinstance(payload['documents'],list) or len(payload['documents'])>20:raise ValueError('Referencias inválidas.')
            for ref in payload['documents']:self.templates.document(gid,ref['id'],ref['revision'])
        elif kind in ('evidence','evidence_new'):
            from evidence import Evidence,FIELDS
            service=Evidence(self.store)
            if kind=='evidence':service.get(gid,target,revision)
            else:service.projects.get(gid,target,revision)
            if not isinstance(payload,dict) or set(payload)!={'content','student_id','kind','source_id'}:raise ValueError('Copia de evidencia inválida.')
            if not isinstance(payload['content'],dict) or set(payload['content'])!=set(FIELDS) or any(not isinstance(v,str) for v in payload['content'].values()):raise ValueError('Texto de evidencia inválido.')
            if kind=='evidence_new':
                if payload['student_id'] is not None:self.store._require_membership(gid,payload['student_id'])
                service.source(gid,payload['kind'],payload['source_id'])
        elif kind=='lesson':
            from lesson_packs import LessonPacks
            LessonPacks(self.store).get(gid,target,revision)
            if not isinstance(payload,dict) or set(payload)!={'title','teacher_guide','worksheet','slides'}:raise ValueError('Copia de materiales inválida.')
            if any(not isinstance(payload[k],str) for k in ('title','teacher_guide','worksheet')) or not isinstance(payload['slides'],list) or not 2<=len(payload['slides'])<=20:raise ValueError('Copia de materiales inválida.')
            for slide in payload['slides']:
                if not isinstance(slide,dict) or set(slide)!={'title','body','notes'} or not isinstance(slide['title'],str) or not isinstance(slide['notes'],str) or not isinstance(slide['body'],list) or any(not isinstance(v,str) for v in slide['body']):raise ValueError('Diapositiva inválida.')
        elif kind=='review':
            from template_suggestions import TemplateSuggestions
            service=TemplateSuggestions(self.store);proposal=service.get(gid,target)
            if proposal['state']!='pending':raise ValueError('La propuesta ya está resuelta.')
            allowed={c['id'] for c in service.review(gid,target)}
            if not isinstance(payload,dict) or set(payload)!={'values','selected'} or not isinstance(payload['values'],dict) or not isinstance(payload['selected'],list):raise ValueError('Copia de revisión inválida.')
            if set(payload['values'])!=allowed or not set(payload['selected'])<=allowed or any(not isinstance(v,str) for v in payload['values'].values()):raise ValueError('Campos ajenos a la revisión.')
        elif kind=='profile':
            from teaching_profiles import TeachingProfiles
            if target is not None:TeachingProfiles(self.store).get(gid,target)
            if not isinstance(payload,dict) or set(payload)!={'name','teacher','requirements','questions'} or any(not isinstance(v,str) for v in payload.values()):raise ValueError('Copia de perfil inválida.')
        else:raise ValueError('Tipo de recuperación inválido.')
        if target is not None and (type(revision) is not int or revision<(0 if kind=='review' else 1)):raise ValueError('Falta revisión base.')
        encoded=json.dumps(payload,ensure_ascii=False)
        if len(encoded.encode('utf-8'))>600000:raise ValueError('Copia de recuperación demasiado grande.')
        return encoded
    def put(self,token,gid,kind,target,revision,payload):
        if not isinstance(token,str) or not token or len(token)>80:raise ValueError('Sesión inválida.')
        encoded=self.validate(gid,kind,target,revision,payload)
        con=self.store.con;con.execute('BEGIN IMMEDIATE')
        try:
            existing=con.execute('SELECT * FROM recovery_snapshots WHERE token=?',(token,)).fetchone()
            if existing and (existing['group_id']!=gid or existing['kind']!=kind or existing['target_id']!=target):raise ValueError('La sesión pertenece a otro documento o grupo.')
            con.execute('INSERT INTO recovery_snapshots VALUES(?,?,?,?,?,?,?) ON CONFLICT(token) DO UPDATE SET base_revision=excluded.base_revision,payload=excluded.payload,updated_at=excluded.updated_at',(token,gid,kind,target,revision,encoded,now()));con.commit()
        except Exception:con.rollback();raise
    def list(self,gid,kind,target):
        return [dict(r,payload=json.loads(r['payload'])) for r in self.store.con.execute('SELECT * FROM recovery_snapshots WHERE group_id IS ? AND kind=? AND target_id IS ? ORDER BY updated_at DESC,token',(gid,kind,target))]
    def get(self,gid,token):
        row=self.store.con.execute('SELECT * FROM recovery_snapshots WHERE token=? AND group_id IS ?',(token,gid)).fetchone()
        if row is None:raise ValueError('Copia no disponible en este grupo.')
        return dict(row,payload=json.loads(row['payload']))
    def delete(self,gid,token):
        with self.store.con:self.store.con.execute('DELETE FROM recovery_snapshots WHERE token=? AND group_id IS ?',(token,gid))
