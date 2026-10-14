import json
import sqlite3
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch
from core import Store
from templates import Templates
from drafts import RevisionConflict
from template_suggestions import TemplateSuggestions,decode_proposal
from test_templates import fixture

class SuggestionsTest(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.store=Store(self.root/'db.sqlite3')
        self.gid=self.store.group('Escuela A','1');self.other=self.store.group('Escuela B','2');self.templates=Templates(self.store)
        self.path=self.root/'source.docx';fixture(self.path,3);tid=self.templates.import_file(self.gid,self.path,'Propio')
        self.did=self.templates.create(self.gid,tid,'Semana');self.schema=json.loads(self.templates.get(self.gid,tid)['schema_json'])
        self.key=next(f['id'] for f in self.schema['fields'] if f['text']=='Completar');self.service=TemplateSuggestions(self.store)
    def tearDown(self):self.store.close();self.tmp.cleanup()
    def provider(self,value='Actividad sugerida'):
        key=self.key
        class Fake:
            def respond(self,messages):return json.dumps({'changes':{key:value},'notes':'Revisar nivel.'})
        return Fake()
    def propose(self):return self.service.propose(self.gid,self.did,'Preparar una clase',1,self.provider())
    def test_preview_and_apply_once(self):
        sid=self.propose();self.assertEqual(self.templates.document(self.gid,self.did)['revision'],1)
        diff=self.service.review(self.gid,sid);self.assertEqual(diff[0]['before'],'Completar');self.assertEqual(diff[0]['after'],'Actividad sugerida')
        self.assertEqual(self.service.resolve(self.gid,sid,True),2);self.assertEqual(self.service.resolve(self.gid,sid,True),2)
        self.assertEqual(self.templates.document(self.gid,self.did,1)['changes'],'{}')
    def test_discard_persists(self):
        sid=self.propose();self.service.resolve(self.gid,sid);other=Store(self.root/'db.sqlite3')
        try:
            with self.assertRaises(ValueError):TemplateSuggestions(other).resolve(self.gid,sid,True)
        finally:other.close()
        self.assertEqual(self.templates.document(self.gid,self.did)['revision'],1)
    def test_scope(self):
        sid=self.propose()
        for fn,args in [(self.service.get,(self.other,sid)),(self.service.review,(self.other,sid)),(self.service.resolve,(self.other,sid)),(self.service.list,(self.other,self.did))]:
            with self.assertRaises(ValueError):fn(*args)
    def test_stale(self):
        sid=self.propose();self.templates.save(self.gid,self.did,{self.key:'Edición manual'},1)
        with self.assertRaises(RevisionConflict):self.service.resolve(self.gid,sid,True)
        self.assertEqual(json.loads(self.templates.document(self.gid,self.did)['changes'])[self.key],'Edición manual');self.assertEqual(self.service.get(self.gid,sid)['state'],'pending')
    def test_changed_during_request(self):
        parent=self
        class Concurrent:
            def respond(self,messages):
                parent.templates.save(parent.gid,parent.did,{parent.key:'Nueva versión'},1)
                return parent.provider().respond(messages)
        sid=self.service.propose(self.gid,self.did,'Objetivo',1,Concurrent())
        with self.assertRaises(RevisionConflict):self.service.resolve(self.gid,sid,True)
    def test_invalid_payloads(self):
        for raw in ('no JSON','{"changes":',json.dumps({'changes':{'unknown':'X'},'notes':''}),json.dumps({'changes':{self.key:1},'notes':''}),'{"changes":{},"changes":{},"notes":""}'):
            class Fake:
                def respond(self,messages):return raw
            with self.assertRaises(ValueError):self.service.propose(self.gid,self.did,'Objetivo',1,Fake())
        self.assertEqual(self.service.list(self.gid,self.did),[]);self.assertEqual(self.templates.document(self.gid,self.did)['revision'],1)
    def test_empty_changes(self):
        class Fake:
            def respond(self,messages):return '{"changes":{},"notes":"Falta el nivel del grupo."}'
        sid=self.service.propose(self.gid,self.did,'Objetivo',1,Fake());self.assertEqual(self.service.review(self.gid,sid),[])
        with self.assertRaises(ValueError):self.service.resolve(self.gid,sid,True)
    def test_context_private_records_excluded(self):
        self.store.add_student(self.gid,'ALUMNO_SECRETO');self.store.create_task('TAREA_SECRETA',self.other)
        _,_,messages=self.service.context(self.gid,self.did,'Objetivo',1);text=json.dumps(messages)
        for secret in ('ALUMNO_SECRETO','TAREA_SECRETA',str(self.root),'Escuela B'):self.assertNotIn(secret,text)
        self.assertIn('Completar',text)
    def test_size_limit_before_provider(self):
        class Forbidden:
            def respond(self,messages):raise AssertionError('Must not call')
        with patch('template_suggestions.MAX_CONTEXT',1):
            with self.assertRaises(ValueError):self.service.propose(self.gid,self.did,'Objetivo',1,Forbidden())
    def test_existing_edits_preserved(self):
        other=next(f['id'] for f in self.schema['fields'] if f['id']!=self.key);self.templates.save(self.gid,self.did,{other:'Mi texto'},1)
        sid=self.service.propose(self.gid,self.did,'Objetivo',2,self.provider());self.service.resolve(self.gid,sid,True)
        changes=json.loads(self.templates.document(self.gid,self.did)['changes']);self.assertEqual(changes[other],'Mi texto');self.assertEqual(changes[self.key],'Actividad sugerida')
    def test_atomic_rollback(self):
        sid=self.propose();self.store.con.executescript("CREATE TRIGGER fail_suggestion BEFORE UPDATE ON template_suggestions BEGIN SELECT RAISE(ABORT,'failure'); END;")
        with self.assertRaises(sqlite3.Error):self.service.resolve(self.gid,sid,True)
        self.assertEqual(self.templates.document(self.gid,self.did)['revision'],1);self.assertEqual(self.service.get(self.gid,sid)['state'],'pending')
    def test_varied_columns(self):
        for columns in (6,8):
            fixture(self.path,columns);tid=self.templates.import_file(self.gid,self.path,str(columns));did=self.templates.create(self.gid,tid,'Semana')
            _,schema,messages=self.service.context(self.gid,did,'Objetivo',1);self.assertEqual(schema['tables'][0]['columns'],columns)
            fields=json.loads(messages[1]['content'])['fields'];key=next(f['id'] for f in fields if f['text']=='Completar')
            parsed=decode_proposal(json.dumps({'changes':{key:'Actividad'},'notes':''}),schema);self.assertEqual(parsed['changes'][key],'Actividad')

    def test_proposal_export_material_chat_flow(self):
        from chat import ChatService
        sid=self.propose();self.service.resolve(self.gid,sid,True)
        path=self.root/'prepared.docx';self.templates.export(self.gid,self.did,path)
        chat=ChatService(self.store);mid=chat.materials.import_file(self.gid,path)
        self.assertIn('Actividad sugerida',chat.materials.get(self.gid,mid)['content'])
        parent=self
        class FakeChat:
            source='online'
            def respond(self,messages):
                parent.assertIn('Actividad sugerida',json.dumps(messages,ensure_ascii=False))
                return 'Documento disponible para revisión.'
        answer=chat.send(self.gid,'Revisa este documento',FakeChat(),include_records=False,material_ids=[mid])
        self.assertIn('revisión',answer)
