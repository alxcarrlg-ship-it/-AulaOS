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


    def test_selective_edited_acceptance_and_audit(self):
        other=next(f['id'] for f in self.schema['fields'] if f['id']!=self.key)
        payload={self.key:'Idea IA',other:'No aceptar'}
        class Fake:
            def respond(self,messages):return json.dumps({'changes':payload,'notes':''})
        sid=self.service.propose(self.gid,self.did,'Objetivo',1,Fake())
        self.assertEqual(self.service.resolve(self.gid,sid,True,[self.key],{self.key:'Mi adaptación'}),2)
        doc=json.loads(self.templates.document(self.gid,self.did)['changes'])
        self.assertEqual(doc,{self.key:'Mi adaptación'})
        row=self.service.get(self.gid,sid)
        self.assertEqual(json.loads(row['changes']),payload)
        self.assertEqual(json.loads(row['applied_changes']),doc)
        self.assertEqual(self.service.resolve(self.gid,sid,True,[self.key],{self.key:'Mi adaptación'}),2)
        with self.assertRaises(ValueError):self.service.resolve(self.gid,sid,True,[self.key],{self.key:'Otra edición'})
        self.assertEqual(self.templates.document(self.gid,self.did)['revision'],2)

    def test_invalid_review_does_not_resolve_or_write(self):
        sid=self.propose()
        for keys,edits in [([],{}),(['unknown'],{}),([self.key,self.key],{}),([self.key],{'unknown':'x'}),([self.key],{self.key:None}),([self.key],{self.key:'x\x00'}),([self.key],{self.key:'x'*120001}),([self.key],{self.key:'Cita [M9999]'})]:
            with self.subTest(keys=keys,kind=str(edits)[:50]):
                with self.assertRaises(ValueError):self.service.resolve(self.gid,sid,True,keys,edits)
                self.assertEqual(self.templates.document(self.gid,self.did)['revision'],1)
                self.assertEqual(self.service.get(self.gid,sid)['state'],'pending')
                self.assertIsNone(self.service.get(self.gid,sid)['applied_changes'])

    def test_legacy_applied_audit_and_migration(self):
        sid=self.propose();self.service.resolve(self.gid,sid,True)
        self.store.con.execute('UPDATE template_suggestions SET applied_changes=NULL WHERE id=?',(sid,));self.store.con.commit()
        TemplateSuggestions(self.store);TemplateSuggestions(self.store)
        self.assertEqual(self.service.resolve(self.gid,sid,True,[self.key]),2)

    def test_selective_export_retains_original_other_fields(self):
        sid=self.propose();self.service.resolve(self.gid,sid,True,[self.key],{self.key:'Texto revisado'})
        path=self.root/'reviewed.docx';self.templates.export(self.gid,self.did,path)
        from templates import inspect_template
        fields=inspect_template(path.read_bytes())['fields']
        original={f['id']:f['text'] for f in self.schema['fields']}
        for field in fields:self.assertEqual(field['text'],'Texto revisado' if field['id']==self.key else original[field['id']])


    def test_review_draft_survives_reopen_without_applying(self):
        sid=self.propose();self.service.save_review(self.gid,sid,[],{self.key:'Mi texto pendiente'})
        other=Store(self.root/'db.sqlite3')
        try:
            draft=TemplateSuggestions(other).review_draft(self.gid,sid)
            self.assertEqual(draft['selected'],[]);self.assertEqual(draft['values'],{self.key:'Mi texto pendiente'})
        finally:other.close()
        self.assertEqual(self.templates.document(self.gid,self.did)['revision'],1)
        self.assertEqual(self.service.get(self.gid,sid)['state'],'pending')

    def test_review_draft_conflicts_preserve_latest(self):
        sid=self.propose();self.service.save_review(self.gid,sid,[self.key],{self.key:'Uno'})
        with self.assertRaises(RevisionConflict):self.service.save_review(self.gid,sid,[],{self.key:'Dos'},0)
        with self.assertRaises(RevisionConflict):self.service.resolve(self.gid,sid,True,[self.key],{self.key:'Dos'},0)
        self.assertEqual(self.service.review_draft(self.gid,sid)['values'][self.key],'Uno')
        self.assertEqual(self.service.resolve(self.gid,sid,True,[self.key],{self.key:'Uno'},1),2)

    def test_review_draft_scope_and_invalid_payload(self):
        sid=self.propose()
        with self.assertRaises(ValueError):self.service.review_draft(self.other,sid)
        with self.assertRaises(ValueError):self.service.save_review(self.other,sid,[],{self.key:'x'})
        for keys,values in [(['unknown'],{self.key:'x'}),([self.key,self.key],{self.key:'x'}),([],{}),([],{self.key:None}),([],{self.key:'x\x00'})]:
            with self.assertRaises(ValueError):self.service.save_review(self.gid,sid,keys,values)
        self.assertIsNone(self.service.review_draft(self.gid,sid))

    def test_review_draft_resolved_is_readable_but_not_writable(self):
        sid=self.propose();self.service.save_review(self.gid,sid,[],{self.key:'Pendiente'})
        self.service.resolve(self.gid,sid,False)
        self.assertEqual(self.service.review_draft(self.gid,sid)['values'][self.key],'Pendiente')
        with self.assertRaises(ValueError):self.service.save_review(self.gid,sid,[],{self.key:'Otro'},1)

    def test_review_draft_stale_document_keeps_work_without_applying(self):
        sid=self.propose();self.templates.save(self.gid,self.did,{self.key:'Nueva versión'},1)
        self.service.save_review(self.gid,sid,[self.key],{self.key:'Revisión pendiente'})
        with self.assertRaises(RevisionConflict):self.service.resolve(self.gid,sid,True,[self.key],{self.key:'Revisión pendiente'},1)
        self.assertEqual(self.service.review_draft(self.gid,sid)['values'][self.key],'Revisión pendiente')
        self.assertEqual(json.loads(self.templates.document(self.gid,self.did)['changes'])[self.key],'Nueva versión')

    def test_profile_school_scope_and_teacher_variants(self):
        profiles=self.service.profiles
        one=profiles.save(self.gid,'Planeación','Docente A','Actividades TR/Ss')
        two=profiles.save(self.gid,'Planeación','Docente B','Preguntas abiertas')
        sibling=self.store.group('Escuela A','Otro grupo')
        self.assertEqual({r['id'] for r in profiles.list(sibling)},{one,two})
        self.assertEqual(profiles.list(self.other),[])
        with self.assertRaises(ValueError):profiles.get(self.other,one)
        with self.assertRaises(ValueError):profiles.save(self.other,'X','Y','Z',one,1)

    def test_profile_opt_in_and_snapshot(self):
        profiles=self.service.profiles;pid=profiles.save(self.gid,'Mi formato','Docente','Requisito privado')
        _,_,messages=self.service.context(self.gid,self.did,'Clase',1)
        self.assertNotIn('Requisito privado',json.dumps(messages))
        sid=self.service.propose(self.gid,self.did,'Clase',1,self.provider(),profile_id=pid,profile_revision=1)
        profiles.save(self.gid,'Mi formato','Docente','Nuevo requisito',pid,1)
        saved=json.loads(self.service.get(self.gid,sid)['profile_json'])
        self.assertEqual(saved['requirements'],'Requisito privado');self.assertEqual(saved['revision'],1)
        self.assertEqual(self.templates.document(self.gid,self.did)['revision'],1)

    def test_profile_conflicts_stop_before_provider(self):
        profiles=self.service.profiles;pid=profiles.save(self.gid,'Formato','Docente','Uno')
        profiles.save(self.gid,'Formato','Docente','Dos',pid,1)
        with self.assertRaises(RevisionConflict):profiles.save(self.gid,'Formato','Docente','Tres',pid,1)
        class Forbidden:
            def respond(self,messages):raise AssertionError('No debe enviarse')
        with self.assertRaises(RevisionConflict):self.service.propose(self.gid,self.did,'Clase',1,Forbidden(),profile_id=pid,profile_revision=1)
        self.assertEqual(profiles.get(self.gid,pid)['requirements'],'Dos')

    def test_profile_validation_and_context_budget(self):
        profiles=self.service.profiles
        for name,teacher,requirements in [('', 'Docente','X'),('X','','Y'),('X','Y',''),('X','Y','a'*6001)]:
            with self.assertRaises(ValueError):profiles.save(self.gid,name,teacher,requirements)
        pid=profiles.save(self.gid,'Formato','Docente','a'*6000)
        with patch('template_suggestions.MAX_CONTEXT',1000):
            with self.assertRaises(ValueError):self.service.context(self.gid,self.did,'Clase',1,profile_id=pid)

    def test_profile_reopen_and_no_fixed_structure(self):
        pid=self.service.profiles.save(self.gid,'Libre','Docente','Usar el formato de la escuela; no exigir seis columnas.')
        other=Store(self.root/'db.sqlite3')
        try:self.assertEqual(TemplateSuggestions(other).profiles.get(self.gid,pid)['name'],'Libre')
        finally:other.close()
        _,schema,messages=self.service.context(self.gid,self.did,'Clase',1,profile_id=pid)
        self.assertEqual(schema['tables'][0]['columns'],3)
        self.assertEqual(json.loads(messages[-1]['content'])['teaching_profile']['id'],pid)

    def test_required_details_block_before_provider_and_allow_answers(self):
        pid=self.service.profiles.save(self.gid,'Formato','Docente','Requisitos',questions=['Sesiones','Producto'])
        class Forbidden:
            def respond(self,messages):raise AssertionError('No debe consumir API')
        with self.assertRaises(ValueError):self.service.propose(self.gid,self.did,'Clase',1,Forbidden(),profile_id=pid)
        sid=self.service.propose(self.gid,self.did,'Clase\nSesiones: 3\nProducto: Cartel',1,self.provider(),profile_id=pid)
        self.assertEqual(json.loads(self.service.get(self.gid,sid)['profile_json'])['questions'],['Sesiones','Producto'])

    def test_required_details_validation_and_preservation(self):
        profiles=self.service.profiles
        for questions in [['X','x'],['Dato:'],['a\nb'],['X']*9,[None]]:
            with self.assertRaises(ValueError):profiles.save(self.gid,'Formato','Docente','Texto',questions=questions)
        pid=profiles.save(self.gid,'Formato','Docente','Texto',questions=['Sesiones'])
        profiles.save(self.gid,'Formato','Docente','Otro texto',pid,1)
        self.assertEqual(profiles.snapshot(self.gid,pid)['questions'],['Sesiones'])
        profiles.save(self.gid,'Formato','Docente','Otro texto',pid,2,questions=[])
        self.assertEqual(profiles.snapshot(self.gid,pid)['questions'],[])

    def test_missing_details_are_explicit_not_inferred(self):
        from teaching_profiles import missing_details
        profile={'questions':['Sesiones','Producto']}
        self.assertEqual(missing_details(profile,'Haré tres sesiones con cartel'),['Sesiones','Producto'])
        self.assertEqual(missing_details(profile,'SESIONES: 3\nProducto: pendiente'),['Producto'])
        self.assertEqual(missing_details(profile,'Sesiones: 3\nProducto: No aplica porque será práctica oral'),[])
        self.assertEqual(missing_details(None,'Clase'),[])
