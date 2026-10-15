"""Non-secret settings and Windows user-scoped encrypted credential storage."""
import json
import os
from pathlib import Path
from online import PROFILES

DEFAULTS={'mode':'Básico sin conexión','profile':'Económico','monthly_limit':100,
          'max_output_tokens':1800,'include_records':False}

class Settings:
    def __init__(self,folder):
        self.folder=Path(folder);self.folder.mkdir(parents=True,exist_ok=True)
        self.path=self.folder/'settings.json'
    def load(self):
        try:
            data=json.loads(self.path.read_text(encoding='utf-8'))
            return self.validate(data)
        except (OSError,ValueError,TypeError):return dict(DEFAULTS)
    @staticmethod
    def validate(data):
        if not isinstance(data,dict):raise ValueError('Configuración inválida')
        result={key:data.get(key,value) for key,value in DEFAULTS.items()}
        if result['mode'] not in ('Básico sin conexión','OpenAI online') or result['profile'] not in PROFILES:
            raise ValueError('Configuración de IA inválida')
        for key,low,high in [('monthly_limit',1,10000),('max_output_tokens',256,4096)]:
            if type(result[key]) is not int or not low <= result[key] <= high:raise ValueError('Límite inválido')
        if type(result['include_records']) is not bool:raise ValueError('Contexto inválido')
        return result
    def save(self,data):
        clean=self.validate(data)
        tmp=self.path.with_suffix('.tmp');tmp.write_text(json.dumps(clean,ensure_ascii=False,indent=2),encoding='utf-8')
        os.replace(tmp,self.path)


def _dpapi(raw,protect):
    if os.name!='nt':raise RuntimeError('El guardado cifrado está disponible en Windows; usa clave de sesión en este entorno.')
    import ctypes
    from ctypes import wintypes
    class Blob(ctypes.Structure):
        _fields_=[('size',wintypes.DWORD),('data',ctypes.POINTER(ctypes.c_ubyte))]
    buffer=ctypes.create_string_buffer(raw)
    source=Blob(len(raw),ctypes.cast(buffer,ctypes.POINTER(ctypes.c_ubyte)));target=Blob()
    crypt=ctypes.WinDLL('crypt32',use_last_error=True)
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    fn=crypt.CryptProtectData if protect else crypt.CryptUnprotectData
    fn.argtypes=[ctypes.POINTER(Blob),ctypes.c_void_p,ctypes.POINTER(Blob),ctypes.c_void_p,ctypes.c_void_p,wintypes.DWORD,ctypes.POINTER(Blob)]
    fn.restype=wintypes.BOOL
    kernel.LocalFree.argtypes=[ctypes.c_void_p];kernel.LocalFree.restype=ctypes.c_void_p
    if not fn(ctypes.byref(source),None,None,None,None,1,ctypes.byref(target)):
        raise OSError('Windows no pudo proteger o recuperar la credencial de este usuario.')
    try:return ctypes.string_at(target.data,target.size)
    finally:kernel.LocalFree(target.data)

class CredentialVault:
    def __init__(self,folder):self.path=Path(folder)/'openai-key.dpapi'
    def load(self):
        if not self.path.exists():return os.environ.get('OPENAI_API_KEY','')
        return _dpapi(self.path.read_bytes(),False).decode('utf-8')
    def save(self,key):
        data=_dpapi(key.strip().encode('utf-8'),True)
        self.path.parent.mkdir(parents=True,exist_ok=True)
        tmp=self.path.with_suffix('.tmp');tmp.write_bytes(data);os.replace(tmp,self.path)
    def delete(self):self.path.unlink(missing_ok=True)
