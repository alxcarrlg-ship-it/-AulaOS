"""Review all before/after fields before accepting a versioned template proposal."""
import json
import queue
import threading
import tkinter as tk
from tkinter import ttk,messagebox
from core import Store
from online import OpenAIProvider,MeteredProvider
from template_suggestions import TemplateSuggestions
from teaching_profiles_ui import ProfileEditor

class SuggestionWindow(tk.Toplevel):
    def __init__(self,editor):
        super().__init__(editor.app);self.editor=editor;self.app=editor.app;self.gid=editor.gid;self.did=editor.did
        self.service=TemplateSuggestions(self.app.store);self.busy=False;self.results=queue.Queue();self.rows=[]
        self.title('Contenido para tu formato · propuesta revisable');self.geometry('980x780')
        ttk.Label(self,text='Describe tema, nivel, sesiones y requisitos. La IA propondrá cambios solo en campos existentes.',wraplength=920).pack(anchor='w',padx=12,pady=8)
        self.goal=tk.Text(self,height=4,wrap='word');self.goal.pack(fill='x',padx=12)
        profile_bar=ttk.Frame(self);profile_bar.pack(fill='x',padx=12,pady=4)
        ttk.Label(profile_bar,text='Perfil de esta escuela:').pack(side='left')
        self.profile_box=ttk.Combobox(profile_bar,state='readonly',width=38);self.profile_box.pack(side='left',padx=6)
        ttk.Button(profile_bar,text='Nuevo',command=lambda:self.edit_profile(True)).pack(side='left')
        ttk.Button(profile_bar,text='Ver / editar',command=self.edit_profile).pack(side='left',padx=6)
        self.refresh_profiles()
        self.use_sources=tk.BooleanVar(value=False)
        ttk.Checkbutton(self,text='Usar los materiales seleccionados para el chat de este grupo (hasta tres)',variable=self.use_sources).pack(anchor='w',padx=12,pady=4)
        ttk.Button(self,text='Pedir propuesta con OpenAI',command=self.request).pack(anchor='w',padx=12,pady=6)
        self.box=tk.Listbox(self,height=5,exportselection=False);self.box.pack(fill='x',padx=12)
        self.preview=tk.Text(self,wrap='word',state='disabled');self.preview.pack(fill='both',expand=True,padx=12,pady=8)
        controls=ttk.Frame(self);controls.pack(fill='x',padx=12)
        self.apply=ttk.Button(controls,text='Elegir, editar y aplicar cambios',command=lambda:self.resolve(True));self.apply.pack(side='left')
        self.reject=ttk.Button(controls,text='Descartar propuesta',command=lambda:self.resolve(False));self.reject.pack(side='left',padx=6)
        self.notice=tk.StringVar(value='No se modifica el documento al pedir una propuesta. Revisar exactitud pedagógica y distribución antes de entregar.')
        ttk.Label(self,textvariable=self.notice,wraplength=920).pack(padx=12,pady=8)
        self.box.bind('<<ListboxSelect>>',self.show);self.refresh();self.app.draft_editors.add(self);self.protocol('WM_DELETE_WINDOW',self.try_close);self.poll_id=self.after(100,self.poll)
    def refresh_profiles(self,pid=None):
        self.profile_rows=self.service.profiles.list(self.gid)
        self.profile_box.configure(values=['Sin perfil']+[r['name']+' · '+r['teacher'] for r in self.profile_rows])
        self.profile_box.current(next((i+1 for i,r in enumerate(self.profile_rows) if r['id']==pid),0))
    def selected_profile(self):
        index=self.profile_box.current()
        return self.profile_rows[index-1] if index>0 else None
    def edit_profile(self,new=False):
        if self.busy:return
        row=None if new else self.selected_profile()
        if not new and row is None:messagebox.showinfo('Perfil','Selecciona un perfil o crea uno nuevo.',parent=self);return
        dialog=ProfileEditor(self,self.service.profiles,self.gid,row['id'] if row else None)
        self.wait_window(dialog)
        self.refresh_profiles(dialog.result or (row['id'] if row else None))
    def selected(self):return self.rows[self.box.curselection()[0]] if self.box.curselection() else None
    def refresh(self):
        self.rows=self.service.list(self.gid,self.did);self.box.delete(0,'end')
        for row in self.rows:self.box.insert('end',f"#{row['id']} · base v{row['base_revision']} · "+{'pending':'Por revisar','applied':'Aplicada','rejected':'Descartada'}[row['state']]+' · '+row['created_at'])
        if self.rows:self.box.selection_set(0)
        self.show()
    def show(self,event=None):
        row=self.selected();text='Las propuestas y su estado se conservan en este documento.'
        pending=bool(row and row['state']=='pending' and not self.busy)
        self.apply.configure(state='normal' if pending else 'disabled');self.reject.configure(state='normal' if pending else 'disabled')
        if row:
            text='PETICIÓN\n'+row['goal']+'\n\nNOTAS DE LA IA (revisar)\n'+row['notes']+'\n\n'
            profile=json.loads(row['profile_json'])
            if profile:text+='PERFIL UTILIZADO · '+profile['name']+' · '+profile['teacher']+' · v'+str(profile['revision'])+'\n'+profile['requirements']+'\n\n'
            sources=json.loads(row['sources_json'])
            text+='FUENTES ENVIADAS\n'+('\n'.join('['+s['source']+'] '+s['title'] for s in sources) or 'Ninguna')+'\n\n'
            differences=self.service.review(self.gid,row['id'])
            if not differences:text+='La IA no propuso cambios de texto. Revisa sus notas.'
            for change in differences:text+=change['location']+' · '+change['id']+'\nANTES:\n'+change['before']+'\nPROPUESTA:\n'+change['after']+'\n\n'
            if row['state']=='applied':
                accepted=json.loads(row['applied_changes'] or row['changes'])
                text+='CAMBIOS APROBADOS (los demás se omitieron)\n'
                for key,value in accepted.items():text+=key+'\n'+value+'\n\n'
            for source in sources:text+='COPIA DE FUENTE ['+source['source']+'] '+source['title']+'\n'+source['text']+'\n\n'
        self.preview.configure(state='normal');self.preview.delete('1.0','end');self.preview.insert('1.0',text);self.preview.configure(state='disabled')
    def request(self):
        if self.busy:return
        if not self.editor.winfo_exists():messagebox.showinfo('Editor cerrado','Abre el documento otra vez para pedir una propuesta sobre su versión actual.',parent=self);return
        if not self.editor.save():return
        goal=self.goal.get('1.0','end-1c').strip();revision=self.editor.revision
        material_ids=list(self.app.attachments.get(self.gid,[])) if self.use_sources.get() else []
        profile=self.selected_profile();profile_id=profile['id'] if profile else None;profile_revision=profile['revision'] if profile else None
        try:
            _,_,messages=self.service.context(self.gid,self.did,goal,revision,material_ids,profile_id,profile_revision)
            sources=json.loads(messages[-1]['content'])['sources']
        except Exception as exc:messagebox.showerror('Propuesta',str(exc),parent=self);return
        if not self.app.api_key:self.app.configure_online()
        if not self.app.api_key:return
        source_names=', '.join('['+s['source']+'] '+s['title'] for s in sources) or 'ninguna'
        profile_notice=('\nPerfil: '+profile['name']+' · '+profile['teacher']+'\n'+profile['requirements']) if profile else '\nSin perfil docente.'
        if not messagebox.askyesno('Enviar campos a OpenAI','Se enviarán tu petición y los textos actuales de los párrafos editables. Fuentes: '+source_names+'. Pueden contener datos personales. No se envían el Word, imágenes, otros registros ni historial. La consulta consume API.'+profile_notice+'\n¿Continuar?',parent=self):return
        settings=dict(self.app.settings);key=self.app.api_key;db=self.app.store.db_path;gid=self.gid;did=self.did
        self.busy=True;self.show();self.notice.set('Preparando propuesta… El documento no se modificará hasta que la aceptes.')
        def work():
            store=None
            try:
                store=Store(db);provider=MeteredProvider(store,OpenAIProvider(key,settings['profile'],settings['max_output_tokens']),settings['monthly_limit'])
                sid=TemplateSuggestions(store).propose(gid,did,goal,revision,provider,material_ids,profile_id,profile_revision);self.results.put((sid,None))
            except Exception as exc:self.results.put((None,str(exc)))
            finally:
                if store:store.close()
        threading.Thread(target=work,daemon=True).start()
    def resolve(self,apply):
        if self.busy:return
        row=self.selected()
        if not row:return
        if apply and self.editor.winfo_exists():
            self.editor.capture()
            if self.editor.changes!=self.editor.saved:messagebox.showinfo('Cambios locales','Guarda tus cambios en el editor antes de continuar. Si cambió la versión, tendrás que pedir una propuesta nueva.',parent=self);return
        if apply:
            dialog=ReviewChanges(self,self.service.review(self.gid,row['id']),lambda keys,edits:self.service.resolve(self.gid,row['id'],True,keys,edits,dialog.draft_revision),
                self.service.review_draft(self.gid,row['id']),lambda keys,values,version:self.service.save_review(self.gid,row['id'],keys,values,version))
            self.wait_window(dialog)
            if dialog.result is None:return
            revision=dialog.result
        else:
            try:revision=self.service.resolve(self.gid,row['id'],False)
            except Exception as exc:messagebox.showerror('No se aplicó',str(exc),parent=self);return
        if apply and self.editor.winfo_exists():
            doc=self.editor.service.document(self.gid,self.did);self.editor.revision=doc['revision'];self.editor.changes=json.loads(doc['changes']);self.editor.saved=dict(self.editor.changes);self.editor.active=None;self.editor.select();self.editor.notice.set(f'Propuesta aplicada como versión {revision}. Revisa el Word exportado.')
        self.refresh();self.notice.set(f'Guardada nueva versión {revision}.' if apply else 'Propuesta descartada. Documento intacto.')
    def poll(self):
        try:sid,error=self.results.get_nowait()
        except queue.Empty:pass
        else:
            self.busy=False;self.app.refresh_usage();self.refresh();self.notice.set(error or 'Propuesta guardada. Revisa TODOS los cambios antes de aplicarlos.')
        self.poll_id=self.after(100,self.poll)
    def try_close(self):
        if self.busy:messagebox.showinfo('Solicitud en curso','Espera a que termine; no habrá reintentos automáticos.',parent=self);return False
        self.after_cancel(self.poll_id);self.app.draft_editors.discard(self);self.destroy();return True


class ReviewChanges(tk.Toplevel):
    """Local review only; the parent commits the chosen text atomically."""
    def __init__(self,parent,changes,on_apply,draft,on_save):
        super().__init__(parent);self.result=None;self.changes=changes;self.active=None;self.on_apply=on_apply
        self.values={c['id']:c['after'] for c in changes};self.included=set(self.values)
        self.on_save=on_save;self.draft_revision=draft['revision'] if draft else 0
        if draft:self.values=dict(draft['values']);self.included=set(draft['selected'])
        self.saved_values=dict(self.values);self.saved_included=set(self.included)
        self.title('Revisar campos antes de guardar');self.geometry('900x700');self.transient(parent)
        ttk.Label(self,text='Selecciona cada campo para revisarlo. Desmarca los que quieras omitir y corrige el texto.\nAl aplicar se cierra esta propuesta; los campos omitidos conservan su contenido.',wraplength=860).pack(anchor='w',padx=12,pady=8)
        self.box=tk.Listbox(self,height=6,exportselection=False);self.box.pack(fill='x',padx=12)
        for c in changes:self.box.insert('end',c['location']+' · '+c['id'])
        self.include=tk.BooleanVar(value=True)
        ttk.Checkbutton(self,text='Incluir este campo',variable=self.include,command=self.capture).pack(anchor='w',padx=12)
        ttk.Label(self,text='Antes').pack(anchor='w',padx=12)
        self.before=tk.Text(self,height=5,wrap='word',state='disabled');self.before.pack(fill='x',padx=12)
        ttk.Label(self,text='Texto que se guardará (editable)').pack(anchor='w',padx=12)
        self.after_text=tk.Text(self,wrap='word');self.after_text.pack(fill='both',expand=True,padx=12,pady=6)
        self.count=tk.StringVar();ttk.Label(self,textvariable=self.count).pack(anchor='w',padx=12)
        controls=ttk.Frame(self);controls.pack(fill='x',padx=12,pady=8)
        ttk.Button(controls,text='Aplicar selección como nueva versión',command=self.accept).pack(side='left')
        ttk.Button(controls,text='Guardar para continuar después',command=self.save).pack(side='left',padx=8)
        ttk.Button(controls,text='Cerrar revisión',command=self.cancel).pack(side='left',padx=8)
        self.box.bind('<<ListboxSelect>>',self.select);self.protocol('WM_DELETE_WINDOW',self.cancel)
        if changes:self.box.selection_set(0);self.select()
        self.grab_set()
    def capture(self):
        if self.active is not None:
            self.values[self.active]=self.after_text.get('1.0','end-1c')
            if self.include.get():self.included.add(self.active)
            else:self.included.discard(self.active)
        self.count.set(f'{len(self.included)} de {len(self.changes)} campos incluidos.')
    def select(self,event=None):
        self.capture()
        if not self.box.curselection():return
        change=self.changes[self.box.curselection()[0]];self.active=change['id']
        self.include.set(self.active in self.included)
        self.before.configure(state='normal');self.before.delete('1.0','end');self.before.insert('1.0',change['before']);self.before.configure(state='disabled')
        self.after_text.delete('1.0','end');self.after_text.insert('1.0',self.values[self.active])
    def accept(self):
        self.capture()
        if not self.included:messagebox.showinfo('Sin campos','Incluye al menos un campo o vuelve para descartar la propuesta.',parent=self);return
        keys=[c['id'] for c in self.changes if c['id'] in self.included]
        try:self.result=self.on_apply(keys,{k:self.values[k] for k in keys})
        except Exception as exc:messagebox.showerror('No se aplicó',str(exc),parent=self);return
        self.destroy()
    def save(self):
        self.capture()
        keys=[c['id'] for c in self.changes if c['id'] in self.included]
        try:self.draft_revision=self.on_save(keys,dict(self.values),self.draft_revision)
        except Exception as exc:messagebox.showerror('No se guardó',str(exc),parent=self);return False
        self.saved_values=dict(self.values);self.saved_included=set(self.included)
        self.count.set('Revisión guardada para continuar después. El documento aún no cambia.')
        return True
    def cancel(self):
        self.capture()
        if self.included!=self.saved_included or self.values!=self.saved_values:
            answer=messagebox.askyesnocancel('Guardar revisión','¿Guardar tus correcciones y selección para continuar después? No se aplicarán al documento.',parent=self)
            if answer is None:return
            if answer and not self.save():return
        self.destroy()
