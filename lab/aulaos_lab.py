"""AulaOS Lab v0.1: escritorio, local, sin servicios externos obligatorios."""
import datetime as dt
import os
import threading
import tkinter as tk
from tkinter import ttk,filedialog,messagebox,simpledialog
from pathlib import Path
from core import Store, STATUS, today

APP_DIR=Path(os.getenv('LOCALAPPDATA',Path.home()/'.aulaos_lab'))/'AulaOSLab'
APP_DIR.mkdir(parents=True,exist_ok=True)
DB_FILE=APP_DIR/'aulaos.sqlite3'

class AulaOS(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('AulaOS Lab · Asistente docente local (v0.1)')
        self.geometry('1150x800');self.minsize(875,600)
        self.configure(bg='#f3f6fb')
        self.store=Store(DB_FILE)
        self.gid=None;self.select_student=None
        self.group_ids={}
        self._style()
        self._build()
        self.refresh_groups()
        self.after(15000,self.check_excel)
        self.protocol('WM_DELETE_WINDOW',self.close)
    def _style(self):
        st=ttk.Style(self)
        if 'clam' in st.theme_names():st.theme_use('clam')
        st.configure('TFrame',background='#f3f6fb')
        st.configure('TLabel',background='#f3f6fb',foreground='#1b2d43',font=('Segoe UI',10))
        st.configure('Title.TLabel',font=('Segoe UI Semibold',20),foreground='#184d7f')
        st.configure('TButton',font=('Segoe UI',10),padding=7)
        st.configure('TNotebook',background='#f3f6fb')
        st.configure('Treeview',font=('Segoe UI',10),rowheight=29)
        st.configure('Treeview.Heading',font=('Segoe UI Semibold',10))
    def _build(self):
        top=ttk.Frame(self,padding=(17,14,17,8));top.pack(fill='x')
        ttk.Label(top,text='AulaOS',style='Title.TLabel').pack(side='left')
        ttk.Label(top,text='  LAB 0.1 · PRIVADO · OFFLINE',foreground='#698398').pack(side='left',padx=8)
        context=ttk.Frame(self,padding=(18,4));context.pack(fill='x')
        ttk.Label(context,text='Escuela y grupo:').pack(side='left')
        self.group_box=ttk.Combobox(context,state='readonly',width=38)
        self.group_box.pack(side='left',padx=8)
        self.group_box.bind('<<ComboboxSelected>>',lambda e:self.group_change())
        ttk.Button(context,text='+ Crear grupo',command=self.create_group).pack(side='left',padx=3)
        ttk.Button(context,text='Importar Excel / CSV',command=self.import_file).pack(side='left',padx=3)
        ttk.Label(context,text='Fecha de registro:').pack(side='left',padx=(20,5))
        self.day=tk.StringVar(value=today())
        ttk.Entry(context,textvariable=self.day,width=12).pack(side='left')
        self.tabs=ttk.Notebook(self);self.tabs.pack(fill='both',expand=True,padx=18,pady=10)
        self.tab_att=ttk.Frame(self.tabs,padding=12);self.tab_notes=ttk.Frame(self.tabs,padding=12)
        self.tab_tasks=ttk.Frame(self.tabs,padding=12);self.tab_chat=ttk.Frame(self.tabs,padding=12)
        self.tabs.add(self.tab_att,text='    Pase de lista    ');self.tabs.add(self.tab_notes,text='    Historial y observaciones    ')
        self.tabs.add(self.tab_tasks,text='    Pendientes    ');self.tabs.add(self.tab_chat,text='    Consultas locales    ')
        self._attendance();self._notes();self._tasks();self._chat()
        self.status=tk.StringVar(value='Preparado. Los datos se guardan en tu computadora.')
        ttk.Label(self,textvariable=self.status,foreground='#4c6174',padding=(18,6)).pack(anchor='w')
    def _attendance(self):
        ttk.Label(self.tab_att,text='↑ Presente     ↓ Falta     ← Justificada     → Retardo     · Al marcar avanza al siguiente estudiante',foreground='#506980').pack(anchor='w',pady=(0,10))
        frame=ttk.Frame(self.tab_att);frame.pack(fill='both',expand=True)
        self.stree=ttk.Treeview(frame,columns=('name','status'),show='headings',selectmode='browse')
        self.stree.heading('name',text='Estudiante');self.stree.heading('status',text='Registro del día')
        self.stree.column('name',width=450);self.stree.column('status',width=200)
        self.stree.pack(side='left',fill='both',expand=True)
        sb=ttk.Scrollbar(frame,orient='vertical',command=self.stree.yview);sb.pack(side='right',fill='y');self.stree.configure(yscrollcommand=sb.set)
        self.stree.bind('<<TreeviewSelect>>',lambda e:self.selected())
        for k,s in [('<Up>','A'),('<Down>','F'),('<Left>','J'),('<Right>','R')]:
            self.stree.bind(k,lambda e,v=s:self.mark_current(v))
        buttons=ttk.Frame(self.tab_att);buttons.pack(fill='x',pady=8)
        for k,label in [('A','↑ Presente'),('F','↓ Falta'),('J','← Justificada'),('R','→ Retardo')]:
            ttk.Button(buttons,text=label,command=lambda x=k:self.mark_current(x)).pack(side='left',padx=3)
        ttk.Button(buttons,text='+ Agregar alumno',command=self.manual_student).pack(side='right',padx=3)
        ttk.Button(buttons,text='Actualizar desde archivo',command=lambda:self.reimport(True)).pack(side='right',padx=3)
    def _notes(self):
        ttk.Label(self.tab_notes,text='Observaciones precisas y cronológicas. Una anotación no es una sanción automática.').pack(anchor='w',pady=5)
        box=ttk.Frame(self.tab_notes);box.pack(fill='x',pady=6)
        ttk.Label(box,text='Estudiante:').pack(side='left')
        self.student_note_box=ttk.Combobox(box,width=47,state='readonly');self.student_note_box.pack(side='left',padx=8)
        self.student_note_box.bind('<<ComboboxSelected>>',lambda e:self.load_timeline())
        ttk.Label(box,text='Tipo:').pack(side='left',padx=(10,0))
        self.event_type=ttk.Combobox(box,width=19,state='readonly',values=['Observación','Conducta','Participación','Trabajo','Comunicación','Otro'])
        self.event_type.set('Observación');self.event_type.pack(side='left',padx=4)
        ttk.Label(self.tab_notes,text='Describe qué ocurrió (hechos observables; el registro usa la fecha indicada arriba):').pack(anchor='w')
        self.event_text=tk.Text(self.tab_notes,height=4,wrap='word',font=('Segoe UI',11));self.event_text.pack(fill='x',pady=6)
        actions=ttk.Frame(self.tab_notes);actions.pack(fill='x')
        ttk.Button(actions,text='Guardar observación',command=self.save_event).pack(side='left')
        ttk.Button(actions,text='Exportar historial HTML',command=self.export_history).pack(side='left',padx=7)
        ttk.Button(actions,text='Grabar nota de voz (10 s, opcional)',command=self.record_audio).pack(side='left',padx=7)
        ttk.Label(self.tab_notes,text='Historial del estudiante seleccionado:').pack(anchor='w',pady=(14,4))
        self.timeline=tk.Text(self.tab_notes,font=('Consolas',10),wrap='word',state='disabled');self.timeline.pack(fill='both',expand=True)
    def _tasks(self):
        row=ttk.Frame(self.tab_tasks);row.pack(fill='x',pady=10)
        self.task_title=tk.StringVar();ttk.Entry(row,textvariable=self.task_title,width=70).pack(side='left',fill='x',expand=True)
        self.task_due=tk.StringVar();ttk.Entry(row,textvariable=self.task_due,width=14).pack(side='left',padx=8)
        ttk.Label(row,text='AAA-MM-DD (opcional)').pack(side='left',padx=(0,9))
        ttk.Button(row,text='Añadir',command=self.add_task).pack(side='left')
        self.task_tree=ttk.Treeview(self.tab_tasks,columns=('title','due','group','state'),show='headings')
        for col,label,width in [('title','Pendiente',480),('due','Fecha objetivo',125),('group','Grupo',190),('state','Estado',95)]:
            self.task_tree.heading(col,text=label);self.task_tree.column(col,width=width)
        self.task_tree.pack(fill='both',expand=True,pady=9)
        ttk.Button(self.tab_tasks,text='Alternar realizada / pendiente',command=self.toggle_task).pack(side='left')
        ttk.Button(self.tab_tasks,text='Crear respaldo local',command=self.backup_now).pack(side='right')
    def _chat(self):
        ttk.Label(self.tab_chat,text='Asistente de consultas local (reglas verificables; todavía NO es un modelo de IA).',foreground='#476682').pack(anchor='w',pady=6)
        self.chatlog=tk.Text(self.tab_chat,font=('Segoe UI',11),wrap='word',state='disabled')
        self.chatlog.pack(fill='both',expand=True,pady=7)
        row=ttk.Frame(self.tab_chat);row.pack(fill='x',pady=6)
        self.chat_msg=tk.StringVar();ent=ttk.Entry(row,textvariable=self.chat_msg)
        ent.pack(side='left',fill='x',expand=True,padx=(0,8));ent.bind('<Return>',lambda e:self.ask())
        ttk.Button(row,text='Consultar',command=self.ask).pack(side='left')
        self.append_chat('AulaOS','Puedes preguntar: «¿Cuántas faltas lleva [nombre]?», «Historial de [nombre]» o «Pendientes».')
    def close(self):
        try:self.store.backup()
        except Exception as exc:messagebox.showwarning('Respaldo pendiente',f'No pude crear el respaldo automático: {exc}',parent=self)
        self.store.close();self.destroy()
    def toast(self,s):self.status.set(s)
    def create_group(self):
        a=simpledialog.askstring('Nueva escuela','Nombre de la escuela:',parent=self)
        if not a:return
        b=simpledialog.askstring('Nuevo grupo','Nombre del grupo (ej. 2.º D):',parent=self)
        if not b:return
        try:
            gid=self.store.group(a,b);self.refresh_groups(gid);self.toast('Grupo guardado en la base local.')
        except Exception as e:messagebox.showerror('Error',str(e),parent=self)
    def refresh_groups(self,pick=None):
        groups=self.store.groups();self.group_ids={f"{g['school']} · {g['name']}":g['id'] for g in groups}
        self.group_box['values']=list(self.group_ids)
        wanted=pick or self.gid
        label=next((x for x,i in self.group_ids.items() if i==wanted),None)
        if label:self.group_box.set(label)
        elif groups:self.group_box.set(list(self.group_ids)[0])
        self.group_change()
    def group_change(self):
        self.gid=self.group_ids.get(self.group_box.get());self.refresh_students();self.load_tasks()
    def refresh_students(self):
        self.stree.delete(*self.stree.get_children());self.students_by_name={}
        if self.gid is None:return
        day=self.get_day(quiet=True);marks=self.store.marks(self.gid,day) if day else {}
        for r in self.store.students(self.gid):
            self.stree.insert('',tk.END,iid=str(r['id']),values=(r['name'],STATUS.get(marks.get(r['id']), '—')))
            self.students_by_name[f"{r['name']}  ·  #{r['id']}"]=r['id']
        names=list(self.students_by_name)
        self.student_note_box['values']=names
        if names and self.student_note_box.get() not in names:self.student_note_box.set(names[0])
        if self.stree.get_children():self.stree.selection_set(self.stree.get_children()[0]);self.stree.focus(self.stree.get_children()[0])
        self.load_timeline()
    def selected(self):
        ids=self.stree.selection()
        if ids:
            sid=int(ids[0]);label=next((k for k,v in self.students_by_name.items() if v==sid),None)
            if label:self.student_note_box.set(label);self.load_timeline()
    def get_day(self,quiet=False):
        try:return dt.date.fromisoformat(self.day.get().strip()).isoformat()
        except ValueError:
            if not quiet:messagebox.showwarning('Fecha','Usa AAAA-MM-DD',parent=self)
            return None
    def mark_current(self,value):
        if not self.gid or not self.get_day():return 'break'
        ids=self.stree.selection()
        if not ids:return 'break'
        sid=int(ids[0]);children=self.stree.get_children();i=children.index(ids[0]);day=self.get_day()
        self.store.mark(self.gid,sid,day,value)
        self.stree.item(ids[0],values=(self.stree.item(ids[0],'values')[0],STATUS[value]))
        if i+1<len(children):
            nxt=children[i+1];self.stree.selection_set(nxt);self.stree.focus(nxt);self.stree.see(nxt)
        self.toast(f'{STATUS[value]} registrada para {day}. Guardada localmente.');return 'break'
    def manual_student(self):
        if not self.gid:return
        name=simpledialog.askstring('Alumno','Nombre del estudiante:',parent=self)
        if name:self.store.add_student(self.gid,name);self.refresh_students()
    def import_file(self):
        if not self.gid:
            messagebox.showinfo('Grupo','Primero crea o selecciona una escuela y grupo.',parent=self);return
        p=filedialog.askopenfilename(title='Selecciona una lista',filetypes=[('Excel o CSV','*.xlsx *.xlsm *.csv'),('Todos','*.*')])
        if not p:return
        try:
            msg=self.store.import_csv(self.gid,p) if p.lower().endswith('.csv') else self.store.import_excel(self.gid,p,force=True)
            self.refresh_students();self.toast(msg);messagebox.showinfo('Importación',msg,parent=self)
            self.show_conflicts()
        except Exception as e:messagebox.showerror('No pude importar',str(e),parent=self)
    def reimport(self,force=False):
        if not self.gid:return
        row=next((g for g in self.store.groups() if g['id']==self.gid),None)
        if not row or not row['source_path']:
            if force:messagebox.showinfo('Archivo','Este grupo aún no tiene un archivo Excel vinculado.',parent=self)
            return
        try:
            msg=self.store.import_excel(self.gid,row['source_path'],force=force)
            if msg!='Sin cambios desde la última lectura.':self.refresh_students();self.toast(msg);self.show_conflicts()
            elif force:self.toast(msg)
        except Exception as e:self.toast(f'Excel pendiente: {e}')
    def check_excel(self):
        if self.winfo_exists():
            try:self.reimport(False)
            finally:self.after(15000,self.check_excel)
    def show_conflicts(self):
        if not self.gid:return
        rows=self.store.unresolved_conflicts(self.gid)
        if not rows:return
        x=rows[0]
        prompt=(f"Se detectó una discrepancia de asistencia para {x['name']} el {x['day']}.\n"
                f"En AulaOS: {STATUS[x['local_status']]}. En Excel: {STATUS[x['excel_status']]}.\n\n"
                'Sí = usar Excel · No = mantener AulaOS · Cancelar = revisar después.\n'
                f'Quedan {len(rows)} discrepancia(s).')
        answer=messagebox.askyesnocancel('Conflicto entre registros',prompt,parent=self)
        if answer is None:return
        self.store.resolve_conflict(x['id'],choose_excel=answer);self.refresh_students()
    def save_event(self):
        if not self.gid or not self.get_day():return
        sid=self.students_by_name.get(self.student_note_box.get());desc=self.event_text.get('1.0','end').strip()
        if not sid or not desc:messagebox.showwarning('Faltan datos','Selecciona estudiante y escribe los hechos.',parent=self);return
        try:
            self.store.log_event(self.gid,sid,self.get_day(),self.event_type.get(),desc)
            self.event_text.delete('1.0','end');self.load_timeline();self.toast('Observación guardada con fecha y hora.')
        except Exception as e:messagebox.showerror('Error',str(e),parent=self)
    def load_timeline(self):
        if not hasattr(self,'timeline'):return
        sid=self.students_by_name.get(self.student_note_box.get())
        txt=self.store.student_summary(sid) if sid else 'Selecciona un estudiante.'
        self.timeline.configure(state='normal');self.timeline.delete('1.0','end');self.timeline.insert('end',txt);self.timeline.configure(state='disabled')
    def export_history(self):
        sid=self.students_by_name.get(self.student_note_box.get())
        if not sid:return
        p=filedialog.asksaveasfilename(defaultextension='.html',filetypes=[('Informe HTML','*.html')],initialfile='historial_docente.html')
        if p:self.store.export_html(sid,p);self.toast('Historial exportado. Verifica los datos antes de compartirlo.')
    def record_audio(self):
        sid=self.students_by_name.get(self.student_note_box.get())
        if not sid:messagebox.showwarning('Alumno','Selecciona el alumno antes de grabar.',parent=self);return
        try:
            import sounddevice as sd
        except ImportError:
            messagebox.showinfo('Audio opcional','La grabación local necesita el complemento gratuito sounddevice. Instálalo con: python -m pip install sounddevice\n\nLa transcripción todavía no está implementada.',parent=self);return
        folder=APP_DIR/'audios';folder.mkdir(exist_ok=True)
        path=folder/f'{sid}_{dt.datetime.now().strftime("%Y%m%d_%H%M%S")}.wav'
        self.toast('Grabando audio durante 10 segundos…')
        def work():
            try:
                import wave
                sample_rate=16000
                audio=sd.rec(10*sample_rate,samplerate=sample_rate,channels=1,dtype='int16');sd.wait()
                with wave.open(str(path),'wb') as f:f.setnchannels(1);f.setsampwidth(2);f.setframerate(sample_rate);f.writeframes(audio.tobytes())
                self.after(0,lambda:self.audio_done(sid,path))
            except Exception as e:self.after(0,lambda err=str(e):messagebox.showerror('Grabación fallida',err,parent=self))
        threading.Thread(target=work,daemon=True).start()
    def audio_done(self,sid,path):
        self.store.log_event(self.gid,sid,self.get_day() or today(),'Audio por transcribir',f'Archivo local: {path.name} (requiere revisión y transcripción).')
        self.load_timeline();self.toast(f'Audio local guardado: {path.name}. Sin transcripción automática todavía.')
    def backup_now(self):
        try:
            location=self.store.backup()
            messagebox.showinfo('Respaldo creado',f'Se guardó una copia coherente de la base de AulaOS en:\n{location}',parent=self)
        except Exception as e:messagebox.showerror('Respaldo fallido',str(e),parent=self)
    def add_task(self):
        name=self.task_title.get().strip();due=self.task_due.get().strip()
        try:self.store.create_task(name,self.gid,due or None);self.task_title.set('');self.task_due.set('');self.load_tasks()
        except Exception as e:messagebox.showwarning('Pendiente',str(e),parent=self)
    def load_tasks(self):
        if not hasattr(self,'task_tree'):return
        self.task_tree.delete(*self.task_tree.get_children())
        for task in self.store.tasks():self.task_tree.insert('',tk.END,iid=str(task['id']),values=(task['title'],task['due'] or '—',task['grupo'] or 'General','Hecha' if task['done'] else 'Pendiente'))
    def toggle_task(self):
        items=self.task_tree.selection()
        if not items:return
        tid=int(items[0]);task=next((t for t in self.store.tasks() if t['id']==tid),None)
        if task:self.store.task_done(tid,not task['done']);self.load_tasks()
    def append_chat(self,who,msg):
        self.chatlog.configure(state='normal');self.chatlog.insert('end',f'{who}:\n{msg}\n\n');self.chatlog.see('end');self.chatlog.configure(state='disabled')
    def ask(self):
        question=self.chat_msg.get().strip()
        if not question:return
        self.chat_msg.set('');self.append_chat('Docente',question)
        self.append_chat('AulaOS',self.store.consult(self.gid,question))

if __name__=='__main__':AulaOS().mainloop()
