import tempfile
import unittest
from pathlib import Path
from core import Store
from chat import ChatService
from drafts import Drafts, RevisionConflict

class DraftTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.path=Path(self.temp.name)/'db.sqlite3'
        self.store=Store(self.path);self.a=self.store.group('A','2A');self.b=self.store.group('B','2A')
        self.chat=ChatService(self.store);self.drafts=Drafts(self.store)
    def tearDown(self):self.store.close();self.temp.cleanup()
    def create(self):return self.drafts.create(self.a,'Guía de inglés','# Objetivo\nPracticar preguntas.')
    def test_versions_survive_restart(self):
        did=self.create();self.drafts.save(self.a,did,'Guía de inglés','Revisión dos',1)
        self.store.close();self.store=Store(self.path);self.drafts=Drafts(self.store)
        self.assertEqual(self.drafts.get(self.a,did)['content'],'Revisión dos')
        self.assertIn('Objetivo',self.drafts.get(self.a,did,1)['content'])
        self.assertEqual([r['revision'] for r in self.drafts.history(self.a,did)],[2,1])
    def test_group_isolation_all_operations(self):
        did=self.create()
        for action in [lambda:self.drafts.get(self.b,did),lambda:self.drafts.history(self.b,did),
                       lambda:self.drafts.save(self.b,did,'No','No',1),lambda:self.drafts.restore(self.b,did,1,1),
                       lambda:self.drafts.snapshot(self.b,did)]:
            with self.assertRaises(ValueError):action()
        self.assertEqual(self.drafts.list(self.b),[]);self.assertEqual(self.drafts.list(None),[])
        self.assertEqual(self.drafts.get(self.a,did)['revision'],1)
    def test_concurrent_edit_does_not_overwrite(self):
        did=self.create();other=Store(self.path)
        try:
            service=Drafts(other);base=service.get(self.a,did)
            self.drafts.save(self.a,did,'Primera ventana','Contenido A',1)
            with self.assertRaises(RevisionConflict):service.save(self.a,did,'Segunda ventana','Contenido B',base['revision'])
            self.assertEqual(service.get(self.a,did)['content'],'Contenido A')
            self.assertEqual(len(service.history(self.a,did)),2)
        finally:other.close()
    def test_restore_creates_revision_without_deleting(self):
        did=self.create();first=self.drafts.get(self.a,did)
        self.drafts.save(self.a,did,'Título nuevo','Segundo contenido',1)
        rev=self.drafts.restore(self.a,did,1,2)
        self.assertEqual(rev,3);self.assertEqual(self.drafts.get(self.a,did)['content'],first['content'])
        self.assertEqual(self.drafts.get(self.a,did)['restored_from'],1)
        self.assertEqual(self.drafts.get(self.a,did,2)['content'],'Segundo contenido')
    def test_no_change_does_not_create_version(self):
        did=self.create();r=self.drafts.get(self.a,did)
        self.assertEqual(self.drafts.save(self.a,did,r['title'],r['content'],1),1)
        self.assertEqual(len(self.drafts.history(self.a,did)),1)
    def test_invalid_input_leaves_history_unchanged(self):
        did=self.create()
        for title,content in [('','text'),('Title',''),('x'*201,'text'),('Title','x'*120001),('Title','bad\x00')]:
            with self.assertRaises(ValueError):self.drafts.save(self.a,did,title,content,1)
        self.assertEqual(len(self.drafts.history(self.a,did)),1)
    def test_material_is_immutable_after_edit_and_restore(self):
        mid=self.chat.materials.save(self.a,'Original','Con fuente [W1](https://example.org).')
        did=self.drafts.from_material(self.a,mid);self.drafts.save(self.a,did,'Adaptación','Texto editado',1)
        self.assertIn('https://example.org',self.chat.materials.get(self.a,mid)['content'])
        snap=self.drafts.snapshot(self.a,did);self.assertEqual(snap,self.drafts.snapshot(self.a,did))
        self.drafts.restore(self.a,did,1,2)
        self.assertEqual(self.chat.materials.get(self.a,snap)['content'],'Texto editado')
        self.assertEqual(self.drafts.get(self.a,did)['source_material_id'],mid)
    def test_wrong_group_material_rejected(self):
        mid=self.chat.materials.save(self.a,'Original','Datos')
        with self.assertRaises(ValueError):self.drafts.from_material(self.b,mid)
        self.assertEqual(self.drafts.list(self.b),[])
    def test_old_chat_attachment_keeps_exact_snapshot(self):
        did=self.create();mid=self.drafts.snapshot(self.a,did)
        class Failed:
            def respond(self,messages):raise OSError('Simulated')
        with self.assertRaises(OSError):self.chat.send(self.a,'Pregunta',Failed(),material_ids=[mid])
        uid=self.chat.history(self.a)[0]['id'];self.drafts.save(self.a,did,'Cambiado','No enviar este cambio',1)
        captured=[]
        class Capture:
            def respond(self,messages):captured.extend(messages);return 'ok'
        self.chat.send(self.a,'Pregunta',Capture(),retry_id=uid)
        text=str(captured);self.assertIn('Practicar preguntas',text);self.assertNotIn('No enviar este cambio',text)
    def test_backup_contains_versions(self):
        did=self.create();backup=self.store.backup();copy=Store(backup)
        try:self.assertIn('Objetivo',Drafts(copy).get(self.a,did)['content'])
        finally:copy.close()
    def test_general_draft_and_title_search(self):
        did=self.drafts.create(None,'INGLÉS general','Contenido')
        self.assertEqual(self.drafts.list(None,'inglés')[0]['id'],did)
        self.assertEqual(self.drafts.list(self.a),[])
    def test_initialization_keeps_existing_04_data(self):
        mid=self.chat.materials.save(self.a,'Anterior','Datos previos');self.chat.send(self.a,'Hola')
        before=self.chat.history(self.a);Drafts(self.store);Drafts(self.store)
        self.assertEqual(self.chat.history(self.a),before);self.assertEqual(self.chat.materials.get(self.a,mid)['content'],'Datos previos')

if __name__=='__main__':unittest.main()
