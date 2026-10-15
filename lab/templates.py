"""Local DOCX templates and versioned instances. Patch text, preserve package parts."""
import hashlib
import io
import json
from pathlib import Path
import re
import zipfile
from lxml import etree as ET
from core import now
from drafts import RevisionConflict

W='http://schemas.openxmlformats.org/wordprocessingml/2006/main'
NS={'w':W}
def tag(name):return '{'+W+'}'+name
MAX_FILE=10*1024*1024
MAX_EXPANDED=40*1024*1024
PART=re.compile(r'word/(document|header\d+|footer\d+)\.xml$')


def package(data):
    if len(data)>MAX_FILE:raise ValueError('Plantilla demasiado grande: máximo 10 MB.')
    try:
        archive=zipfile.ZipFile(io.BytesIO(data));infos=archive.infolist()
        names=[i.filename for i in infos]
        if len(infos)>3000 or len(set(names))!=len(names) or sum(i.file_size for i in infos)>MAX_EXPANDED:
            raise ValueError('Paquete DOCX demasiado grande o con entradas duplicadas.')
        if 'word/document.xml' not in names or '[Content_Types].xml' not in names:raise ValueError('No es un DOCX válido.')
        if any(n.startswith('/') or '..' in n.split('/') for n in names):raise ValueError('Rutas no admitidas en el DOCX.')
        parts={i.filename:archive.read(i) for i in infos}
        archive.close()
        for name,raw in parts.items():
            if name.endswith(('.xml','.rels')):
                if b'<!DOCTYPE' in raw.upper() or b'<!ENTITY' in raw.upper():raise ValueError('XML con declaraciones externas no admitido.')
                root=parse(raw)
                if name.endswith('.rels'):
                    for rel in root:
                        if rel.get('TargetMode')=='External' and not rel.get('Type','').endswith('/hyperlink'):
                            raise ValueError('La plantilla contiene recursos externos vinculados; incrústalos primero en Word.')
            if any(s in name.lower() for s in ('vbaproject','activex','embeddings/','_xmlsignatures/')):
                raise ValueError('Usa un DOCX sin macros, objetos incrustados o firmas digitales.')
        if b'macroEnabled' in parts['[Content_Types].xml']:raise ValueError('No se admiten documentos con macros.')
        if 'word/settings.xml' in parts and parse(parts['word/settings.xml']).find('w:documentProtection',NS) is not None:
            raise ValueError('La plantilla está protegida. Usa una copia editable autorizada.')
        return parts
    except (zipfile.BadZipFile,ET.XMLSyntaxError,RuntimeError,KeyError) as exc:
        raise ValueError('No se pudo leer el paquete DOCX.') from exc


def parse(raw):return ET.fromstring(raw,ET.XMLParser(resolve_entities=False,no_network=True))
def text_of(node):
    return ''.join(n.text or '' if n.tag==tag('t') else '\n' if n.tag==tag('br') else '\t' for n in node.iter() if n.tag in (tag('t'),tag('br'),tag('tab')))


def editable(p):
    # Never flatten drawings, fields, revisions, hyperlinks or content controls.
    if any(a.tag in (tag('sdt'),tag('ins'),tag('del')) for a in p.iterancestors()):return False
    for child in p:
        if child.tag==tag('pPr'):continue
        if child.tag!=tag('r'):return False
        if any(n.tag not in (tag('rPr'),tag('t'),tag('br'),tag('tab')) for n in child):return False
    return True


def inspect_template(data):
    parts=package(data);fields=[];tables=[];sections=[];skipped=0
    for name in sorted(n for n in parts if PART.fullmatch(n)):
        root=parse(parts[name]);table_nodes=list(root.iter(tag('tbl')))
        for ti,table in enumerate(table_nodes):
            rows=table.findall('w:tr',NS);grid=table.find('w:tblGrid',NS)
            tables.append({'part':name,'table':ti+1,'columns':len(grid) if grid is not None else None,
                          'rows':len(rows),'first_row':[text_of(c) for c in rows[0].findall('w:tc',NS)] if rows else [],
                          'merged':bool(table.findall('.//w:gridSpan',NS) or table.findall('.//w:vMerge',NS))})
        for i,p in enumerate(root.iter(tag('p'))):
            if not editable(p):skipped+=1;continue
            location='Cuerpo' if name=='word/document.xml' else 'Encabezado' if '/header' in name else 'Pie de página'
            cell=next((a for a in p.iterancestors() if a.tag==tag('tc')),None)
            if cell is not None:
                row=cell.getparent();table=row.getparent()
                if table in table_nodes:
                    location+=f" · tabla {table_nodes.index(table)+1}, fila {list(table.findall('w:tr',NS)).index(row)+1}, celda {list(row.findall('w:tc',NS)).index(cell)+1}"
            fields.append({'id':name+':'+str(i),'location':location,'text':text_of(p)})
        for sec in root.iter(tag('sectPr')):
            size=sec.find('w:pgSz',NS)
            sections.append(dict(size.attrib) if size is not None else {})
    if len(fields)>5000:raise ValueError('Máximo 5000 párrafos editables por plantilla.')
    if not fields:raise ValueError('No se encontraron párrafos editables compatibles.')
    from template_recognition import enrich
    return enrich({'fields':fields,'tables':tables,'sections':sections,'images':sum(n.startswith('word/media/') for n in parts),
            'skipped':skipped,'notice':'Reconocimiento estructural; revisa qué campos debes cambiar. Las celdas combinadas conservan su geometría. Los párrafos con objetos, campos o revisiones no se editan.'},parts)


def context_fields(schema,changes):
    """Compact labels for online context; preserve stable IDs and current text."""
    result=[]
    for f in schema['fields']:
        item={k:f[k] for k in ('id','location')}
        item['text']=changes.get(f['id'],f['text'])
        if f.get('label'):item.update(label=f['label'],label_custom=f.get('label_custom',False))
        if f.get('section_hint'):item['section_hint']=f['section_hint']
        result.append(item)
    return result

def validate_changes(schema,changes):
    if not isinstance(changes,dict):raise ValueError('Cambios no válidos.')
    allowed={f['id'] for f in schema['fields']}
    if not set(changes)<=allowed:raise ValueError('Campo ajeno a esta plantilla.')
    if any(not isinstance(v,str) for v in changes.values()):raise ValueError('Los campos deben contener texto.')
    if sum(len(v) for v in changes.values())>120000:raise ValueError('Máximo 120000 caracteres de cambios.')
    for value in changes.values():
        if any(not (c in '\t\n\r' or 0x20<=ord(c)<=0xD7FF or 0xE000<=ord(c)<=0xFFFD or 0x10000<=ord(c)<=0x10FFFF) for c in value):
            raise ValueError('Caracteres no admitidos en Word.')
    return dict(changes)


def render_template(data,changes):
    schema=inspect_template(data);changes=validate_changes(schema,changes)
    if not changes:return data
    parts=package(data)
    for name in {key.rsplit(':',1)[0] for key in changes}:
        root=parse(parts[name]);paragraphs=list(root.iter(tag('p')))
        for key,value in changes.items():
            part,index=key.rsplit(':',1)
            if part!=name:continue
            p=paragraphs[int(index)]
            # Retain paragraph properties and all run properties, including font/color.
            runs=p.findall('w:r',NS)
            if not runs:runs=[ET.SubElement(p,tag('r'))]
            for run in runs:
                for child in list(run):
                    if child.tag!=tag('rPr'):run.remove(child)
            for chunk in re.split(r'(\n|\t)',value.replace('\r\n','\n').replace('\r','\n')):
                if chunk=='\n':ET.SubElement(runs[0],tag('br'))
                elif chunk=='\t':ET.SubElement(runs[0],tag('tab'))
                elif chunk:
                    t=ET.SubElement(runs[0],tag('t'));t.set('{http://www.w3.org/XML/1998/namespace}space','preserve');t.text=chunk
        parts[name]=ET.tostring(root,xml_declaration=True,encoding='UTF-8',standalone=True)
    out=io.BytesIO()
    with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as archive:
        for name,raw in parts.items():archive.writestr(name,raw)
    return out.getvalue()


class Templates:
    def __init__(self,store):
        self.store=store
        store.con.executescript('''
        CREATE TABLE IF NOT EXISTS document_templates(
          id INTEGER PRIMARY KEY,group_id INTEGER REFERENCES groups(id),name TEXT NOT NULL,
          teacher TEXT NOT NULL,original_path TEXT NOT NULL,digest TEXT NOT NULL,data BLOB NOT NULL,
          schema_json TEXT NOT NULL,created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS template_documents(
          id INTEGER PRIMARY KEY,template_id INTEGER NOT NULL REFERENCES document_templates(id),
          title TEXT NOT NULL,current_revision INTEGER NOT NULL,created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS template_document_revisions(
          document_id INTEGER NOT NULL REFERENCES template_documents(id),revision INTEGER NOT NULL,
          changes TEXT NOT NULL,created_at TEXT NOT NULL,PRIMARY KEY(document_id,revision));
        CREATE TABLE IF NOT EXISTS template_field_labels(
          template_id INTEGER PRIMARY KEY REFERENCES document_templates(id),revision INTEGER NOT NULL,labels_json TEXT NOT NULL);
        ''')
    def import_file(self,gid,path,name,teacher=''):
        path=Path(path)
        if path.suffix.lower()!='.docx':raise ValueError('Por ahora se admiten plantillas .docx.')
        if path.stat().st_size>MAX_FILE:raise ValueError('Máximo 10 MB por plantilla.')
        if not name.strip() or len(name)>200 or len(teacher)>200:raise ValueError('Nombre obligatorio; nombre y docente máximo 200 caracteres.')
        data=path.read_bytes();schema=inspect_template(data)
        with self.store.con:
            return self.store.con.execute('INSERT INTO document_templates(group_id,name,teacher,original_path,digest,data,schema_json,created_at) VALUES(?,?,?,?,?,?,?,?)',
                (gid,name.strip(),teacher.strip(),str(path.resolve()),hashlib.sha256(data).hexdigest(),data,json.dumps(schema,ensure_ascii=False),now())).lastrowid
    def get(self,gid,tid):
        row=self.store.con.execute('SELECT * FROM document_templates WHERE id=? AND group_id IS ?',(tid,gid)).fetchone()
        if row is None:raise ValueError('Plantilla no disponible en este grupo.')
        result=dict(row);schema=json.loads(result['schema_json'])
        if schema.get('recognition_version')!=1:schema=inspect_template(result['data'])
        labels=self.store.con.execute('SELECT * FROM template_field_labels WHERE template_id=?',(tid,)).fetchone()
        result['labels_revision']=labels['revision'] if labels else 0
        custom=json.loads(labels['labels_json']) if labels else {}
        for field in schema['fields']:
            field['label']=custom.get(field['id'],field.get('label_hint',''))
            field['label_custom']=field['id'] in custom
        result['schema_json']=json.dumps(schema,ensure_ascii=False)
        return result
    def set_label(self,gid,tid,field_id,label,expected_revision):
        if label is not None and (not isinstance(label,str) or len(label)>120 or any(ord(c)<32 for c in label)):
            raise ValueError('Nombre de campo: hasta 120 caracteres, sin saltos de línea.')
        con=self.store.con;con.execute('BEGIN IMMEDIATE')
        try:
            template=self.get(gid,tid)
            if template['labels_revision']!=expected_revision:raise RevisionConflict('Otro editor cambió los nombres de campo; vuelve a abrir el documento.')
            if field_id not in {f['id'] for f in json.loads(template['schema_json'])['fields']}:raise ValueError('Campo ajeno a la plantilla.')
            row=con.execute('SELECT labels_json FROM template_field_labels WHERE template_id=?',(tid,)).fetchone()
            labels=json.loads(row[0]) if row else {}
            if label is None:labels.pop(field_id,None)
            else:labels[field_id]=label.strip()
            rev=expected_revision+1
            con.execute('INSERT INTO template_field_labels VALUES(?,?,?) ON CONFLICT(template_id) DO UPDATE SET revision=excluded.revision,labels_json=excluded.labels_json',(tid,rev,json.dumps(labels,ensure_ascii=False)))
            con.commit();return rev
        except Exception:con.rollback();raise
    def list(self,gid):
        return [dict(r) for r in self.store.con.execute('SELECT id,name,teacher,created_at FROM document_templates WHERE group_id IS ? ORDER BY id DESC',(gid,))]
    def create(self,gid,tid,title):
        self.get(gid,tid)
        if not title.strip() or len(title)>200:raise ValueError('Título obligatorio, máximo 200 caracteres.')
        with self.store.con:
            did=self.store.con.execute('INSERT INTO template_documents(template_id,title,current_revision,created_at) VALUES(?,?,1,?)',(tid,title.strip(),now())).lastrowid
            self.store.con.execute('INSERT INTO template_document_revisions VALUES(?,1,?,?)',(did,'{}',now()))
        return did
    def document(self,gid,did,revision=None):
        row=self.store.con.execute('''SELECT d.*,r.revision,r.changes FROM template_documents d
            JOIN document_templates t ON t.id=d.template_id JOIN template_document_revisions r ON r.document_id=d.id
            AND r.revision=COALESCE(?,d.current_revision) WHERE d.id=? AND t.group_id IS ?''',(revision,did,gid)).fetchone()
        if row is None:raise ValueError('Documento o versión no disponible en este grupo.')
        return dict(row)
    def documents(self,gid):
        return [dict(r) for r in self.store.con.execute('SELECT d.* FROM template_documents d JOIN document_templates t ON t.id=d.template_id WHERE t.group_id IS ? ORDER BY d.id DESC',(gid,))]
    def save(self,gid,did,changes,expected_revision):
        con=self.store.con;con.execute('BEGIN IMMEDIATE')
        try:
            doc=self.document(gid,did);template=self.get(gid,doc['template_id'])
            if doc['current_revision']!=expected_revision:raise RevisionConflict('Otra ventana guardó una versión nueva. Tu texto sigue abierto; guarda una copia.')
            changes=validate_changes(json.loads(template['schema_json']),changes)
            if changes==json.loads(doc['changes']):con.commit();return expected_revision
            revision=expected_revision+1
            con.execute('INSERT INTO template_document_revisions VALUES(?,?,?,?)',(did,revision,json.dumps(changes,ensure_ascii=False),now()))
            con.execute('UPDATE template_documents SET current_revision=? WHERE id=?',(revision,did));con.commit();return revision
        except Exception:con.rollback();raise
    def export(self,gid,did,path,revision=None):
        doc=self.document(gid,did,revision);template=self.get(gid,doc['template_id']);path=Path(path)
        if path.suffix.lower()!='.docx':raise ValueError('El archivo debe terminar en .docx.')
        if str(path.resolve())==template['original_path']:raise ValueError('Elige un archivo nuevo; la plantilla original se conserva.')
        data=render_template(template['data'],json.loads(doc['changes']))
        with path.open('xb') as out:
            try:out.write(data)
            except Exception:out.close();path.unlink(missing_ok=True);raise
        return path
