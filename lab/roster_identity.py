"""Deterministic roster matching. Rows are order, not student identity."""
from collections import Counter,defaultdict
import re

HEADERS={'matricula','id alumno','identificador','student id','numero de control'}

def identifier(value):
    if value is None or value=='':return None
    # Identifiers must be text: numeric spreadsheet cells can lose leading zeros.
    if not isinstance(value,str):raise ValueError('La matrícula debe estar guardada como texto, conservando ceros iniciales. No se importó la lista.')
    result=value.strip().upper()
    if not result:return None
    if len(result)>80 or not re.fullmatch(r'[A-Z0-9][A-Z0-9._/-]*',result):raise ValueError('Matrícula inválida: usa hasta 80 letras, números o . _ / - sin espacios.')
    return result

def header_index(headers,normalize):
    hits=[i for i,h in enumerate(headers) if normalize(h) in HEADERS]
    if len(hits)>1:raise ValueError('Hay varias columnas de matrícula/identificador. Conserva solo una para importar.')
    return hits[0] if hits else None

def resolve(known,roster,normalize):
    """Roster contains dictionaries row/name/external_id/marks; return matched IDs."""
    names=Counter(normalize(r['name']) for r in roster)
    ids=[r['external_id'] for r in roster if r['external_id']]
    if len(ids)!=len(set(ids)):raise ValueError('Hay matrículas duplicadas en la lista; no se aplicaron cambios.')
    if any(names[normalize(r['name'])]>1 and not r['external_id'] for r in roster):raise ValueError('Hay nombres idénticos (homónimos) sin matrícula: cada uno necesita un identificador distinto.')
    by_name=defaultdict(list);by_id={}
    for person in known:
        by_name[normalize(person['name'])].append(person)
        if person['external_id']:by_id[person['external_id']]=person
    result=[];used=set()
    for row in roster:
        key=row['external_id'];matches=by_name[normalize(row['name'])];chosen=by_id.get(key) if key else None
        if chosen is None:
            if len(matches)>1:raise ValueError('Identidades registradas ambiguas. Asigna matrículas a los alumnos existentes antes de importar.')
            if matches:
                match=matches[0]
                if key and match['external_id'] and key!=match['external_id']:raise ValueError('La matrícula no coincide con la registrada para '+row['name']+'. Revisa la identidad antes de importar.')
                if key and names[normalize(row['name'])]>1:raise ValueError('No se puede asignar por nombre una matrícula a homónimos existentes. Asigna primero sus matrículas en la lista local.')
                chosen=match
        if chosen is not None:
            if chosen['id'] in used:raise ValueError('Dos filas apuntan al mismo alumno; no se aplicaron cambios.')
            used.add(chosen['id'])
        result.append(dict(row,student_id=chosen['id'] if chosen else None,external_id=key or (chosen['external_id'] if chosen else None)))
    return result
