"""Periodic recovery copies; restores into editor only, never commits a revision."""
import json
import uuid
import tkinter as tk
from tkinter import ttk,messagebox
from recovery import Recovery

class RecoveryController:
    INTERVAL=10000
    def __init__(self,editor,kind,read,apply):
        self.editor=editor;self.kind=kind;self.read=read;self.apply=apply;self.service=Recovery(editor.app.store)
        self.token=uuid.uuid4().hex;self.last=None;self.recovered=set()
        if not hasattr(editor.app,'recovery_active'):editor.app.recovery_active=set()
        editor.app.recovery_active.add(self.token)
        bar=ttk.Frame(editor);bar.pack(fill='x',padx=12,pady=3)
        ttk.Button(bar,text='Recuperar trabajo',command=self.open).pack(side='left')
        self.status=tk.StringVar(value='Recuperación local cada 10 s mientras hay cambios; no guarda una versión aprobada.')
        ttk.Label(bar,textvariable=self.status,wraplength=650).pack(side='left',padx=8)
        if self.candidates():self.status.set('Hay copias de trabajo anteriores disponibles en «Recuperar trabajo».')
        self.timer=editor.after(self.INTERVAL,self.tick)
    def candidates(self):
        return [r for r in self.service.list(self.editor.gid,self.kind,self.editor.did) if r['token'] not in self.editor.app.recovery_active]
    def tick(self):
        try:
            payload=self.read()
            if self.editor.dirty():
                signature=(self.editor.did,self.editor.revision,json.dumps(payload,ensure_ascii=False,sort_keys=True))
                if signature!=self.last:
                    self.service.put(self.token,self.editor.gid,self.kind,self.editor.did,self.editor.revision,payload)
                    self.last=signature;self.status.set('Copia de recuperación actualizada en este equipo.')
            elif self.last is not None:
                self.service.delete(self.editor.gid,self.token);self.last=None
        except Exception as exc:self.status.set('No se pudo actualizar la recuperación: '+str(exc))
        finally:self.timer=self.editor.after(self.INTERVAL,self.tick)
    def saved(self):
        # Called only after the document's explicit save succeeds.
        try:
            for token in self.recovered|{self.token}:self.service.delete(self.editor.gid,token)
            self.recovered.clear();self.last=None
            self.status.set('Versión guardada; la recuperación seguirá protegiendo las próximas ediciones.')
        except Exception as exc:self.status.set('Versión guardada; quedó una copia de recuperación pendiente: '+str(exc))
        finally:
            self.editor.app.recovery_active.discard(self.token);self.token=uuid.uuid4().hex
            self.editor.app.recovery_active.add(self.token);self.last=None
    def stop(self):
        self.editor.after_cancel(self.timer)
        # Explicit closing/discard removes only this window's working copy.
        try:self.service.delete(self.editor.gid,self.token)
        except Exception:pass
        self.editor.app.recovery_active.discard(self.token)
    def open(self):
        rows=self.candidates()
        if not rows:messagebox.showinfo('Recuperación','No hay copias de otras sesiones para este documento. Los borradores nuevos se recuperan desde Nuevo borrador.',parent=self.editor);return
        win=tk.Toplevel(self.editor);win.title('Recuperar trabajo local');win.geometry('800x600')
        box=tk.Listbox(win,height=5,exportselection=False);box.pack(fill='x',padx=12,pady=8)
        for r in rows:box.insert('end',f"{r['updated_at']} · base v{r['base_revision'] or 0} · sesión {r['token'][:8]}")
        body=tk.Text(win,wrap='word',state='disabled');body.pack(fill='both',expand=True,padx=12)
        def chosen():return rows[box.curselection()[0]] if box.curselection() else None
        def show(event=None):
            row=chosen()
            if row:
                body.configure(state='normal');body.delete('1.0','end');body.insert('1.0',json.dumps(row['payload'],ensure_ascii=False,indent=2));body.configure(state='disabled')
        def recover():
            row=chosen()
            if not row:return
            if not messagebox.askyesno('Recuperar en el editor','Se reemplazará el texto abierto, sin guardar una versión. Si la versión base quedó antigua, Guardar versión rechazará el conflicto; podrás usar Guardar copia. ¿Continuar?',parent=win):return
            try:
                row=self.service.get(self.editor.gid,row['token'])
                self.service.validate(self.editor.gid,self.kind,self.editor.did,row['base_revision'],row['payload'])
                self.apply(row['payload'],row['base_revision']);self.recovered.add(row['token']);self.last=None
                # Capture immediately after recovery, rather than waiting for the timer.
                self.service.put(self.token,self.editor.gid,self.kind,self.editor.did,self.editor.revision,self.read())
            except Exception as exc:messagebox.showerror('Recuperación',str(exc),parent=win);return
            self.status.set('Texto recuperado; revisa y guarda una versión o una copia.');win.destroy()
        def remove():
            row=chosen()
            if row and messagebox.askyesno('Descartar copia','¿Eliminar esta copia recuperable? Las versiones guardadas se conservan.',parent=win):
                self.service.delete(self.editor.gid,row['token']);win.destroy()
        bar=ttk.Frame(win);bar.pack(pady=8)
        ttk.Button(bar,text='Recuperar texto',command=recover).pack(side='left');ttk.Button(bar,text='Descartar esta copia',command=remove).pack(side='left',padx=8)
        box.bind('<<ListboxSelect>>',show);box.selection_set(0);show()
