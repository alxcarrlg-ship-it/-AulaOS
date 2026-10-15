import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from core import Store
from drafts import RevisionConflict
from projects import Projects,FIELDS
from template_suggestions import TemplateSuggestions
from test_templates import fixture

class ProjectsTest(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.db=Path(self.tmp.name)/'db.sqlite3';self.store=Store(self.db)
        self.gid=self.store.group('Escuela','A');self.other=self.store.group('Escuela','B');self.service=Projects(self.store)
        self.content=dict(title='Animales',planned='Tres sesiones y un cartel',completed='',pending='Cartel',next_step='Practicar vocabulario',documents=[])
        path=Path(self.tmp.name)/'source.docx';fixture(path,3)
        tid=self.service.templates.import_file(self.gid,path,'Formato')
        self.did=self.service.templates.create(self.gid,tid,'Primera semana')
        self.key=next(f['id'] for f in json.loads(self.service.templates.get(self.gid,tid)['schema_json'])['fields'] if f['text']=='Completar')
    def tearDown(self):self.store.close();self.tmp.cleanup()
    def save(self):return self.service.save(self.gid,self.content)[0]
    def test_separates_planned_completed_and_pending(self):
        pid=self.save();row=self.service.get(self.gid,pid)
        self.assertEqual(row['planned'],self.content['planned']);self.assertEqual(row['completed'],'');self.assertEqual(row['pending'],'Cartel')
    def test_history_persistence_and_noop(self):
        pid=self.save();self.assertEqual(self.service.save(self.gid,self.content,pid,1),(pid,1))
        updated=dict(self.content,completed='Una sesión realizada',pending='Dos sesiones y cartel')
        self.service.save(self.gid,updated,pid,1)
        self.assertEqual(self.service.get(self.gid,pid,1)['completed'],'')
        self.assertEqual([r['revision'] for r in self.service.history(self.gid,pid)],[2,1])
        other=Store(self.db)
        try:self.assertEqual(Projects(other).get(self.gid,pid)['completed'],'Una sesión realizada')
        finally:other.close()
    def test_scope_including_same_school(self):
        pid=self.save()
        self.assertEqual(self.service.list(self.other),[])
        for fn,args in [(self.service.get,(self.other,pid)),(self.service.history,(self.other,pid)),(self.service.save,(self.other,self.content,pid,1)),(self.service.snapshot,(self.other,pid))]:
            with self.assertRaises(ValueError):fn(*args)
    def test_conflicting_edit_preserves_latest(self):
        pid=self.save();self.service.save(self.gid,dict(self.content,completed='Sesión 1'),pid,1)
        with self.assertRaises(RevisionConflict):self.service.save(self.gid,dict(self.content,completed='Sesión 2'),pid,1)
        self.assertEqual(self.service.get(self.gid,pid)['completed'],'Sesión 1')
    def test_invalid_payloads_no_projects_created(self):
        for content in [dict(self.content,title=''),dict(self.content,pending=1),dict(self.content,planned='x'*10001),dict(self.content,documents=[{'id':999,'revision':1}]),dict(self.content,unknown='X')]:
            with self.assertRaises(ValueError):self.service.save(self.gid,content)
        self.assertEqual(self.service.list(self.gid),[])
    def test_document_links_pin_revision_without_marking_completed(self):
        content=dict(self.content,documents=[{'id':self.did,'revision':1,'title':'Título falso'}])
        pid=self.service.save(self.gid,content)[0]
        self.service.templates.save(self.gid,self.did,{self.key:'Texto de semana nueva'},1)
        row=self.service.get(self.gid,pid)
        self.assertEqual(row['documents'],[dict(id=self.did,revision=1,title='Primera semana')]);self.assertEqual(row['completed'],'')
        with self.assertRaises(ValueError):self.service.save(self.other,content)
    def test_atomic_rollback(self):
        pid=self.save()
        self.store.con.executescript("CREATE TRIGGER fail_project BEFORE INSERT ON teaching_project_revisions BEGIN SELECT RAISE(ABORT,'failure'); END;")
        with self.assertRaises(sqlite3.Error):self.service.save(self.gid,dict(self.content,pending='Algo nuevo'),pid,1)
        self.assertEqual(self.service.get(self.gid,pid)['revision'],1);self.assertEqual(len(self.service.history(self.gid,pid)),1)
    def provider(self):
        key=self.key
        class Fake:
            def respond(self,messages):return json.dumps({'changes':{key:'Seguir con el cartel'},'notes':'Adaptación de pendientes.'})
        return Fake()
    def test_generation_opt_in_and_immutable_snapshot(self):
        pid=self.save();suggestions=TemplateSuggestions(self.store)
        _,_,messages=suggestions.context(self.gid,self.did,'Clase siguiente',1)
        self.assertIsNone(json.loads(messages[-1]['content'])['project_progress'])
        sid=suggestions.propose(self.gid,self.did,'Clase siguiente',1,self.provider(),project_id=pid,project_revision=1)
        snapshot=json.loads(suggestions.get(self.gid,sid)['project_json']);self.assertEqual(snapshot['pending'],'Cartel')
        self.service.save(self.gid,dict(self.content,pending='Producto terminado',completed='Cartel realizado'),pid,1)
        self.assertEqual(json.loads(suggestions.get(self.gid,sid)['project_json']),snapshot)
    def test_progress_changed_before_apply_blocks_old_suggestion(self):
        pid=self.save();suggestions=TemplateSuggestions(self.store)
        sid=suggestions.propose(self.gid,self.did,'Siguiente',1,self.provider(),project_id=pid,project_revision=1)
        self.service.save(self.gid,dict(self.content,completed='Actividad realizada'),pid,1)
        with self.assertRaises(RevisionConflict):suggestions.resolve(self.gid,sid,True)
        self.assertEqual(self.service.templates.document(self.gid,self.did)['revision'],1)
        self.assertEqual(suggestions.get(self.gid,sid)['state'],'pending')
    def test_generation_and_apply_do_not_change_progress(self):
        pid=self.save();suggestions=TemplateSuggestions(self.store)
        before=self.service.get(self.gid,pid)
        sid=suggestions.propose(self.gid,self.did,'Siguiente',1,self.provider(),project_id=pid,project_revision=1)
        suggestions.resolve(self.gid,sid,True)
        self.assertEqual(self.service.get(self.gid,pid),before)
        self.assertEqual(self.service.templates.document(self.gid,self.did)['revision'],2)
    def test_stale_and_other_group_before_provider(self):
        pid=self.save();suggestions=TemplateSuggestions(self.store)
        self.service.save(self.gid,dict(self.content,pending='Cambio'),pid,1)
        class Forbidden:
            def respond(self,messages):raise AssertionError('No llamar')
        with self.assertRaises(RevisionConflict):suggestions.propose(self.gid,self.did,'Siguiente',1,Forbidden(),project_id=pid,project_revision=1)
        other_pid=self.service.save(self.other,self.content)[0]
        with self.assertRaises(ValueError):suggestions.propose(self.gid,self.did,'Siguiente',1,Forbidden(),project_id=other_pid)
    def test_combined_context_budget_prevents_send(self):
        pid=self.service.save(self.gid,dict(self.content,planned='😀'*9000,pending='',next_step=''))[0]
        suggestions=TemplateSuggestions(self.store)
        with self.assertRaises(ValueError):suggestions.context(self.gid,self.did,'Siguiente',1,project_id=pid)
