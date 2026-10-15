import csv
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from docx import Document
from core import Store
from templates import Templates
from projects import Projects
from evidence import Evidence
from template_suggestions import TemplateSuggestions
from recovery import Recovery
from settings import Settings, DEFAULTS
from launcher import main
from release_check import run_checks
from test_templates import fixture


class ReleaseCandidateTests(unittest.TestCase):
    def test_offline_packaging_checks_do_not_open_user_data_or_network(self):
        with tempfile.TemporaryDirectory() as folder:
            sentinel = Path(folder) / 'aulaos.sqlite3'
            sentinel.write_bytes(b'untouched user data')
            with patch.dict('os.environ', {'AULAOS_DATA_DIR': folder}), patch('socket.socket', side_effect=AssertionError('network forbidden')):
                report = run_checks()
            self.assertTrue(report['ok'], report)
            self.assertEqual(sentinel.read_bytes(), b'untouched user data')

    def test_launcher_report_never_overwrites(self):
        with tempfile.TemporaryDirectory() as folder:
            report = Path(folder) / 'result.json'
            with patch('release_check.run_checks', return_value={'ok': False}):
                self.assertEqual(main(['--self-test', str(report)]), 1)
                before = report.read_bytes()
                with self.assertRaises(FileExistsError):main(['--self-test', str(report)])
                self.assertEqual(report.read_bytes(), before)

    def test_wrong_shape_settings_do_not_prevent_startup(self):
        with tempfile.TemporaryDirectory() as folder:
            settings = Settings(folder)
            for value in [None, [], 'wrong', 123]:
                settings.path.write_text(json.dumps(value), encoding='utf-8')
                self.assertEqual(settings.load(), DEFAULTS)
                with self.assertRaises(ValueError):settings.save(value)

    def test_teacher_journey_reopen_backup_and_export(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            store = Store(root / 'school.sqlite3')
            try:
                gid = store.group('Escuela sintética', '2A')
                other = store.group('Otra escuela', '2A')
                roster = root / 'roster.csv'
                with roster.open('w', newline='', encoding='utf-8') as stream:
                    writer = csv.writer(stream)
                    writer.writerows([['Nombre', 'Matrícula'], ['Nombre igual', '001'], ['Nombre igual', '002']])
                store.import_csv(gid, roster)
                first, second = store.students(gid)
                store.mark(gid, first['id'], '2026-10-15', 'A')
                templates = Templates(store)
                source = root / 'own.docx'
                original = fixture(source, 8)
                tid = templates.import_file(gid, source, 'Formato de ocho columnas')
                did = templates.create(gid, tid, 'Clase')
                key = next(f['id'] for f in json.loads(templates.get(gid, tid)['schema_json'])['fields'] if f['text'] == 'Completar')
                projects = Projects(store)
                pid, pv = projects.save(gid, dict(title='Our voices', planned='Presentación', completed='', pending='Ensayo', next_step='Practicar', documents=[{'id': did, 'revision': 1}]))
                class Fake:
                    def respond(self, messages):
                        return json.dumps({'changes': {key: 'Texto propuesto'}, 'notes': 'Revisar'})
                suggestions = TemplateSuggestions(store)
                proposal = suggestions.propose(gid, did, 'Preparar ensayo', 1, Fake())
                recovery = Recovery(store)
                payload = {'values': {key: 'Texto corregido por docente'}, 'selected': [key]}
                recovery.put('synthetic-session', gid, 'review', proposal, 0, payload)
                self.assertEqual(templates.document(gid, did)['revision'], 1)
                recovered = recovery.get(gid, 'synthetic-session')['payload']
                suggestions.resolve(gid, proposal, True, recovered['selected'], recovered['values'], 0)
                templates.export(gid, did, root / 'lesson.docx')
                evidence = Evidence(store)
                eid = evidence.create(gid, pid, pv, dict(title='Ensayo', day='2026-10-15', observation='Dijo dos frases.', next_step='Practicar', due='', status='Por revisar'), student_id=first['id'])
                backup = store.backup()
                self.assertEqual(source.read_bytes(), original)
                self.assertIn('Texto corregido por docente', '\n'.join(c.text for t in Document(root / 'lesson.docx').tables for row in t.rows for c in row.cells))
                with self.assertRaises(ValueError):evidence.get(other, eid)
            finally:
                store.close()
            restored = Store(backup)
            try:
                self.assertEqual(Evidence(restored).get(gid, eid)['student']['id'], first['id'])
                self.assertNotIn(second['id'], restored.marks(gid, '2026-10-15'))
                self.assertEqual(Templates(restored).document(gid, did)['revision'], 2)
                self.assertEqual(restored.con.execute('PRAGMA quick_check').fetchone()[0], 'ok')
            finally:
                restored.close()
