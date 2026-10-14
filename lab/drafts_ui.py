"""Desktop editor for local draft revisions; no network calls."""
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
from pathlib import Path
import webbrowser
import sqlite3
from document_export import export_document


class DraftEditor(tk.Toplevel):
    def __init__(self,app,gid,did=None):
        super().__init__(app)
        self.app=app;self.service=app.drafts;self.gid=gid;self.did=did
        self.geometry('900x700');self.minsize(720,500)
        group=next((g for g in app.store.groups() if g['id']==gid),None)
        scope=(group['school']+' · '+group['name']) if group else 'General'
        self.title('Borrador · '+scope);self.revision=None;self.saved=('', '')
        self.title_text=tk.StringVar();self.notice=tk.StringVar(value='Nuevo borrador sin guardar')
        ttk.Label(self,text='Título').pack(anchor='w',padx=14,pady=(12,0))
        ttk.Entry(self,textvariable=self.title_text).pack(fill='x',padx=14,pady=5)
        ttk.Label(self,text='Texto y Markdown básico: # títulos, **negrita**, listas, tablas y [fuente](https://…).',wraplength=850).pack(anchor='w',padx=14)
        frame=ttk.Frame(self);frame.pack(fill='both',expand=True,padx=14,pady=10)
        self.body=tk.Text(frame,wrap='word',font=('Segoe UI',11),undo=True)
        scroll=ttk.Scrollbar(frame,command=self.body.yview);self.body.configure(yscrollcommand=scroll.set)
        scroll.pack(side='right',fill='y');self.body.pack(fill='both',expand=True)
        row=ttk.Frame(self);row.pack(fill='x',padx=14,pady=4)
        for title,command in [('Guardar versión',self.save),('Historial',self.history),('Guardar copia',self.save_copy),('Adjuntar copia al chat',self.attach)]:
            ttk.Button(row,text=title,command=command).pack(side='left',padx=3)
        row2=ttk.Frame(self);row2.pack(fill='x',padx=14,pady=4)
        for title,suffix in [('Exportar Word','.docx'),('Exportar HTML imprimible','.html'),('Exportar Markdown','.md')]:
            ttk.Button(row2,text=title,command=lambda s=suffix:self.export(s)).pack(side='left',padx=3)
        ttk.Label(self,textvariable=self.notice,wraplength=850).pack(anchor='w',padx=14,pady=8)
        if did is not None:self.load()
        self.protocol('WM_DELETE_WINDOW',self.try_close)
        app.draft_editors.add(self)

    def values(self):return self.title_text.get().strip(),self.body.get('1.0','end-1c').strip()
    def dirty(self):return self.values()!=self.saved

    def load(self):
        row=self.service.get(self.gid,self.did);self.revision=row['revision']
        self.title_text.set(row['title']);self.body.delete('1.0','end');self.body.insert('1.0',row['content'])
        self.body.edit_reset();self.saved=(row['title'],row['content'])
        self.notice.set(f"Borrador B{self.did} · versión {self.revision} · guardado localmente · {row['created_at']}")

    def save(self):
        title,content=self.values()
        try:
            if self.did is None:self.did=self.service.create(self.gid,title,content);self.revision=1
            else:self.revision=self.service.save(self.gid,self.did,title,content,self.revision)
        except (ValueError,OSError,sqlite3.Error) as exc:
            messagebox.showerror('No se guardó',str(exc)+'\nTu texto sigue en el editor. Puedes usar Guardar copia.',parent=self);return False
        self.saved=(title,content);self.notice.set(f'Borrador B{self.did} · versión {self.revision} guardada en este equipo.')
        return True

    def save_copy(self):
        title,content=self.values()
        title=simpledialog.askstring('Guardar copia','Título de la copia:',initialvalue=title+' — copia',parent=self)
        if not title:return
        try:did=self.service.create(self.gid,title,content)
        except (ValueError,sqlite3.Error) as exc:messagebox.showerror('Copia',str(exc),parent=self);return
        self.did=did;self.load()

    def attach(self):
        if not self.save():return
        try:mid=self.service.snapshot(self.gid,self.did,self.revision)
        except (ValueError,sqlite3.Error) as exc:
            messagebox.showerror('No se adjuntó',str(exc),parent=self);return
        self.app.attachments[self.gid]=[mid]
        if self.gid==self.app.gid:self.app.refresh_attachments()
        self.notice.set(f'Copia M{mid} de la versión {self.revision} seleccionada para el chat de su grupo. Aún no se envió.')

    def export(self,suffix):
        if not self.save():return
        formats={'.docx':'Documento Word','.html':'HTML imprimible','.md':'Texto Markdown'}
        # File dialog handles the explicit overwrite decision; exporter defaults to exclusive creation.
        path=filedialog.asksaveasfilename(parent=self,defaultextension=suffix,filetypes=[(formats[suffix],'*'+suffix)])
        if not path:return
        try:
            if Path(path).suffix.lower()!=suffix:raise ValueError('La extensión debe ser '+suffix)
            row=self.service.get(self.gid,self.did,self.revision)
            export_document(row['title'],row['content'],path,overwrite=Path(path).exists())
        except (ValueError,OSError,ImportError) as exc:messagebox.showerror('No se exportó',str(exc),parent=self);return
        self.notice.set('Exportado: '+str(path))
        if suffix=='.html' and messagebox.askyesno('Documento imprimible','¿Abrirlo en el navegador para revisar o imprimir?',parent=self):
            webbrowser.open(Path(path).resolve().as_uri())

    def history(self):
        if self.did is None:messagebox.showinfo('Versiones','Guarda el borrador primero.',parent=self);return
        win=tk.Toplevel(self);win.title('Historial · restaurar conserva las versiones');win.geometry('760x560')
        history_did=self.did
        rows=self.service.history(self.gid,history_did)
        box=tk.Listbox(win,exportselection=False,height=7);box.pack(fill='x',padx=12,pady=8)
        for r in rows:box.insert('end',f"Versión {r['revision']} · {r['created_at']} · {r['title']}"+ (f" · restaurada desde {r['restored_from']}" if r['restored_from'] else ''))
        preview=tk.Text(win,wrap='word',state='disabled');preview.pack(fill='both',expand=True,padx=12)
        def selected():
            sel=box.curselection();return rows[sel[0]]['revision'] if sel else None
        def show(event=None):
            rev=selected()
            if rev is None:return
            r=self.service.get(self.gid,history_did,rev);preview.configure(state='normal');preview.delete('1.0','end')
            preview.insert('end',r['content']);preview.configure(state='disabled')
        def restore():
            rev=selected()
            if rev is None:return
            if history_did!=self.did:
                messagebox.showinfo('Historial anterior','Este historial pertenece a otro borrador. Abre el historial de la copia actual.',parent=win);return
            if not messagebox.askyesno('Restaurar versión',f'La versión {rev} se copiará como una versión nueva. Los cambios actuales se guardarán primero.',parent=win):return
            if not self.save():return
            try:self.service.restore(self.gid,self.did,rev,self.revision)
            except (ValueError,sqlite3.Error) as exc:messagebox.showerror('No se restauró',str(exc),parent=win);return
            self.load();win.destroy()
        box.bind('<<ListboxSelect>>',show)
        ttk.Button(win,text='Restaurar como nueva versión',command=restore).pack(pady=10)
        if rows:box.selection_set(0);show()

    def try_close(self):
        if self.dirty():
            answer=messagebox.askyesnocancel('Cambios sin guardar','¿Guardar antes de cerrar este borrador?',parent=self)
            if answer is None:return False
            if answer and not self.save():return False
        self.app.draft_editors.discard(self);self.destroy();return True


def open_drafts(app,gid):
    win=tk.Toplevel(app);win.title('Borradores del grupo');win.geometry('720x430')
    ttk.Label(win,text='Tus borradores y versiones se guardan en este equipo.').pack(anchor='w',padx=12,pady=10)
    search=tk.StringVar();ttk.Entry(win,textvariable=search).pack(fill='x',padx=12)
    box=tk.Listbox(win,exportselection=False);box.pack(fill='both',expand=True,padx=12,pady=8)
    rows=[]
    def refresh(*args):
        rows[:]=app.drafts.list(gid,search.get());box.delete(0,'end')
        for r in rows:box.insert('end',f"B{r['id']} · v{r['current_revision']} · {r['title']}")
    def edit(event=None):
        selected=box.curselection()
        if selected:DraftEditor(app,gid,rows[selected[0]]['id'])
    controls=ttk.Frame(win);controls.pack(fill='x',padx=12,pady=8)
    for title,command in [('Nuevo borrador',lambda:DraftEditor(app,gid)),('Abrir',edit),('Actualizar lista',refresh)]:
        ttk.Button(controls,text=title,command=command).pack(side='left',padx=3)
    search.trace_add('write',refresh);box.bind('<Double-Button-1>',edit);refresh()
