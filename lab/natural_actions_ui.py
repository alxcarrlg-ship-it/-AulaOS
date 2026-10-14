"""Explicit online interpretation initiated from the chat composer."""
import queue
import threading
import tkinter as tk
from tkinter import ttk,messagebox
from core import Store
from natural_actions import NaturalActions
from online import OpenAIProvider,MeteredProvider
from actions_ui import open_actions

class NaturalActionWindow(tk.Toplevel):
    def __init__(self,app,gid,text=''):
        super().__init__(app);self.app=app;self.gid=gid;self.busy=False;self.results=queue.Queue()
        scope=app.chat_service.actions.scope(gid);self.title('Preparar acción · '+scope);self.geometry('780x490')
        ttk.Label(self,text='Pide una tarea, observación o borrador con tus palabras. Destino: '+scope,wraplength=730).pack(padx=12,pady=10)
        self.body=tk.Text(self,height=7,wrap='word');self.body.pack(fill='both',expand=True,padx=12);self.body.insert('1.0',text)
        ttk.Label(self,text='Se enviará únicamente esta petición y la fecha local a OpenAI. No se envían listas de alumnos, adjuntos ni historial. La interpretación consume API.',wraplength=730).pack(padx=12,pady=10)
        ttk.Button(self,text='Interpretar con OpenAI y preparar propuesta',command=self.request).pack(pady=8)
        self.notice=tk.StringVar(value='Todavía no se ha enviado nada. La acción deberá confirmarse después en Acciones.')
        ttk.Label(self,textvariable=self.notice,wraplength=730).pack(padx=12,pady=10)
        self.app.draft_editors.add(self);self.protocol('WM_DELETE_WINDOW',self.try_close);self.poll_id=self.after(100,self.poll)
    def request(self):
        if self.busy:return
        goal=self.body.get('1.0','end-1c').strip()
        if not goal or len(goal)>6000:self.notice.set('Escribe una petición de hasta 6000 caracteres.');return
        if not self.app.api_key:self.app.configure_online()
        if not self.app.api_key:return
        key=self.app.api_key;settings=dict(self.app.settings);db=self.app.store.db_path;gid=self.gid
        self.busy=True;self.notice.set('Interpretando… No se guardarán registros hasta revisar y confirmar la propuesta.')
        def work():
            store=None
            try:
                store=Store(db);provider=MeteredProvider(store,OpenAIProvider(key,settings['profile'],settings['max_output_tokens']),settings['monthly_limit'])
                result=NaturalActions(store).propose(gid,goal,provider);self.results.put((result,None))
            except Exception as exc:self.results.put((None,str(exc)))
            finally:
                if store:store.close()
        threading.Thread(target=work,daemon=True).start()
    def poll(self):
        try:result,error=self.results.get_nowait()
        except queue.Empty:pass
        else:
            self.busy=False;self.app.refresh_usage()
            if error:self.notice.set(error)
            elif result['action_id'] is None:self.notice.set(result['clarification'])
            else:
                self.notice.set(f"Propuesta #{result['action_id']} guardada para revisión. Todavía no aplicada.");open_actions(self.app,self.gid)
        self.poll_id=self.after(100,self.poll)
    def try_close(self):
        if self.busy:messagebox.showinfo('Solicitud en curso','Espera a que termine la interpretación.',parent=self);return False
        self.after_cancel(self.poll_id);self.app.draft_editors.discard(self);self.destroy();return True
