import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch
from core import Store
from drafts import Drafts
from projects import Projects
from evidence import Evidence
from recovery import Recovery
from migrations import CURRENT_VERSION,prepare

class MigrationTests(unittest.TestCase):
    def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.path=self.root/'db.sqlite3'
    def tearDown(self):self.tmp.cleanup()
    def legacy(self):
        db=Store(self.path);gid=db.group('Escuela','A');sid=db.add_student(gid,'Alumno')
        db.mark(gid,sid,'2026-10-15','F');db.log_event(gid,sid,'2026-10-15','Nota','Conservar')
        draft=Drafts(db).create(gid,'Trabajo','Texto guardado')
        projects=Projects(db);pid,_=projects.save(gid,dict(title='Proyecto',planned='Actividad',completed='',pending='Producto',next_step='Ensayo',documents=[]))
        evidence=Evidence(db);eid=evidence.create(gid,pid,1,dict(title='Evidencia',day='2026-10-15',observation='Observado',next_step='',due='',status='Por revisar'))
        Recovery(db).put('session',gid,'draft',draft,1,dict(title='Trabajo pendiente',content='Texto recuperable'))
        with db.con:
            db.con.execute('DROP INDEX idx_student_external_id');db.con.execute('ALTER TABLE students DROP COLUMN external_id')
            db.con.execute('DROP TABLE schema_migrations');db.con.execute('PRAGMA user_version=0')
        db.close();return gid,sid,draft,pid,eid
    def test_legacy_upgrade_preserves_records_working_copies_and_verified_backup(self):
        gid,sid,did,pid,eid=self.legacy();db=Store(self.path)
        try:
            self.assertEqual(db.con.execute('PRAGMA user_version').fetchone()[0],CURRENT_VERSION)
            self.assertEqual(db.attendance_counts(sid),{'F':1});self.assertEqual(db.events(sid)[0]['detail'],'Conservar')
            self.assertEqual(Drafts(db).get(gid,did)['content'],'Texto guardado')
            self.assertEqual(Projects(db).get(gid,pid)['pending'],'Producto')
            self.assertEqual(Evidence(db).get(gid,eid)['content']['observation'],'Observado')
            self.assertEqual(Recovery(db).get(gid,'session')['payload']['content'],'Texto recuperable')
            self.assertIsNone(db.students(gid)[0]['external_id'])
            backup=sqlite3.connect(db.migration_backup)
            try:
                self.assertEqual(backup.execute('PRAGMA quick_check').fetchone()[0],'ok')
                self.assertEqual(backup.execute('PRAGMA user_version').fetchone()[0],0)
                self.assertNotIn('external_id',[r[1] for r in backup.execute('PRAGMA table_info(students)')])
                self.assertEqual(backup.execute('SELECT count(*) FROM recovery_snapshots').fetchone()[0],1)
            finally:backup.close()
        finally:db.close()
    def test_reopen_is_idempotent_no_new_migration_backup(self):
        self.legacy();first=Store(self.path);first.close();before=list((self.root/'migration_backups').glob('*.sqlite3'))
        second=Store(self.path)
        try:
            self.assertIsNone(second.migration_backup);self.assertEqual(second.con.execute('SELECT count(*) FROM schema_migrations').fetchone()[0],CURRENT_VERSION)
            self.assertEqual(list((self.root/'migration_backups').glob('*.sqlite3')),before)
        finally:second.close()
    def test_new_database_needs_no_preupgrade_backup(self):
        db=Store(self.path)
        try:self.assertIsNone(db.migration_backup);self.assertEqual(db.con.execute('PRAGMA user_version').fetchone()[0],CURRENT_VERSION)
        finally:db.close()
    def test_future_database_rejected_before_schema_changes(self):
        con=sqlite3.connect(self.path);con.execute('CREATE TABLE future_data(value TEXT)');con.execute("INSERT INTO future_data VALUES('Conservar')");con.execute('PRAGMA user_version=99');con.commit();con.close()
        before=self.path.read_bytes()
        with self.assertRaisesRegex(ValueError,'más reciente'):Store(self.path)
        self.assertEqual(self.path.read_bytes(),before)
    def test_backup_failure_stops_upgrade(self):
        self.legacy();con=sqlite3.connect(self.path)
        try:
            with patch('migrations.sqlite3.connect',side_effect=OSError('Disco lleno')):
                with self.assertRaises(OSError):prepare(con,self.path)
            self.assertEqual(con.execute('PRAGMA user_version').fetchone()[0],0)
            self.assertNotIn('external_id',[r[1] for r in con.execute('PRAGMA table_info(students)')])
        finally:con.close()
    def test_failed_unique_index_migration_rolls_back_version(self):
        db=Store(self.path);gid=db.group('Escuela','A');db.add_student(gid,'Uno');db.add_student(gid,'Dos')
        with db.con:
            db.con.execute('DROP INDEX idx_student_external_id');db.con.execute("UPDATE students SET external_id='DUPLICADO'")
            db.con.execute('DROP TABLE schema_migrations');db.con.execute('PRAGMA user_version=0')
        db.close()
        with self.assertRaises(sqlite3.IntegrityError):Store(self.path)
        con=sqlite3.connect(self.path)
        try:
            self.assertEqual(con.execute('PRAGMA user_version').fetchone()[0],0)
            self.assertEqual(con.execute('SELECT count(*) FROM students').fetchone()[0],2)
            self.assertEqual(con.execute("SELECT count(*) FROM sqlite_master WHERE name='idx_student_external_id'").fetchone()[0],0)
            self.assertTrue(list((self.root/'migration_backups').glob('*.sqlite3')))
        finally:con.close()
