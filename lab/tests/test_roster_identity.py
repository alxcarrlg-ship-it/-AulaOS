import csv
import tempfile
import unittest
from pathlib import Path
from openpyxl import Workbook
from core import Store

class RosterIdentityTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.db=Store(self.root/'db')
        self.gid=self.db.group('Escuela','A');self.other=self.db.group('Escuela','B')
    def tearDown(self):self.db.close();self.tmp.cleanup()
    def csv(self,rows):
        path=self.root/'lista.csv'
        with path.open('w',newline='',encoding='utf-8') as f:
            writer=csv.writer(f);writer.writerow(['Nombre','Matrícula']);writer.writerows(rows)
        return path
    def excel(self,rows):
        path=self.root/'lista.xlsx';book=Workbook();book.active.title='Asistencia';book.active.append(['Nombre del alumno','Matrícula','15/10/2026'])
        for row in rows:book.active.append(row)
        book.save(path);book.close();return path
    def test_csv_homonyms_distinct_ids_and_reordering(self):
        self.db.import_csv(self.gid,self.csv([['Alex Ejemplo','001'],['Alex Ejemplo','002']]))
        before={r['external_id']:r['id'] for r in self.db.students(self.gid)}
        self.db.log_event(self.gid,before['001'],'2026-10-15','Nota','Del primero')
        self.db.import_csv(self.gid,self.csv([['Alex Ejemplo','002'],['Alex Corregido','001']]))
        after={r['external_id']:r['id'] for r in self.db.students(self.gid)}
        self.assertEqual(before,after);self.assertEqual(len(self.db.events(after['001'])),1);self.assertEqual(self.db.events(after['002']),[])
    def test_excel_changed_name_keeps_history_and_manual_attendance(self):
        self.db.import_excel(self.gid,self.excel([['Antes','0007','F']]),True)
        sid=self.db.students(self.gid)[0]['id'];self.db.mark(self.gid,sid,'2026-10-15','A')
        self.db.import_excel(self.gid,self.excel([['Después','0007','F']]),True)
        row=self.db.students(self.gid)[0];self.assertEqual(row['id'],sid);self.assertEqual(row['name'],'Después')
        self.assertEqual(self.db.marks(self.gid,'2026-10-15')[sid],'A');self.assertEqual(len(self.db.unresolved_conflicts(self.gid)),1)
    def test_adopts_id_for_unique_legacy_name(self):
        sid=self.db.add_student(self.gid,'Sin matrícula');self.db.mark(self.gid,sid,'2026-10-15','F')
        self.db.import_csv(self.gid,self.csv([['Sin matrícula','A-01']]))
        row=self.db.students(self.gid)[0];self.assertEqual(row['id'],sid);self.assertEqual(row['external_id'],'A-01')
        self.db.import_csv(self.gid,self.csv([['Sin matrícula','']]))
        self.assertEqual(self.db.students(self.gid)[0]['external_id'],'A-01')
    def test_duplicate_ids_reject_whole_import(self):
        sid=self.db.add_student(self.gid,'Original');before=[dict(r) for r in self.db.students(self.gid)]
        for path in [self.csv([['Uno','x'],['Dos',' X ']]),self.excel([['Uno','x','A'],['Dos','x','F']])]:
            with self.assertRaises(ValueError):
                if path.suffix=='.csv':self.db.import_csv(self.gid,path)
                else:self.db.import_excel(self.gid,path,True)
            self.assertEqual([dict(r) for r in self.db.students(self.gid)],before)
    def test_conflicting_identifier_never_reassigns_history(self):
        self.db.import_csv(self.gid,self.csv([['Alumno','ID1']]))
        sid=self.db.students(self.gid)[0]['id'];self.db.log_event(self.gid,sid,'2026-10-15','Nota','Histórico')
        with self.assertRaises(ValueError):self.db.import_csv(self.gid,self.csv([['Alumno','ID2']]))
        self.assertEqual(self.db.students(self.gid)[0]['external_id'],'ID1');self.assertEqual(len(self.db.events(sid)),1)
    def test_same_id_allowed_across_groups_and_manual_conflicts(self):
        a=self.db.add_student(self.gid,'Uno');b=self.db.add_student(self.other,'Dos');c=self.db.add_student(self.gid,'Tres')
        self.db.set_student_identifier(self.gid,a,'001');self.db.set_student_identifier(self.other,b,'001')
        with self.assertRaises(ValueError):self.db.set_student_identifier(self.gid,c,'001')
        with self.assertRaises(ValueError):self.db.set_student_identifier(self.other,a,'002')
        with self.assertRaises(ValueError):self.db.set_student_identifier(self.gid,a,'002',expected=None)
        self.db.set_student_identifier(self.gid,a,'002',expected='001')
        self.assertEqual(next(r for r in self.db.students(self.gid) if r['id']==a)['external_id'],'002')
    def test_numeric_excel_ids_rejected_instead_of_losing_zeroes(self):
        with self.assertRaisesRegex(ValueError,'texto'):self.db.import_excel(self.gid,self.excel([['Alumno',123,'A']]),True)
        self.assertEqual(self.db.students(self.gid),[])
    def test_legacy_homonyms_require_manual_assignment(self):
        a=self.db.add_student(self.gid,'Nombre igual');b=self.db.add_student(self.gid,'Nombre igual')
        with self.assertRaises(ValueError):self.db.import_csv(self.gid,self.csv([['Nombre igual','001'],['Nombre igual','002']]))
        self.db.set_student_identifier(self.gid,a,'001');self.db.set_student_identifier(self.gid,b,'002')
        self.db.import_csv(self.gid,self.csv([['Nombre igual','002'],['Nombre igual','001']]))
        self.assertEqual({r['id'] for r in self.db.students(self.gid)},{a,b})
    def test_multiple_id_columns_rejected(self):
        path=self.root/'ambiguous.csv';path.write_text('Nombre,Matrícula,Student ID\nAlumno,001,002\n')
        with self.assertRaises(ValueError):self.db.import_csv(self.gid,path)
        self.assertEqual(self.db.students(self.gid),[])
