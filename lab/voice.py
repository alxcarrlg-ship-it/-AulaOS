"""Review-first file transcription and bounded local microphone capture."""
import io
import json
from pathlib import Path
import socket
import ssl
import uuid
import wave
from urllib.request import Request, build_opener
from urllib.error import HTTPError, URLError
from core import now
from online import NoRedirect, OnlineError, classify_http, UsageLedger

MODEL='gpt-4o-mini-transcribe'
MAX_AUDIO=25_000_000
EXTENSIONS={'.mp3','.mp4','.mpeg','.mpga','.m4a','.wav','.webm'}


def validate_audio(data,suffix):
    if suffix.lower() not in EXTENSIONS:raise ValueError('Audio compatible: MP3, MP4, MPEG, MPGA, M4A, WAV o WebM.')
    if not data or len(data)>MAX_AUDIO:raise ValueError('El audio debe tener contenido y no superar 25 MB.')


def read_audio(path):
    path=Path(path)
    if not path.is_file():raise ValueError('Elige un archivo de audio normal.')
    with path.open('rb') as stream:data=stream.read(MAX_AUDIO+1)
    validate_audio(data,path.suffix)
    return data,path.suffix.lower()


def record_wav(stop,seconds=30,backend=None):
    if not 1<=seconds<=30:raise ValueError('La grabación admite hasta 30 segundos.')
    if backend is None:
        try:import sounddevice as backend
        except (ImportError,OSError):raise RuntimeError('El componente de micrófono no está disponible. Puedes elegir un archivo de audio.') from None
    frames=[];rate=16000;block=1600
    with backend.RawInputStream(samplerate=rate,channels=1,dtype='int16',blocksize=block) as stream:
        for _ in range(int(seconds*rate/block)):
            if stop.is_set():break
            data,overflow=stream.read(block)
            if overflow:raise RuntimeError('El micrófono perdió muestras. Graba otra vez o elige un archivo.')
            frames.append(bytes(data))
    if not frames:raise ValueError('No se capturó audio.')
    out=io.BytesIO()
    with wave.open(out,'wb') as wav:
        wav.setnchannels(1);wav.setsampwidth(2);wav.setframerate(rate);wav.writeframes(b''.join(frames))
    return out.getvalue()


class Transcriber:
    def __init__(self,key,transport=None):
        if not key or not key.strip():raise OnlineError('configuration','Conecta tu clave de OpenAI para transcribir. Grabar y escribir siguen disponibles sin conexión.')
        self.key=key.strip();self.transport=transport or self.http
    def transcribe(self,data,suffix,language=''):
        validate_audio(data,suffix)
        if language not in ('','es','en'):raise ValueError('Idioma no admitido.')
        boundary='AulaOS'+uuid.uuid4().hex
        while boundary.encode() in data:boundary='AulaOS'+uuid.uuid4().hex
        fields={'model':MODEL,'response_format':'json'}
        if language:fields['language']=language
        body=b''
        for name,value in fields.items():
            body+=f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'.encode()
        # Never expose a local path, student's name or original filename in the upload.
        body+=f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="audio{suffix.lower()}"\r\nContent-Type: application/octet-stream\r\n\r\n'.encode()+data+f'\r\n--{boundary}--\r\n'.encode()
        result=self.transport(body,'multipart/form-data; boundary='+boundary)
        if not isinstance(result,dict) or not isinstance(result.get('text'),str) or not result['text'].strip():raise OnlineError('empty','No llegó una transcripción legible. Puede haber consumo; no se reintentó.')
        if len(result['text'])>120000:raise OnlineError('protocol','La transcripción supera el límite de texto.')
        return result['text'].strip()
    def http(self,body,content_type):
        req=Request('https://api.openai.com/v1/audio/transcriptions',data=body,headers={'Authorization':'Bearer '+self.key,'Content-Type':content_type})
        try:
            with build_opener(NoRedirect()).open(req,timeout=120) as response:raw=response.read(2*1024*1024+1)
            if len(raw)>2*1024*1024:raise OnlineError('protocol','Respuesta de transcripción demasiado grande.')
            return json.loads(raw)
        except HTTPError as exc:
            code=''
            try:code=json.loads(exc.read(65536)).get('error',{}).get('code','')
            except (ValueError,AttributeError):pass
            raise classify_http(exc.code,code) from None
        except ssl.SSLError:raise OnlineError('security','No se pudo verificar la conexión segura.') from None
        except (URLError,OSError,socket.timeout):raise OnlineError('connection','No se completó la transcripción. Puedes reintentar manualmente; podría haber consumo.') from None
        except (ValueError,TypeError):raise OnlineError('protocol','Respuesta de transcripción ilegible.') from None


class VoiceNotes:
    def __init__(self,store):
        self.store=store;self.ledger=UsageLedger(store)
        store.con.execute('''CREATE TABLE IF NOT EXISTS voice_notes(id INTEGER PRIMARY KEY,
          group_id INTEGER REFERENCES groups(id),text TEXT NOT NULL,model TEXT NOT NULL,
          usage_id INTEGER REFERENCES online_usage(id),created_at TEXT NOT NULL)''');store.con.commit()
    def transcribe(self,gid,data,suffix,provider,limit,language=''):
        validate_audio(data,suffix)
        if language not in ('','es','en'):raise ValueError('Idioma no admitido.')
        if gid is not None and not self.store.con.execute('SELECT 1 FROM groups WHERE id=?',(gid,)).fetchone():raise ValueError('Grupo inexistente.')
        rid=self.ledger.reserve('Transcripción de voz',limit)
        try:text=provider.transcribe(data,suffix,language)
        except Exception as exc:
            self.ledger.finish(rid,error=getattr(exc,'kind','unknown'));raise
        # Audio tariffs differ from text profiles: report unknown cost, never a zero estimate.
        with self.store.con:
            self.store.con.execute("UPDATE online_usage SET state='complete',web_estimate_usd=0 WHERE id=?",(rid,))
            return self.store.con.execute('INSERT INTO voice_notes(group_id,text,model,usage_id,created_at) VALUES(?,?,?,?,?)',(gid,text,MODEL,rid,now())).lastrowid
    def get(self,gid,nid):
        row=self.store.con.execute('SELECT * FROM voice_notes WHERE id=? AND group_id IS ?',(nid,gid)).fetchone()
        if row is None:raise ValueError('Transcripción no disponible en este grupo.')
        return dict(row)
    def list(self,gid):return [dict(r) for r in self.store.con.execute('SELECT * FROM voice_notes WHERE group_id IS ? ORDER BY id DESC',(gid,))]
