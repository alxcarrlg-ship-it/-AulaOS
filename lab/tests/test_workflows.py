import json
import tempfile
import unittest
from pathlib import Path
from core import Store
from workflows import Workflows,is_workflow
from test_templates import fixture

class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.store=Store(self.root/'db');self.gid=self.store.group('A','1');self.other=self.store.group('B','1');self.service=Workflows(self.store)
        self.content=dict(title='Our voices',planned='Plan',completed='',pending='Cartel',next_step='Ensayo',documents=[])
        self.pid,_=self.service.projects.save(self.gid,self.content)
        p=self.root/'source.docx';fixture(p);tid=self.service.templates.import_file(self.gid,p,'Formato');self.did=self.service.templates.create(self.gid,tid,'Semana uno')
    def tearDown(self):self.store.close();self.tmp.cleanup()
    def fake(self,steps,clarification=''):
        class Fake:
            def respond(inner,messages):self.messages=messages;return json.dumps(dict(steps=steps,clarification=clarification))
        return Fake()
    def test_local_route_and_no_project_mutation(self):
        wid,_=self.service.prepare(self.gid,f'proyecto #{self.pid}')
        step=self.service.step(self.gid,wid,0);self.assertEqual(step['destination']['id'],self.pid)
        self.assertEqual(self.service.projects.get(self.gid,self.pid)['revision'],1)
        self.assertTrue(is_workflow('/trabajar proyecto #1'));self.assertFalse(is_workflow('/trabajarotro'))
    def test_natural_multiple_steps_exact_targets_no_records_sent(self):
        goal='Abre Our voices y prepara materiales de Semana uno'
        provider=self.fake([dict(tool='project',target='Our voices',request='Revisar avance'),dict(tool='lesson',target='Semana uno',request='Preparar actividades')])
        wid,_=self.service.prepare(self.gid,goal,provider)
        self.assertEqual(len(self.service.get(self.gid,wid)['steps']),2)
        self.assertEqual(self.messages[-1]['content'],goal);self.assertNotIn('Cartel',json.dumps(self.messages))
    def test_cross_group_and_invented_destination(self):
        provider=self.fake([dict(tool='project',target='Our voices',request='Abrir')])
        with self.assertRaises(ValueError):self.service.prepare(self.gid,'Abre otro',provider)
        with self.assertRaises(ValueError):self.service.prepare(self.other,'Abre Our voices',provider)
        wid,_=self.service.prepare(self.gid,f'proyecto #{self.pid}')
        with self.assertRaises(ValueError):self.service.get(self.other,wid)
        with self.assertRaises(ValueError):self.service.step(self.other,wid,0)
    def test_stale_project_blocks_navigation(self):
        wid,_=self.service.prepare(self.gid,f'evidencias #{self.pid}')
        self.service.projects.save(self.gid,dict(self.content,pending='Cambio'),self.pid,1)
        with self.assertRaisesRegex(ValueError,'cambió'):self.service.step(self.gid,wid,0)
    def test_duplicate_titles_require_id(self):
        self.service.projects.save(self.gid,self.content)
        with self.assertRaises(ValueError):self.service.prepare(self.gid,'Abre Our voices',self.fake([dict(tool='project',target='Our voices',request='Abrir')]))
        self.assertIsNotNone(self.service.prepare(self.gid,f'proyecto #{self.pid}')[0])
    def test_clarification_and_rejected_tools_never_save(self):
        self.assertEqual(self.service.prepare(self.gid,'Prepara la clase',self.fake([], '¿Qué planeación?')),(None,'¿Qué planeación?'))
        for step in [dict(tool='shell',target=None,request='rm'),dict(tool='resources',target='#1',request='Buscar')]:
            with self.assertRaises(ValueError):self.service.prepare(self.gid,'Prepara #1',self.fake([step]))
        self.assertEqual(self.service.list(self.gid),[])
    def test_end_to_end_route_to_saved_planning_and_export(self):
        wid,_=self.service.prepare(self.gid,f'planeación #{self.did}');step=self.service.step(self.gid,wid,0)
        doc=self.service.templates.document(self.gid,step['destination']['id']);template=self.service.templates.get(self.gid,doc['template_id']);key=json.loads(template['schema_json'])['fields'][0]['id']
        self.service.templates.save(self.gid,self.did,{key:'Texto revisado por el docente'},doc['revision'])
        path=self.root/'export.docx';self.service.templates.export(self.gid,self.did,path)
        self.assertTrue(path.exists())
        with self.assertRaises(ValueError):self.service.step(self.gid,wid,0)
