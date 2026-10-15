"""Conversational entry to existing reviewed workflows, without automatic execution."""
import json
import queue
import threading
import tkinter as tk
from tkinter import ttk,messagebox
from core import Store
from online import OpenAIProvider,MeteredProvider
from workflows import Workflows,TOOLS

class WorkflowWindow(tk.Toplevel):
    def __init__(self,app,gid,goal=''):
        super().__init__(app);self.app=app;self.gid=gid;self.service=Workflows(app.store);self.busy=False;self.results=queue.Queue();self.wid=None
        self.title('Organizar trabajo desde el chat');self.geometry('950x750')
        ttk.Label(self,text='Describe lo que necesitas. La ruta abre herramientas para revisar y guardar; no ejecuta ni confirma cambios por ti.',wraplength=900).pack(padx=12,pady=8)
        self.goal=tk.Text(self,height=4,wrap='word');self.goal.pack(fill='x',padx=12);self.goal.insert('1.0',goal)
        self.online=tk.BooleanVar(value=False);ttk.Checkbutton(self,text='Interpretar petición libre con OpenAI (solo se envía esta petición)',variable=self.online).pack(anchor='w',padx=12)
        ttk.Button(self,text='Preparar ruta',command=self.prepare).pack(anchor='w',padx=12,pady=5)
        catalog=self.service.catalog(gid)
        text='CATÁLOGO LOCAL (no se envía):\n'+'\n'.join(f"{kind}: {r['title']} · #{r['id']}" for kind,rows in catalog.items() for r in rows)
        text+='\nSin IA: proyecto #ID, evidencias #ID, planeación #ID o materiales #ID.'
        catalogue=tk.Text(self,height=5,wrap='word');catalogue.pack(fill='x',padx=12);catalogue.insert('1.0',text);catalogue.configure(state='disabled')
        self.history=ttk.Combobox(self,state='readonly');self.history.pack(fill='x',padx=12,pady=8);self.history.bind('<<ComboboxSelected>>',self.select)
        self.steps=tk.Listbox(self,height=5,exportselection=False);self.steps.pack(fill='x',padx=12);self.steps.bind('<<ListboxSelect>>',self.show)
        self.preview=tk.Text(self,wrap='word',state='disabled');self.preview.pack(fill='both',expand=True,padx=12,pady=8)
        ttk.Button(self,text='Abrir paso seleccionado para revisarlo',command=self.open_step).pack(pady=6)
        self.notice=tk.StringVar(value='Preparar una ruta no significa completar sus pasos.');ttk.Label(self,textvariable=self.notice,wraplength=900).pack(padx=12)
        self.refresh();self.app.draft_editors.add(self);self.protocol('WM_DELETE_WINDOW',self.try_close);self.timer=self.after(100,self.poll)
    def refresh(self,wid=None):
        self.rows=self.service.list(self.gid);self.history.configure(values=[f"#{r['id']} · {r['goal'][:100]}" for r in self.rows])
        if self.rows:self.history.current(next((i for i,r in enumerate(self.rows) if r['id']==wid),0));self.select()
    def select(self,event=None):
        if self.history.current()<0:return
        self.wid=self.rows[self.history.current()]['id'];self.plan=self.service.get(self.gid,self.wid);self.steps.delete(0,'end')
        for i,s in enumerate(self.plan['steps'],1):self.steps.insert('end',f"{i}. {TOOLS[s['tool']]} · "+(s['destination']['title'] if s['destination'] else 'Petición nueva'))
        self.steps.selection_set(0);self.show()
    def show(self,event=None):
        if not self.steps.curselection():return
        step=self.plan['steps'][self.steps.curselection()[0]]
        text=step['request']+'\n\nDestino: '+json.dumps(step['destination'],ensure_ascii=False)+'\n\nAbrir este paso no genera contenido ni guarda cambios automáticamente.'
        self.preview.configure(state='normal');self.preview.delete('1.0','end');self.preview.insert('1.0',text);self.preview.configure(state='disabled')
    def prepare(self):
        if self.busy:return
        goal=self.goal.get('1.0','end-1c');online=self.online.get()
        if not online:
            try:wid,note=self.service.prepare(self.gid,goal);self.refresh(wid);self.notice.set(note or 'Ruta local preparada.')
            except Exception as exc:messagebox.showerror('Ruta',str(exc),parent=self)
            return
        if not self.app.api_key:self.app.configure_online()
        if not self.app.api_key:return
        if not messagebox.askyesno('Interpretar con IA','Se enviará solo la petición escrita, que puede contener datos personales. No se envían el catálogo, alumnos, documentos, adjuntos ni historial. Consume API. ¿Continuar?',parent=self):return
        self.busy=True;self.notice.set('Interpretando petición…');settings=dict(self.app.settings);key=self.app.api_key;db=self.app.store.db_path;gid=self.gid
        def work():
            store=None
            try:
                store=Store(db);provider=MeteredProvider(store,OpenAIProvider(key,settings['profile'],settings['max_output_tokens']),settings['monthly_limit'])
                self.results.put((*Workflows(store).prepare(gid,goal,provider),None))
            except Exception as exc:self.results.put((None,'',str(exc)))
            finally:
                if store:store.close()
        threading.Thread(target=work,daemon=True).start()
    def poll(self):
        try:wid,note,error=self.results.get_nowait()
        except queue.Empty:pass
        else:
            self.busy=False;self.app.refresh_usage()
            if wid:self.refresh(wid)
            self.notice.set(error or note or 'Ruta preparada. Revisa cada paso antes de abrirlo.')
        self.timer=self.after(100,self.poll)
    def open_step(self):
        if self.busy or not self.steps.curselection():return
        try:step=self.service.step(self.gid,self.wid,self.steps.curselection()[0])
        except Exception as exc:messagebox.showerror('Destino',str(exc),parent=self);return
        tool=step['tool'];dest=step['destination'];request=step['request']
        if tool=='project':
            from projects_ui import ProjectEditor
            ProjectEditor(self.app,self.gid,dest['id'])
        elif tool=='evidence':
            from evidence_ui import EvidenceWindow
            EvidenceWindow(self.app,self.gid,dest['id'])
        elif tool in ('planning','lesson'):
            from templates_ui import TemplateEditor
            editor=TemplateEditor(self.app,self.gid,dest['id'])
            if tool=='lesson':
                from lesson_packs_ui import LessonWindow
                win=LessonWindow(editor);win.request_text.insert('1.0',request)
            else:
                from template_suggestions_ui import SuggestionWindow
                win=SuggestionWindow(editor);win.goal.insert('1.0',request)
        elif tool=='resources':
            from resource_workflow_ui import open_resources
            open_resources(self.app,self.gid)
        elif tool=='action':
            from natural_actions_ui import NaturalActionWindow
            NaturalActionWindow(self.app,self.gid,request)
        self.notice.set('Herramienta abierta para revisión. El paso no se marca como realizado.')
    def try_close(self):
        if self.busy:messagebox.showinfo('En curso','Espera a que termine la interpretación.',parent=self);return False
        self.after_cancel(self.timer);self.app.draft_editors.discard(self);self.destroy();return True

def open_workflow(app,gid,goal=''):
    if gid is None:messagebox.showinfo('Grupo','Selecciona un grupo para organizar su trabajo.',parent=app);return
    WorkflowWindow(app,gid,goal)
