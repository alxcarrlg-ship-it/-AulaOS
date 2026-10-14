"""Asynchronous catalog scans with explicit file preview and attachment."""
import queue
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from core import Store
from folders import Folders

class FolderWindow(tk.Toplevel):
    def __init__(self,app,gid):
        super().__init__(app);self.app=app;self.gid=gid;self.service=Folders(app.store);self.busy=False;self.results=queue.Queue();self.preview_item=None
        self.title('Carpetas elegidas · búsqueda local');self.geometry('950x730')
        ttk.Label(self,text='Solo se catalogan nombres de archivos en tus carpetas elegidas. Nada se envía al buscar.').pack(padx=12,pady=8)
        self.folders=tk.Listbox(self,height=4,exportselection=False);self.folders.pack(fill='x',padx=12)
        row=ttk.Frame(self);row.pack(fill='x',padx=12,pady=5)
        for title,fn in [('Elegir carpeta',self.add),('Actualizar catálogo',self.scan),('Desvincular carpeta',self.remove)]:ttk.Button(row,text=title,command=fn).pack(side='left',padx=3)
        self.query=tk.StringVar();ttk.Entry(self,textvariable=self.query).pack(fill='x',padx=12);self.query.trace_add('write',lambda *args:self.search())
        self.files=tk.Listbox(self,height=8,exportselection=False);self.files.pack(fill='x',padx=12,pady=5)
        ttk.Button(self,text='Leer archivo seleccionado',command=self.read).pack(anchor='w',padx=12)
        self.preview=tk.Text(self,wrap='word',state='disabled');self.preview.pack(fill='both',expand=True,padx=12,pady=5)
        ttk.Button(self,text='Guardar copia y adjuntar al chat',command=self.attach).pack(pady=5)
        self.notice=tk.StringVar();ttk.Label(self,textvariable=self.notice,wraplength=900).pack(padx=12,pady=5)
        self.folder_rows=[];self.file_rows=[];self.refresh();app.draft_editors.add(self);self.protocol('WM_DELETE_WINDOW',self.try_close);self.poll_id=self.after(100,self.poll)
    def refresh(self):
        self.folder_rows=self.service.list(self.gid);self.folders.delete(0,'end')
        for r in self.folder_rows:self.folders.insert('end',r['path']+' · '+(r['scanned_at'] or 'Sin actualizar'))
        if self.folder_rows:self.folders.selection_set(0)
        self.search()
    def selected_folder(self):return self.folder_rows[self.folders.curselection()[0]] if self.folders.curselection() else None
    def search(self):
        self.file_rows=self.service.search(self.gid,self.query.get());self.files.delete(0,'end')
        for r in self.file_rows:self.files.insert('end',r['relative_path']+' · '+r['root'])
    def add(self):
        if self.busy:return
        path=filedialog.askdirectory(parent=self)
        if not path:return
        try:fid=self.service.add(self.gid,path);self.refresh();self.scan(fid)
        except Exception as exc:messagebox.showerror('Carpeta',str(exc),parent=self)
    def remove(self):
        if self.busy:return
        row=self.selected_folder()
        if row and messagebox.askyesno('Desvincular','¿Quitar esta carpeta del catálogo? Sus archivos y las copias ya guardadas se conservan.',parent=self):
            self.service.remove(self.gid,row['id']);self.preview_item=None;self.refresh()
    def run(self,fn):
        if self.busy:return
        self.busy=True;self.notice.set('Leyendo en este equipo…')
        db=self.app.store.db_path
        def worker():
            store=None
            try:store=Store(db);self.results.put((fn(Folders(store)),None))
            except Exception as exc:self.results.put((None,str(exc)))
            finally:
                if store:store.close()
        threading.Thread(target=worker,daemon=True).start()
    def scan(self,fid=None):
        row=self.selected_folder()
        if fid is None and not row:return
        fid=fid if fid is not None else row['id']
        self.run(lambda service:('scan',service.scan(self.gid,fid)))
    def read(self):
        if not self.files.curselection() or self.busy:return
        row=dict(self.file_rows[self.files.curselection()[0]])
        self.run(lambda service:('read',(row,service.read(self.gid,row['folder_id'],row['relative_path']))))
    def attach(self):
        if self.busy or not self.preview_item:return
        row,item=self.preview_item
        self.run(lambda service:('attach',service.snapshot(self.gid,row['folder_id'],row['relative_path'],item['digest'])))
    def poll(self):
        try:result,error=self.results.get_nowait()
        except queue.Empty:pass
        else:
            self.busy=False
            if error:self.notice.set(error)
            elif result[0]=='scan':self.refresh();self.notice.set(result[1])
            elif result[0]=='attach':
                try:
                    ids=list(dict.fromkeys(self.app.attachments.get(self.gid,[])+[result[1]]));self.service.materials.context(self.gid,ids)
                    self.app.attachments[self.gid]=ids
                    if self.app.gid==self.gid:self.app.refresh_attachments()
                    self.notice.set('Copia guardada y seleccionada para el chat del grupo de origen; aún no enviada.')
                except Exception as exc:self.notice.set(str(exc)+' La copia sigue disponible en Materiales para elegir un fragmento.')
            else:
                self.preview_item=result[1];row,item=result[1]
                self.preview.configure(state='normal');self.preview.delete('1.0','end');self.preview.insert('1.0',item['text']);self.preview.configure(state='disabled')
                self.notice.set(('Cambió desde el catálogo; se muestra el contenido actual. ' if item['changed'] else '')+item['warning'])
        self.poll_id=self.after(100,self.poll)
    def try_close(self):
        if self.busy:messagebox.showinfo('Lectura en curso','Espera a que termine la lectura.',parent=self);return False
        self.after_cancel(self.poll_id);self.app.draft_editors.discard(self);self.destroy();return True
