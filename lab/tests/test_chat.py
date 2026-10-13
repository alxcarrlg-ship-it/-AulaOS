import json
import tempfile
import unittest
from pathlib import Path
from core import Store
from chat import ChatService,OllamaProvider

class CaptureProvider:
    def __init__(self):self.messages=None
    def respond(self,messages):self.messages=messages;return 'Respuesta de prueba'

class ChatTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.path=Path(self.temp.name)/'db.sqlite3'
        self.db=Store(self.path);self.a=self.db.group('Escuela A','2A');self.b=self.db.group('Escuela B','2A')
        self.chat=ChatService(self.db)
    def tearDown(self):self.db.close();self.temp.cleanup()
    def test_history_survives_restart(self):
        self.chat.send(self.a,'Hola',CaptureProvider());self.db.close();self.db=Store(self.path)
        self.assertEqual(len(ChatService(self.db).history(self.a)),2)
    def test_group_context_and_conversations_are_isolated(self):
        self.db.add_student(self.a,'Rosa Ejemplo');self.db.add_student(self.b,'Mateo Ejemplo')
        self.db.create_task('Privado de A',self.a);self.chat.send(self.a,'Mensaje exclusivo A',CaptureProvider())
        p=CaptureProvider();self.chat.send(self.b,'Hola B',p)
        payload=json.dumps(p.messages,ensure_ascii=False)
        self.assertNotIn('Rosa',payload);self.assertNotIn('Privado de A',payload);self.assertNotIn('Mensaje exclusivo A',payload)
        self.assertIn('Mateo',payload);self.assertEqual(self.chat.history(None),[])
    def test_provider_failure_is_not_an_assistant_answer(self):
        class Failed:
            def respond(self,messages):raise OSError('Sin modelo')
        with self.assertRaises(OSError):self.chat.send(self.a,'Fallará',Failed())
        self.assertEqual(self.chat.history(self.a)[0]['state'],'failed')
        p=CaptureProvider();self.chat.send(self.a,'Nuevo',p)
        self.assertNotIn('Fallará',json.dumps(p.messages))
    def test_offline_tasks_are_scoped(self):
        self.db.create_task('Solo A',self.a);self.db.create_task('Solo B',self.b)
        self.assertNotIn('Solo B',self.chat.send(self.a,'Pendientes'))
    def test_nonlocal_provider_rejected(self):
        with self.assertRaises(ValueError):OllamaProvider('modelo','https://example.com')
    def test_http_provider_contract(self):
        from http.server import BaseHTTPRequestHandler,HTTPServer
        import threading
        received=[]
        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                received.append((self.path,json.loads(self.rfile.read(int(self.headers['Content-Length'])))))
                self.send_response(200);self.end_headers();self.wfile.write(b'{"message":{"content":"ok"}}')
            def log_message(self,*args):pass
        server=HTTPServer(('127.0.0.1',0),Handler);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        try:
            p=OllamaProvider('modelo',f'http://127.0.0.1:{server.server_port}')
            self.assertEqual(p.respond([{'role':'user','content':'hola'}]),'ok')
            self.assertEqual(received[0][0],'/api/chat');self.assertFalse(received[0][1]['stream'])
        finally:server.shutdown();server.server_close();thread.join()
