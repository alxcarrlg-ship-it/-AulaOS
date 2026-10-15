import copy
import json
import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile
from lxml import etree as E
from core import Store
from drafts import RevisionConflict
from lesson_packs import LessonPacks,validate
from lesson_export import export_presentation
from test_templates import fixture

SAMPLE={'title':'Our classroom','teacher_guide':'# Clase de 30 minutos\nPracticar vocabulario.\nRespuestas: desk, chair.','worksheet':'# My classroom\nWrite two things you can see.','slides':[{'title':'Our classroom','body':['English practice','Things around us'],'notes':'Presenta el objetivo en español.'},{'title':'Things we can see','body':['Look around the classroom.','Write two things you can see.','Share your words with a partner.'],'notes':'Respuestas posibles: desk, chair. Usa la guía para apoyar al grupo.'},{'title':'A sentence about my classroom','body':['I can see a desk.','Write your own sentence.','Read it to your partner.'],'notes':'Cierre: pide una oración y comprueba el uso de a/an.'}]}
class LessonTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.store=Store(self.root/'db.sqlite3');self.gid=self.store.group('Escuela','A');self.other=self.store.group('Escuela','B');self.service=LessonPacks(self.store)
        path=self.root/'template.docx';fixture(path,3);tid=self.service.templates.import_file(self.gid,path,'Formato');self.did=self.service.templates.create(self.gid,tid,'Clase')
    def tearDown(self):self.store.close();self.tmp.cleanup()
    def generate(self):
        class Fake:
            def respond(self,messages):return json.dumps(SAMPLE)
        return self.service.generate(self.gid,self.did,1,'Clase de inglés, 30 minutos',Fake())
    def test_source_snapshot_and_unchanged_planning(self):
        pid=self.generate();row=self.service.get(self.gid,pid)
        self.assertEqual(row['source_revision'],1);self.assertEqual(row['data'],SAMPLE)
        self.assertEqual(self.service.templates.document(self.gid,self.did)['revision'],1)
        self.assertIn('fields',json.loads(row['source_json']))
    def test_scope(self):
        pid=self.generate()
        with self.assertRaises(ValueError):self.service.get(self.other,pid)
        with self.assertRaises(ValueError):self.service.save(self.other,pid,SAMPLE,1)
        with self.assertRaises(ValueError):self.service.context(self.other,self.did,1,'Clase')
    def test_edit_history_and_conflict(self):
        pid=self.generate();edited=copy.deepcopy(SAMPLE);edited['worksheet']='Actividad corregida'
        self.assertEqual(self.service.save(self.gid,pid,edited,1),2)
        self.assertEqual(self.service.get(self.gid,pid,1)['data'],SAMPLE)
        with self.assertRaises(RevisionConflict):self.service.save(self.gid,pid,SAMPLE,1)
        self.assertEqual(self.service.save(self.gid,pid,edited,2),2)
    def test_invalid_content_rejected(self):
        for key,value in [('slides',[]),('teacher_guide',''),('title','x'*101)]:
            with self.assertRaises(ValueError):validate(dict(SAMPLE,**{key:value}))
        data=copy.deepcopy(SAMPLE);data['slides'][0]['body']=['x'*151]
        with self.assertRaises(ValueError):validate(data)
    def test_context_privacy_and_limits(self):
        self.store.add_student(self.gid,'ALUMNO_SECRETO')
        _,payload=self.service.context(self.gid,self.did,1,'Clase');self.assertNotIn('ALUMNO_SECRETO',json.dumps(payload))
        with self.assertRaises(ValueError):self.service.context(self.gid,self.did,1,'x'*6001)
        with self.assertRaises(RevisionConflict):self.service.context(self.gid,self.did,99,'Clase')
    def test_malformed_provider_does_not_save(self):
        class Bad:
            def respond(self,messages):return '{'
        with self.assertRaises(ValueError):self.service.generate(self.gid,self.did,1,'Clase',Bad())
        self.assertEqual(self.service.list(self.gid,self.did),[])
    def test_pptx_native_text_notes_relationships_and_no_overwrite(self):
        path=self.root/'slides.pptx';export_presentation(SAMPLE,'Planeación #1 v1',path)
        with ZipFile(path) as z:
            ns={'a':'http://schemas.openxmlformats.org/drawingml/2006/main'}
            for i,slide in enumerate(SAMPLE['slides'],1):
                root=E.fromstring(z.read(f'ppt/slides/slide{i}.xml'));texts=root.xpath('//a:t/text()',namespaces=ns)
                self.assertEqual(texts,[slide['title']]+slide['body'])
                notes=z.read(f'ppt/notesSlides/notesSlide{i}.xml').decode();self.assertIn('Planeación #1 v1',notes)
                rels=z.read(f'ppt/notesSlides/_rels/notesSlide{i}.xml.rels').decode();self.assertIn(f'/slide{i}.xml',rels)
            for name in z.namelist():
                if name.endswith(('.xml','.rels')):E.fromstring(z.read(name))
        before=path.read_bytes()
        with self.assertRaises(FileExistsError):export_presentation(SAMPLE,'Otro',path)
        self.assertEqual(path.read_bytes(),before)
