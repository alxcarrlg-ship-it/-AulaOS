"""Explicit school/teacher requirements; no inferred or global defaults."""
import json
from core import now
from drafts import RevisionConflict

class TeachingProfiles:
    def __init__(self,store):
        self.store=store
        store.con.execute('''CREATE TABLE IF NOT EXISTS teaching_profiles(
            id INTEGER PRIMARY KEY,school_id INTEGER NOT NULL REFERENCES schools(id),
            name TEXT NOT NULL,teacher TEXT NOT NULL,requirements TEXT NOT NULL,
            revision INTEGER NOT NULL,updated_at TEXT NOT NULL,
            UNIQUE(school_id,name,teacher))''')
        columns={r[1] for r in store.con.execute('PRAGMA table_info(teaching_profiles)')}
        if 'questions_json' not in columns:store.con.execute("ALTER TABLE teaching_profiles ADD COLUMN questions_json TEXT NOT NULL DEFAULT '[]'")
        store.con.commit()
    def school(self,gid):
        row=self.store.con.execute('SELECT school_id FROM groups WHERE id=?',(gid,)).fetchone()
        if row is None:raise ValueError('Grupo inexistente.')
        return row['school_id']
    def list(self,gid):
        return [dict(r) for r in self.store.con.execute('SELECT * FROM teaching_profiles WHERE school_id=? ORDER BY teacher,name,id',(self.school(gid),))]
    def get(self,gid,pid):
        row=self.store.con.execute('SELECT * FROM teaching_profiles WHERE id=? AND school_id=?',(pid,self.school(gid))).fetchone()
        if row is None:raise ValueError('Perfil inexistente o de otra escuela.')
        return dict(row)
    def save(self,gid,name,teacher,requirements,pid=None,expected_revision=0,questions=None):
        values=(name,teacher,requirements)
        if any(not isinstance(v,str) for v in values):raise ValueError('El perfil debe contener texto.')
        name,teacher,requirements=(v.strip() for v in values)
        if not name or not teacher or not requirements:raise ValueError('Completa nombre del perfil, docente y requisitos.')
        if len(name)>120 or len(teacher)>160 or len(requirements)>6000:raise ValueError('Máximo: nombre 120, docente 160 y requisitos 6000 caracteres.')
        if questions is not None:
            if not isinstance(questions,list) or len(questions)>8 or any(not isinstance(q,str) or not q.strip() or len(q)>100 or any(c in q for c in ':\n\r') for q in questions):raise ValueError('Usa hasta 8 datos, de 100 caracteres, sin dos puntos ni saltos de línea.')
            questions=[q.strip() for q in questions]
            if len({q.casefold() for q in questions})!=len(questions):raise ValueError('No repitas datos requeridos.')
        con=self.store.con;con.execute('BEGIN IMMEDIATE')
        try:
            school=self.school(gid)
            if pid is None:
                if expected_revision!=0:raise RevisionConflict('El perfil nuevo no tiene una versión anterior.')
                pid=con.execute('INSERT INTO teaching_profiles(school_id,name,teacher,requirements,revision,updated_at) VALUES(?,?,?,?,1,?)',(school,name,teacher,requirements,now())).lastrowid
            else:
                current=self.get(gid,pid)
                if current['revision']!=expected_revision:raise RevisionConflict('Otro editor modificó el perfil. Vuelve a abrirlo antes de guardar.')
                con.execute('UPDATE teaching_profiles SET name=?,teacher=?,requirements=?,revision=revision+1,updated_at=? WHERE id=?',(name,teacher,requirements,now(),pid))
            if questions is not None:con.execute('UPDATE teaching_profiles SET questions_json=? WHERE id=?',(json.dumps(questions,ensure_ascii=False),pid))
            con.commit();return pid
        except Exception:con.rollback();raise
    def snapshot(self,gid,pid,expected_revision=None):
        if pid is None:return None
        row=self.get(gid,pid)
        if expected_revision is not None and row['revision']!=expected_revision:raise RevisionConflict('El perfil cambió. Revisa su versión actual antes de enviarlo.')
        return dict({key:row[key] for key in ('id','name','teacher','requirements','revision')},questions=json.loads(row['questions_json']))


def missing_details(profile,goal):
    """Check explicit labelled answers, never infer facts from prose."""
    if not profile:return []
    answers={}
    for line in goal.splitlines():
        label,separator,value=line.partition(':')
        if separator:answers[label.strip().casefold()]=value.strip()
    placeholders={'','pendiente','por definir','no sé','no se','?'}
    return [q for q in profile.get('questions',[]) if answers.get(q.casefold(),'').casefold() in placeholders]


def conflicting_details(profile,goal):
    if not profile:return []
    found={q:[] for q in profile.get('questions',[])}
    for line in goal.splitlines():
        label,sep,value=line.partition(':')
        if not sep:continue
        for q in found:
            if label.strip().casefold()==q.casefold() and not missing_details({'questions':[q]},line):
                if value.strip().casefold() not in [v.casefold() for v in found[q]]:found[q].append(value.strip())
    return [q for q,values in found.items() if len(values)>1]
