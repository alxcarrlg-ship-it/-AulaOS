"""OpenAI Responses adapter. No automatic retries or embedded credentials."""
from dataclasses import dataclass
from research import domains, render_web, SEARCH_PRICE_USD, MAX_TOOL_CALLS
import datetime as dt
import json
import socket
import ssl
from urllib.error import HTTPError, URLError
from urllib.request import Request, build_opener, HTTPRedirectHandler

# Standard text prices per million tokens, verified 2026-10-13.
# Estimates only: ignore cache discounts; search action costs are recorded separately.
PROFILES = {
    'Económico': ('gpt-6-luna', .10, .50),
    'Mayor capacidad': ('gpt-6.1-sol', 2.00, 10.00),
}
PRICE_DATE = '2026-10-13'

class OnlineError(RuntimeError):
    def __init__(self, kind, message):
        super().__init__(message)
        self.kind = kind

class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None

@dataclass(frozen=True)
class Reply:
    text: str
    input_tokens: int | None
    output_tokens: int | None
    response_id: str
    model: str
    incomplete: bool = False
    web_searches: int | None = 0
    sources: tuple = ()
    research: bool = False
    evidence: str = ""


def classify_http(status, code=''):
    if status == 401:
        return OnlineError('authentication', 'La clave de OpenAI no fue aceptada. Revisa la conexión de tu cuenta.')
    if status == 403:
        return OnlineError('permission', 'La cuenta no tiene permiso para esta operación o modelo.')
    if code in {'insufficient_quota', 'credit_balance_exhausted', 'billing_hard_limit_reached',
                'organization_spend_limit_exceeded', 'project_spend_limit_exceeded',
                'organization_usage_limit_exceeded'}:
        return OnlineError('quota', 'OpenAI indica falta de crédito o un límite de gasto. El modo básico sigue disponible.')
    if status == 429:
        return OnlineError('rate_limit', 'OpenAI está limitando las solicitudes. Puedes reintentar más tarde.')
    if status >= 500:
        return OnlineError('service', 'OpenAI no pudo completar la solicitud. Tu mensaje sigue guardado.')
    return OnlineError('request', 'OpenAI rechazó la solicitud. Revisa el modelo o la configuración; no se reintentó automáticamente.')


class OpenAIProvider:
    def __init__(self, api_key, profile='Económico', max_output_tokens=1800, transport=None, research=False, allowed_domains=None):
        if not api_key or not api_key.strip():
            raise OnlineError('configuration', 'Conecta tu clave de OpenAI para usar IA online. El modo básico ya funciona.')
        if profile not in PROFILES:
            raise ValueError('Perfil desconocido')
        if not 256 <= max_output_tokens <= 4096:
            raise ValueError('El límite de respuesta debe estar entre 256 y 4096 tokens')
        self.research=bool(research)
        self.allowed_domains=domains(allowed_domains)
        self.request_options={"research":True,"domains":self.allowed_domains} if self.research else {}
        self._key = api_key.strip()
        self.profile = profile
        self.model = PROFILES[profile][0]
        self.max_output_tokens = max_output_tokens
        self.transport = transport or self._http

    def _http(self, payload):
        request = Request('https://api.openai.com/v1/responses',
                          data=json.dumps(payload).encode('utf-8'),
                          headers={'Authorization': 'Bearer '+self._key, 'Content-Type': 'application/json'})
        try:
            with build_opener(NoRedirect()).open(request, timeout=120 if self.research else 60) as response:
                body = response.read(4*1024*1024 + 1)
            if len(body) > 4*1024*1024:
                raise OnlineError('protocol', 'La respuesta superó el tamaño permitido; no se reintentó.')
            return json.loads(body)
        except HTTPError as exc:
            code = ''
            try:
                body = json.loads(exc.read(65536))
                code = body.get('error', {}).get('code', '')
            except (ValueError, AttributeError):
                pass
            raise classify_http(exc.code, code) from None
        except ssl.SSLError:
            raise OnlineError('security', 'No se pudo verificar la conexión segura con OpenAI.') from None
        except (URLError, OSError, socket.timeout):
            raise OnlineError('connection', 'No se pudo completar la conexión con OpenAI. El mensaje quedó guardado; un reintento sería una nueva solicitud y podría generar consumo.') from None
        except (ValueError, TypeError):
            raise OnlineError('protocol', 'OpenAI devolvió una respuesta ilegible. El mensaje quedó guardado.') from None

    def respond(self, messages):
        # Bound transfer size. Context selection belongs to ChatService.
        if len(json.dumps(messages, ensure_ascii=False).encode('utf-8')) > 60000:
            raise OnlineError('context', 'El contexto es demasiado grande. Reduce las fuentes o inicia una consulta más específica.')
        payload = {'model': self.model, 'input': messages, 'store': False,
                   'max_output_tokens': self.max_output_tokens, 'reasoning': {'effort': 'low'},
                   'service_tier': 'default'}
        if self.research:
            tool={'type':'web_search','external_web_access':True}
            if self.allowed_domains:tool['filters']={'allowed_domains':self.allowed_domains}
            payload.update(tools=[tool],tool_choice='required',max_tool_calls=MAX_TOOL_CALLS,
                           include=['web_search_call.action.sources'])
        data = self.transport(payload)
        if not isinstance(data, dict):
            raise OnlineError('protocol', 'Formato de respuesta inesperado.')
        if data.get('error'):
            raise OnlineError('service', 'OpenAI no completó la respuesta; tu mensaje quedó guardado.')
        output = data.get('output', [])
        if not isinstance(output, list):
            raise OnlineError('protocol', 'Formato de respuesta inesperado.')
        parts = []
        for item in output:
            if not isinstance(item, dict) or item.get('type') != 'message':
                continue
            for part in item.get('content', []) or []:
                if not isinstance(part,dict):continue
                if part.get('type') == 'output_text' and isinstance(part.get('text'), str):
                    parts.append(part['text'])
                elif part.get('type') == 'refusal' and isinstance(part.get('refusal'), str):
                    parts.append(part['refusal'])
        text = '\n'.join(parts).strip()
        sources=();web_searches=0;evidence=''
        if self.research:text,sources,web_searches,evidence=render_web(output,data.get('status'))
        if not text:
            raise OnlineError('empty', 'El servicio terminó sin texto visible. Puede haber consumo; no se reintentó automáticamente.')
        incomplete = data.get('status') == 'incomplete'
        if data.get('status') not in ('completed', 'incomplete'):
            raise OnlineError('protocol', 'La respuesta no terminó; el mensaje sigue guardado.')
        if incomplete:
            text += '\n\n[Respuesta incompleta: se alcanzó un límite. Continuar requiere otra solicitud.]'
        usage = data.get('usage') or {}
        if not isinstance(usage,dict):usage={}
        def count(name):
            value = usage.get(name)
            return value if type(value) is int and value >= 0 else None
        return Reply(text, count('input_tokens'), count('output_tokens'),
                     str(data.get('id', '')), str(data.get('model', self.model)), incomplete,web_searches,sources,self.research,evidence)


class UsageLedger:
    def __init__(self, store):
        self.con = store.con
        self.con.execute('''CREATE TABLE IF NOT EXISTS online_usage(
            id INTEGER PRIMARY KEY, month TEXT NOT NULL, profile TEXT NOT NULL,
            state TEXT NOT NULL, input_tokens INTEGER, output_tokens INTEGER,
            estimate_usd REAL, response_id TEXT, created_at TEXT NOT NULL)''')
        columns={r[1] for r in self.con.execute('PRAGMA table_info(online_usage)')}
        for name,definition in [('research','INTEGER NOT NULL DEFAULT 0'),('web_searches','INTEGER'),('web_estimate_usd','REAL')]:
            if name not in columns:self.con.execute(f'ALTER TABLE online_usage ADD COLUMN {name} {definition}')
        self.con.commit()

    def reserve(self, profile, limit, month=None, research=False):
        if type(limit) is not int or not 1 <= limit <= 10000:
            raise ValueError('Límite mensual inválido')
        month = month or dt.datetime.now().strftime('%Y-%m')
        # Atomic across different SQLite connections/windows. Pending/errors also count.
        self.con.execute('BEGIN IMMEDIATE')
        try:
            count = self.con.execute('SELECT count(*) FROM online_usage WHERE month=?', (month,)).fetchone()[0]
            if count >= limit:
                raise OnlineError('budget', 'Se alcanzó el límite mensual de solicitudes de AulaOS. El modo básico sigue disponible.')
            rid = self.con.execute('INSERT INTO online_usage(month,profile,state,created_at) VALUES(?,?,?,?)',
                                   (month, profile, 'pending', dt.datetime.now().astimezone().isoformat())).lastrowid
            self.con.execute('UPDATE online_usage SET research=? WHERE id=?',(int(research),rid))
            self.con.commit()
            return rid
        except Exception:
            self.con.rollback()
            raise

    def finish(self, rid, reply=None, error=None):
        estimate = None
        if reply and reply.input_tokens is not None and reply.output_tokens is not None:
            profile = self.con.execute('SELECT profile FROM online_usage WHERE id=?', (rid,)).fetchone()[0]
            model, input_rate, output_rate = PROFILES[profile]
            if reply.model == model or reply.model.startswith(model+'-'):
                estimate = (reply.input_tokens*input_rate+reply.output_tokens*output_rate)/1_000_000
        is_research=self.con.execute('SELECT research FROM online_usage WHERE id=?',(rid,)).fetchone()[0]
        web_estimate=(reply.web_searches*SEARCH_PRICE_USD if reply and reply.web_searches is not None else None) if is_research else 0
        with self.con:
            self.con.execute('UPDATE online_usage SET web_searches=?,web_estimate_usd=? WHERE id=?',
                             (reply.web_searches if reply else None,web_estimate,rid))
            self.con.execute('UPDATE online_usage SET state=?,input_tokens=?,output_tokens=?,estimate_usd=?,response_id=? WHERE id=?',
                ('complete' if reply else (error or 'unknown'), reply.input_tokens if reply else None,
                 reply.output_tokens if reply else None, estimate, reply.response_id if reply else None, rid))

    def summary(self, month=None):
        month = month or dt.datetime.now().strftime('%Y-%m')
        row = self.con.execute('''SELECT count(*) attempts, COALESCE(sum(input_tokens),0) input_tokens,
            COALESCE(sum(output_tokens),0) output_tokens, COALESCE(sum(estimate_usd),0) estimate_usd,
            COALESCE(sum(CASE WHEN estimate_usd IS NULL OR (research=1 AND web_estimate_usd IS NULL) THEN 1 ELSE 0 END),0) unknown,
            COALESCE(sum(web_searches),0) web_searches, COALESCE(sum(web_estimate_usd),0) web_estimate_usd,
            COALESCE(sum(research),0) research_attempts
            FROM online_usage WHERE month=?''', (month,)).fetchone()
        return dict(row)


class MeteredProvider:
    source = "online"
    def __init__(self, store, provider, monthly_limit=100):
        self.research=provider.research;self.request_options=provider.request_options
        self.source="research" if self.research else "online"
        self.provider=provider; self.ledger=UsageLedger(store); self.limit=monthly_limit
    def respond(self, messages):
        self.last_reply=None
        rid=self.ledger.reserve(self.provider.profile, self.limit,research=self.research)
        try:
            reply=self.provider.respond(messages)
        except Exception as exc:
            self.ledger.finish(rid,error=exc.kind if isinstance(exc,OnlineError) else 'unknown')
            raise
        self.ledger.finish(rid,reply=reply)
        self.last_reply=reply
        return reply.text
