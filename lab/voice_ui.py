"""Record/select audio, explicitly transcribe, review, then stage text for chat."""
import queue
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
from core import Store, now
from voice import VoiceNotes, Transcriber, read_audio, record_wav
from materials import Materials

class VoiceWindow(tk.Toplevel):
    def __init__(self,app,gid):
        super().__init__(app);self.app=app;self.gid=gid;self.service=VoiceNotes(app.store)
        self.busy=False;self.recording=False;self.audio=None;self.suffix='.wav';self.results=queue.Queue();self.stop=threading.Event();self.saved_text='';self.audio_saved=True
        self.title('Voz · revisar antes de enviar');self.geometry('850x650')
        ttk.Label(self,text='Graba hasta 30 segundos o elige un audio. Transcribir usa OpenAI y consume API; no envía registros escolares.',wraplength=800).pack(padx=12,pady=10)
        row=ttk.Frame(self);row.pack(fill='x',padx=12)
        for title,fn in [('Grabar',self.record),('Detener',self.stop.set),('Elegir audio',self.choose),('Guardar audio',self.save_audio)]:ttk.Button(row,text=title,command=fn).pack(side='left',padx=3)
        self.language=tk.StringVar(value='Automático')
        ttk.Combobox(row,textvariable=self.language,values=['Automático','Español','Inglés'],state='readonly',width=13).pack(side='left',padx=8)
        ttk.Button(self,text='Transcribir con OpenAI',command=self.transcribe).pack(anchor='w',padx=12,pady=8)
        self.notice=tk.StringVar(value='Sin audio seleccionado. Las grabaciones quedan en memoria hasta guardarlas o cerrar.')
        ttk.Label(self,textvariable=self.notice,wraplength=800).pack(padx=12,pady=5)
        ttk.Label(self,text='Revisa nombres, fechas y números. Una transcripción puede contener errores.').pack(anchor='w',padx=12)
        self.body=tk.Text(self,wrap='word',undo=True);self.body.pack(fill='both',expand=True,padx=12,pady=8)
        row=ttk.Frame(self);row.pack(fill='x',padx=12,pady=10)
        for title,fn in [('Pasar texto al chat',self.stage),('Guardar texto como material',self.save_text),('Transcripciones anteriores',self.history)]:ttk.Button(row,text=title,command=fn).pack(side='left',padx=3)
        app.draft_editors.add(self);self.protocol('WM_DELETE_WINDOW',self.try_close);self.poll_id=self.after(100,self.poll)
    def text(self):return self.body.get('1.0','end-1c').strip()
    def replace_text(self,text):
        if self.text()!=self.saved_text and not messagebox.askyesno('Texto editado','Hay cambios sin guardar. ¿Reemplazarlos por esta transcripción?',parent=self):return False
        self.body.delete('1.0','end');self.body.insert('1.0',text);self.saved_text=text;return True
    def run(self,fn):
        if self.busy:return
        self.busy=True
        def worker():
            try:self.results.put((fn(),None))
            except Exception as exc:self.results.put((None,str(exc)))
        threading.Thread(target=worker,daemon=True).start()
    def can_replace_audio(self):
        return not self.audio or self.audio_saved or messagebox.askyesno('Grabación sin guardar','¿Reemplazar el audio grabado que todavía no has guardado?',parent=self)
    def record(self):
        if self.busy or not self.can_replace_audio():return
        if getattr(self.app,'microphone_busy',False):messagebox.showinfo('Micrófono','Ya hay otra grabación en curso.',parent=self);return
        self.app.microphone_busy=True;self.recording=True;self.stop.clear();self.notice.set('Grabando… Detén cuando termines (máximo 30 s). No se envía audio.')
        self.run(lambda:('audio',(record_wav(self.stop),'.wav','Grabación local')))
    def choose(self):
        if self.busy or not self.can_replace_audio():return
        path=filedialog.askopenfilename(parent=self,filetypes=[('Audio','*.wav *.mp3 *.mp4 *.mpeg *.mpga *.m4a *.webm')])
        if path:self.run(lambda:('audio',(*read_audio(path),Path(path).name)))
    def save_audio(self):
        if self.busy or not self.audio:return
        path=filedialog.asksaveasfilename(parent=self,defaultextension=self.suffix,filetypes=[('Audio','*'+self.suffix)])
        if not path:return
        try:
            if Path(path).suffix.lower()!=self.suffix:raise ValueError('Conserva la extensión '+self.suffix)
            with open(path,'xb') as out:out.write(self.audio)
            self.audio_saved=True;self.notice.set('Audio guardado en '+path)
        except (ValueError,OSError) as exc:messagebox.showerror('Audio',str(exc)+' Elige un archivo nuevo.',parent=self)
    def transcribe(self):
        if self.busy or not self.audio:return
        if not self.app.api_key:self.app.configure_online()
        if not self.app.api_key:return
        if not messagebox.askyesno('Enviar audio a OpenAI',f'Se enviará únicamente este audio ({len(self.audio)/1_000_000:.2f} MB). Cuenta como un intento del límite mensual. Su costo quedará sin estimación confirmada. ¿Transcribir?',parent=self):return
        data=self.audio;suffix=self.suffix;key=self.app.api_key;limit=self.app.settings['monthly_limit'];language={'Automático':'','Español':'es','Inglés':'en'}[self.language.get()];db=self.app.store.db_path;gid=self.gid
        self.notice.set('Transcribiendo… No se reenviará automáticamente si falla.')
        def work():
            store=Store(db)
            try:return 'note',VoiceNotes(store).transcribe(gid,data,suffix,Transcriber(key),limit,language)
            finally:store.close()
        self.run(work)
    def stage(self):
        if self.busy:return
        if self.app.gid!=self.gid:messagebox.showinfo('Grupo de origen','Selecciona en la ventana principal el grupo donde abriste esta nota antes de pasarla al chat.',parent=self);return
        text=self.text()
        if not text:return
        previous=self.app.chat_msg.get().strip();self.app.chat_msg.set(previous+'\n'+text if previous else text)
        self.notice.set('Texto añadido al cuadro del chat. Revísalo y pulsa Enviar cuando quieras; no se ha ejecutado ninguna acción.')
    def save_text(self):
        text=self.text()
        if not text:return False
        try:Materials(self.app.store).save(self.gid,'Nota de voz · '+now(),text,'Texto de transcripción revisable; puede contener errores.')
        except Exception as exc:messagebox.showerror('Texto',str(exc),parent=self);return False
        self.saved_text=text;self.notice.set('Texto guardado como material local.');return True
    def history(self):
        if self.busy:return
        win=tk.Toplevel(self);win.title('Transcripciones del grupo');win.geometry('700x420')
        rows=self.service.list(self.gid);box=tk.Listbox(win,exportselection=False);box.pack(fill='both',expand=True,padx=10,pady=10)
        for row in rows:box.insert('end',row['created_at']+' · '+row['text'][:90])
        def load():
            if self.busy:return
            if box.curselection() and self.replace_text(rows[box.curselection()[0]]['text']):win.destroy()
        ttk.Button(win,text='Abrir para revisar',command=load).pack(pady=8)
    def poll(self):
        try:result,error=self.results.get_nowait()
        except queue.Empty:pass
        else:
            self.busy=False;was_recording=self.recording
            if self.recording:self.app.microphone_busy=False;self.recording=False
            self.app.refresh_usage()
            if error:self.notice.set(error)
            elif result[0]=='audio':
                self.audio,self.suffix,name=result[1];self.audio_saved=not was_recording;self.notice.set(f'{name} · {len(self.audio)/1_000_000:.2f} MB · listo para guardar o transcribir.')
            else:
                row=self.service.get(self.gid,result[1]);self.replace_text(row['text']);self.notice.set('Transcripción original guardada localmente. Revisa el texto antes de usarlo.')
        self.poll_id=self.after(100,self.poll)
    def try_close(self):
        if self.busy:
            if self.recording:self.stop.set()
            messagebox.showinfo('Proceso en curso','Espera a que termine. Detener la grabación no envía el audio.',parent=self);return False
        if self.text()!=self.saved_text:
            answer=messagebox.askyesnocancel('Texto sin guardar','¿Guardar el texto editado como material antes de cerrar?',parent=self)
            if answer is None or answer and not self.save_text():return False
        if self.audio and not self.audio_saved and not messagebox.askyesno('Grabación sin guardar','El audio grabado solo está en memoria. ¿Cerrar y descartarlo? Las transcripciones ya guardadas se conservan.',parent=self):return False
        self.after_cancel(self.poll_id);self.audio=None;self.app.draft_editors.discard(self);self.destroy();return True
