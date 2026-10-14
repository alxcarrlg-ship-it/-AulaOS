import io
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch
import wave
from core import Store
from chat import ChatService
from folders import Folders, safe_file
from voice import VoiceNotes, Transcriber, read_audio, record_wav, MAX_AUDIO
from online import OnlineError, UsageLedger

class LocalTest(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.store=Store(self.root/'db.sqlite3')
        self.gid=self.store.group('A','1');self.other=self.store.group('B','1');self.folder=self.root/'files';self.folder.mkdir()
    def tearDown(self):self.store.close();self.tmp.cleanup()
    def catalog(self):
        service=Folders(self.store);fid=service.add(self.gid,self.folder);return service,fid
    def test_catalog_names_only_supported_and_nested(self):
        (self.folder/'guía.txt').write_text('Hola');(self.folder/'private.exe').write_text('No');(self.folder/'sub').mkdir();(self.folder/'sub'/'plan.md').write_text('Texto')
        service,fid=self.catalog();service.scan(self.gid,fid)
        self.assertEqual(len(service.search(self.gid)),2);self.assertEqual(len(service.search(self.gid,'guia')),1)
        self.assertEqual(service.materials.list(self.gid),[])
    def test_scope_and_remove_preserve_material(self):
        (self.folder/'a.txt').write_text('Hola');service,fid=self.catalog();service.scan(self.gid,fid)
        item=service.read(self.gid,fid,'a.txt');mid=service.snapshot(self.gid,fid,'a.txt',item['digest'])
        with self.assertRaises(ValueError):service.read(self.other,fid,'a.txt')
        service.remove(self.gid,fid);self.assertEqual(service.search(self.gid),[]);self.assertEqual(service.materials.get(self.gid,mid)['content'],'Hola')
        self.assertTrue((self.folder/'a.txt').exists())
    def test_changed_after_preview_rejected(self):
        path=self.folder/'a.txt';path.write_text('Primero');service,fid=self.catalog();service.scan(self.gid,fid);item=service.read(self.gid,fid,'a.txt')
        path.write_text('Segundo texto')
        with self.assertRaises(ValueError):service.snapshot(self.gid,fid,'a.txt',item['digest'])
        self.assertTrue(service.read(self.gid,fid,'a.txt')['changed'])
    def test_missing_removed_on_refresh(self):
        path=self.folder/'a.txt';path.write_text('Hola');service,fid=self.catalog();service.scan(self.gid,fid);path.unlink()
        with self.assertRaises(OSError):service.read(self.gid,fid,'a.txt')
        service.scan(self.gid,fid);self.assertEqual(service.search(self.gid),[])
    def test_symlinks_and_traversal(self):
        outside=self.root/'outside.txt';outside.write_text('Privado');(self.folder/'link.txt').symlink_to(outside)
        service,fid=self.catalog();service.scan(self.gid,fid);self.assertEqual(service.search(self.gid),[])
        with self.assertRaises(ValueError):safe_file(self.folder,'../outside.txt')
        with self.assertRaises(ValueError):safe_file(self.folder,'link.txt')
    def test_scan_limit_reported(self):
        for i in range(6):(self.folder/f'{i}.txt').write_text('X')
        service,fid=self.catalog()
        with patch('folders.MAX_ENTRIES',2):notice=service.scan(self.gid,fid)
        self.assertIn('parcial',notice);self.assertLessEqual(len(service.search(self.gid)),2)
    def test_disconnected_keeps_catalog(self):
        (self.folder/'a.txt').write_text('Hola');service,fid=self.catalog();service.scan(self.gid,fid);self.folder.rename(self.root/'moved')
        with self.assertRaises(ValueError):service.scan(self.gid,fid)
        self.assertEqual(len(service.search(self.gid)),1)
    def test_chat_search_no_provider(self):
        class Forbidden:
            def respond(self,messages):raise AssertionError('Network')
        (self.folder/'plan.txt').write_text('Contenido');service,fid=self.catalog();service.scan(self.gid,fid)
        result=ChatService(self.store).send(self.gid,'/buscar plan',Forbidden())
        self.assertIn('plan.txt',result);self.assertNotIn('Contenido',result);self.assertEqual(UsageLedger(self.store).summary()['attempts'],0)
    def test_filename_not_in_upload_and_json_fields(self):
        captured=[]
        provider=Transcriber('fake',lambda body,kind:captured.append((body,kind)) or {'text':' Hola '})
        self.assertEqual(provider.transcribe(b'bytes','.wav','es'),'Hola')
        body,kind=captured[0];self.assertIn(b'filename="audio.wav"',body);self.assertIn(b'gpt-4o-mini-transcribe',body);self.assertIn(b'name="language"',body);self.assertNotIn(b'fake',body)
    def test_no_empty_or_bad_audio_request(self):
        provider=Transcriber('fake',lambda *args:self.fail('Called transport'))
        for data,suffix in ((b'', '.wav'),(b'X','.exe')):
            with self.assertRaises(ValueError):provider.transcribe(data,suffix)
        with patch('voice.MAX_AUDIO',1):
            with self.assertRaises(ValueError):provider.transcribe(b'XX','.wav')
    def test_invalid_response(self):
        for result in ({}, {'text':''}, ['bad'], {'text':9}):
            with self.assertRaises(OnlineError):Transcriber('fake',lambda *args:result).transcribe(b'X','.mp3')
    def test_transcription_saved_scoped_unknown_cost(self):
        service=VoiceNotes(self.store);provider=Transcriber('fake',lambda *args:{'text':'/tarea Revisar'})
        nid=service.transcribe(self.gid,b'X','.wav',provider,10)
        self.assertEqual(service.get(self.gid,nid)['text'],'/tarea Revisar');self.assertEqual(self.store.tasks(),[])
        with self.assertRaises(ValueError):service.get(self.other,nid)
        summary=service.ledger.summary();self.assertEqual(summary['attempts'],1);self.assertEqual(summary['unknown'],1)
    def test_failure_no_auto_retry(self):
        calls=[]
        def fail(*args):calls.append(1);raise OnlineError('connection','Offline')
        service=VoiceNotes(self.store)
        with self.assertRaises(OnlineError):service.transcribe(self.gid,b'X','.wav',Transcriber('fake',fail),10)
        self.assertEqual(len(calls),1);self.assertEqual(service.list(self.gid),[]);self.assertEqual(service.ledger.summary()['attempts'],1)
    def test_shared_monthly_limit(self):
        ledger=UsageLedger(self.store);ledger.reserve('Económico',1)
        service=VoiceNotes(self.store)
        with self.assertRaises(OnlineError):service.transcribe(self.gid,b'X','.wav',Transcriber('fake',lambda *args:self.fail('Called')),1)
    def test_invalid_group_does_not_consume(self):
        service=VoiceNotes(self.store)
        with self.assertRaises(ValueError):service.transcribe(999,b'X','.wav',Transcriber('fake'),10)
        self.assertEqual(service.ledger.summary()['attempts'],0)
    def test_recording_bounded_no_network(self):
        class Stream:
            def __enter__(self):return self
            def __exit__(self,*args):pass
            def read(self,count):return b'\x00\x00'*count,False
        class Backend:
            RawInputStream=lambda *args,**kwargs:Stream()
        data=record_wav(threading.Event(),seconds=1,backend=Backend())
        with wave.open(io.BytesIO(data),'rb') as wav:self.assertEqual(wav.getnframes(),16000);self.assertEqual(wav.getnchannels(),1)
    def test_record_cancel_before_capture(self):
        class Stream:
            def __enter__(self):return self
            def __exit__(self,*args):pass
        class Backend:RawInputStream=lambda *args,**kwargs:Stream()
        stop=threading.Event();stop.set()
        with self.assertRaises(ValueError):record_wav(stop,backend=Backend())
    def test_original_audio_unchanged(self):
        path=self.root/'audio.wav';path.write_bytes(b'Original');data,suffix=read_audio(path)
        self.assertEqual(data,b'Original');self.assertEqual(suffix,'.wav');self.assertEqual(path.read_bytes(),b'Original')
