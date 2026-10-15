"""Explicit semantic review with reusable report and guarded request adoption."""
import json
import queue
import threading
import tkinter as tk
from tkinter import ttk,messagebox
from core import Store
from online import OpenAIProvider,MeteredProvider
from clarifications import Clarifications

class ClarificationWindow(tk.Toplevel):
    def __init__(self,parent):
        super().__init__(parent.app);self.parent=parent;self.app=parent.app;self.gid=parent.gid
        self.service=Clarifications(self.app.store);self.busy=False;self.queue=queue.Queue();self.row=None
        self.title('Revisar petición antes de generar');self.geometry('820x650');self.transient(parent)
        ttk.Label(self,text='Revisión opcional online: interpreta datos y señala posibles contradicciones. Puede equivocarse.\\nSolo envía tu petición y el perfil seleccionado; no envía documentos, fuentes, expedientes ni historial.'.replace('\\n','\n'),wraplength=780).pack(padx=12,pady=10)
        controls=ttk.Frame(self);controls.pack(fill='x',padx=12)
        ttk.Button(controls,text='Revisar petición actual con IA',command=self.request).pack(side='left')
        ttk.Button(controls,text='Abrir última revisión de este grupo',command=self.latest).pack(side='left',padx=6)
        self.text=tk.Text(self,wrap='word',state='disabled');self.text.pack(fill='both',expand=True,padx=12,pady=10)
        self.use=ttk.Button(self,text='Usar respuestas interpretadas en mi petición',command=self.adopt,state='disabled');self.use.pack(pady=4)
        self.notice=tk.StringVar(value='Leer una revisión guardada no consume API. Generar la planeación es un paso separado.')
        ttk.Label(self,textvariable=self.notice,wraplength=780).pack(padx=12,pady=8)
        self.app.draft_editors.add(self);self.protocol('WM_DELETE_WINDOW',self.try_close);self.poll_id=self.after(100,self.poll)
    def current(self):
        if not self.parent.winfo_exists():raise ValueError('La ventana de propuestas se cerró.')
        profile=self.parent.selected_profile()
        return self.parent.goal.get('1.0','end-1c').strip(),profile['id'] if profile else None,profile['revision'] if profile else None
    def latest(self):
        if self.busy:return
        self.row=self.service.latest(self.gid);self.show()
    def show(self):
        text='No hay una revisión guardada para este grupo.'
        if self.row:
            report=json.loads(self.row['report_json']);profile=json.loads(self.row['profile_json'])
            text='PETICIÓN REVISADA\n'+self.row['goal']+'\n\nPERFIL\n'+(json.dumps(profile,ensure_ascii=False,indent=2) if profile else 'Sin perfil')+'\n\nDATOS INTERPRETADOS (verificar)\n'
            for item in report['answers']:text+=item['label']+': '+item['value']+'\nSustento: «'+item['evidence']+'»\n\n'
            text+='DUDAS O POSIBLES CONTRADICCIONES\n'
            for item in report['issues']:text+=item['question']+'\n'+'\n'.join('«'+e+'»' for e in item['evidence'])+'\n\n'
            if not report['issues']:text+='La revisión no señaló contradicciones; esto no garantiza que no existan.\n'
            text+='\nSi hay dudas, corrige la petición original y vuelve a revisarla. No se decide por ti.'
        self.text.configure(state='normal');self.text.delete('1.0','end');self.text.insert('1.0',text);self.text.configure(state='disabled')
        self.use.configure(state='normal' if self.row and not self.busy else 'disabled')
    def request(self):
        if self.busy:return
        try:
            goal,pid,revision=self.current();profile,_=self.service.context(self.gid,goal,pid,revision)
        except Exception as exc:messagebox.showerror('Revisión',str(exc),parent=self);return
        if not self.app.api_key:self.app.configure_online()
        if not self.app.api_key:return
        if not messagebox.askyesno('Enviar a OpenAI','Se enviará tu petición actual y el perfil '+(profile['name']+' de '+profile['teacher'] if profile else '(ninguno)')+'. Esta revisión consume API, además de la generación posterior. ¿Continuar?',parent=self):return
        settings=dict(self.app.settings);key=self.app.api_key;db=self.app.store.db_path;gid=self.gid
        self.busy=True;self.show();self.notice.set('Revisando… No se modificará la petición ni el documento.')
        def work():
            store=None
            try:
                store=Store(db);provider=MeteredProvider(store,OpenAIProvider(key,settings['profile'],settings['max_output_tokens']),settings['monthly_limit'])
                rid=Clarifications(store).analyze(gid,goal,provider,pid,revision);self.queue.put((rid,None))
            except Exception as exc:self.queue.put((None,str(exc)))
            finally:
                if store:store.close()
        threading.Thread(target=work,daemon=True).start()
    def adopt(self):
        if self.busy or not self.row:return
        try:
            goal,pid,revision=self.current()
            revised=self.service.suggested_request(self.gid,self.row['id'],goal,pid,revision)
        except Exception as exc:messagebox.showerror('No se cambió la petición',str(exc),parent=self);return
        if revised==goal:messagebox.showinfo('Sin datos nuevos','No hay respuestas nuevas que añadir. Puedes volver a la petición.',parent=self);return
        if not messagebox.askyesno('Revisar antes de usar','Esta será tu petición, sin enviarla todavía:\n\n'+revised+'\n\n¿Usar estas respuestas?',parent=self):return
        self.parent.goal.delete('1.0','end');self.parent.goal.insert('1.0',revised)
        self.notice.set('Respuestas añadidas a la petición. Puedes corregirlas; aún no se generó contenido.')
    def poll(self):
        try:rid,error=self.queue.get_nowait()
        except queue.Empty:pass
        else:
            self.busy=False;self.app.refresh_usage()
            if rid:self.row=self.service.get(self.gid,rid)
            self.show();self.notice.set(error or 'Revisión guardada. Verifica interpretaciones y dudas antes de usarlas.')
        self.poll_id=self.after(100,self.poll)
    def try_close(self):
        if self.busy:messagebox.showinfo('Revisión en curso','Espera a que termine; no hay reintentos automáticos.',parent=self);return False
        self.after_cancel(self.poll_id);self.app.draft_editors.discard(self);self.destroy();return True
