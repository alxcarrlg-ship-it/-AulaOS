"""Explicit school/teacher requirements; no inferred or global defaults."""
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
    def save(self,gid,name,teacher,requirements,pid=None,expected_revision=0):
        values=(name,teacher,requirements)
        if any(not isinstance(v,str) for v in values):raise ValueError('El perfil debe contener texto.')
        name,teacher,requirements=(v.strip() for v in values)
        if not name or not teacher or not requirements:raise ValueError('Completa nombre del perfil, docente y requisitos.')
        if len(name)>120 or len(teacher)>160 or len(requirements)>6000:raise ValueError('Máximo: nombre 120, docente 160 y requisitos 6000 caracteres.')
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
            con.commit();return pid
        except Exception:con.rollback();raise
    def snapshot(self,gid,pid,expected_revision=None):
        if pid is None:return None
        row=self.get(gid,pid)
        if expected_revision is not None and row['revision']!=expected_revision:raise RevisionConflict('El perfil cambió. Revisa su versión actual antes de enviarlo.')
        return {key:row[key] for key in ('id','name','teacher','requirements','revision')}
