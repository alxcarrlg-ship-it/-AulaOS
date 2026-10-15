"""Reviewable navigation plans: open existing tools, never execute model code."""
import json
import re
from core import normalize,now
from projects import Projects
from templates import Templates
from template_suggestions import unique_object

TOOLS={'project':'Proyecto y avance','evidence':'Evidencias del proyecto','planning':'Editar planeación','lesson':'Materiales de clase','resources':'Recursos web','action':'Preparar tarea, observación o borrador'}
SYSTEM='''Organiza una petición docente como hasta cuatro pasos revisables. No ejecutes acciones. Devuelve solo JSON con steps y clarification. Si falta identificar un destino, deja steps vacío y pregunta en clarification. Cada paso tiene tool, target y request. tool es project (ver/editar avance), evidence (ver/registrar evidencias de proyecto), planning (editar planeación), lesson (preparar materiales de una planeación), resources (buscar recursos web), action (preparar tarea, observación individual o borrador). Para project/evidence/planning/lesson, target debe ser un nombre de proyecto/planeación o #ID copiado literalmente de la petición, nunca inventado. Para resources/action, target es null. request es la instrucción para ese paso. No prometas haber guardado, generado, exportado o enviado nada. No inventes datos ni pasos dependientes de resultados aún inexistentes. No hay ejecución de código, borrado ni envío a terceros.'''

def is_workflow(text):return bool(re.match(r'^/trabajar(?:\s|$)',text.strip(),re.I))

class Workflows:
    def __init__(self,store):self.store=store;self.projects=Projects(store);self.templates=Templates(store)
    def catalog(self,gid):
        return {'projects':[{'id':r['id'],'title':r['title']} for r in self.projects.list(gid)],'planning':[{'id':r['id'],'title':r['title']} for r in self.templates.documents(gid)]}
    def resolve(self,gid,tool,target):
        rows=self.projects.list(gid) if tool in ('project','evidence') else self.templates.documents(gid)
        hits=[r for r in rows if '#'+str(r['id'])==target or normalize(r['title'])==normalize(target)]
        if len(hits)!=1:raise ValueError('Destino inexistente o ambiguo en este grupo. Usa el #ID del catálogo local.')
        r=hits[0];return {'id':r['id'],'title':r['title'],'revision':r.get('revision',r.get('current_revision'))}
    def prepare(self,gid,goal,provider=None):
        self.projects.group(gid)
        if not isinstance(goal,str) or not goal.strip() or len(goal)>6000:raise ValueError('Petición obligatoria de hasta 6000 caracteres.')
        goal=goal.strip()
        if provider is None:
            match=re.fullmatch(r'(proyecto|evidencias|planeacion|planeación|materiales)\s+(#\d+)',goal,re.I)
            if not match:raise ValueError('Sin IA usa: proyecto #ID, evidencias #ID, planeación #ID o materiales #ID. Para una petición libre, activa la interpretación online.')
            tool={'proyecto':'project','evidencias':'evidence','planeacion':'planning','planeación':'planning','materiales':'lesson'}[match[1].lower()]
            data={'steps':[{'tool':tool,'target':match[2],'request':goal}],'clarification':''}
        else:
            raw=provider.respond([{'role':'system','content':SYSTEM},{'role':'user','content':goal}])
            if not isinstance(raw,str) or len(raw)>30000:raise ValueError('Ruta de trabajo inválida.')
            try:data=json.loads(raw,object_pairs_hook=unique_object)
            except (json.JSONDecodeError,RecursionError) as exc:raise ValueError('Respuesta incompleta; no se guardó una ruta.') from exc
        if not isinstance(data,dict) or set(data)!={'steps','clarification'} or not isinstance(data['steps'],list) or len(data['steps'])>4 or not isinstance(data['clarification'],str) or len(data['clarification'])>3000:raise ValueError('Formato de ruta inválido.')
        if not data['steps']:
            if not data['clarification'].strip():raise ValueError('Falta aclaración.')
            return None,data['clarification']
        if data['clarification']:raise ValueError('La respuesta mezcla pasos y una aclaración pendiente.')
        steps=[]
        for step in data['steps']:
            if not isinstance(step,dict) or set(step)!={'tool','target','request'}:raise ValueError('Paso inválido.')
            tool=step['tool'];target=step['target'];request=step['request']
            if not isinstance(tool,str) or tool not in TOOLS or not isinstance(request,str) or not request.strip() or len(request)>6000:raise ValueError('Herramienta o petición inválida.')
            destination=None
            if tool in ('resources','action'):
                if target is not None:raise ValueError('Destino inesperado.')
            else:
                if not isinstance(target,str) or not target.strip() or not re.search(r'(?<!\w)'+re.escape(normalize(target))+r'(?!\w)',normalize(goal)):raise ValueError('El destino no aparece literalmente en tu petición.')
                destination=self.resolve(gid,tool,target)
            steps.append(dict(tool=tool,destination=destination,request=request))
        with self.store.con:
            wid=self.store.con.execute('INSERT INTO workflow_plans(group_id,goal,steps_json,created_at) VALUES(?,?,?,?)',(gid,goal,json.dumps(steps,ensure_ascii=False),now())).lastrowid
        return wid,''
    def get(self,gid,wid):
        row=self.store.con.execute('SELECT * FROM workflow_plans WHERE id=? AND group_id=?',(wid,gid)).fetchone()
        if row is None:raise ValueError('Ruta no disponible en este grupo.')
        return dict(row,steps=json.loads(row['steps_json']))
    def list(self,gid):
        self.projects.group(gid)
        return [dict(r) for r in self.store.con.execute('SELECT id,goal,created_at FROM workflow_plans WHERE group_id=? ORDER BY id DESC',(gid,))]
    def step(self,gid,wid,index):
        steps=self.get(gid,wid)['steps']
        if type(index) is not int or not 0<=index<len(steps):raise ValueError('Paso inexistente.')
        step=steps[index];dest=step['destination']
        if dest:
            current=self.resolve(gid,step['tool'],'#'+str(dest['id']))
            if current!=dest:raise ValueError('El destino cambió desde que se preparó la ruta. Prepara una ruta nueva para revisar su versión actual.')
        return step
