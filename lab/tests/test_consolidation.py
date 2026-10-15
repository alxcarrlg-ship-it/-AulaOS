import copy
import json
import socket
import ssl
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock,patch
from urllib.error import URLError
from core import Store
from recovery import Recovery
from projects import Projects
from evidence import Evidence
from lesson_packs import LessonPacks
from template_suggestions import TemplateSuggestions
from teaching_profiles import TeachingProfiles
from online import OpenAIProvider,OnlineError,MeteredProvider
from voice import Transcriber
from test_templates import fixture
from test_lesson_packs import SAMPLE

class ConsolidationTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.store=Store(self.root/'db');self.gid=self.store.group('Escuela','A');self.other=self.store.group('Otra','B');self.recovery=Recovery(self.store)
        self.project=dict(title='Proyecto',planned='Plan',completed='',pending='Producto',next_step='Ensayo',documents=[])
        self.projects=Projects(self.store);self.pid,_=self.projects.save(self.gid,self.project)
        p=self.root/'source.docx';fixture(p);self.tid=self.recovery.templates.import_file(self.gid,p,'Formato');self.did=self.recovery.templates.create(self.gid,self.tid,'Clase')
    def tearDown(self):self.store.close();self.tmp.cleanup()
    def test_incomplete_project_recovery_preserves_approved_version(self):
        value=dict(self.project,title='',pending='Trabajo por terminar')
        self.recovery.put('p',self.gid,'project',self.pid,1,value)
        self.assertEqual(self.projects.get(self.gid,self.pid)['pending'],'Producto')
        self.recovery.put('new',self.gid,'project',None,0,value)
        self.assertEqual(self.recovery.list(self.gid,'project',None)[0]['payload'],value)
        with self.assertRaises(ValueError):self.recovery.put('bad',self.other,'project',self.pid,1,value)
    def test_evidence_new_and_existing_scoped_recovery(self):
        service=Evidence(self.store);sid=self.store.add_student(self.gid,'Alumno');other=self.store.add_student(self.other,'Ajeno')
        content=dict(title='Ensayo',day='2026-10-15',observation='Dos frases',next_step='',due='',status='Por revisar')
        payload=dict(content=dict(content,observation=''),student_id=sid,kind='Sin adjunto',source_id=None)
        self.recovery.put('new',self.gid,'evidence_new',self.pid,1,payload)
        self.assertEqual(service.list(self.gid,self.pid),[])
        with self.assertRaises(ValueError):self.recovery.put('bad',self.gid,'evidence_new',self.pid,1,dict(payload,student_id=other))
        eid=service.create(self.gid,self.pid,1,content);self.recovery.put('existing',self.gid,'evidence',eid,1,payload)
        self.assertEqual(service.get(self.gid,eid)['content']['observation'],'Dos frases')
    def test_lesson_recovery_incomplete_body_and_source_unchanged(self):
        class Fake:
            def respond(self,messages):return json.dumps(SAMPLE)
        service=LessonPacks(self.store);pid=service.generate(self.gid,self.did,1,'Clase',Fake())
        pending=copy.deepcopy(SAMPLE);pending['slides'][0]['body']=[]
        self.recovery.put('lesson',self.gid,'lesson',pid,1,pending)
        self.assertEqual(service.get(self.gid,pid)['data'],SAMPLE)
        with self.assertRaises(ValueError):self.recovery.put('foreign',self.other,'lesson',pid,1,pending)
    def test_review_recovery_preserves_selection_without_apply(self):
        service=TemplateSuggestions(self.store);key=json.loads(self.recovery.templates.get(self.gid,self.tid)['schema_json'])['fields'][0]['id']
        class Fake:
            def respond(self,messages):return json.dumps({'changes':{key:'Nuevo'},'notes':'Revisar'})
        sid=service.propose(self.gid,self.did,'Actualizar',1,Fake());value={'values':{key:'Corrección parcial'},'selected':[]}
        self.recovery.put('review',self.gid,'review',sid,0,value)
        self.assertEqual(self.recovery.templates.document(self.gid,self.did)['revision'],1)
        with self.assertRaises(ValueError):self.recovery.put('bad',self.gid,'review',sid,0,{'values':{'fake':'x'},'selected':[]})
        service.resolve(self.gid,sid,False)
        with self.assertRaises(ValueError):self.recovery.validate(self.gid,'review',sid,0,value)
    def test_profile_recovery_never_changes_current_requirements(self):
        profiles=TeachingProfiles(self.store);pid=profiles.save(self.gid,'Perfil','Docente','Requisitos')
        value=dict(name='',teacher='Docente',requirements='En edición',questions='')
        self.recovery.put('profile',self.gid,'profile',pid,1,value)
        self.assertEqual(profiles.get(self.gid,pid)['requirements'],'Requisitos')
        with self.assertRaises(ValueError):self.recovery.put('bad',self.other,'profile',pid,1,value)
    def test_context_measurement_does_not_bypass_actual_send_limit(self):
        service=TemplateSuggestions(self.store);mid=service.materials.save(self.gid,'Fuente','x'*15000)
        args=(self.gid,self.did,'a'*5000,1,[mid])
        _,_,messages=service.context(*args,enforce_limit=False)
        self.assertGreater(len(messages[-1]['content'].encode('utf-8')),18000)
        with self.assertRaises(ValueError):service.context(*args)
        self.assertEqual(service.list(self.gid,self.did),[])
    def test_timeout_security_and_network_classified_without_retry(self):
        cases=[(socket.timeout(),'timeout'),(URLError(socket.timeout()),'timeout'),(URLError(ssl.SSLError()),'security'),(URLError('network'),'connection')]
        for error,kind in cases:
            for module,call in [('online',lambda:OpenAIProvider('test')._http({})),('voice',lambda:Transcriber('test').http(b'x','audio/test'))]:
                opener=Mock();opener.open.side_effect=error
                with patch(module+'.build_opener',return_value=opener):
                    with self.assertRaises(OnlineError) as caught:call()
                self.assertEqual(caught.exception.kind,kind);self.assertEqual(opener.open.call_count,1)
