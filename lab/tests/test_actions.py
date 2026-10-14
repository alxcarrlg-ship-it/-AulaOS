import tempfile
import unittest
import sqlite3
from pathlib import Path
from core import Store
from chat import ChatService
from actions import Actions
from drafts import Drafts

class ActionsTest(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.path=Path(self.tmp.name)/'db.sqlite3'
        self.store=Store(self.path);self.gid=self.store.group('Escuela','1A');self.other=self.store.group('Otra','1A')
        self.sid=self.store.add_student(self.gid,'Ana Pérez');self.actions=Actions(self.store)
    def tearDown(self):self.store.close();self.tmp.cleanup()
    def propose(self,text):
        self.actions.propose(self.gid,text)
        return self.actions.list(self.gid)[0]['id']
    def test_preview_and_confirm_once(self):
        aid=self.propose('/tarea Revisar examen | 2026-10-20');self.assertEqual(self.store.tasks(),[])
        result=self.actions.resolve(self.gid,aid,True)
        self.assertEqual(result,self.actions.resolve(self.gid,aid,True));self.assertEqual(len(self.store.tasks()),1)
    def test_cancel_persists(self):
        aid=self.propose('/tarea Revisar');self.actions.resolve(self.gid,aid);other=Store(self.path)
        try:
            with self.assertRaises(ValueError):Actions(other).resolve(self.gid,aid,True)
        finally:other.close()
        self.assertEqual(self.store.tasks(),[])
    def test_scope(self):
        aid=self.propose('/tarea Revisar')
        for operation in (self.actions.get,self.actions.preview,self.actions.resolve):
            with self.assertRaises(ValueError):operation(self.other,aid)
        self.assertEqual(self.actions.list(self.other),[])
    def test_ambiguous_name_requires_id(self):
        self.store.add_student(self.gid,'Ana Pérez')
        with self.assertRaises(ValueError):self.propose('/observacion Ana Pérez | Participó')
        aid=self.propose(f'/observacion #{self.sid} | Participó | 2026-10-14');self.actions.resolve(self.gid,aid,True)
        self.assertEqual(self.store.events(self.sid)[0]['detail'],'Participó')
    def test_changed_identity(self):
        aid=self.propose('/observacion Ana Pérez | Participó')
        with self.store.con:self.store.con.execute('UPDATE students SET active=0 WHERE id=?',(self.sid,))
        with self.assertRaises(ValueError):self.actions.resolve(self.gid,aid,True)
        self.assertEqual(self.actions.get(self.gid,aid)['state'],'pending');self.assertEqual(self.store.events(self.sid),[])
    def test_changed_group(self):
        aid=self.propose('/tarea Revisar')
        with self.store.con:self.store.con.execute("UPDATE groups SET name='2A' WHERE id=?",(self.gid,))
        with self.assertRaises(ValueError):self.actions.resolve(self.gid,aid,True)
    def test_draft(self):
        aid=self.propose('/borrador Guía | # Inicio\nA | B\nContenido');did=self.actions.resolve(self.gid,aid,True)
        row=Drafts(self.store).get(self.gid,did)
        self.assertEqual(row['content'],'# Inicio\nA | B\nContenido');self.assertEqual(row['revision'],1)
    def test_invalid_fields(self):
        for text in ['/tarea X | mañana','/observacion Ana Pérez |','/borrador X','/tarea |','/observacion Ana Pérez | X | 2026-02-30']:
            with self.assertRaises(ValueError):self.propose(text)
        self.assertEqual(self.actions.list(self.gid),[])
    def test_general(self):
        self.actions.propose(None,'/tarea General');aid=self.actions.list(None)[0]['id'];self.actions.resolve(None,aid,True)
        with self.assertRaises(ValueError):self.actions.propose(None,'/observacion Ana Pérez | X')
    def test_chat_local_route(self):
        class Forbidden:
            def respond(self,messages):raise AssertionError('Network must not run')
        chat=ChatService(self.store);answer=chat.send(self.gid,'crea tarea: Revisar | 2026-10-20',Forbidden(),material_ids=[999])
        self.assertIn('Por confirmar',answer);self.assertEqual(self.store.tasks(),[]);self.assertEqual(chat.history(self.gid)[-1]['source'],'action')
    def test_explicit_only(self):
        self.assertIsNone(self.actions.propose(self.gid,'Ejemplo: /tarea No ejecutar'))
        self.assertIsNone(self.actions.propose(self.gid,'¿Qué tareas tengo?'))
    def test_chat_invalid_feedback(self):
        chat=ChatService(self.store);answer=chat.send(self.gid,'/tarea X | mañana')
        self.assertIn('No se preparó',answer);self.assertEqual(chat.history(self.gid)[-1]['state'],'complete')
    def test_recovery(self):
        self.actions.propose(self.gid,'/tarea X',request_id=44);self.actions.propose(self.gid,'/tarea X',request_id=44)
        self.assertEqual(len(self.actions.list(self.gid)),1)
    def test_atomic_failure(self):
        aid=self.propose('/tarea X')
        self.store.con.executescript("CREATE TRIGGER fail_action BEFORE UPDATE ON action_proposals BEGIN SELECT RAISE(ABORT,'failure'); END;")
        with self.assertRaises(sqlite3.Error):self.actions.resolve(self.gid,aid,True)
        self.assertEqual(self.store.tasks(),[]);self.assertEqual(self.actions.get(self.gid,aid)['state'],'pending')
    def test_two_connections(self):
        aid=self.propose('/tarea X');other=Store(self.path)
        try:
            second=Actions(other);first=self.actions.resolve(self.gid,aid,True);self.assertEqual(second.resolve(self.gid,aid,True),first)
        finally:other.close()
        self.assertEqual(len(self.store.tasks()),1)
