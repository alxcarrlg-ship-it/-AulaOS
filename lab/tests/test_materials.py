import json
import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile
from openpyxl import Workbook
from core import Store
from chat import ChatService
from materials import extract, Materials

class Provider:
    source='online'
    def respond(self,messages):self.messages=messages;return 'Borrador basado en [M1].'

class MaterialTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.db=Store(self.root/'db.sqlite3');self.a=self.db.group('A','2A');self.b=self.db.group('B','2A')
        self.chat=ChatService(self.db);self.m=self.chat.materials
    def tearDown(self):self.db.close();self.temp.cleanup()
    def doc(self,name,text):
        p=self.root/name;p.write_text(text,encoding='utf-8');return p
    def test_text_snapshot_dedup_and_restart(self):
        p=self.doc('plan.txt','Material de inglés áéí');mid=self.m.import_file(self.a,p)
        self.assertEqual(mid,self.m.import_file(self.a,p));p.unlink()
        self.db.close();self.db=Store(self.root/'db.sqlite3')
        self.assertEqual(Materials(self.db).get(self.a,mid)['content'],'Material de inglés áéí')
    def test_docx_paragraphs_and_tables(self):
        p=self.root/'plan.docx'
        with ZipFile(p,'w') as z:
            z.writestr('word/document.xml','<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>Objetivo</w:t></w:r></w:p><w:tbl><w:tr><w:tc><w:p><w:r><w:t>Actividad</w:t></w:r></w:p></w:tc></w:tr></w:tbl></w:body></w:document>')
        text,warning,_=extract(p);self.assertEqual(text,'Objetivo\nActividad');self.assertIn('sin imágenes',warning)
    def test_excel_all_sheets_formulas_not_evaluated(self):
        p=self.root/'notes.xlsx';book=Workbook();book.active.title='Primera';book.active.append(['Nombre','Valor']);book.active.append(['Ejemplo','=1+2'])
        book.create_sheet('Segunda').append(['Contenido']);book.save(p);book.close()
        text,warning,_=extract(p)
        for value in ['Primera','Segunda','A2: Ejemplo','B2: =1+2']:self.assertIn(value,text)
        self.assertIn('no se calculan',warning)
    def test_csv_does_not_import_students(self):
        mid=self.m.import_file(self.a,self.doc('lista.csv','Nombre,Edad\nEjemplo,12'))
        self.assertIn('Ejemplo',self.m.get(self.a,mid)['content']);self.assertEqual(self.db.students(self.a),[])
    def test_scope_and_general_are_isolated(self):
        mid=self.m.save(self.a,'Privado A','No compartir con B')
        self.assertEqual(self.m.list(self.b),[]);self.assertEqual(self.m.list(None),[])
        with self.assertRaises(ValueError):self.m.get(self.b,mid)
        with self.assertRaises(ValueError):self.chat.send(self.b,'hola',Provider(),material_ids=[mid])
        self.assertEqual(self.chat.history(self.b),[])
    def test_only_selected_materials_are_sent(self):
        one=self.m.save(self.a,'Elegido','Contenido elegido');self.m.save(self.a,'Sin permiso','Contenido no seleccionado')
        p=Provider();self.chat.send(self.a,'Resume',p,include_records=False,material_ids=[one])
        payload=json.dumps(p.messages,ensure_ascii=False)
        self.assertIn('Contenido elegido',payload);self.assertNotIn('Contenido no seleccionado',payload)
        self.assertIn('[Mnumero]',payload)
    def test_no_implicit_attachment_on_next_turn(self):
        mid=self.m.save(self.a,'Archivo','Texto secreto original')
        self.chat.send(self.a,'Resume',Provider(),material_ids=[mid]);p=Provider();self.chat.send(self.a,'Siguiente',p)
        self.assertNotIn('Texto secreto original',json.dumps(p.messages))
    def test_retry_keeps_original_attachment(self):
        class Failure(Provider):
            def respond(self,messages):raise OSError('Fallo simulado')
        mid=self.m.save(self.a,'Plan','Texto del plan');other=self.m.save(self.a,'Otro','No sustituir')
        with self.assertRaises(OSError):self.chat.send(self.a,'Resume',Failure(),material_ids=[mid])
        failed=self.chat.history(self.a)[0]['id'];p=Provider()
        self.chat.send(self.a,'Resume',p,retry_id=failed,material_ids=[other])
        self.assertIn('Texto del plan',json.dumps(p.messages));self.assertNotIn('No sustituir',json.dumps(p.messages))
        self.assertEqual(len(self.chat.history(self.a)),2)
    def test_offline_lists_sources_without_ai_claim(self):
        mid=self.m.save(self.a,'Planeación','Texto')
        answer=self.chat.send(self.a,'Resume',material_ids=[mid])
        self.assertIn('sin análisis de IA',answer);self.assertIn('Planeación',answer)
    def test_oversize_context_rejected_before_request_or_history(self):
        mid=self.m.save(self.a,'Grande','á'*10000);p=Provider()
        with self.assertRaises(ValueError):self.chat.send(self.a,'Resume',p,material_ids=[mid])
        self.assertFalse(hasattr(p,'messages'));self.assertEqual(self.chat.history(self.a),[])
    def test_max_three_and_duplicates(self):
        ids=[self.m.save(self.a,str(i),str(i)) for i in range(4)]
        with self.assertRaises(ValueError):self.m.context(self.a,ids)
        self.assertEqual(len(self.m.context(self.a,[ids[0],ids[0]])),1)
    def test_empty_corrupt_and_unsupported(self):
        for name,text in [('empty.txt',''),('bad.docx','broken'),('legacy.doc','text'),('binary.txt','\x00')]:
            with self.subTest(name=name),self.assertRaises(ValueError):extract(self.doc(name,text))
    def test_large_file_rejected(self):
        p=self.root/'big.txt';p.write_bytes(b'x'*(10*1024*1024+1))
        with self.assertRaises(ValueError):extract(p)
    def test_save_response_and_find_by_title(self):
        self.chat.send(self.a,'Crea una actividad',Provider())
        mid=self.m.save(self.a,'Actividad INGLÉS',self.chat.history(self.a)[-1]['content'])
        self.assertEqual(self.m.list(self.a,'inglés')[0]['id'],mid)
        self.assertIn('Borrador',self.m.get(self.a,mid)['content'])
    def test_xml_entities_rejected(self):
        p=self.root/'entities.docx'
        with ZipFile(p,'w') as z:z.writestr('word/document.xml','<!DOCTYPE x [<!ENTITY a "contenido">]><x>&a;</x>')
        with self.assertRaises(ValueError):extract(p)

if __name__=='__main__':unittest.main()
