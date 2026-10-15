"""AulaOS internal 0.15-dev: local records/materials and optional OpenAI chat."""
import datetime as dt
import os
import threading
import queue
import json
import re
import webbrowser
from research import domains, safe_url
from chat import ChatService
from actions import command
from actions_ui import open_actions
from templates_ui import open_templates
from folders_ui import FolderWindow
from folders import is_search
from voice_ui import VoiceWindow
from projects_ui import open_projects
from resource_workflow_ui import open_resources
from natural_actions_ui import NaturalActionWindow
from drafts import Drafts
from drafts_ui import DraftEditor, open_drafts
from online import OpenAIProvider, MeteredProvider, UsageLedger, OnlineError, PROFILES
from settings import Settings, CredentialVault
import tkinter as tk
from tkinter import ttk,filedialog,messagebox,simpledialog
from pathlib import Path
from core import Store, STATUS, today

APP_DIR=Path(os.getenv('AULAOS_DATA_DIR') or (Path(os.getenv('LOCALAPPDATA',Path.home()/'.aulaos_lab'))/'AulaOSLab'))
APP_DIR.mkdir(parents=True,exist_ok=True)
DB_FILE=APP_DIR/'aulaos.sqlite3'

class AulaOS(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('AulaOS · Desarrollo interno 0.15-dev')
        self.geometry('1150x800');self.minsize(875,600)
        self.configure(bg='#f3f6fb')
        self.store=Store(DB_FILE)
        self.chat_service=ChatService(self.store)
        self.chat_service.recover_interrupted()
        self.drafts=Drafts(self.store);self.draft_editors=set()
        self.settings_store=Settings(APP_DIR);self.settings=self.settings_store.load()
        self.vault=CredentialVault(APP_DIR);self.api_key='';self.credential_notice=''
        try:self.api_key=self.vault.load()
        except OSError:self.credential_notice='No se pudo recuperar la clave guardada. Puedes volver a conectarla.'
        except RuntimeError:self.credential_notice='La clave guardada requiere Windows. Modo básico disponible.'
        if not self.api_key:self.settings['mode']='Básico sin conexión'
        self.usage=UsageLedger(self.store)
        self.chat_busy=False;self.chat_results=queue.Queue();self.microphone_busy=False
        self.attachments={}
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
        ttk.Label(top,text='  DESARROLLO 0.15-dev · DATOS LOCALES',foreground='#698398').pack(side='left',padx=8)
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
        self.tabs.add(self.tab_tasks,text='    Pendientes    ');self.tabs.add(self.tab_chat,text='    Asistente    ')
        self._attendance();self._notes();self._tasks();self._chat()
        self.tabs.select(self.tab_chat)
        self.after(100,self.poll_chat)
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
        ttk.Button(actions,text='Voz: grabar / transcribir',command=self.record_audio).pack(side='left',padx=7)
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
        ttk.Label(self.tab_chat,text='Tus conversaciones quedan guardadas por escuela y grupo.',foreground='#476682').pack(anchor='w',pady=6)
        config=ttk.Frame(self.tab_chat);config.pack(fill='x')
        self.chat_mode=tk.StringVar(value=self.settings['mode'])
        self.mode_box=ttk.Combobox(config,textvariable=self.chat_mode,state='readonly',width=24,values=['Básico sin conexión','OpenAI online'])
        self.mode_box.pack(side='left');self.mode_box.bind('<<ComboboxSelected>>',lambda e:self.mode_changed())
        ttk.Button(config,text='Conexión y consumo',command=self.configure_online).pack(side='left',padx=8)
        self.mode_hint=tk.StringVar();ttk.Label(self.tab_chat,textvariable=self.mode_hint,wraplength=950).pack(anchor='w',pady=5)
        web_row=ttk.Frame(self.tab_chat);web_row.pack(fill='x',pady=4)
        self.research_mode=tk.BooleanVar(value=False)
        ttk.Checkbutton(web_row,text='Investigar en internet (esta consulta)',variable=self.research_mode,command=self.refresh_mode_hint).pack(side='left')
        ttk.Label(web_row,text='Dominios opcionales:').pack(side='left',padx=5)
        self.research_domains=tk.StringVar();ttk.Entry(web_row,textvariable=self.research_domains,width=32).pack(side='left')
        self.usage_text=tk.StringVar();ttk.Label(self.tab_chat,textvariable=self.usage_text,foreground='#506980').pack(anchor='w')
        local_bar=ttk.Frame(self.tab_chat);local_bar.pack(fill='x',pady=4)
        ttk.Button(local_bar,text='Recursos web',command=lambda:open_resources(self,self.gid)).pack(side='left',padx=5)
        ttk.Button(local_bar,text='Carpetas / buscar archivos',command=lambda:FolderWindow(self,self.gid)).pack(side='left')
        ttk.Button(local_bar,text='Voz / dictado',command=self.record_audio).pack(side='left',padx=5)
        ttk.Button(local_bar,text='Preparar acción con IA',command=lambda:NaturalActionWindow(self,self.gid,self.chat_msg.get())).pack(side='left',padx=5)
        material_bar=ttk.Frame(self.tab_chat);material_bar.pack(fill='x',pady=5)
        ttk.Button(material_bar,text='Materiales / adjuntar',command=self.open_materials).pack(side='left')
        ttk.Button(material_bar,text='Guardar respuesta',command=self.save_response).pack(side='left',padx=5)
        ttk.Button(material_bar,text='Proyectos',command=lambda:open_projects(self,self.gid)).pack(side='left',padx=5)
        ttk.Button(material_bar,text='Plantillas',command=lambda:open_templates(self,self.gid)).pack(side='left',padx=5)
        ttk.Button(material_bar,text='Acciones',command=lambda:open_actions(self,self.gid)).pack(side='left',padx=5)
        ttk.Button(material_bar,text='Borradores',command=lambda:open_drafts(self,self.gid)).pack(side='left',padx=5)
        ttk.Button(material_bar,text='Quitar adjuntos',command=self.clear_attachments).pack(side='left')
        self.attachment_text=tk.StringVar(value='Sin adjuntos para la próxima consulta')
        ttk.Label(self.tab_chat,textvariable=self.attachment_text,wraplength=950).pack(anchor='w')
        self.chatlog=tk.Text(self.tab_chat,font=('Segoe UI',11),wrap='word',state='disabled')
        self.chatlog.pack(fill='both',expand=True,pady=7)
        ttk.Label(self.tab_chat,text='Sin internet: /acciones muestra formatos; /buscar nombre busca archivos en tus carpetas.',foreground='#476682').pack(anchor='w')
        row=ttk.Frame(self.tab_chat);row.pack(fill='x',pady=6)
        self.chat_msg=tk.StringVar();ent=ttk.Entry(row,textvariable=self.chat_msg)
        ent.pack(side='left',fill='x',expand=True,padx=(0,8));ent.bind('<Return>',lambda e:self.ask())
        self.chat_send=ttk.Button(row,text='Enviar',command=self.ask);self.chat_send.pack(side='left')
        self.retry_button=ttk.Button(row,text='Reintentar último fallido',command=self.retry_chat);self.retry_button.pack(side='left',padx=5)
        self.refresh_mode_hint();self.refresh_usage()

    def refresh_mode_hint(self):
        if self.chat_mode.get()=='OpenAI online' and self.research_mode.get():
            self.mode_hint.set('Investigación: solo se envía tu pregunta actual, sin historial, registros ni adjuntos. Hasta 3 llamadas web; estimación US$0.01 por búsqueda más tokens. No incluyas datos personales en la pregunta.')
        elif self.chat_mode.get()=='OpenAI online':
            records='Incluye registros del grupo seleccionado.' if self.settings['include_records'] else 'Registros escolares no adjuntos.'
            self.mode_hint.set('Envío a OpenAI: tu mensaje y el historial previo online de este grupo. '+records+' Los adjuntos seleccionados también se envían. El historial puede contener información de adjuntos previos. Consumo API separado de ChatGPT.')
        else:self.mode_hint.set('Modo básico: datos y consultas guardadas en este equipo. Sin generación avanzada ni búsquedas web.')

    def refresh_attachments(self):
        ids=self.attachments.get(self.gid,[])
        names=[self.chat_service.materials.get(self.gid,i)['title'] for i in ids]
        self.attachment_text.set('Próxima consulta: '+', '.join(names) if names else 'Sin adjuntos para la próxima consulta')

    def clear_attachments(self):
        self.attachments[self.gid]=[];self.refresh_attachments()

    def open_materials(self):
        gid=self.gid;materials=self.chat_service.materials
        win=tk.Toplevel(self);win.title('Materiales del grupo · disponibles sin conexión');win.geometry('850x600')
        ttk.Label(win,text='Se guarda una copia del texto. El original permanece intacto. Adjuntar online envía el texto a OpenAI.',wraplength=800).pack(padx=10,pady=8)
        search=tk.StringVar();entry=ttk.Entry(win,textvariable=search);entry.pack(fill='x',padx=10)
        box=tk.Listbox(win,selectmode='extended',exportselection=False,height=7);box.pack(fill='x',padx=10,pady=5)
        preview=tk.Text(win,wrap='word',state='disabled');preview.pack(fill='both',expand=True,padx=10)
        rows=[]
        def refresh(*args):
            rows[:]=materials.list(gid,search.get());box.delete(0,'end')
            for r in rows:box.insert('end',f"[M{r['id']}] {r['title']}")
        def selected():return [rows[i]['id'] for i in box.curselection()]
        def show(event=None):
            ids=selected()
            if not ids:return
            r=materials.get(gid,ids[0]);preview.configure(state='normal');preview.delete('1.0','end')
            for tag in preview.tag_names():
                if tag.startswith('link_'):preview.tag_delete(tag)
            self.insert_links(preview,r['warning']+'\n\n'+r['content']);preview.configure(state='disabled')
        def import_doc():
            path=filedialog.askopenfilename(parent=win,filetypes=[('Documentos compatibles','*.txt *.md *.csv *.docx *.xlsx')])
            if not path:return
            try:
                mid=materials.import_file(gid,path);search.set('');refresh()
                index=next(i for i,r in enumerate(rows) if r['id']==mid)
                box.selection_clear(0,'end');box.selection_set(index);show()
            except Exception as exc:messagebox.showerror('No se importó',str(exc),parent=win)
        def attach():
            ids=selected()
            try:materials.context(gid,ids)
            except ValueError as exc:messagebox.showerror('Adjuntos',str(exc),parent=win);return
            self.attachments[gid]=ids
            if gid==self.gid:self.refresh_attachments()
            win.destroy()
        def save_fragment():
            fragment=preview.get('sel.first','sel.last') if preview.tag_ranges('sel') else ''
            if not fragment:messagebox.showinfo('Fragmento','Selecciona texto de la vista previa primero.',parent=win);return
            title=simpledialog.askstring('Guardar fragmento','Título del fragmento:',parent=win)
            if title:
                materials.save(gid,title,fragment,'Fragmento seleccionado por el docente; puede omitir contexto del original.');refresh()
        def export():
            ids=selected()
            if not ids:return
            r=materials.get(gid,ids[0]);path=filedialog.asksaveasfilename(parent=win,defaultextension='.md',filetypes=[('Texto Markdown','*.md')])
            if path:
                try:Path(path).write_text(r['content'],encoding='utf-8')
                except OSError as exc:messagebox.showerror('Exportación',str(exc),parent=win)
        def edit_copy():
            ids=selected()
            if not ids:return
            try:did=self.drafts.from_material(gid,ids[0])
            except ValueError as exc:messagebox.showerror('Borrador',str(exc),parent=win);return
            DraftEditor(self,gid,did)
        ttk.Button(win,text='Editar una copia del material seleccionado',command=edit_copy).pack(anchor='w',padx=10,pady=5)
        controls=ttk.Frame(win);controls.pack(fill='x',padx=10,pady=10)
        for title,command in [('Importar archivo',import_doc),('Adjuntar seleccionados',attach),('Guardar fragmento',save_fragment),('Exportar texto',export)]:
            ttk.Button(controls,text=title,command=command).pack(side='left',padx=3)
        search.trace_add('write',refresh);box.bind('<<ListboxSelect>>',show);refresh()

    def save_response(self):
        answers=[r for r in self.chat_service.history(self.gid) if r['role']=='assistant' and r['state']=='complete']
        if not answers:self.toast('Todavía no hay una respuesta para guardar.');return
        title=simpledialog.askstring('Guardar respuesta como material','Título:',parent=self)
        if title:
            try:
                mid=self.chat_service.materials.save(self.gid,title,answers[-1]['content'])
                did=self.drafts.from_material(self.gid,mid)
            except ValueError as exc:messagebox.showerror('Material',str(exc),parent=self);return
            self.toast('Respuesta guardada; copia editable abierta.')
            DraftEditor(self,self.gid,did)

    def refresh_usage(self):
        u=self.usage.summary()
        self.usage_text.set(f"Este mes: {u['attempts']}/{self.settings['monthly_limit']} intentos online · {u['input_tokens']+u['output_tokens']} tokens informados · estimación US${u['estimate_usd']:.4f} · web: {u['web_searches']} búsquedas / US${u['web_estimate_usd']:.4f} adicionales · {u['unknown']} sin costo confirmado")

    def mode_changed(self):
        if self.chat_mode.get()=='OpenAI online' and not self.api_key:
            self.configure_online()
            if not self.api_key:self.chat_mode.set('Básico sin conexión')
        self.settings['mode']=self.chat_mode.get();self.settings_store.save(self.settings);self.refresh_mode_hint()

    def configure_online(self):
        win=tk.Toplevel(self);win.title('Conexión de OpenAI y consumo');win.transient(self);win.grab_set()
        box=ttk.Frame(win,padding=18);box.pack(fill='both',expand=True)
        ttk.Label(box,text='La API de OpenAI tiene consumo separado de ChatGPT. No se harán llamadas al guardar.',wraplength=550).pack(anchor='w',pady=5)
        if self.credential_notice:ttk.Label(box,text=self.credential_notice,wraplength=550).pack(anchor='w')
        ttk.Label(box,text='Clave API personal (vacío conserva la actual):').pack(anchor='w')
        key=tk.StringVar();ttk.Entry(box,textvariable=key,show='•',width=60).pack(fill='x',pady=5)
        remember=tk.BooleanVar(value=False)
        ttk.Checkbutton(box,text='Guardar cifrada para este usuario de Windows',variable=remember,state='normal' if os.name=='nt' else 'disabled').pack(anchor='w')
        ttk.Label(box,text='Perfil de respuesta:').pack(anchor='w',pady=(10,0))
        profile=tk.StringVar(value=self.settings['profile']);ttk.Combobox(box,textvariable=profile,values=list(PROFILES),state='readonly').pack(anchor='w')
        limit=tk.StringVar(value=str(self.settings['monthly_limit']));output=tk.StringVar(value=str(self.settings['max_output_tokens']))
        ttk.Label(box,text='Máximo de intentos online por mes (también cuentan errores):').pack(anchor='w',pady=(10,0));ttk.Entry(box,textvariable=limit,width=10).pack(anchor='w')
        ttk.Label(box,text='Longitud máxima de respuesta (256–4096 tokens):').pack(anchor='w');ttk.Entry(box,textvariable=output,width=10).pack(anchor='w')
        records=tk.BooleanVar(value=self.settings['include_records'])
        ttk.Checkbutton(box,text='Adjuntar registros del grupo activo al consultar online',variable=records).pack(anchor='w',pady=10)
        ttk.Label(box,text='Los límites son locales a esta instalación. La estimación no sustituye la factura; algunas solicitudes fallidas pueden consumir. El historial online puede contener datos compartidos previamente.',wraplength=550).pack(anchor='w')
        def save():
            try:
                values=dict(self.settings,profile=profile.get(),monthly_limit=int(limit.get()),max_output_tokens=int(output.get()),include_records=records.get())
                Settings.validate(values)
                new_key=key.get().strip()
                if new_key:
                    if remember.get():self.vault.save(new_key)
                    else:self.vault.delete()
                    self.api_key=new_key
                self.settings_store.save(values);self.settings=values;self.credential_notice=''
                self.refresh_mode_hint();self.refresh_usage();win.destroy()
            except (ValueError,OSError,RuntimeError) as exc:messagebox.showerror('Configuración',str(exc),parent=win)
        def forget():
            self.vault.delete();self.api_key='';self.chat_mode.set('Básico sin conexión')
            self.settings['mode']='Básico sin conexión';self.settings_store.save(self.settings);self.refresh_mode_hint();win.destroy()
        row=ttk.Frame(box);row.pack(fill='x',pady=(14,0))
        ttk.Button(row,text='Guardar',command=save).pack(side='left')
        ttk.Button(row,text='Olvidar clave',command=forget).pack(side='left',padx=8)
        ttk.Button(row,text='Cancelar',command=win.destroy).pack(side='right')
        self.wait_window(win)

    def close(self):
        if self.chat_busy:
            messagebox.showinfo('Solicitud en curso','Espera a que termine la solicitud antes de cerrar. Los registros ya están guardados.',parent=self)
            return
        for editor in list(self.draft_editors):
            if editor.winfo_exists() and not editor.try_close():return
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
        self.load_chat()
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
        VoiceWindow(self,self.gid)

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
        self.chatlog.configure(state='normal');self.chatlog.insert('end',who+':\n')
        self.insert_links(self.chatlog,msg)
        self.chatlog.insert('end','\n\n');self.chatlog.see('end');self.chatlog.configure(state='disabled')

    def insert_links(self,widget,text):
        offset=0
        for match in re.finditer(r'\[([^\]\n]+)\]\((https?://[^\s)]+)\)',text):
            widget.insert('end',text[offset:match.start()]);url=safe_url(match.group(2))
            if url:
                tag='link_'+str(len(widget.tag_names()))
                widget.insert('end',match.group(1),(tag,));widget.tag_configure(tag,foreground='#175ca4',underline=True)
                widget.tag_bind(tag,'<Button-1>',lambda e,u=url:self.open_source(u))
            else:widget.insert('end',match.group(0))
            offset=match.end()
        widget.insert('end',text[offset:])

    def open_source(self,url):
        if safe_url(url) and messagebox.askyesno('Abrir fuente',url+'\n\n¿Abrir en tu navegador?',parent=self):
            webbrowser.open(url,new=2)

    def load_chat(self):
        self.refresh_attachments()
        self.chatlog.configure(state='normal');self.chatlog.delete('1.0','end');self.chatlog.configure(state='disabled')
        for tag in self.chatlog.tag_names():
            if tag.startswith('link_'):self.chatlog.tag_delete(tag)
        for item in self.chat_service.history(self.gid):
            label='Docente' if item['role']=='user' else 'AulaOS'
            if item['state']!='complete':label+=' · '+{'failed':'no completado','pending':'en curso'}.get(item['state'],item['state'])
            label+=' · '+{'online':'OpenAI','basic':'básico','ai':'local','legacy':'anterior','research':'investigación web','files':'archivos locales','action':'acciones locales'}.get(item['source'],item['source'])
            self.append_chat(label,item['content'])
            ids=[r[0] for r in self.store.con.execute('SELECT material_id FROM message_materials WHERE message_id=?',(item['id'],))]
            if ids:self.append_chat('Adjuntos',', '.join(f'[M{i}]' for i in ids))
    def retry_chat(self):
        if self.chat_busy:return
        users=[m for m in self.chat_service.history(self.gid) if m['role']=='user']
        if not users or users[-1]['state']!='failed':self.toast('El último mensaje de este grupo no necesita reintento.');return
        message=users[-1]
        if self.chat_mode.get()=='OpenAI online' and not messagebox.askyesno('Reintentar consulta','Será una nueva solicitud online y puede generar consumo. ¿Reintentar el mensaje guardado?',parent=self):return
        self.ask(message['id'],message['content'])

    def ask(self,retry_id=None,retry_text=None):
        question=retry_text if retry_text is not None else self.chat_msg.get().strip()
        if not question or self.chat_busy:return
        material_ids=list(self.attachments.get(self.gid,[]))
        gid=self.gid;settings=dict(self.settings);mode=self.chat_mode.get();api_key=self.api_key
        research=self.research_mode.get();allowed=[]
        if command(question) or is_search(question):mode='Básico sin conexión';research=False;material_ids=[]
        if retry_id is not None:
            original=next(m for m in self.chat_service.history(gid) if m['id']==retry_id)
            saved=json.loads(original['request_options']);research=bool(saved.get('research'));allowed=saved.get('domains',[])
        if research:
            if mode!='OpenAI online':self.toast('La investigación requiere OpenAI online. Puedes leer hallazgos guardados sin conexión.');return
            if retry_id is None:
                if material_ids:self.toast('Quita los adjuntos para investigar. Solo se enviará tu pregunta.');return
                try:allowed=domains(self.research_domains.get())
                except ValueError as exc:messagebox.showerror('Dominios',str(exc),parent=self);return
            else:material_ids=[]
        if mode=='OpenAI online' and not api_key:
            self.configure_online();return
        if retry_id is None:
            try:self.chat_service.materials.context(gid,material_ids)
            except ValueError as exc:messagebox.showerror('Adjuntos',str(exc),parent=self);return
            if not command(question) and not is_search(question):self.clear_attachments()
        self.research_mode.set(False);self.refresh_mode_hint()
        self.chat_busy=True;self.chat_send.configure(state='disabled');self.retry_button.configure(state='disabled')
        if retry_id is None:self.chat_msg.set('');self.append_chat('Docente',question)
        self.toast('Investigando en la web… Puede tardar hasta dos minutos.' if research else 'Consultando OpenAI…' if mode=='OpenAI online' else 'Consultando registros locales…')
        def work():
            store=None
            try:
                store=Store(DB_FILE)
                provider=MeteredProvider(store,OpenAIProvider(api_key,settings['profile'],settings['max_output_tokens'],research=research,allowed_domains=allowed),settings['monthly_limit']) if mode=='OpenAI online' else None
                answer=ChatService(store).send(gid,question,provider,include_records=settings['include_records'],retry_id=retry_id,material_ids=material_ids)
                self.chat_results.put((gid,answer,None,None))
            except Exception as exc:self.chat_results.put((gid,None,str(exc),getattr(exc,'kind','unknown')))
            finally:
                if store is not None:store.close()
        threading.Thread(target=work,daemon=True).start()

    def poll_chat(self):
        try:gid,answer,error,kind=self.chat_results.get_nowait()
        except queue.Empty:pass
        else:
            self.chat_busy=False;self.chat_send.configure(state='normal');self.retry_button.configure(state='normal')
            if gid==self.gid:self.load_chat()
            self.refresh_usage()
            if error:
                if kind=='connection':
                    self.chat_mode.set('Básico sin conexión');self.settings['mode']='Básico sin conexión';self.settings_store.save(self.settings);self.refresh_mode_hint()
                self.toast(error)
            elif gid!=self.gid:self.toast('Respuesta guardada en el grupo de origen.')
            else:
                self.toast('Respuesta guardada localmente.')
                if any(r['state']=='pending' for r in self.chat_service.actions.list(gid)):open_actions(self,gid)
        self.after(100,self.poll_chat)

if __name__=='__main__':AulaOS().mainloop()
