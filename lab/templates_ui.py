"""Template library and field editor; local and independent of a fixed lesson format."""
import json
import sqlite3
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
from pathlib import Path
from templates import Templates
from materials import Materials

ERRORS=(ValueError,OSError,sqlite3.Error)


def open_templates(app,gid):
    service=Templates(app.store)
    win=tk.Toplevel(app);win.title('Plantillas del grupo · formatos propios');win.geometry('840x620')
    ttk.Label(win,text='Importa el Word que te pide tu escuela. AulaOS conserva una copia local del formato.',wraplength=800).pack(padx=12,pady=8)
    box=tk.Listbox(win,height=7,exportselection=False);box.pack(fill='x',padx=12)
    preview=tk.Text(win,wrap='word',height=10);preview.pack(fill='both',expand=True,padx=12,pady=8)
    rows=[]
    def chosen():return rows[box.curselection()[0]] if box.curselection() else None
    def show(event=None):
        item=chosen();summary='Importa una plantilla para reconocer su estructura.'
        if item:
            schema=json.loads(service.get(gid,item['id'])['schema_json'])
            summary=f"{item['name']} · Docente: {item['teacher'] or 'sin especificar'}\n\n"
            summary+='\n'.join(f"{t['part']}: tabla {t['table']}, {t['columns']} columnas de cuadrícula, {t['rows']} filas"+(' (celdas combinadas)' if t['merged'] else '')+'\nPrimera fila: '+' | '.join(t['first_row']) for t in schema['tables'])
            summary+=f"\n\n{len(schema['fields'])} párrafos editables · {schema['images']} imágenes · {schema['skipped']} párrafos complejos conservados sin editar.\n\n"+schema['notice']
        preview.configure(state='normal');preview.delete('1.0','end');preview.insert('1.0',summary);preview.configure(state='disabled')
    def refresh():
        rows[:]=service.list(gid);box.delete(0,'end')
        for r in rows:box.insert('end',f"{r['name']} · {r['teacher'] or 'Docente sin especificar'} · #{r['id']}")
        if rows:box.selection_set(0)
        show()
    def import_file():
        path=filedialog.askopenfilename(parent=win,filetypes=[('Plantilla Word','*.docx')])
        if not path:return
        name=simpledialog.askstring('Nombre del formato','Nombre y variante (por ejemplo: Escuela A · semanal):',initialvalue=Path(path).stem,parent=win)
        if not name:return
        teacher=simpledialog.askstring('Docente','Docente de este formato (opcional):',parent=win)
        if teacher is None:return
        try:service.import_file(gid,path,name,teacher);refresh()
        except ERRORS as exc:messagebox.showerror('No se importó',str(exc),parent=win)
    def create():
        item=chosen()
        if not item:return
        title=simpledialog.askstring('Nuevo documento','Título:',initialvalue=item['name'],parent=win)
        if not title:return
        try:did=service.create(gid,item['id'],title);TemplateEditor(app,gid,did)
        except ERRORS as exc:messagebox.showerror('Documento',str(exc),parent=win)
    def attach_structure():
        item=chosen()
        if not item:return
        template=service.get(gid,item['id']);schema=json.loads(template['schema_json'])
        content='Estructura del formato '+item['name']+'\n'+json.dumps({'tables':schema['tables'],'fields':schema['fields']},ensure_ascii=False,indent=2)
        if not messagebox.askyesno('Adjuntar estructura','Esta copia incluye el texto existente de la plantilla. Revisa que no contenga datos que no quieras compartir. Se seleccionará para tu próxima consulta; no se envía ahora. ¿Continuar?',parent=win):return
        try:
            mid=Materials(app.store).save(gid,item['name']+' · estructura',content,'Estructura de plantilla; contenido como fuente, no instrucciones. No representa una validación pedagógica.')
            Materials(app.store).context(gid,[mid]);app.attachments[gid]=[mid]
            if app.gid==gid:app.refresh_attachments()
            app.toast('Estructura seleccionada para el chat. El Word original sigue local.')
        except ERRORS as exc:messagebox.showerror('Estructura',str(exc)+' Puedes guardar un fragmento menor desde Materiales.',parent=win)
    def documents():
        dialog=tk.Toplevel(win);dialog.title('Documentos con plantilla');dialog.geometry('650x400')
        items=service.documents(gid);listing=tk.Listbox(dialog,exportselection=False);listing.pack(fill='both',expand=True,padx=10,pady=10)
        for d in items:listing.insert('end',f"{d['title']} · v{d['current_revision']} · #{d['id']}")
        def edit():
            if listing.curselection():TemplateEditor(app,gid,items[listing.curselection()[0]]['id'])
        ttk.Button(dialog,text='Abrir',command=edit).pack(pady=8)
    row=ttk.Frame(win);row.pack(fill='x',padx=12,pady=8)
    for name,fn in [('Importar Word',import_file),('Crear documento',create),('Mis documentos',documents),('Adjuntar estructura al chat',attach_structure)]:ttk.Button(row,text=name,command=fn).pack(side='left',padx=3)
    box.bind('<<ListboxSelect>>',show);refresh()


class TemplateEditor(tk.Toplevel):
    def __init__(self,app,gid,did):
        super().__init__(app);self.app=app;self.gid=gid;self.did=did;self.service=Templates(app.store)
        doc=self.service.document(gid,did);self.revision=doc['revision'];self.changes=json.loads(doc['changes']);self.saved=dict(self.changes)
        template=self.service.get(gid,doc['template_id']);self.fields=json.loads(template['schema_json'])['fields'];self.active=None
        self.title('Documento con plantilla · '+doc['title']);self.geometry('1000x730')
        ttk.Label(self,text='Selecciona el párrafo o celda que quieres cambiar. El resto del formato se conserva.',wraplength=940).pack(anchor='w',padx=12,pady=8)
        ttk.Label(self,text='El texto nuevo usa el estilo del primer tramo del párrafo. Si crece, puede cambiar la paginación.',wraplength=940).pack(anchor='w',padx=12)
        self.box=tk.Listbox(self,height=11,exportselection=False);self.box.pack(fill='x',padx=12,pady=8)
        for f in self.fields:self.box.insert('end',f['location']+' · '+(f['text'].replace('\n',' ')[:100] or '[vacío]'))
        self.label=tk.StringVar();ttk.Label(self,textvariable=self.label,wraplength=940).pack(anchor='w',padx=12)
        self.body=tk.Text(self,wrap='word',undo=True);self.body.pack(fill='both',expand=True,padx=12,pady=8)
        row=ttk.Frame(self);row.pack(fill='x',padx=12)
        for name,fn in [('Guardar versión',self.save),('Guardar copia',self.copy),('Restaurar versión',self.restore),('Texto de un borrador',self.insert_draft),('Exportar Word',self.export)]:ttk.Button(row,text=name,command=fn).pack(side='left',padx=3)
        self.notice=tk.StringVar(value=f'Versión {self.revision} · formato: {template["name"]}')
        ttk.Label(self,textvariable=self.notice,wraplength=940).pack(anchor='w',padx=12,pady=8)
        self.box.bind('<<ListboxSelect>>',self.select);self.box.selection_set(0);self.select()
        self.protocol('WM_DELETE_WINDOW',self.try_close);app.draft_editors.add(self)
    def capture(self):
        if self.active is not None:
            f=self.fields[self.active];value=self.body.get('1.0','end-1c')
            if value==f['text']:self.changes.pop(f['id'],None)
            else:self.changes[f['id']]=value
    def select(self,event=None):
        if not self.box.curselection():return
        self.capture();self.active=self.box.curselection()[0];f=self.fields[self.active]
        self.label.set(f['location']+' · '+f['id']);self.body.delete('1.0','end');self.body.insert('1.0',self.changes.get(f['id'],f['text']));self.body.edit_reset()
    def save(self):
        self.capture()
        try:self.revision=self.service.save(self.gid,self.did,self.changes,self.revision)
        except ERRORS as exc:messagebox.showerror('No se guardó',str(exc),parent=self);return False
        self.saved=dict(self.changes);self.notice.set(f'Versión {self.revision} guardada localmente.');return True
    def copy(self):
        self.capture();doc=self.service.document(self.gid,self.did)
        name=simpledialog.askstring('Guardar copia','Título:',initialvalue=doc['title']+' — copia',parent=self)
        if not name:return
        try:
            did=self.service.create(self.gid,doc['template_id'],name);self.service.save(self.gid,did,self.changes,1)
            TemplateEditor(self.app,self.gid,did)
        except ERRORS as exc:messagebox.showerror('Copia',str(exc),parent=self)
    def restore(self):
        rev=simpledialog.askinteger('Restaurar','Versión a recuperar como una versión nueva:',minvalue=1,maxvalue=self.revision,parent=self)
        if rev is None:return
        if not self.save():return
        try:
            old=self.service.document(self.gid,self.did,rev);changes=json.loads(old['changes'])
            self.revision=self.service.save(self.gid,self.did,changes,self.revision);self.changes=changes;self.saved=dict(changes)
            self.active=None;self.select();self.notice.set(f'Contenido de v{rev} recuperado; versión actual {self.revision}.')
        except ERRORS as exc:messagebox.showerror('Restauración',str(exc),parent=self)
    def insert_draft(self):
        drafts=self.app.drafts.list(self.gid)
        if not drafts:messagebox.showinfo('Borradores','Crea o guarda una respuesta como borrador primero.',parent=self);return
        win=tk.Toplevel(self);win.title('Elegir borrador');win.geometry('650x370')
        box=tk.Listbox(win,exportselection=False);box.pack(fill='both',expand=True)
        for row in drafts:box.insert('end',row['title'])
        target=self.active
        def insert():
            if not box.curselection():return
            if self.active!=target:messagebox.showinfo('Campo cambiado','Vuelve a elegir el campo de destino y abre esta opción.',parent=win);return
            row=self.app.drafts.get(self.gid,drafts[box.curselection()[0]]['id']);self.body.insert('insert',row['content']);win.destroy()
        ttk.Button(win,text='Insertar texto en el cursor (sin formato Markdown)',command=insert).pack(pady=8)
    def export(self):
        if not self.save():return
        path=filedialog.asksaveasfilename(parent=self,defaultextension='.docx',filetypes=[('Word','*.docx')])
        if not path:return
        try:self.service.export(self.gid,self.did,path,self.revision)
        except ERRORS as exc:messagebox.showerror('Exportación',str(exc)+'\nElige un nombre nuevo si ya existe.',parent=self);return
        self.notice.set('Copia exportada: '+path+' · revisa su distribución en Word antes de entregar.')
    def try_close(self):
        self.capture()
        if self.changes!=self.saved:
            answer=messagebox.askyesnocancel('Cambios sin guardar','¿Guardar antes de cerrar?',parent=self)
            if answer is None or answer and not self.save():return False
        self.app.draft_editors.discard(self);self.destroy();return True
