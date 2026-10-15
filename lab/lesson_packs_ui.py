"""Generate, review and export class packs without altering the source planning."""
import copy
import json
import queue
import threading
import tkinter as tk
from tkinter import ttk,messagebox,filedialog
from core import Store
from online import OpenAIProvider,MeteredProvider
from lesson_packs import LessonPacks
from lesson_export import export_presentation
from document_export import export_document
from recovery_ui import RecoveryController

class LessonWindow(tk.Toplevel):
    def __init__(self,editor):
        super().__init__(editor.app);self.app=editor.app;self.editor=editor;self.gid=editor.gid;self.did=editor.did
        self.service=LessonPacks(self.app.store);self.busy=False;self.results=queue.Queue();self.current=None;self.active=None;self.rows=[]
        self.title('Materiales desde esta planeación');self.geometry('1050x850')
        ttk.Label(self,text='Describe la sesión, duración, idioma de alumnos y recursos. Se enviarán tu petición y el texto editable de la planeación guardada.',wraplength=1000).pack(padx=12,pady=6)
        self.request_text=tk.Text(self,height=3,wrap='word');self.request_text.pack(fill='x',padx=12)
        ttk.Button(self,text='Preparar guía, actividad y presentación con IA',command=self.generate).pack(anchor='w',padx=12,pady=5)
        self.selector=ttk.Combobox(self,state='readonly');self.selector.pack(fill='x',padx=12);self.selector.bind('<<ComboboxSelected>>',self.select_pack)
        self.title_value=tk.StringVar();ttk.Entry(self,textvariable=self.title_value).pack(fill='x',padx=12,pady=5)
        book=ttk.Notebook(self);book.pack(fill='both',expand=True,padx=12);self.texts={}
        for key,label in [('teacher_guide','Guía docente / respuestas'),('worksheet','Actividad para alumnos')]:
            pane=ttk.Frame(book);book.add(pane,text=label);body=tk.Text(pane,wrap='word');body.pack(fill='both',expand=True);self.texts[key]=body
        pane=ttk.Frame(book);book.add(pane,text='Presentación')
        self.slides=tk.Listbox(pane,height=4,exportselection=False);self.slides.pack(fill='x');self.slides.bind('<<ListboxSelect>>',self.select_slide)
        self.slide_title=tk.StringVar();ttk.Entry(pane,textvariable=self.slide_title).pack(fill='x',pady=4)
        ttk.Label(pane,text='Texto para alumnos: una línea por punto (máximo cinco)').pack(anchor='w')
        self.slide_body=tk.Text(pane,height=6,wrap='word');self.slide_body.pack(fill='both',expand=True)
        ttk.Label(pane,text='Notas del docente: se exportan como notas, no como texto visible').pack(anchor='w')
        self.slide_notes=tk.Text(pane,height=5,wrap='word');self.slide_notes.pack(fill='both',expand=True)
        controls=ttk.Frame(self);controls.pack(fill='x',padx=12,pady=8)
        for label,fn in [('Guardar revisión',self.save),('Exportar guía Word',lambda:self.export('teacher_guide')),('Exportar actividad Word',lambda:self.export('worksheet')),('Exportar PowerPoint',lambda:self.export('slides'))]:ttk.Button(controls,text=label,command=fn).pack(side='left',padx=4)
        self.notice=tk.StringVar(value='Revisa coherencia, respuestas y presentación antes de usar. Los cambios requieren guardar.')
        ttk.Label(self,textvariable=self.notice,wraplength=1000).pack(padx=12,pady=6)
        self.refresh();self.app.draft_editors.add(self);self.protocol('WM_DELETE_WINDOW',self.try_close);self.poll_id=self.after(100,self.poll)
        self.recovery=RecoveryController(self,'lesson',self.values,self.recover_text,target=lambda:self.current['id'] if self.current else None,revision=lambda:self.current['revision'] if self.current else None)
    def capture_slide(self):
        if self.current and self.active is not None:self.data['slides'][self.active]=dict(title=self.slide_title.get(),body=self.slide_body.get('1.0','end-1c').splitlines(),notes=self.slide_notes.get('1.0','end-1c'))
    def values(self):
        self.capture_slide()
        if not self.current:return None
        self.data.update(title=self.title_value.get(),**{k:v.get('1.0','end-1c') for k,v in self.texts.items()});return self.data
    def dirty(self):return bool(self.current and self.values()!=self.saved)
    def refresh(self,pid=None):
        self.rows=self.service.list(self.gid,self.did);self.selector.configure(values=[f"Paquete #{r['id']} · planeación v{r['source_revision']} · paquete v{r['current_revision']}" for r in self.rows])
        if self.rows:self.selector.current(next((i for i,r in enumerate(self.rows) if r['id']==pid),0));self.load(self.rows[self.selector.current()]['id'])
    def select_pack(self,event=None):
        if self.dirty() and not messagebox.askyesno('Cambios sin guardar','¿Descartar cambios y abrir el otro paquete?',parent=self):
            self.selector.current(next(i for i,r in enumerate(self.rows) if r['id']==self.current['id']));return
        self.load(self.rows[self.selector.current()]['id'])
    def recover_text(self,payload,revision):
        self.data=copy.deepcopy(payload);self.current['revision']=revision;self.display_data()
    def load(self,pid):
        if hasattr(self,'recovery'):self.recovery.discard()
        self.current=self.service.get(self.gid,pid);self.data=copy.deepcopy(self.current['data']);self.saved=copy.deepcopy(self.data);self.display_data()
    def display_data(self):
        self.active=None
        self.title_value.set(self.data['title'])
        for k,v in self.texts.items():v.delete('1.0','end');v.insert('1.0',self.data[k])
        self.slides.delete(0,'end')
        for i,s in enumerate(self.data['slides'],1):self.slides.insert('end',f"{i}. {s['title']}")
        self.slides.selection_set(0);self.select_slide()
        self.notice.set(f"Origen: planeación #{self.did} v{self.current['source_revision']}. Revisión del paquete {self.current['revision']}.")
    def select_slide(self,event=None):
        self.capture_slide()
        if not self.slides.curselection():return
        self.active=self.slides.curselection()[0];s=self.data['slides'][self.active];self.slide_title.set(s['title'])
        for box,text in [(self.slide_body,'\n'.join(s['body'])),(self.slide_notes,s['notes'])]:box.delete('1.0','end');box.insert('1.0',text)
    def save(self):
        if self.busy or not self.current:return False
        try:revision=self.service.save(self.gid,self.current['id'],self.values(),self.current['revision'])
        except Exception as exc:messagebox.showerror('No se guardó',str(exc),parent=self);return False
        self.current['revision']=revision;self.saved=copy.deepcopy(self.data);self.notice.set(f'Revisión {revision} guardada.');self.recovery.saved();return True
    def export(self,kind):
        if not self.save():return
        suffix='.pptx' if kind=='slides' else '.docx'
        path=filedialog.asksaveasfilename(parent=self,defaultextension=suffix,filetypes=[('PowerPoint' if kind=='slides' else 'Word','*'+suffix)])
        if not path:return
        provenance=f"AulaOS: planeación #{self.did} v{self.current['source_revision']}; paquete #{self.current['id']} v{self.current['revision']}."
        try:
            if kind=='slides':export_presentation(self.data,provenance,path)
            else:export_document(self.data['title'],self.data[kind],path)
        except Exception as exc:messagebox.showerror('No se exportó',str(exc),parent=self);return
        self.notice.set('Copia exportada. Revisa su distribución antes de usarla en clase.')
    def generate(self):
        if self.busy:return
        if self.dirty() and not self.save():return
        if not self.editor.winfo_exists():messagebox.showinfo('Planeación','Abre de nuevo la planeación antes de generar.',parent=self);return
        if not self.editor.save():return
        request=self.request_text.get('1.0','end-1c').strip();revision=self.editor.revision
        try:self.service.context(self.gid,self.did,revision,request)
        except Exception as exc:messagebox.showerror('Materiales',str(exc),parent=self);return
        if not self.app.api_key:self.app.configure_online()
        if not self.app.api_key:return
        if not messagebox.askyesno('Enviar a OpenAI','Se enviarán la petición y los textos editables de esta versión de la planeación. Pueden contener datos personales. No se envían archivos, imágenes, expedientes ni historial. Consume API. ¿Continuar?',parent=self):return
        settings=dict(self.app.settings);key=self.app.api_key;db=self.app.store.db_path;gid=self.gid;did=self.did
        self.busy=True;self.notice.set('Preparando materiales… La planeación no se modificará.')
        def work():
            store=None
            try:
                store=Store(db);provider=MeteredProvider(store,OpenAIProvider(key,settings['profile'],settings['max_output_tokens']),settings['monthly_limit'])
                pid=LessonPacks(store).generate(gid,did,revision,request,provider);self.results.put((pid,None))
            except Exception as exc:self.results.put((None,str(exc)))
            finally:
                if store:store.close()
        threading.Thread(target=work,daemon=True).start()
    def poll(self):
        try:pid,error=self.results.get_nowait()
        except queue.Empty:pass
        else:
            self.busy=False;self.app.refresh_usage()
            # Edits made while the request ran must not be silently overwritten.
            if pid and not self.dirty():self.refresh(pid)
            elif pid:messagebox.showinfo('Paquete guardado','El nuevo paquete quedó guardado. Reabre esta ventana tras guardar tus cambios para consultarlo.',parent=self)
            if error:self.notice.set(error)
        self.poll_id=self.after(100,self.poll)
    def try_close(self):
        if self.busy:messagebox.showinfo('Solicitud en curso','Espera a que termine; no hay reintentos automáticos.',parent=self);return False
        if self.dirty() and not messagebox.askyesno('Cambios sin guardar','¿Cerrar y descartar estos cambios?',parent=self):return False
        self.recovery.stop();self.after_cancel(self.poll_id);self.app.draft_editors.discard(self);self.destroy();return True
