"""Group-scoped, manual progress with immutable history and explicit document links."""
import tkinter as tk
from tkinter import ttk,messagebox
from projects import Projects,FIELDS,LABELS,describe

class ProjectEditor(tk.Toplevel):
    def __init__(self,app,gid,pid=None):
        super().__init__(app);self.app=app;self.gid=gid;self.pid=pid;self.result=None;self.service=Projects(app.store)
        row=self.service.get(gid,pid) if pid is not None else dict(revision=0,documents=[],**{k:'' for k in FIELDS})
        self.revision=row['revision'];self.references=list(row['documents']);self.original={k:row[k] for k in (*FIELDS,'documents')}
        self.title('Proyecto y avance del grupo');self.geometry('860x680')
        ttk.Label(self,text='Registra solo lo que sabes. Guardar una planeación no significa haberla realizado. Los campos vacíos quedan sin registrar.',wraplength=820).pack(padx=12,pady=8)
        self.title_value=tk.StringVar(value=row['title']);ttk.Label(self,text='Nombre del proyecto').pack(anchor='w',padx=12)
        ttk.Entry(self,textvariable=self.title_value).pack(fill='x',padx=12)
        notebook=ttk.Notebook(self);notebook.pack(fill='both',expand=True,padx=12,pady=8);self.inputs={}
        for key in FIELDS[1:]:
            pane=ttk.Frame(notebook);notebook.add(pane,text=LABELS[key].split(' (')[0])
            ttk.Label(pane,text=LABELS[key]).pack(anchor='w')
            body=tk.Text(pane,wrap='word');body.pack(fill='both',expand=True);body.insert('1.0',row[key]);self.inputs[key]=body
        ttk.Label(self,text='Vincular planeación guardada (referencia a una versión; no registra una clase realizada)').pack(anchor='w',padx=12)
        bar=ttk.Frame(self);bar.pack(fill='x',padx=12)
        self.docs=self.service.templates.documents(gid)
        self.doc_box=ttk.Combobox(bar,state='readonly',width=65,values=[d['title']+' · #'+str(d['id'])+' v'+str(d['current_revision']) for d in self.docs]);self.doc_box.pack(side='left')
        ttk.Button(bar,text='Vincular',command=self.link).pack(side='left',padx=6)
        self.links=tk.Listbox(self,height=3,exportselection=False);self.links.pack(fill='x',padx=12,pady=4);self.refresh_links()
        controls=ttk.Frame(self);controls.pack(fill='x',padx=12,pady=8)
        ttk.Button(controls,text='Quitar vínculo seleccionado',command=self.unlink).pack(side='left')
        ttk.Button(controls,text='Ver historial',command=self.history).pack(side='left',padx=8)
        ttk.Button(controls,text='Guardar avance',command=self.save).pack(side='right')
        self.app.draft_editors.add(self);self.protocol('WM_DELETE_WINDOW',self.try_close)
    def values(self):return dict(title=self.title_value.get(),documents=list(self.references),**{k:v.get('1.0','end-1c') for k,v in self.inputs.items()})
    def refresh_links(self):
        self.links.delete(0,'end')
        for d in self.references:self.links.insert('end',d['title']+' · #'+str(d['id'])+' v'+str(d['revision']))
    def link(self):
        index=self.doc_box.current()
        if index<0:return
        d=self.docs[index];ref=dict(id=d['id'],revision=d['current_revision'],title=d['title'])
        if any(r['id']==ref['id'] and r['revision']==ref['revision'] for r in self.references):return
        if len(self.references)>=20:messagebox.showinfo('Límite','Máximo 20 referencias por proyecto.',parent=self);return
        self.references.append(ref);self.refresh_links()
    def unlink(self):
        if self.links.curselection():self.references.pop(self.links.curselection()[0]);self.refresh_links()
    def history(self):
        if self.pid is None:messagebox.showinfo('Historial','Guarda primero el proyecto.',parent=self);return
        HistoryWindow(self,self.service,self.gid,self.pid)
    def save(self):
        try:self.pid,self.revision=self.service.save(self.gid,self.values(),self.pid,self.revision)
        except Exception as exc:messagebox.showerror('No se guardó',str(exc),parent=self);return
        self.result=self.pid;self.original=self.values();self.try_close()
    def try_close(self):
        if self.values()!=self.original and not messagebox.askyesno('Cambios sin guardar','¿Cerrar y descartar los cambios de esta ventana? El avance ya guardado se conserva.',parent=self):return False
        self.app.draft_editors.discard(self);self.destroy();return True

class HistoryWindow(tk.Toplevel):
    def __init__(self,parent,service,gid,pid):
        super().__init__(parent);self.service=service;self.gid=gid;self.pid=pid
        self.title('Historial de avance · solo lectura');self.geometry('760x600')
        self.rows=service.history(gid,pid)
        self.box=ttk.Combobox(self,state='readonly',values=['v'+str(r['revision'])+' · '+r['created_at'] for r in self.rows]);self.box.pack(fill='x',padx=12,pady=8)
        self.body=tk.Text(self,wrap='word',state='disabled');self.body.pack(fill='both',expand=True,padx=12,pady=8)
        self.box.bind('<<ComboboxSelected>>',self.show);self.box.current(0);self.show()
    def show(self,event=None):
        row=self.service.get(self.gid,self.pid,self.rows[self.box.current()]['revision'])
        self.body.configure(state='normal');self.body.delete('1.0','end');self.body.insert('1.0',describe(row));self.body.configure(state='disabled')

class ProjectsWindow(tk.Toplevel):
    def __init__(self,app,gid):
        super().__init__(app);self.app=app;self.gid=gid;self.service=Projects(app.store)
        self.title('Proyectos de este grupo');self.geometry('780x600')
        self.box=tk.Listbox(self,height=7,exportselection=False);self.box.pack(fill='x',padx=12,pady=8)
        controls=ttk.Frame(self);controls.pack(fill='x',padx=12)
        ttk.Button(controls,text='Nuevo proyecto',command=lambda:self.edit(True)).pack(side='left')
        ttk.Button(controls,text='Registrar avance / editar',command=self.edit).pack(side='left',padx=8)
        ttk.Button(controls,text='Actualizar',command=self.refresh).pack(side='left')
        self.body=tk.Text(self,wrap='word',state='disabled');self.body.pack(fill='both',expand=True,padx=12,pady=8)
        self.box.bind('<<ListboxSelect>>',self.show);self.refresh()
    def refresh(self):
        self.rows=self.service.list(self.gid);self.box.delete(0,'end')
        for r in self.rows:self.box.insert('end',r['title']+' · #'+str(r['id'])+' v'+str(r['revision']))
        if self.rows:self.box.selection_set(0)
        self.show()
    def show(self,event=None):
        row=self.rows[self.box.curselection()[0]] if self.box.curselection() else None
        self.body.configure(state='normal');self.body.delete('1.0','end');self.body.insert('1.0',describe(row));self.body.configure(state='disabled')
    def edit(self,new=False):
        if not new and not self.box.curselection():return
        pid=None if new else self.rows[self.box.curselection()[0]]['id']
        dialog=ProjectEditor(self.app,self.gid,pid);self.wait_window(dialog)
        if self.winfo_exists():self.refresh()


def open_projects(app,gid):
    if gid is None:messagebox.showinfo('Grupo','Selecciona un grupo primero.',parent=app);return
    ProjectsWindow(app,gid)
