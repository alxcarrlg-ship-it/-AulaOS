import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from core import Store
from drafts import RevisionConflict
from clarifications import Clarifications,decode
from teaching_profiles import conflicting_details

class ClarificationsTest(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.db=Path(self.tmp.name)/'db.sqlite3';self.store=Store(self.db)
        self.gid=self.store.group('Escuela A','1');self.other=self.store.group('Escuela B','2')
        self.service=Clarifications(self.store)
        self.pid=self.service.profiles.save(self.gid,'Formato','Docente','Preferir tres sesiones',questions=['Sesiones'])
        self.goal='Prepara tres sesiones sobre animales.'
        self.report={'answers':[{'label':'Sesiones','value':'3','evidence':'tres sesiones'}],'issues':[]}
    def tearDown(self):self.store.close();self.tmp.cleanup()
    def provider(self,report=None):
        report=self.report if report is None else report
        class Fake:
            def respond(self,messages):return json.dumps(report)
        return Fake()
    def analyze(self,report=None):return self.service.analyze(self.gid,self.goal,self.provider(report),self.pid,1)
    def test_analysis_persists_without_mutating_requests(self):
        rid=self.analyze();row=self.service.get(self.gid,rid)
        self.assertEqual(row['goal'],self.goal)
        self.assertEqual(json.loads(row['report_json']),self.report)
        revised=self.service.suggested_request(self.gid,rid,self.goal,self.pid,1)
        self.assertEqual(revised,self.goal+'\nSesiones: 3')
        self.assertEqual(self.service.get(self.gid,rid)['goal'],self.goal)
        other=Store(self.db)
        try:self.assertEqual(Clarifications(other).latest(self.gid)['id'],rid)
        finally:other.close()
    def test_scope(self):
        rid=self.analyze()
        with self.assertRaises(ValueError):self.service.get(self.other,rid)
        with self.assertRaises(ValueError):self.service.context(self.other,self.goal,self.pid,1)
        self.assertIsNone(self.service.latest(self.other))
    def test_excludes_records_history_and_materials(self):
        self.store.add_student(self.gid,'ALUMNO_SECRETO');self.store.create_task('TAREA_SECRETA',self.gid)
        _,messages=self.service.context(self.gid,self.goal,self.pid,1)
        payload=json.loads(messages[-1]['content']);self.assertEqual(set(payload),{'request','profile'})
        self.assertNotIn('ALUMNO_SECRETO',json.dumps(messages));self.assertNotIn('TAREA_SECRETA',json.dumps(messages))
    def test_invalid_reports_do_not_persist(self):
        invalid=[{}, {'answers':{},'issues':[]}, {'answers':[{'label':'Otro','value':'3','evidence':'tres sesiones'}],'issues':[]},
            {'answers':[{'label':'Sesiones','value':'3','evidence':'cuatro sesiones'}],'issues':[]},
            {'answers':[{'label':'Sesiones','value':'3\nProducto: cartel','evidence':'tres sesiones'}],'issues':[]},
            {'answers':[],'issues':[{'question':'¿Cuántas?','evidence':['No está aquí']}]}]
        for report in invalid:
            with self.subTest(report=report):
                with self.assertRaises(ValueError):self.analyze(report)
        self.assertIsNone(self.service.latest(self.gid))
    def test_duplicate_keys_and_oversize_response(self):
        profile=self.service.profiles.snapshot(self.gid,self.pid)
        for text in ['{"answers":[],"answers":[],"issues":[]}','x'*40001,'```json\n{}\n```']:
            with self.assertRaises(ValueError):decode(text,self.goal,profile)
    def test_changed_goal_or_profile_blocks_adoption(self):
        rid=self.analyze()
        with self.assertRaises(ValueError):self.service.suggested_request(self.gid,rid,'Otro tema',self.pid,1)
        self.service.profiles.save(self.gid,'Formato','Docente','Cinco sesiones',self.pid,1)
        with self.assertRaises(RevisionConflict):self.service.suggested_request(self.gid,rid,self.goal,self.pid,1)
        with self.assertRaises(ValueError):self.service.suggested_request(self.gid,rid,self.goal,self.pid,2)
    def test_issues_need_resolution_before_adoption(self):
        report={'answers':[],'issues':[{'question':'¿Se mantiene la preferencia de tres sesiones?','evidence':['Preferir tres sesiones']} ]}
        rid=self.analyze(report)
        with self.assertRaises(ValueError):self.service.suggested_request(self.gid,rid,self.goal,self.pid,1)
    def test_failure_has_no_report_or_automatic_retry(self):
        class Failure:
            calls=0
            def respond(self,messages):self.calls+=1;raise RuntimeError('Red interrumpida')
        provider=Failure()
        with self.assertRaises(RuntimeError):self.service.analyze(self.gid,self.goal,provider,self.pid,1)
        self.assertEqual(provider.calls,1);self.assertIsNone(self.service.latest(self.gid))
    def test_no_profile_supported(self):
        rid=self.service.analyze(self.gid,self.goal,self.provider({'answers':[],'issues':[]}))
        self.assertEqual(self.service.suggested_request(self.gid,rid,self.goal),self.goal)
    def test_context_limits_before_provider(self):
        class Forbidden:
            def respond(self,messages):raise AssertionError('No llamar')
        with self.assertRaises(ValueError):self.service.analyze(self.gid,'x'*6001,Forbidden())
        self.service.profiles.save(self.gid,'Formato','Docente','😀'*6000,self.pid,1)
        with self.assertRaises(ValueError):self.service.analyze(self.gid,self.goal,Forbidden(),self.pid,2)
    def test_explicit_answer_not_overwritten(self):
        goal=self.goal+'\nSesiones: 4'
        rid=self.service.analyze(self.gid,goal,self.provider(),self.pid,1)
        self.assertEqual(self.service.suggested_request(self.gid,rid,goal,self.pid,1),goal)
    def test_local_duplicate_conflicts(self):
        profile=self.service.profiles.snapshot(self.gid,self.pid)
        self.assertEqual(conflicting_details(profile,'Sesiones: 3\nSESIONES: 4'),['Sesiones'])
        self.assertEqual(conflicting_details(profile,'Sesiones: pendiente\nSesiones: 3\nSESIONES: 3'),[])
        goal=self.goal+'\nSesiones: 3\nSesiones: 4'
        rid=self.service.analyze(self.gid,goal,self.provider(),self.pid,1)
        with self.assertRaises(ValueError):self.service.suggested_request(self.gid,rid,goal,self.pid,1)
