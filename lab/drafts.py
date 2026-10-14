"""Offline drafts with immutable revisions and optimistic concurrency checks."""
import hashlib
from core import now
from materials import Materials, MAX_TEXT


class RevisionConflict(ValueError):
    pass


class Drafts:
    def __init__(self, store):
        self.store=store
        self.materials=Materials(store)
        store.con.executescript('''
        CREATE TABLE IF NOT EXISTS drafts(
          id INTEGER PRIMARY KEY, group_id INTEGER REFERENCES groups(id),
          source_material_id INTEGER REFERENCES materials(id), current_revision INTEGER NOT NULL,
          created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS draft_revisions(
          draft_id INTEGER NOT NULL REFERENCES drafts(id), revision INTEGER NOT NULL,
          title TEXT NOT NULL, content TEXT NOT NULL, created_at TEXT NOT NULL,
          restored_from INTEGER, PRIMARY KEY(draft_id,revision));
        CREATE INDEX IF NOT EXISTS draft_group ON drafts(group_id,updated_at);
        ''')

    @staticmethod
    def validate(title, content):
        title=title.strip();content=content.strip()
        if not title or not content:raise ValueError('Escribe título y contenido antes de guardar.')
        if len(title)>200 or len(content)>MAX_TEXT:raise ValueError('Máximo 200 caracteres en el título y 120000 en el contenido.')
        if any(ord(c)<32 and c not in '\t\n\r' for c in title+content):
            raise ValueError('El texto contiene caracteres de control no admitidos.')
        return title,content

    def create(self,gid,title,content,source_material_id=None):
        title,content=self.validate(title,content)
        if source_material_id is not None:self.materials.get(gid,source_material_id)
        stamp=now()
        with self.store.con:
            did=self.store.con.execute('INSERT INTO drafts(group_id,source_material_id,current_revision,created_at,updated_at) VALUES(?,?,1,?,?)',
                                      (gid,source_material_id,stamp,stamp)).lastrowid
            self.store.con.execute('INSERT INTO draft_revisions VALUES(?,1,?,?,?,NULL)',(did,title,content,stamp))
        return did

    def from_material(self,gid,mid):
        material=self.materials.get(gid,mid)
        return self.create(gid,material['title'],material['content'],mid)

    def get(self,gid,did,revision=None):
        row=self.store.con.execute('''SELECT d.id,d.group_id,d.source_material_id,d.current_revision,
            r.revision,r.title,r.content,r.created_at,r.restored_from
            FROM drafts d JOIN draft_revisions r ON r.draft_id=d.id
            AND r.revision=COALESCE(?,d.current_revision) WHERE d.id=? AND d.group_id IS ?''',(revision,did,gid)).fetchone()
        if row is None:raise ValueError('Borrador o versión no disponible en este grupo.')
        return dict(row)

    def list(self,gid,query=''):
        rows=self.store.con.execute('''SELECT d.id,r.title,d.current_revision,d.updated_at
            FROM drafts d JOIN draft_revisions r ON r.draft_id=d.id AND r.revision=d.current_revision
            WHERE d.group_id IS ? ORDER BY d.updated_at DESC,d.id DESC''',(gid,))
        return [dict(r) for r in rows if query.casefold() in r['title'].casefold()]

    def history(self,gid,did):
        self.get(gid,did)
        return [dict(r) for r in self.store.con.execute('SELECT revision,title,created_at,restored_from FROM draft_revisions WHERE draft_id=? ORDER BY revision DESC',(did,))]

    def save(self,gid,did,title,content,expected_revision,restored_from=None):
        title,content=self.validate(title,content)
        self.store.con.execute('BEGIN IMMEDIATE')
        try:
            current=self.get(gid,did)
            if current['revision']!=expected_revision:
                raise RevisionConflict('Otra ventana guardó una versión más reciente. Conserva tu texto y abre la versión actual antes de continuar.')
            if restored_from is not None:self.get(gid,did,restored_from)
            if (title,content)==(current['title'],current['content']) and restored_from is None:
                self.store.con.commit();return current['revision']
            revision=current['revision']+1;stamp=now()
            self.store.con.execute('INSERT INTO draft_revisions VALUES(?,?,?,?,?,?)',(did,revision,title,content,stamp,restored_from))
            self.store.con.execute('UPDATE drafts SET current_revision=?,updated_at=? WHERE id=?',(revision,stamp,did))
            self.store.con.commit();return revision
        except Exception:
            self.store.con.rollback();raise

    def restore(self,gid,did,revision,expected_revision):
        old=self.get(gid,did,revision)
        return self.save(gid,did,old['title'],old['content'],expected_revision,restored_from=revision)

    def snapshot(self,gid,did,revision=None):
        row=self.get(gid,did,revision)
        digest=hashlib.sha256(f"draft:{did}:{row['revision']}:{row['title']}:{row['content']}".encode()).hexdigest()
        return self.materials.save(gid,row['title'],row['content'],
             f"Copia del borrador B{did}, versión {row['revision']}. Revisar antes de usar. La edición del borrador no cambia esta copia.",digest)
