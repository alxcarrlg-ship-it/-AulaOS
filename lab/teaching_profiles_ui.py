"""Local profile editor, scoped to the current school's groups."""
import json
import tkinter as tk
from tkinter import ttk,messagebox
from recovery_ui import RecoveryController

class ProfileEditor(tk.Toplevel):
    def __init__(self,parent,service,gid,pid=None):
        super().__init__(parent);self.app=parent.app;self.service=service;self.gid=gid;self.pid=pid;self.result=None
        row=service.get(gid,pid) if pid is not None else dict(name='',teacher='',requirements='',revision=0,questions_json='[]')
        self.revision=row['revision'];self.original=(row['name'],row['teacher'],row['requirements'],'\n'.join(json.loads(row['questions_json'])))
        self.title('Requisitos de escuela y docente');self.geometry('720x500');self.transient(parent)
        ttk.Label(self,text='Disponible para los grupos de esta escuela. El perfil se envía a la IA solo cuando lo seleccionas.',wraplength=680).pack(padx=12,pady=10)
        self.name=tk.StringVar(value=row['name']);self.teacher=tk.StringVar(value=row['teacher'])
        for label,var in [('Nombre del perfil',self.name),('Docente',self.teacher)]:
            ttk.Label(self,text=label).pack(anchor='w',padx=12);ttk.Entry(self,textvariable=var).pack(fill='x',padx=12,pady=4)
        ttk.Label(self,text='Requisitos y preferencias (máximo 6000 caracteres)').pack(anchor='w',padx=12)
        self.body=tk.Text(self,wrap='word');self.body.pack(fill='both',expand=True,padx=12,pady=6);self.body.insert('1.0',row['requirements'])
        ttk.Label(self,text='Datos que se deben aclarar antes de generar (opcional, uno por línea; máximo 8)').pack(anchor='w',padx=12)
        self.questions=tk.Text(self,height=4,wrap='word');self.questions.pack(fill='x',padx=12);self.questions.insert('1.0','\n'.join(json.loads(row['questions_json'])))
        ttk.Button(self,text='Guardar perfil local',command=self.save).pack(pady=8)
        self.recovery=RecoveryController(self,'profile',self.recovery_values,self.recover_text,target=lambda:self.pid)
        self.protocol('WM_DELETE_WINDOW',self.close);self.grab_set()
    def dirty(self):return self.values()!=self.original
    def recovery_values(self):return dict(zip(('name','teacher','requirements','questions'),self.values()))
    def recover_text(self,payload,revision):
        self.revision=revision;self.name.set(payload['name']);self.teacher.set(payload['teacher'])
        for box,key in [(self.body,'requirements'),(self.questions,'questions')]:box.delete('1.0','end');box.insert('1.0',payload[key])
    def values(self):return self.name.get(),self.teacher.get(),self.body.get('1.0','end-1c'),self.questions.get('1.0','end-1c')
    def save(self):
        try:self.result=self.service.save(self.gid,*self.values()[:3],pid=self.pid,expected_revision=self.revision,questions=[q.strip() for q in self.values()[3].splitlines() if q.strip()])
        except Exception as exc:messagebox.showerror('No se guardó',str(exc),parent=self);return
        self.recovery.saved();self.recovery.stop();self.destroy()
    def close(self):
        if self.values()!=self.original and not messagebox.askyesno('Cambios sin guardar','¿Cerrar y descartar los cambios de este perfil?',parent=self):return
        self.recovery.stop();self.destroy()
