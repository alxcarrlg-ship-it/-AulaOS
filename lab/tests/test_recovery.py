import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from core import Store
from drafts import RevisionConflict
from recovery import Recovery
from recovery_ui import RecoveryController
from test_templates import fixture

class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.db=Path(self.tmp.name)/'db';self.store=Store(self.db)
        self.gid=self.store.group('Escuela','A');self.other=self.store.group('Escuela','B');self.service=Recovery(self.store)
        self.did=self.service.drafts.create(self.gid,'Título','Aprobado')
        self.payload={'title':'Título en edición','content':'Trabajo pendiente'}
        path=Path(self.tmp.name)/'template.docx';fixture(path)
        self.tid=self.service.templates.import_file(self.gid,path,'Formato');self.doc=self.service.templates.create(self.gid,self.tid,'Planeación')
        self.key=next(f['id'] for f in json.loads(self.service.templates.get(self.gid,self.tid)['schema_json'])['fields'] if f['text']=='Completar')
    def tearDown(self):self.store.close();self.tmp.cleanup()
    def put(self,token='session'):self.service.put(token,self.gid,'draft',self.did,1,self.payload)
    def test_working_copy_does_not_create_approved_revision(self):
        self.put();self.assertEqual(self.service.drafts.get(self.gid,self.did)['content'],'Aprobado')
        self.assertEqual(len(self.service.drafts.history(self.gid,self.did)),1)
        self.assertEqual(self.service.get(self.gid,'session')['payload'],self.payload)
    def test_independent_windows_and_scoped_delete(self):
        self.put('one');self.service.put('two',self.gid,'draft',self.did,1,dict(self.payload,content='Otra ventana'))
        self.assertEqual(len(self.service.list(self.gid,'draft',self.did)),2)
        self.service.delete(self.other,'one');self.assertEqual(len(self.service.list(self.gid,'draft',self.did)),2)
        self.service.delete(self.gid,'one');self.assertEqual(self.service.get(self.gid,'two')['payload']['content'],'Otra ventana')
    def test_cross_group_and_token_reassignment_rejected(self):
        self.put()
        with self.assertRaises(ValueError):self.service.get(self.other,'session')
        self.assertEqual(self.service.list(self.other,'draft',self.did),[])
        with self.assertRaises(ValueError):self.service.put('foreign',self.other,'draft',self.did,1,self.payload)
        with self.assertRaises(ValueError):self.service.put('session',self.gid,'draft',None,None,self.payload)
    def test_new_incomplete_draft_recovers_without_creating_document(self):
        incomplete={'title':'','content':'Una idea a medias'}
        self.service.put('new',self.gid,'draft',None,None,incomplete)
        self.assertEqual(len(self.service.drafts.list(self.gid)),1)
        self.assertEqual(self.service.list(self.gid,'draft',None)[0]['payload'],incomplete)
    def test_template_snapshot_validates_ids_and_preserves_document(self):
        changes={self.key:'Actividad sin terminar'}
        self.service.put('template',self.gid,'template',self.doc,1,changes)
        self.assertEqual(self.service.templates.document(self.gid,self.doc)['changes'],'{}')
        with self.assertRaises(ValueError):self.service.put('bad',self.gid,'template',self.doc,1,{'foreign':'x'})
        self.assertEqual(self.service.get(self.gid,'template')['payload'],changes)
    def test_stale_base_remains_recoverable_but_cannot_overwrite_newer_revision(self):
        self.put();self.service.drafts.save(self.gid,self.did,'Actual','Nueva versión',1)
        row=self.service.get(self.gid,'session')
        with self.assertRaises(RevisionConflict):self.service.drafts.save(self.gid,self.did,**row['payload'],expected_revision=row['base_revision'])
        self.assertEqual(self.service.drafts.get(self.gid,self.did)['content'],'Nueva versión')
        self.assertEqual(self.service.get(self.gid,'session')['payload'],self.payload)
    def test_survives_reopen_and_backup(self):
        self.put();other=Store(self.db)
        try:self.assertEqual(Recovery(other).get(self.gid,'session')['payload'],self.payload)
        finally:other.close()
        other=Store(self.store.backup())
        try:self.assertEqual(Recovery(other).get(self.gid,'session')['payload'],self.payload)
        finally:other.close()
    def test_invalid_payload_does_not_replace_last_good_copy(self):
        self.put()
        for payload in [{'title':'x'},dict(self.payload,content='x'*120001),dict(self.payload,title=5)]:
            with self.assertRaises(ValueError):self.service.put('session',self.gid,'draft',self.did,1,payload)
        self.assertEqual(self.service.get(self.gid,'session')['payload'],self.payload)
    def controller(self):
        c=RecoveryController.__new__(RecoveryController);c.service=self.service;c.kind='draft';c.token='active';c.last=None;c.recovered=set()
        self.status=[];self.scheduled=[]
        c.status=SimpleNamespace(set=self.status.append)
        c.editor=SimpleNamespace(gid=self.gid,did=self.did,revision=1,app=SimpleNamespace(recovery_active={'active'}),dirty=lambda:True,after=lambda delay,fn:self.scheduled.append((delay,fn)),after_cancel=lambda timer:None)
        c.read=lambda:dict(self.payload)
        return c
    def test_timer_copies_dirty_text_without_saving_and_hides_active_windows(self):
        c=self.controller();self.put('crashed');c.tick()
        self.assertEqual(self.service.get(self.gid,'active')['payload'],self.payload)
        self.assertEqual([r['token'] for r in c.candidates()],['crashed'])
        self.assertEqual(self.scheduled[-1][0],10000)
        self.assertEqual(self.service.drafts.get(self.gid,self.did)['revision'],1)
        c.editor.dirty=lambda:False;c.tick()
        with self.assertRaises(ValueError):self.service.get(self.gid,'active')
        self.assertEqual(self.service.get(self.gid,'crashed')['payload'],self.payload)
    def test_autosave_error_visible_and_scheduler_continues(self):
        c=self.controller();c.read=lambda:{'title':'','content':'x'*120001};c.tick()
        self.assertIn('No se pudo',self.status[-1]);self.assertEqual(len(self.scheduled),1)
    def test_success_cleanup_and_discard_only_own_working_copy(self):
        c=self.controller();self.put('recovered');self.put('other');c.tick();c.recovered={'recovered'};c.saved()
        self.assertEqual([r['token'] for r in self.service.list(self.gid,'draft',self.did)],['other'])
        c.tick();c.stop();self.assertEqual([r['token'] for r in self.service.list(self.gid,'draft',self.did)],['other'])
