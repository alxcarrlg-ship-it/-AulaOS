import json
import tempfile
import unittest
from pathlib import Path
from core import Store
from online import Reply,MeteredProvider,OnlineError
from resource_workflow import ResourceWorkflow

class ResourceTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.store=Store(Path(self.tmp.name)/'db.sqlite3');self.gid=self.store.group('Escuela','A');self.other=self.store.group('Escuela','B');self.service=ResourceWorkflow(self.store)
        self.source={'id':'W1','url':'https://example.org/resource','title':'Recurso','kind':'cited'}
        self.report={'activity':'Actividad propia: juego oral de vocabulario, 15 minutos.','fit':'Nivel inicial sin pantalla.','limitations':'Revisar adecuación. Solo se dispone del resumen.','source_ids':['W1']}
    def tearDown(self):self.store.close();self.tmp.cleanup()
    def search_provider(self,evidence='sourced',incomplete=False):
        source=self.source
        class Provider:
            research=True
            def respond(self,messages):
                self.messages=messages;self.last_reply=Reply('Resumen con recurso [W1].',100,100,'r','modelo',incomplete,1,(source,),True,evidence)
                return self.last_reply.text
        return Provider()
    def adaptation_provider(self,report=None):
        report=self.report if report is None else report
        class Provider:
            research=False
            def respond(self,messages):self.messages=messages;return json.dumps(report)
        return Provider()
    def search(self):return self.service.search(self.gid,'Vocabulario A1, 15 minutos, sin pantalla',self.search_provider())
    def test_search_and_adaptation_preserve_parent_and_sources(self):
        rid=self.search();aid=self.service.adapt(self.gid,rid,['W1'],'Juego oral A1',self.adaptation_provider())
        row=self.service.get(self.gid,aid)
        self.assertEqual(row['parent_id'],rid);self.assertEqual(json.loads(row['sources_json']),[self.source])
        self.assertIn('ADAPTACIÓN PROPUESTA',row['content']);self.assertIn(self.source['url'],row['content'])
        self.assertEqual(len(self.service.list(self.gid)),2)
    def test_no_group_records_in_search_context(self):
        self.store.add_student(self.gid,'ALUMNO_SECRETO');self.store.create_task('TAREA_SECRETA',self.gid)
        provider=self.search_provider();self.service.search(self.gid,'Recursos A1',provider)
        text=json.dumps(provider.messages);self.assertNotIn('ALUMNO_SECRETO',text);self.assertNotIn('TAREA_SECRETA',text)
        self.assertEqual(provider.messages[-1]['content'],'Recursos A1')
    def test_scope_and_material_scope(self):
        rid=self.search()
        for fn,args in [(self.service.get,(self.other,rid)),(self.service.adaptation_context,(self.other,rid,['W1'],'Clase')),(self.service.to_material,(self.other,rid))]:
            with self.assertRaises(ValueError):fn(*args)
        self.assertEqual(self.service.list(self.other),[])
    def test_unconfirmed_and_incomplete_block_adaptation(self):
        for provider in [self.search_provider('unconfirmed'),self.search_provider(incomplete=True)]:
            rid=self.service.search(self.gid,'Tema',provider)
            self.assertEqual(self.service.get(self.gid,rid)['evidence'],'unconfirmed')
            with self.assertRaises(ValueError):self.service.adaptation_context(self.gid,rid,['W1'],'Clase')
    def test_missing_metadata_not_trusted(self):
        class Provider:
            research=True
            def respond(self,messages):return 'Aquí está https://example.org/inventado'
        rid=self.service.search(self.gid,'Tema',Provider())
        self.assertEqual(json.loads(self.service.get(self.gid,rid)['sources_json']),[])
        self.assertEqual(self.service.get(self.gid,rid)['evidence'],'unconfirmed')
    def test_consulted_only_source_not_selectable(self):
        self.source['kind']='consulted';rid=self.search()
        with self.assertRaises(ValueError):self.service.adaptation_context(self.gid,rid,['W1'],'Clase')
    def test_invalid_selections_and_payloads(self):
        rid=self.search()
        for ids in [[],['W9'],['W1','W1']]:
            with self.assertRaises(ValueError):self.service.adaptation_context(self.gid,rid,ids,'Clase')
        for report in [dict(self.report,source_ids=['W9']),dict(self.report,activity='Referencia [W9]'),dict(self.report,activity='Abre https://evil.example/test'),dict(self.report,activity=7),{}]:
            with self.assertRaises(ValueError):self.service.adapt(self.gid,rid,['W1'],'Clase',self.adaptation_provider(report))
        self.assertEqual(len(self.service.list(self.gid)),1)
    def test_material_reuse_preserves_provenance(self):
        rid=self.search();aid=self.service.adapt(self.gid,rid,['W1'],'Clase',self.adaptation_provider())
        mid=self.service.to_material(self.gid,aid);self.assertEqual(self.service.to_material(self.gid,aid),mid)
        material=self.service.materials.get(self.gid,mid);self.assertIn(self.source['url'],material['content']);self.assertIn('PETICIÓN',material['content'])
    def test_context_limit_before_provider(self):
        rid=self.search()
        self.store.con.execute('UPDATE resource_runs SET content=? WHERE id=?',('x'*19000,rid));self.store.con.commit()
        class Forbidden:
            research=False
            def respond(self,messages):raise AssertionError('No llamar')
        with self.assertRaises(ValueError):self.service.adapt(self.gid,rid,['W1'],'Clase',Forbidden())
    def test_no_automatic_retry_or_partial_save(self):
        class Failure:
            research=True;calls=0
            def respond(self,messages):self.calls+=1;raise RuntimeError('Falla de red')
        p=Failure()
        with self.assertRaises(RuntimeError):self.service.search(self.gid,'Tema',p)
        self.assertEqual(p.calls,1);self.assertEqual(self.service.list(self.gid),[])
    def test_metered_provider_exposes_metadata_and_clears_on_failure(self):
        source=self.source
        class Raw:
            research=True;request_options={};profile='Económico';fail=False
            def respond(self,messages):
                if self.fail:raise OnlineError('connection','Falló')
                return Reply('Resumen',1,1,'r','modelo',False,1,(source,),True,'sourced')
        raw=Raw();provider=MeteredProvider(self.store,raw)
        rid=self.service.search(self.gid,'Tema',provider)
        self.assertEqual(self.service.get(self.gid,rid)['evidence'],'sourced');self.assertEqual(provider.ledger.summary()['attempts'],1)
        raw.fail=True
        with self.assertRaises(OnlineError):provider.respond([])
        self.assertIsNone(provider.last_reply);self.assertEqual(provider.ledger.summary()['attempts'],2)
