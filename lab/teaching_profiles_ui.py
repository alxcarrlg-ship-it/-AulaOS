"""Local profile editor, scoped to the current school's groups."""
import tkinter as tk
from tkinter import ttk,messagebox

class ProfileEditor(tk.Toplevel):
    def __init__(self,parent,service,gid,pid=None):
        super().__init__(parent);self.service=service;self.gid=gid;self.pid=pid;self.result=None
        row=service.get(gid,pid) if pid is not None else dict(name='',teacher='',requirements='',revision=0)
        self.revision=row['revision'];self.original=(row['name'],row['teacher'],row['requirements'])
        self.title('Requisitos de escuela y docente');self.geometry('720x500');self.transient(parent)
        ttk.Label(self,text='Disponible para los grupos de esta escuela. El perfil se envía a la IA solo cuando lo seleccionas.',wraplength=680).pack(padx=12,pady=10)
        self.name=tk.StringVar(value=row['name']);self.teacher=tk.StringVar(value=row['teacher'])
        for label,var in [('Nombre del perfil',self.name),('Docente',self.teacher)]:
            ttk.Label(self,text=label).pack(anchor='w',padx=12);ttk.Entry(self,textvariable=var).pack(fill='x',padx=12,pady=4)
        ttk.Label(self,text='Requisitos y preferencias (máximo 6000 caracteres)').pack(anchor='w',padx=12)
        self.body=tk.Text(self,wrap='word');self.body.pack(fill='both',expand=True,padx=12,pady=6);self.body.insert('1.0',row['requirements'])
        ttk.Button(self,text='Guardar perfil local',command=self.save).pack(pady=8)
        self.protocol('WM_DELETE_WINDOW',self.close);self.grab_set()
    def values(self):return self.name.get(),self.teacher.get(),self.body.get('1.0','end-1c')
    def save(self):
        try:self.result=self.service.save(self.gid,*self.values(),pid=self.pid,expected_revision=self.revision)
        except Exception as exc:messagebox.showerror('No se guardó',str(exc),parent=self);return
        self.destroy()
    def close(self):
        if self.values()!=self.original and not messagebox.askyesno('Cambios sin guardar','¿Cerrar y descartar los cambios de este perfil?',parent=self):return
        self.destroy()
