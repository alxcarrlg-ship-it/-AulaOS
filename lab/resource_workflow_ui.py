"""Reviewable web resources and adaptations, using existing online accounting."""
import queue
import threading
import json
import tkinter as tk
from tkinter import ttk,messagebox
from core import Store
from online import OpenAIProvider,MeteredProvider
from research import domains
from resource_workflow import ResourceWorkflow

class ResourceWindow(tk.Toplevel):
    def __init__(self,app,gid):
        super().__init__(app);self.app=app;self.gid=gid;self.service=ResourceWorkflow(app.store);self.busy=False;self.results=queue.Queue();self.rows=[];self.sources=[]
        self.title('Recursos para este grupo');self.geometry('1000x820')
        ttk.Label(self,text='Describe tema, objetivo, nivel, minutos y recursos disponibles. Solo se envía lo que escribas aquí; no se envían registros del grupo.',wraplength=940).pack(padx=12,pady=8)
        self.brief=tk.Text(self,height=4,wrap='word');self.brief.pack(fill='x',padx=12)
        bar=ttk.Frame(self);bar.pack(fill='x',padx=12,pady=6)
        ttk.Label(bar,text='Dominios opcionales para buscar:').pack(side='left');self.domain=tk.StringVar();ttk.Entry(bar,textvariable=self.domain,width=35).pack(side='left',padx=6)
        ttk.Button(bar,text='Buscar y comparar recursos',command=lambda:self.run('search')).pack(side='left')
        self.box=tk.Listbox(self,height=4,exportselection=False);self.box.pack(fill='x',padx=12)
        pane=ttk.Frame(self);pane.pack(fill='both',expand=True,padx=12,pady=6)
        self.body=tk.Text(pane,wrap='word',state='disabled');scroll=ttk.Scrollbar(pane,command=self.body.yview);self.body.configure(yscrollcommand=scroll.set)
        scroll.pack(side='right',fill='y');self.body.pack(side='left',fill='both',expand=True)
        ttk.Label(self,text='Fuentes citadas para adaptar (selecciona de una a tres; Ctrl permite selección múltiple)').pack(anchor='w',padx=12)
        self.source_box=tk.Listbox(self,height=3,selectmode='extended',exportselection=False);self.source_box.pack(fill='x',padx=12)
        controls=ttk.Frame(self);controls.pack(fill='x',padx=12,pady=8)
        ttk.Button(controls,text='Preparar adaptación con fuentes elegidas',command=lambda:self.run('adaptation')).pack(side='left')
        ttk.Button(controls,text='Guardar resultado como material',command=self.material).pack(side='left',padx=8)
        self.notice=tk.StringVar(value='Leer resultados guardados no consume API. Las adaptaciones se revisan antes de llevarlas a clase.')
        ttk.Label(self,textvariable=self.notice,wraplength=940).pack(padx=12,pady=8)
        self.box.bind('<<ListboxSelect>>',self.show);self.refresh();self.app.draft_editors.add(self);self.protocol('WM_DELETE_WINDOW',self.try_close);self.poll_id=self.after(100,self.poll)
    def selected(self):return self.rows[self.box.curselection()[0]] if self.box.curselection() else None
    def refresh(self,rid=None):
        self.rows=self.service.list(self.gid);self.box.delete(0,'end')
        for r in self.rows:self.box.insert('end',f"#{r['id']} · "+('Búsqueda' if r['kind']=='search' else 'Adaptación')+' · '+r['brief'].replace('\n',' ')[:75])
        if self.rows:self.box.selection_set(next((i for i,r in enumerate(self.rows) if r['id']==rid),0))
        self.show()
    def show(self,event=None):
        selected=self.selected();self.source_box.delete(0,'end');self.sources=[]
        text='Las investigaciones y adaptaciones quedarán guardadas en este grupo.'
        if selected:
            row=self.service.get(self.gid,selected['id']);text='PETICIÓN ORIGINAL\n'+row['brief']+'\n\n'+row['content']
            if row['kind']=='search' and row['evidence']=='sourced':self.sources=[s for s in json.loads(row['sources_json']) if s['kind']=='cited']
            for s in self.sources:self.source_box.insert('end',s['id']+' · '+s['title']+' · '+s['url'])
        self.body.configure(state='normal');self.body.delete('1.0','end');self.body.insert('1.0',text);self.body.configure(state='disabled')
    def run(self,kind):
        if self.busy:return
        try:
            brief=self.service.brief(self.brief.get('1.0','end-1c'));allowed=domains(self.domain.get()) if kind=='search' else []
            selected=self.selected();rid=selected['id'] if selected else None
            ids=[self.sources[i]['id'] for i in self.source_box.curselection()]
            if kind=='adaptation':
                if rid is None:raise ValueError('Selecciona una investigación y sus fuentes.')
                self.service.adaptation_context(self.gid,rid,ids,brief)
        except Exception as exc:messagebox.showerror('Recursos',str(exc),parent=self);return
        if not self.app.api_key:self.app.configure_online()
        if not self.app.api_key:return
        notice='Se enviará tu petición para buscar recursos en internet.' if kind=='search' else 'Se enviarán tu petición, el resumen de la investigación y las fuentes seleccionadas. No se descargarán páginas ni se hará una búsqueda nueva.'
        if not messagebox.askyesno('Consulta online',notice+' No se envían expedientes ni historial del chat. Consume API. ¿Continuar?',parent=self):return
        settings=dict(self.app.settings);key=self.app.api_key;db=self.app.store.db_path;gid=self.gid
        self.busy=True;self.notice.set('Buscando recursos…' if kind=='search' else 'Preparando adaptación…')
        def work():
            store=None
            try:
                store=Store(db);provider=MeteredProvider(store,OpenAIProvider(key,settings['profile'],settings['max_output_tokens'],research=kind=='search',allowed_domains=allowed),settings['monthly_limit'])
                service=ResourceWorkflow(store)
                result=service.search(gid,brief,provider) if kind=='search' else service.adapt(gid,rid,ids,brief,provider)
                self.results.put((result,None))
            except Exception as exc:self.results.put((None,str(exc)))
            finally:
                if store:store.close()
        threading.Thread(target=work,daemon=True).start()
    def material(self):
        if self.busy or not self.selected():return
        try:mid=self.service.to_material(self.gid,self.selected()['id'])
        except Exception as exc:messagebox.showerror('Material',str(exc),parent=self);return
        self.notice.set(f'Material #{mid} guardado. Puedes seleccionarlo en Materiales para el chat o una planeación. No se adjuntó automáticamente.')
    def poll(self):
        try:rid,error=self.results.get_nowait()
        except queue.Empty:pass
        else:
            self.busy=False;self.app.refresh_usage()
            if rid:self.refresh(rid)
            self.notice.set(error or 'Resultado guardado. Revisa fuentes, adecuación y supuestos antes de utilizarlo.')
        self.poll_id=self.after(100,self.poll)
    def try_close(self):
        if self.busy:messagebox.showinfo('Consulta en curso','Espera a que termine; no habrá reintentos automáticos.',parent=self);return False
        self.after_cancel(self.poll_id);self.app.draft_editors.discard(self);self.destroy();return True


def open_resources(app,gid):
    if gid is None:messagebox.showinfo('Grupo','Selecciona un grupo primero.',parent=app);return
    ResourceWindow(app,gid)
