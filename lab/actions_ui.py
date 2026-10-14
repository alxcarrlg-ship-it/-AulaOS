"""Review local proposals in their original school/group."""
import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3
from drafts_ui import DraftEditor
from actions import HELP


def open_actions(app,gid):
    actions=app.chat_service.actions
    win=tk.Toplevel(app);win.title('Acciones · '+actions.scope(gid));win.geometry('820x620')
    ttk.Label(win,text='Revisa el destino y el texto. Confirmar aplica exactamente esta propuesta.',wraplength=780).pack(padx=12,pady=8)
    box=tk.Listbox(win,height=7,exportselection=False);box.pack(fill='x',padx=12)
    preview=tk.Text(win,wrap='word');preview.pack(fill='both',expand=True,padx=12,pady=8)
    rows=[]
    def selected():
        indices=box.curselection()
        return rows[indices[0]] if indices else None
    def show(event=None):
        row=selected();preview.configure(state='normal');preview.delete('1.0','end')
        preview.insert('end',actions.preview(gid,row['id']) if row else HELP);preview.configure(state='disabled')
        state='normal' if row and row['state']=='pending' else 'disabled'
        confirm.configure(state=state);cancel.configure(state=state)
    def refresh():
        nonlocal rows
        rows=actions.list(gid);box.delete(0,'end')
        for row in rows:
            state={'pending':'Por confirmar','applied':'Aplicado','cancelled':'Cancelado'}[row['state']]
            kind={'task':'Tarea','event':'Observación','draft':'Borrador'}[row['kind']]
            box.insert('end',f"#{row['id']} · {kind} · {state} · {row['created_at']}")
        if rows:box.selection_set(0)
        show()
    def resolve(apply):
        row=selected()
        if not row:return
        try:result=actions.resolve(gid,row['id'],apply)
        except (ValueError,sqlite3.Error) as exc:
            messagebox.showerror('Acción no aplicada',str(exc),parent=win);refresh();return
        app.load_tasks();app.load_timeline();refresh()
        app.toast('Acción aplicada y registrada localmente.' if apply else 'Propuesta cancelada; registros intactos.')
        if apply and row['kind']=='draft':DraftEditor(app,gid,result)
    buttons=ttk.Frame(win);buttons.pack(fill='x',padx=12,pady=8)
    confirm=ttk.Button(buttons,text='Confirmar y guardar',command=lambda:resolve(True));confirm.pack(side='left')
    cancel=ttk.Button(buttons,text='Cancelar propuesta',command=lambda:resolve(False));cancel.pack(side='left',padx=8)
    ttk.Button(buttons,text='Actualizar historial',command=refresh).pack(side='left')
    ttk.Button(buttons,text='Cerrar',command=win.destroy).pack(side='right')
    box.bind('<<ListboxSelect>>',show);refresh()
