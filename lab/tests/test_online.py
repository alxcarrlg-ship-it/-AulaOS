import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError, URLError
from core import Store
from chat import ChatService
from online import OpenAIProvider, MeteredProvider, UsageLedger, OnlineError, classify_http, Reply
from settings import Settings, CredentialVault


def response(status='completed',usage=True):
    data={'id':'resp_fixture','model':'gpt-6-luna','status':status,'output':[
        {'type':'reasoning','summary':[]},
        {'type':'message','content':[{'type':'output_text','text':'Respuesta de prueba'}]}]}
    if usage:data['usage']={'input_tokens':2000,'output_tokens':1000}
    return data


class OnlineTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.db=Store(Path(self.temp.name)/'db.sqlite3')
        self.gid=self.db.group('Plantel ficticio','2A');self.chat=ChatService(self.db)
    def tearDown(self):self.db.close();self.temp.cleanup()
    def test_response_contract_and_cost(self):
        payloads=[]
        def transport(p):payloads.append(p);return response()
        p=MeteredProvider(self.db,OpenAIProvider('test-key',transport=transport))
        self.assertEqual(self.chat.send(self.gid,'Hola',p),'Respuesta de prueba')
        payload=payloads[0]
        self.assertFalse(payload['store']);self.assertEqual(payload['max_output_tokens'],1800)
        self.assertEqual(payload['service_tier'],'default');self.assertNotIn('tools',payload)
        self.assertNotIn('test-key',json.dumps(payload))
        u=p.ledger.summary();self.assertEqual(u['attempts'],1);self.assertEqual(u['output_tokens'],1000)
        self.assertAlmostEqual(u['estimate_usd'],.0007);self.assertEqual(u['unknown'],0)
    def test_budget_blocks_transport_and_survives_restart(self):
        calls=[]
        provider=OpenAIProvider('test',transport=lambda p:(calls.append(p) or response()))
        p=MeteredProvider(self.db,provider,monthly_limit=1)
        self.chat.send(self.gid,'Uno',p)
        with self.assertRaises(OnlineError) as error:self.chat.send(self.gid,'Dos',p)
        self.assertEqual(error.exception.kind,'budget');self.assertEqual(len(calls),1)
        self.db.close();self.db=Store(Path(self.temp.name)/'db.sqlite3')
        self.assertEqual(UsageLedger(self.db).summary()['attempts'],1)
    def test_timeout_not_retried_and_unknown_cost_retained(self):
        calls=[]
        def bad(p):calls.append(p);raise OnlineError('connection','No conectó')
        provider=MeteredProvider(self.db,OpenAIProvider('test',transport=bad))
        with self.assertRaises(OnlineError):self.chat.send(self.gid,'Consulta',provider)
        self.assertEqual(len(calls),1);self.assertEqual(provider.ledger.summary()['unknown'],1)
        self.assertEqual(self.chat.history(self.gid)[0]['error_kind'],'connection')
    def test_manual_retry_reuses_message_and_counts_new_attempt(self):
        def bad(p):raise OnlineError('service','Error')
        with self.assertRaises(OnlineError):
            self.chat.send(self.gid,'Consulta',MeteredProvider(self.db,OpenAIProvider('test',transport=bad)))
        mid=self.chat.history(self.gid)[0]['id']
        self.chat.send(self.gid,'Consulta',MeteredProvider(self.db,OpenAIProvider('test',transport=lambda p:response())),retry_id=mid)
        history=self.chat.history(self.gid)
        self.assertEqual(len(history),2);self.assertEqual(history[0]['id'],mid)
        self.assertEqual(UsageLedger(self.db).summary()['attempts'],2)
    def test_no_cross_group_retry(self):
        def bad(p):raise OSError('No')
        with self.assertRaises(OSError):self.chat.send(self.gid,'Consulta',type('Bad',(),{'respond':staticmethod(bad)})())
        mid=self.chat.history(self.gid)[0]['id'];other=self.db.group('Otro','2A')
        with self.assertRaises(ValueError):self.chat.send(other,'Consulta',retry_id=mid)
        self.assertEqual(self.chat.history(other),[])
    def test_records_not_sent_without_selection(self):
        self.db.add_student(self.gid,'Nombre privado')
        payloads=[]
        provider=MeteredProvider(self.db,OpenAIProvider('test',transport=lambda p:(payloads.append(p) or response())))
        self.chat.send(self.gid,'Explica el pasado simple',provider,include_records=False)
        self.assertNotIn('Nombre privado',json.dumps(payloads))
    def test_offline_history_not_automatically_sent_online(self):
        self.chat.send(self.gid,'Mensaje básico privado')
        payloads=[]
        p=MeteredProvider(self.db,OpenAIProvider('test',transport=lambda p:(payloads.append(p) or response())))
        self.chat.send(self.gid,'Nueva consulta',p)
        self.assertNotIn('Mensaje básico privado',json.dumps(payloads))
    def test_interrupted_messages_are_retained_for_review(self):
        cid=self.chat.conversation(self.gid)
        with self.db.con:self.db.con.execute("INSERT INTO messages(conversation_id,role,content,state,created_at) VALUES(?,'user','Guardado','pending','2026-01-01')",(cid,))
        self.chat.recover_interrupted()
        self.assertEqual(self.chat.history(self.gid)[0]['state'],'failed')
        self.assertEqual(self.chat.history(self.gid)[0]['content'],'Guardado')
    def test_partial_response_is_visible_and_metered(self):
        p=MeteredProvider(self.db,OpenAIProvider('test',transport=lambda _:response('incomplete')))
        self.assertIn('Respuesta incompleta',self.chat.send(self.gid,'Hola',p))
        self.assertEqual(p.ledger.summary()['output_tokens'],1000)
    def test_missing_usage_never_claims_zero_cost(self):
        p=MeteredProvider(self.db,OpenAIProvider('test',transport=lambda _:response(usage=False)))
        self.chat.send(self.gid,'Hola',p);self.assertEqual(p.ledger.summary()['unknown'],1)
    def test_month_rollover_and_pending_reservations_count(self):
        ledger=UsageLedger(self.db);ledger.reserve('Económico',1,month='2026-10')
        with self.assertRaises(OnlineError):ledger.reserve('Económico',1,month='2026-10')
        ledger.reserve('Económico',1,month='2026-11')
        self.assertEqual(ledger.summary('2026-10')['unknown'],1)
    def test_error_categories_are_distinct(self):
        for status,code,expected in [(401,'','authentication'),(403,'','permission'),(429,'insufficient_quota','quota'),(429,'rate_limit_exceeded','rate_limit'),(503,'','service')]:
            self.assertEqual(classify_http(status,code).kind,expected)
    def test_http_error_does_not_expose_server_echoed_secret(self):
        secret='sk-secret-for-test'
        error=HTTPError('https://api.openai.com/v1/responses',401,'Unauthorized',{},io.BytesIO(json.dumps({'error':{'message':secret,'code':'invalid_api_key'}}).encode()))
        with patch('online.build_opener') as opener:
            opener.return_value.open.side_effect=error
            with self.assertRaises(OnlineError) as exc:OpenAIProvider(secret).respond([{'role':'user','content':'Hi'}])
        self.assertNotIn(secret,str(exc.exception))
    def test_network_error_classified_without_claiming_no_internet(self):
        with patch('online.build_opener') as opener:
            opener.return_value.open.side_effect=URLError('unreachable')
            with self.assertRaises(OnlineError) as exc:OpenAIProvider('test').respond([])
        self.assertEqual(exc.exception.kind,'connection')
    def test_config_contains_no_secrets(self):
        settings=Settings(self.temp.name)
        settings.save({'api_key':'SECRET','monthly_limit':33})
        self.assertNotIn('SECRET',settings.path.read_text())
        self.assertEqual(settings.load()['monthly_limit'],33)
    def test_unknown_model_price_is_not_invented(self):
        ledger=UsageLedger(self.db);rid=ledger.reserve('Económico',10)
        ledger.finish(rid,Reply('text',1,2,'resp','unpriced-model'))
        self.assertEqual(ledger.summary()['unknown'],1)
    @unittest.skipUnless(os.name=='nt','Windows DPAPI test')
    def test_windows_credential_roundtrip(self):
        vault=CredentialVault(self.temp.name);vault.save('test-key-private')
        self.assertNotIn(b'test-key-private',vault.path.read_bytes())
        self.assertEqual(vault.load(),'test-key-private');vault.delete();self.assertFalse(vault.path.exists())

if __name__=='__main__':unittest.main()
