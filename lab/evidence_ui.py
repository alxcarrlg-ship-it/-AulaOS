"""Explicit local review of evidence attached to one project."""
import datetime as dt
import tkinter as tk
from tkinter import ttk,messagebox,filedialog
from evidence import Evidence,STATES,describe
from document_export import export_document
from recovery_ui import RecoveryController

class EvidenceWindow(tk.Toplevel):
    def __init__(self,app,gid,pid):
        super().__init__(app);self.app=app;self.gid=gid;self.pid=pid;self.service=Evidence(app.store)
        self.title('Evidencias y seguimiento del proyecto');self.geometry('900x700')
        ttk.Label(self,text='Registros locales. Revisar una evidencia no confirma aprendizaje ni marca el proyecto como realizado.',wraplength=850).pack(padx=12,pady=8)
        self.filter=ttk.Combobox(self,state='readonly',values=['Todos']+list(STATES));self.filter.pack(fill='x',padx=12);self.filter.current(0);self.filter.bind('<<ComboboxSelected>>',self.refresh)
        self.box=tk.Listbox(self,height=7,exportselection=False);self.box.pack(fill='x',padx=12,pady=8);self.box.bind('<<ListboxSelect>>',self.show)
        bar=ttk.Frame(self);bar.pack(fill='x',padx=12)
        for label,fn in [('Nueva evidencia',lambda:self.edit(True)),('Revisar / corregir',self.edit),('Ver historial',self.history),('Exportar informe',self.export),('Actualizar',self.refresh)]:ttk.Button(bar,text=label,command=fn).pack(side='left',padx=3)
        self.body=tk.Text(self,wrap='word',state='disabled');self.body.pack(fill='both',expand=True,padx=12,pady=8);self.refresh()
    def chosen(self):return self.rows[self.box.curselection()[0]] if self.box.curselection() else None
    def refresh(self,event=None):
        self.rows=self.service.list(self.gid,self.pid,None if self.filter.get()=='Todos' else self.filter.get());self.box.delete(0,'end')
        for r in self.rows:self.box.insert('end',f"#{r['id']} · {r['content']['day']} · {r['content']['status']} · {r['content']['title']}")
        if self.rows:self.box.selection_set(0)
        self.show()
    def show(self,event=None):
        row=self.chosen();self.body.configure(state='normal');self.body.delete('1.0','end');self.body.insert('1.0',describe(row) if row else 'Sin evidencias para este filtro.');self.body.configure(state='disabled')
    def edit(self,new=False):
        row=None if new else self.chosen()
        if not new and row is None:return
        win=EvidenceEditor(self,row);self.wait_window(win)
        if self.winfo_exists():self.refresh()
    def history(self):
        row=self.chosen()
        if not row:return
        win=tk.Toplevel(self);win.title('Historial de evidencia · solo lectura');win.geometry('800x600')
        versions=self.service.history(self.gid,row['id']);box=ttk.Combobox(win,state='readonly',values=[f'v{v}' for v in versions]);box.pack(fill='x')
        body=tk.Text(win,wrap='word',state='disabled');body.pack(fill='both',expand=True)
        def show(event=None):
            saved=self.service.get(self.gid,row['id'],versions[box.current()]);body.configure(state='normal');body.delete('1.0','end');body.insert('1.0',describe(saved));body.configure(state='disabled')
        box.bind('<<ComboboxSelected>>',show);box.current(0);show()
    def export(self):
        if not messagebox.askyesno('Informe local','El informe incluye el avance del proyecto y las evidencias del filtro actual, con nombres de alumnos y texto de las fuentes seleccionadas. ¿Preparar una copia local?',parent=self):return
        path=filedialog.asksaveasfilename(parent=self,defaultextension='.docx',filetypes=[('Word','*.docx'),('Markdown','*.md'),('HTML','*.html')])
        if not path:return
        try:export_document('Evidencias y seguimiento',self.service.report(self.gid,self.pid,None if self.filter.get()=='Todos' else self.filter.get()),path)
        except Exception as exc:messagebox.showerror('No se exportó',str(exc),parent=self);return
        messagebox.showinfo('Informe guardado','Revisa la copia antes de compartirla.',parent=self)

class EvidenceEditor(tk.Toplevel):
    def __init__(self,parent,row):
        super().__init__(parent);self.owner=parent;self.app=parent.app;self.gid=parent.gid;self.service=parent.service;self.row=row
        self.project_revision=self.service.projects.get(parent.gid,parent.pid)['revision']
        self.title('Registrar / revisar evidencia');self.geometry('850x750')
        content=row['content'] if row else dict(title='',day=dt.date.today().isoformat(),observation='',next_step='',due='',status=STATES[0])
        self.vars={k:tk.StringVar(value=content[k]) for k in ('title','day','due','status')}
        for key,label in [('title','Título'),('day','Fecha de la evidencia (AAAA-MM-DD)'),('due','Fecha de seguimiento (opcional; no programa recordatorios)')]:
            ttk.Label(self,text=label).pack(anchor='w',padx=12);ttk.Entry(self,textvariable=self.vars[key]).pack(fill='x',padx=12)
        ttk.Combobox(self,textvariable=self.vars['status'],state='readonly',values=STATES).pack(fill='x',padx=12,pady=8)
        self.students=[None]+[dict(r) for r in self.app.store.students(parent.gid)]
        self.student=ttk.Combobox(self,state='readonly',values=['Grupo completo']+[f"{s['name']} (#{s['id']})" for s in self.students[1:]]);self.student.pack(fill='x',padx=12);self.student.current(0)
        self.sources=[('Sin adjunto',None)];source_labels=['Sin adjunto: registrar solo la observación docente']
        for m in self.service.materials.list(parent.gid):self.sources.append(('Material',m['id']));source_labels.append(f"Material #{m['id']}: {m['title']}")
        for e in self.service.observations(parent.gid):self.sources.append(('Observación',e['id']));source_labels.append(f"Observación #{e['id']}: {e['day']} · {e['name']} · {e['category']}")
        self.source=ttk.Combobox(self,state='readonly',values=source_labels);self.source.pack(fill='x',padx=12,pady=6);self.source.current(0)
        ttk.Button(self,text='Ver copia de la fuente',command=self.preview_source).pack(anchor='w',padx=12)
        ttk.Label(self,text='La observación vinculada determina su alumno. La fuente y el destinatario quedan fijos; si elegiste mal, retira el registro y crea otro.',wraplength=800).pack(padx=12)
        if row:
            self.student.set(row['student']['name'] if row['student'] else 'Grupo completo');self.student.configure(state='disabled')
            self.source.set(row['source']['kind']);self.source.configure(state='disabled')
        self.texts={}
        for key,label in [('observation','Qué observaste (sin suponer resultados no registrados)'),('next_step','Siguiente paso / apoyo necesario')]:
            ttk.Label(self,text=label).pack(anchor='w',padx=12);box=tk.Text(self,height=5,wrap='word');box.pack(fill='both',expand=True,padx=12);box.insert('1.0',content[key]);self.texts[key]=box
        ttk.Button(self,text='Guardar registro local',command=self.save).pack(pady=10)
        self.original=self.values();self.app.draft_editors.add(self);self.protocol('WM_DELETE_WINDOW',self.try_close)
        self.recovery=RecoveryController(self,'evidence' if row else 'evidence_new',self.recovery_values,self.recover_text,target=lambda:self.row['id'] if self.row else self.owner.pid,revision=lambda:self.row['revision'] if self.row else self.project_revision)
    def dirty(self):return self.values()!=self.original
    def recovery_values(self):
        student=self.students[self.student.current()] if not self.row else None
        kind,source_id=self.sources[self.source.current()] if not self.row else ('Sin adjunto',None)
        return dict(content=self.content(),student_id=student['id'] if student else None,kind=kind,source_id=source_id)
    def recover_text(self,payload,revision):
        if self.row:self.row['revision']=revision
        else:
            self.project_revision=revision
            index=next((i for i,s in enumerate(self.students) if (s['id'] if s else None)==payload['student_id']),None)
            source=(payload['kind'],payload['source_id'])
            if index is None or source not in self.sources:raise ValueError('Alumno o fuente ya no disponible en esta ventana; vuelve a abrirla.')
            self.student.current(index);self.source.current(self.sources.index(source))
        for k,v in self.vars.items():v.set(payload['content'][k])
        for k,v in self.texts.items():v.delete('1.0','end');v.insert('1.0',payload['content'][k])
    def preview_source(self):
        try:
            if self.row:source=self.row['source']
            else:
                kind,source_id=self.sources[self.source.current()]
                source,_=self.service.source(self.owner.gid,kind,source_id)
        except Exception as exc:messagebox.showerror('Fuente',str(exc),parent=self);return
        win=tk.Toplevel(self);win.title('Fuente de la evidencia · solo lectura');win.geometry('750x500')
        box=tk.Text(win,wrap='word');box.pack(fill='both',expand=True)
        box.insert('1.0',source['kind']+'\n'+(source.get('title') or source.get('category',''))+'\n\n'+source.get('content','Sin adjunto. Se conservará tu observación docente.'));box.configure(state='disabled')
    def content(self):return dict({k:v.get() for k,v in self.vars.items()},**{k:v.get('1.0','end-1c') for k,v in self.texts.items()})
    def values(self):return (self.content(),self.student.get(),self.source.get())
    def save(self):
        try:
            if self.row:self.service.save(self.owner.gid,self.row['id'],self.content(),self.row['revision'])
            else:
                student=self.students[self.student.current()];kind,source_id=self.sources[self.source.current()]
                self.service.create(self.owner.gid,self.owner.pid,self.project_revision,self.content(),student['id'] if student else None,kind,source_id)
        except Exception as exc:messagebox.showerror('No se guardó',str(exc),parent=self);return
        self.original=self.values();self.recovery.saved();self.try_close()
    def try_close(self):
        if self.values()!=self.original and not messagebox.askyesno('Cambios sin guardar','¿Cerrar y descartar estos cambios?',parent=self):return False
        self.recovery.stop();self.app.draft_editors.discard(self);self.destroy();return True
