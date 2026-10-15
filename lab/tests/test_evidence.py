import json
from pathlib import Path
import tempfile
import unittest
from core import Store
from drafts import RevisionConflict
from evidence import Evidence,STATES
from projects import FIELDS
from document_export import export_document

class EvidenceTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.db=self.root/'db';self.store=Store(self.db)
        self.gid=self.store.group('Escuela','A');self.other=self.store.group('Escuela','B');self.service=Evidence(self.store)
        self.project=dict(title='Our voices',planned='Producto oral',completed='',pending='Presentación',next_step='Ensayo',documents=[])
        self.pid,self.pv=self.service.projects.save(self.gid,self.project)
        self.sid=self.store.add_student(self.gid,'Alumno de prueba');self.foreign=self.store.add_student(self.other,'Otro alumno')
        self.content=dict(title='Ensayo',day='2026-10-15',observation='Completó dos frases durante el ensayo.',next_step='Practicar pronunciación.',due='2026-10-16',status='Requiere seguimiento')
    def tearDown(self):self.store.close();self.tmp.cleanup()
    def create(self,**kw):return self.service.create(self.gid,self.pid,self.pv,self.content,**kw)
    def test_no_inferred_completion_or_school_record_changes(self):
        before=self.service.projects.snapshot(self.gid,self.pid);eid=self.create(student_id=self.sid)
        self.assertEqual(self.service.projects.snapshot(self.gid,self.pid),before)
        self.assertEqual(self.store.events(self.sid),[]);self.assertEqual(self.store.tasks(),[])
        self.assertEqual(self.service.get(self.gid,eid)['student']['id'],self.sid)
    def test_snapshot_material_survives_source_change(self):
        mid=self.service.materials.save(self.gid,'Producto','My name is Test.')
        eid=self.create(kind='Material',source_id=mid)
        with self.store.con:self.store.con.execute('UPDATE materials SET content=? WHERE id=?',('Modificado',mid))
        self.service.save(self.gid,eid,dict(self.content,status='Revisada'),1)
        self.assertEqual(self.service.get(self.gid,eid)['source']['content'],'My name is Test.')
    def test_observation_links_owner_and_rejects_wrong_student(self):
        event=self.store.log_event(self.gid,self.sid,'2026-10-14','Participación','Leyó su frase.')
        eid=self.create(kind='Observación',source_id=event)
        self.assertEqual(self.service.get(self.gid,eid)['student']['id'],self.sid)
        other=self.store.add_student(self.gid,'Mismo grupo')
        with self.assertRaises(ValueError):self.create(student_id=other,kind='Observación',source_id=event)
        self.assertEqual(len(self.service.list(self.gid,self.pid)),1)
    def test_group_isolation_sources_students_projects_and_history(self):
        mid=self.service.materials.save(self.other,'Ajeno','Texto privado')
        event=self.store.log_event(self.other,self.foreign,'2026-10-15','Nota','Privado')
        for kwargs in [dict(student_id=self.foreign),dict(kind='Material',source_id=mid),dict(kind='Observación',source_id=event)]:
            with self.assertRaises(ValueError):self.create(**kwargs)
        eid=self.create()
        for fn,args in [(self.service.get,(self.other,eid)),(self.service.list,(self.other,self.pid)),(self.service.history,(self.other,eid)),(self.service.report,(self.other,self.pid)),(self.service.save,(self.other,eid,self.content,1)),(self.service.create,(self.other,self.pid,1,self.content))]:
            with self.assertRaises(ValueError):fn(*args)
        self.assertEqual(self.service.observations(self.gid),[])
    def test_revision_history_conflict_noop_and_retirement(self):
        eid=self.create();retired=dict(self.content,status='Retirada',observation='Registro elegido por error.')
        self.assertEqual(self.service.save(self.gid,eid,self.content,1),1)
        self.assertEqual(self.service.save(self.gid,eid,retired,1),2)
        with self.assertRaises(RevisionConflict):self.service.save(self.gid,eid,self.content,1)
        self.assertEqual(self.service.get(self.gid,eid,1)['content'],self.content)
        self.assertEqual(self.service.history(self.gid,eid),[2,1])
        self.assertEqual(len(self.service.list(self.gid,self.pid,'Retirada')),1)
        self.assertEqual(self.service.list(self.gid,self.pid,'Revisada'),[])
    def test_pinned_project_revision_and_stale_creation(self):
        eid=self.create();self.service.projects.save(self.gid,dict(self.project,pending='Nuevo pendiente'),self.pid,1)
        with self.assertRaises(RevisionConflict):self.create()
        self.assertEqual(self.service.get(self.gid,eid)['project_revision'],1)
        self.assertEqual(len(self.service.list(self.gid,self.pid)),1)
    def test_invalid_input_atomic_and_followup_requires_action(self):
        for update in [dict(day='ayer'),dict(due='2026-02-30'),dict(title=''),dict(observation=''),dict(status='Aprobado'),dict(next_step=''),dict(observation='\x01'),dict(day='20261015')]:
            with self.assertRaises(ValueError):self.service.create(self.gid,self.pid,1,dict(self.content,**update))
        self.assertEqual(self.service.list(self.gid,self.pid),[])
        with self.assertRaises(ValueError):self.create(kind='Archivo',source_id=12)
        with self.assertRaises(ValueError):self.create(source_id=12)
    def test_local_persistence_backup_and_no_implicit_online_context(self):
        eid=self.create(student_id=self.sid)
        backup=self.store.backup();other=Store(backup)
        try:self.assertEqual(Evidence(other).get(self.gid,eid)['content'],self.content)
        finally:other.close()
        snapshot=json.dumps(self.service.projects.snapshot(self.gid,self.pid))
        self.assertNotIn(self.content['observation'],snapshot);self.assertNotIn('Alumno de prueba',snapshot)
    def test_report_filter_and_export_preserves_existing_file(self):
        self.create(student_id=self.sid);eid=self.create();self.service.save(self.gid,eid,dict(self.content,status='Retirada',title='RETIRADO'),1)
        report=self.service.report(self.gid,self.pid,'Requiere seguimiento')
        self.assertIn('Alumno de prueba',report);self.assertNotIn('RETIRADO',report)
        self.assertIn('Requiere seguimiento: 1',report);self.assertIn('Realizado',report)
        path=self.root/'informe.md';export_document('Seguimiento',report,path);before=path.read_bytes()
        with self.assertRaises(FileExistsError):export_document('Seguimiento','Otro',path)
        self.assertEqual(path.read_bytes(),before)
    def test_oversize_source_rejected_without_partial_record(self):
        mid=self.service.materials.save(self.gid,'Extenso','x'*20001)
        with self.assertRaises(ValueError):self.create(kind='Material',source_id=mid)
        self.assertEqual(self.service.list(self.gid,self.pid),[])
