"""Opt-in, bounded local file catalog. Never follows links or uploads on discovery."""
import os
from pathlib import Path
import stat
import time
from core import now, normalize
from materials import Materials, MAX_FILE, extract

SUPPORTED={'.txt','.md','.csv','.docx','.xlsx'}
MAX_ENTRIES=5000
MAX_SECONDS=15
MAX_DEPTH=12


def is_link(path):
    info=path.lstat()
    return stat.S_ISLNK(info.st_mode) or bool(getattr(info,'st_file_attributes',0)&0x400)


def safe_file(root,relative):
    root=Path(root)
    if is_link(root):raise ValueError('La carpeta ahora es un enlace; vuelve a elegir una carpeta real.')
    rel=Path(relative)
    if rel.is_absolute() or '..' in rel.parts:raise ValueError('Ruta fuera de la carpeta autorizada.')
    current=root
    for part in rel.parts:
        current=current/part
        if is_link(current):raise ValueError('No se siguen enlaces ni puntos de redirección.')
    if not current.is_file():raise ValueError('El archivo ya no está disponible.')
    if not current.resolve().is_relative_to(root.resolve()):raise ValueError('Archivo fuera de la carpeta autorizada.')
    return current


class Folders:
    def __init__(self,store):
        self.store=store;self.materials=Materials(store)
        store.con.executescript('''
        CREATE TABLE IF NOT EXISTS watched_folders(id INTEGER PRIMARY KEY,group_id INTEGER REFERENCES groups(id),
          path TEXT NOT NULL,created_at TEXT NOT NULL,scanned_at TEXT,notice TEXT NOT NULL DEFAULT '');
        CREATE UNIQUE INDEX IF NOT EXISTS folder_scope ON watched_folders(COALESCE(group_id,-1),path);
        CREATE TABLE IF NOT EXISTS catalog_files(folder_id INTEGER NOT NULL REFERENCES watched_folders(id) ON DELETE CASCADE,
          relative_path TEXT NOT NULL,size INTEGER NOT NULL,mtime_ns INTEGER NOT NULL,
          PRIMARY KEY(folder_id,relative_path));''')
    def add(self,gid,path):
        path=Path(path).expanduser()
        if is_link(path) or not path.is_dir():raise ValueError('Elige una carpeta real, no un enlace.')
        path=str(path.resolve())
        with self.store.con:
            self.store.con.execute('INSERT OR IGNORE INTO watched_folders(group_id,path,created_at) VALUES(?,?,?)',(gid,path,now()))
        return self.store.con.execute('SELECT id FROM watched_folders WHERE group_id IS ? AND path=?',(gid,path)).fetchone()[0]
    def get(self,gid,fid):
        row=self.store.con.execute('SELECT * FROM watched_folders WHERE id=? AND group_id IS ?',(fid,gid)).fetchone()
        if row is None:raise ValueError('Carpeta no disponible en este grupo.')
        return dict(row)
    def list(self,gid):return [dict(r) for r in self.store.con.execute('SELECT * FROM watched_folders WHERE group_id IS ? ORDER BY id',(gid,))]
    def remove(self,gid,fid):
        self.get(gid,fid)
        with self.store.con:self.store.con.execute('DELETE FROM watched_folders WHERE id=?',(fid,))
    def scan(self,gid,fid):
        folder=self.get(gid,fid);root=Path(folder['path'])
        if not root.is_dir() or is_link(root):raise ValueError('Carpeta desconectada o no disponible; se conserva el catálogo anterior.')
        found=[];stack=[(root,0)];count=0;start=time.monotonic();limited=False;errors=0
        while stack:
            directory,depth=stack.pop()
            if depth>MAX_DEPTH:limited=True;continue
            try:
                if is_link(directory):continue
                with os.scandir(directory) as entries:
                    for entry in entries:
                        count+=1
                        if count>MAX_ENTRIES or time.monotonic()-start>MAX_SECONDS:limited=True;stack=[];break
                        if entry.name.startswith('.') or entry.name.startswith('~$'):continue
                        path=Path(entry.path)
                        try:
                            if is_link(path):continue
                            if entry.is_dir(follow_symlinks=False):stack.append((path,depth+1));continue
                            if path.suffix.lower() not in SUPPORTED or not entry.is_file(follow_symlinks=False):continue
                            info=entry.stat(follow_symlinks=False)
                            if info.st_size>MAX_FILE:continue
                            found.append((fid,str(path.relative_to(root)),info.st_size,info.st_mtime_ns))
                        except OSError:errors+=1
            except OSError:errors+=1
        notice=f'{len(found)} archivos compatibles. '+('Catálogo parcial: alcanzó límite de tiempo, profundidad o entradas. ' if limited else '')+(f'{errors} rutas sin acceso. ' if errors else '')
        # Do not publish a scan after the user disconnected this folder in another window.
        with self.store.con:
            self.get(gid,fid)
            self.store.con.execute('DELETE FROM catalog_files WHERE folder_id=?',(fid,))
            self.store.con.executemany('INSERT INTO catalog_files VALUES(?,?,?,?)',found)
            self.store.con.execute('UPDATE watched_folders SET scanned_at=?,notice=? WHERE id=?',(now(),notice,fid))
        return notice
    def search(self,gid,query=''):
        rows=self.store.con.execute('''SELECT c.*,f.path root,f.scanned_at FROM catalog_files c JOIN watched_folders f
            ON f.id=c.folder_id WHERE f.group_id IS ? ORDER BY c.relative_path''',(gid,))
        q=normalize(query)
        return [dict(r) for r in rows if q in normalize(r['relative_path'])]
    def read(self,gid,fid,relative):
        folder=self.get(gid,fid)
        indexed=self.store.con.execute('SELECT * FROM catalog_files WHERE folder_id=? AND relative_path=?',(fid,relative)).fetchone()
        if indexed is None:raise ValueError('Archivo fuera del catálogo. Actualiza la carpeta.')
        path=safe_file(folder['path'],relative);before=path.stat();text,warning,digest=extract(path);after=path.stat()
        if (before.st_size,before.st_mtime_ns,before.st_ino)!=(after.st_size,after.st_mtime_ns,after.st_ino):raise ValueError('El archivo cambió durante la lectura. Vuelve a abrirlo.')
        changed=(indexed['size'],indexed['mtime_ns'])!=(after.st_size,after.st_mtime_ns)
        return {'title':path.name,'text':text,'warning':warning,'digest':digest,'changed':changed}
    def snapshot(self,gid,fid,relative,expected_digest):
        item=self.read(gid,fid,relative)
        if item['digest']!=expected_digest:raise ValueError('El archivo cambió desde la vista previa. Ábrelo otra vez antes de adjuntar.')
        return self.materials.save(gid,item['title'],item['text'],item['warning']+'\nCopia revisada desde carpeta local.',item['digest'])


def is_search(text):
    return bool(text.split()) and text.split()[0].lower()=='/buscar'


def search_answer(store,gid,text):
    query=text.partition(' ')[2].strip()
    if not query:return 'Usa /buscar seguido de parte del nombre o ruta del archivo. Elige primero carpetas desde Carpetas / buscar archivos.'
    service=Folders(store);rows=service.search(gid,query)
    if not rows:return 'No hay coincidencias en el catálogo de este grupo. Elige o actualiza sus carpetas.'
    return 'Archivos del catálogo local (no se han leído ni enviado):\n'+'\n'.join(r['relative_path']+' — '+r['root'] for r in rows[:50])+('\nHay más resultados; precisa el nombre.' if len(rows)>50 else '')+'\nAbre Carpetas / buscar archivos para revisar el contenido y elegir qué adjuntar. El catálogo puede estar desactualizado.'
