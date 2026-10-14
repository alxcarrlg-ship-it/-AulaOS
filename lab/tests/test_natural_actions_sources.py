import json
import tempfile
from pathlib import Path
import unittest
from core import Store,today
from actions import Actions
from natural_actions import NaturalActions
from templates import Templates
from template_suggestions import TemplateSuggestions
from test_templates import fixture
from materials import Materials

class Fake:
    def __init__(self,payload,callback=None):self.payload=payload;self.callback=callback
    def respond(self,messages):
        if self.callback:self.callback(messages)
        return json.dumps(self.payload,ensure_ascii=False)

class NaturalTest(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.store=Store(self.root/'db.sqlite3')
        self.gid=self.store.group('Escuela','1A');self.other=self.store.group('Otra','1B');self.sid=self.store.add_student(self.gid,'Ana Pérez')
        self.service=NaturalActions(self.store)
    def tearDown(self):self.store.close();self.tmp.cleanup()
    def event(self,query='Ana'):
        return {'kind':'event','data':{'student_query':query,'detail':'Participó en lectura','day':today()},'notes':'Revisar nombre y hechos.'}
    def test_task_review_before_write(self):
        result=self.service.propose(self.gid,'Recuérdame revisar cuadernos',Fake({'kind':'task','data':{'title':'Revisar cuadernos','due':None},'notes':'Pendiente sin alarma.'}))
        self.assertEqual(self.store.tasks(),[]);aid=result['action_id'];self.assertIn('Petición:',self.service.actions.preview(self.gid,aid))
        first=self.service.actions.resolve(self.gid,aid,True);self.assertEqual(self.service.actions.resolve(self.gid,aid,True),first);self.assertEqual(len(self.store.tasks()),1)
    def test_unique_name_resolved_locally(self):
        result=self.service.propose(self.gid,'Registra que Ana participó',Fake(self.event()))
        self.assertEqual(self.store.events(self.sid),[]);self.service.actions.resolve(self.gid,result['action_id'],True)
        self.assertEqual(self.store.events(self.sid)[0]['detail'],'Participó en lectura')
    def test_ambiguous_name_requests_clarification(self):
        self.store.add_student(self.gid,'Ana López');result=self.service.propose(self.gid,'Anota que Ana participó',Fake(self.event()))
        self.assertIsNone(result['action_id']);self.assertIn('Ana López',result['clarification']);self.assertEqual(self.service.actions.list(self.gid),[])
    def test_partial_word_is_not_student_identity(self):
        result=self.service.propose(self.gid,'Anota que An participó',Fake(self.event('An')))
        self.assertIsNone(result['action_id'])
    def test_model_cannot_invent_target(self):
        with self.assertRaises(ValueError):self.service.propose(self.gid,'Registra que Pedro participó',Fake(self.event()))
        self.assertEqual(self.service.actions.list(self.gid),[])
    def test_crossgroup_id_not_accepted(self):
        other_sid=self.store.add_student(self.other,'Juan')
        result=self.service.propose(self.gid,f'Anota para #{other_sid} que participó',Fake(self.event(f'#{other_sid}')))
        self.assertIsNone(result['action_id'])
    def test_only_request_and_date_sent(self):
        def check(messages):
            body=json.dumps(messages,ensure_ascii=False)
            self.assertNotIn('Ana Pérez',body);self.assertNotIn('Escuela',body)
            self.assertEqual(set(json.loads(messages[-1]['content'])),{'request','local_date'})
        self.service.propose(self.gid,'Prepara un borrador',Fake({'kind':'clarify','data':{},'notes':'¿Sobre qué tema?'},check))
    def test_disallowed_operation_and_extra_fields(self):
        for payload in ({'kind':'delete','data':{},'notes':''},{'kind':'task','data':{'title':'X','due':None,'group_id':self.other},'notes':''},{'kind':'task','data':{'title':'X','due':'mañana'},'notes':''}):
            with self.assertRaises(ValueError):self.service.propose(self.gid,'Petición',Fake(payload))
        self.assertEqual(self.service.actions.list(self.gid),[])
    def test_draft_requires_confirmation(self):
        result=self.service.propose(None,'Crea borrador sobre lectura',Fake({'kind':'draft','data':{'title':'Lectura','content':'Texto | con separadores'},'notes':'Propuesta.'}))
        self.assertEqual(self.service.actions.drafts.list(None),[])
        did=self.service.actions.resolve(None,result['action_id'],True)
        self.assertEqual(self.service.actions.drafts.get(None,did)['content'],'Texto | con separadores')
    def test_stale_identity_apply_blocked(self):
        result=self.service.propose(self.gid,'Anota que Ana participó',Fake(self.event()))
        with self.store.con:self.store.con.execute('UPDATE students SET active=0 WHERE id=?',(self.sid,))
        with self.assertRaises(ValueError):self.service.actions.resolve(self.gid,result['action_id'],True)
    def test_offline_parser_still_works_after_migration(self):
        self.service.actions.propose(self.gid,'/tarea Revisar')
        row=self.service.actions.list(self.gid)[0];self.assertEqual(row['source'],'local');self.service.actions.resolve(self.gid,row['id'],True)
        self.assertEqual(len(self.store.tasks()),1)

class SourceTest(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.store=Store(self.root/'db.sqlite3')
        self.gid=self.store.group('A','1');self.other=self.store.group('B','1');self.templates=Templates(self.store)
        path=self.root/'template.docx';fixture(path,3);tid=self.templates.import_file(self.gid,path,'Formato');self.did=self.templates.create(self.gid,tid,'Doc')
        schema=json.loads(self.templates.get(self.gid,tid)['schema_json']);self.key=next(f['id'] for f in schema['fields'] if f['text']=='Completar')
        self.service=TemplateSuggestions(self.store);self.materials=Materials(self.store)
        self.mid=self.materials.save(self.gid,'Guía','Contenido de la guía')
    def tearDown(self):self.store.close();self.tmp.cleanup()
    def test_selected_sources_only_and_saved_copy(self):
        ignored=self.materials.save(self.gid,'No seleccionada','NO_ENVIAR')
        def check(messages):
            payload=json.loads(messages[-1]['content']);self.assertEqual(len(payload['sources']),1);self.assertNotIn('NO_ENVIAR',json.dumps(messages))
        sid=self.service.propose(self.gid,self.did,'Usa la guía',1,Fake({'changes':{self.key:f'Actividad [M{self.mid}]'},'notes':f'Adaptación de [M{self.mid}].'},check),[self.mid])
        sources=json.loads(self.service.get(self.gid,sid)['sources_json']);self.assertEqual(sources[0]['text'],'Contenido de la guía')
        self.service.resolve(self.gid,sid,True);self.assertIn(f'[M{self.mid}]',self.templates.document(self.gid,self.did)['changes'])
    def test_crossgroup_sources_rejected_before_call(self):
        mid=self.materials.save(self.other,'Ajeno','No compartir')
        def fail(messages):self.fail('Provider must not be called')
        with self.assertRaises(ValueError):self.service.propose(self.gid,self.did,'Objetivo',1,Fake({},fail),[mid])
    def test_unknown_citations_rejected(self):
        with self.assertRaises(ValueError):self.service.propose(self.gid,self.did,'Objetivo',1,Fake({'changes':{self.key:'Texto [M99999]'},'notes':''}),[self.mid])
        self.assertEqual(self.templates.document(self.gid,self.did)['revision'],1)
    def test_default_no_sources(self):
        _,_,messages=self.service.context(self.gid,self.did,'Objetivo',1)
        self.assertEqual(json.loads(messages[-1]['content'])['sources'],[])
    def test_provenance_survives_restart(self):
        sid=self.service.propose(self.gid,self.did,'Objetivo',1,Fake({'changes':{self.key:'Actividad'},'notes':'Revisar.'}),[self.mid])
        other=Store(self.root/'db.sqlite3')
        try:self.assertEqual(json.loads(TemplateSuggestions(other).get(self.gid,sid)['sources_json'])[0]['source'],f'M{self.mid}')
        finally:other.close()
