import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from core import Store
from chat import ChatService
from online import OpenAIProvider, MeteredProvider, UsageLedger, OnlineError
from research import safe_url, domains, render_web


def result(status='completed'):
    return {'id':'web_fixture','model':'gpt-6-luna','status':status,
      'usage':{'input_tokens':2000,'output_tokens':1000},'output':[
        {'type':'web_search_call','status':'completed','action':{'type':'search','sources':[
            {'url':'https://example.org/activity','title':'Actividad'},
            {'url':'https://example.org/other','title':'Otra fuente'}]}},
        {'type':'message','content':[{'type':'output_text','text':'Una actividad para clase.',
         'annotations':[{'type':'url_citation','url':'https://example.org/activity','title':'Actividad','start_index':0,'end_index':24}]}]}]}

class ResearchTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.path=Path(self.tmp.name)/'db.sqlite3'
        self.db=Store(self.path);self.gid=self.db.group('Privada','2A');self.chat=ChatService(self.db);self.payloads=[]
    def tearDown(self):self.db.close();self.tmp.cleanup()
    def provider(self,data=None,allowed=None,limit=100):
        data=result() if data is None else data
        def transport(p):self.payloads.append(p);return data
        return MeteredProvider(self.db,OpenAIProvider('fake',transport=transport,research=True,allowed_domains=allowed),limit)
    def test_contract_sources_and_separate_cost(self):
        answer=self.chat.send(self.gid,'Actividades A1',self.provider(allowed=['example.org']))
        p=self.payloads[0];self.assertEqual(p['tools'][0]['type'],'web_search')
        self.assertEqual(p['tools'][0]['filters']['allowed_domains'],['example.org'])
        self.assertTrue(p['tools'][0]['external_web_access']);self.assertEqual(p['tool_choice'],'required')
        self.assertEqual(p['max_tool_calls'],3);self.assertIn('web_search_call.action.sources',p['include'])
        self.assertIn('[W1](https://example.org/activity)',answer);self.assertIn('consultada, no citada',answer)
        u=UsageLedger(self.db).summary();self.assertAlmostEqual(u['estimate_usd'],.0007)
        self.assertAlmostEqual(u['web_estimate_usd'],.01);self.assertEqual(u['web_searches'],1);self.assertEqual(u['unknown'],0)
    def test_research_never_reads_private_context_or_history(self):
        self.db.add_student(self.gid,'Alumno privado')
        self.chat.send(self.gid,'Conversación privada')
        self.chat.send(self.gid,'Primera investigación',self.provider())
        self.chat.send(self.gid,'Consulta pública',self.provider(),include_records=True)
        sent=json.dumps(self.payloads[-1],ensure_ascii=False)
        for private in ['Alumno privado','Conversación privada','Primera investigación','Privada']:
            self.assertNotIn(private,sent)
        self.assertEqual(len(self.payloads[-1]['input']),2)
    def test_reject_attachments_before_usage(self):
        mid=self.chat.materials.save(self.gid,'Secreto','No enviar')
        with self.assertRaises(ValueError):self.chat.send(self.gid,'Busca',self.provider(),material_ids=[mid])
        self.assertEqual(self.payloads,[]);self.assertEqual(UsageLedger(self.db).summary()['attempts'],0)
    def test_sources_and_timestamp_survive_restart_save_and_offline(self):
        answer=self.chat.send(self.gid,'Busca',self.provider());self.db.close();self.db=Store(self.path);self.chat=ChatService(self.db)
        history=self.chat.history(self.gid);self.assertEqual(history[-1]['source'],'research')
        self.assertEqual(history[-1]['content'],answer);self.assertIn('Consulta web:',answer)
        mid=self.chat.materials.save(self.gid,'Hallazgos',answer)
        self.assertIn('https://example.org/activity',self.chat.materials.get(self.gid,mid)['content'])
        self.chat.send(self.gid,'Leer guardado',material_ids=[mid]);self.assertEqual(len(self.payloads),1)
    def test_failure_retry_preserves_domain_and_mode(self):
        def fail(p):raise OnlineError('connection','Simulado')
        p=MeteredProvider(self.db,OpenAIProvider('fake',research=True,allowed_domains=['example.org'],transport=fail))
        with self.assertRaises(OnlineError):self.chat.send(self.gid,'Busca',p)
        mid=self.chat.history(self.gid)[0]['id']
        with self.assertRaises(ValueError):self.chat.send(self.gid,'Busca',self.provider(),retry_id=mid)
        with self.assertRaises(ValueError):self.chat.send(self.gid,'Busca',retry_id=mid)
        self.chat.send(self.gid,'Busca',self.provider(allowed=['example.org']),retry_id=mid)
        self.assertEqual(len(self.chat.history(self.gid)),2);self.assertEqual(UsageLedger(self.db).summary()['attempts'],2)
        self.assertEqual(UsageLedger(self.db).summary()['unknown'],1)
    def test_budget_shared_with_chat_and_not_bypassed_by_search(self):
        self.chat.send(self.gid,'Busca',self.provider(limit=1))
        with self.assertRaises(OnlineError):self.chat.send(self.gid,'Otra',self.provider(limit=1))
        self.assertEqual(len(self.payloads),1)
    def test_no_search_is_not_presented_as_verified(self):
        data=result();data['output']=data['output'][1:]
        text=self.chat.send(self.gid,'Busca',self.provider(data))
        self.assertIn('sin verificación suficiente',text)
        self.assertEqual(UsageLedger(self.db).summary()['web_searches'],0)
    def test_no_citations_is_not_presented_as_verified(self):
        data=result();data['output'][1]['content'][0]['annotations']=[]
        self.assertIn('sin verificación suficiente',self.chat.send(self.gid,'Busca',self.provider(data)))
    def test_incomplete_cost_unknown(self):
        text=self.chat.send(self.gid,'Busca',self.provider(result('incomplete')))
        self.assertIn('Respuesta incompleta',text);self.assertEqual(UsageLedger(self.db).summary()['unknown'],1)
    def test_open_and_find_are_not_search_fees(self):
        data=result()
        for action in ['open_page','find_in_page']:
            data['output'].insert(0,{'type':'web_search_call','status':'completed','action':{'type':action}})
        self.chat.send(self.gid,'Busca',self.provider(data))
        self.assertEqual(UsageLedger(self.db).summary()['web_searches'],1)
    def test_failed_tool_unknown_billing(self):
        data=result();data['output'][0]['status']='failed'
        self.chat.send(self.gid,'Busca',self.provider(data))
        self.assertEqual(UsageLedger(self.db).summary()['unknown'],1)
    def test_unsafe_urls_not_rendered_as_sources(self):
        for url in ['file:///etc/passwd','javascript:alert(1)','https://127.0.0.1/','https://192.168.1.1','https://user:pass@example.org','https://host.local','https://example.org:22']:
            self.assertIsNone(safe_url(url))
        data=result();data['output'][1]['content'][0]['annotations'][0]['url']='file:///bad'
        text,sources,_,_=render_web(data['output'],'completed')
        self.assertNotIn('file:///bad',text);self.assertFalse(any(s['kind']=='cited' for s in sources))
    def test_domains_validation_and_dedup(self):
        self.assertEqual(domains('Example.org,example.org, school.edu'),['example.org','school.edu'])
        for value in ['https://example.org','*.org','localhost','example.org/path','127.0.0.1','a.local']:
            with self.subTest(value=value),self.assertRaises(ValueError):domains(value)
    def test_invalid_offsets_keep_source_without_corrupting_text(self):
        data=result();data['output'][1]['content'][0]['annotations'][0]['end_index']=99999
        text,sources,_,_=render_web(data['output'],'completed')
        self.assertIn('Una actividad para clase.',text);self.assertEqual(len(sources),2)
    def test_migration_keeps_03_messages_and_usage(self):
        self.chat.send(self.gid,'Dato anterior')
        before=self.chat.history(self.gid)
        self.db.con.execute("ALTER TABLE messages DROP COLUMN request_options")
        self.db.con.execute("CREATE TABLE online_usage(id INTEGER PRIMARY KEY,month TEXT,profile TEXT,state TEXT,input_tokens INTEGER,output_tokens INTEGER,estimate_usd REAL,response_id TEXT,created_at TEXT)")
        self.db.con.execute("INSERT INTO online_usage VALUES(1,'2026-10','Económico','complete',100,100,0.00006,'old','2026-10-13')")
        self.db.con.commit()
        self.chat=ChatService(self.db);ledger=UsageLedger(self.db)
        self.assertEqual(before,self.chat.history(self.gid))
        summary=ledger.summary('2026-10');self.assertEqual(summary['attempts'],1)
        self.assertAlmostEqual(summary['estimate_usd'],.00006)
        self.assertEqual(summary['research_attempts'],0);self.assertEqual(summary['unknown'],0)
        # Running migrations again is safe.
        ChatService(self.db);UsageLedger(self.db)

    def test_research_history_not_in_normal_online_chat(self):
        self.chat.send(self.gid,'Hallazgo privado',self.provider())
        captured=[]
        p=MeteredProvider(self.db,OpenAIProvider('fake',transport=lambda x:(captured.append(x) or result())))
        self.chat.send(self.gid,'Normal',p)
        self.assertNotIn('Hallazgo privado',json.dumps(captured));self.assertNotIn('tools',captured[0])

if __name__=='__main__':unittest.main()
