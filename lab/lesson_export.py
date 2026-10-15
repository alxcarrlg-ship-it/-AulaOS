"""Editable PPTX from a bundled authored template; standard-library packaging only."""
import base64
import copy
import io
from pathlib import Path
from zipfile import ZipFile,ZIP_DEFLATED
from lxml import etree as E
from lesson_packs import validate

P='http://schemas.openxmlformats.org/presentationml/2006/main'
A='http://schemas.openxmlformats.org/drawingml/2006/main'
R='http://schemas.openxmlformats.org/officeDocument/2006/relationships'
PK='http://schemas.openxmlformats.org/package/2006/relationships'
CT='http://schemas.openxmlformats.org/package/2006/content-types'
NS={'p':P,'a':A}

def xml(node):return E.tostring(node,xml_declaration=True,encoding='UTF-8',standalone=True)
def paragraphs(body,lines):
    original=body.find('{'+A+'}p');prototype=copy.deepcopy(original)
    for p in list(body.findall('{'+A+'}p')):body.remove(p)
    for line in lines:
        p=copy.deepcopy(prototype)
        for child in list(p):
            if child.tag!='{'+A+'}pPr':p.remove(child)
        run=E.SubElement(p,'{'+A+'}r');style=prototype.find('.//{'+A+'}rPr')
        style=copy.deepcopy(style) if style is not None else E.Element('{'+A+'}rPr')
        E.SubElement(style,'{'+A+'}latin',typeface='Arial');run.append(style)
        E.SubElement(run,'{'+A+'}t').text=line
        body.append(p)

def presentation_bytes(data,provenance):
    validate(data)
    seed=base64.b64decode((Path(__file__).parent/'assets/class_slide.pptx.b64').read_text())
    with ZipFile(io.BytesIO(seed)) as archive:parts={n:archive.read(n) for n in archive.namelist()}
    slide_seed=parts.pop('ppt/slides/slide1.xml');slide_rels=parts.pop('ppt/slides/_rels/slide1.xml.rels')
    notes_seed=parts.pop('ppt/notesSlides/notesSlide1.xml');notes_rels=parts.pop('ppt/notesSlides/_rels/notesSlide1.xml.rels')
    pres=E.fromstring(parts['ppt/presentation.xml']);listing=pres.find('{'+P+'}sldIdLst');listing.clear()
    rels=E.fromstring(parts['ppt/_rels/presentation.xml.rels']);types=E.fromstring(parts['[Content_Types].xml'])
    for rel in list(rels):
        if rel.get('Type').endswith('/slide'):rels.remove(rel)
    for item in list(types):
        if item.get('PartName') in ('/ppt/slides/slide1.xml','/ppt/notesSlides/notesSlide1.xml'):types.remove(item)
    for i,slide in enumerate(data['slides'],1):
        root=E.fromstring(slide_seed)
        for ext in root.xpath('//*[local-name()="extLst"]'):ext.getparent().remove(ext)
        for shape in root.findall('.//{'+P+'}sp'):
            name=shape.find('./p:nvSpPr/p:cNvPr',NS).get('name')
            paragraphs(shape.find('{'+P+'}txBody'),[slide['title']] if name=='title' else slide['body'])
        notes=E.fromstring(notes_seed)
        for shape in notes.findall('.//{'+P+'}sp'):
            ph=shape.find('./p:nvSpPr/p:nvPr/p:ph',NS)
            if ph is not None and ph.get('type')=='body':paragraphs(shape.find('{'+P+'}txBody'),(slide['notes']+'\n\n'+provenance).splitlines())
        parts[f'ppt/slides/slide{i}.xml']=xml(root);parts[f'ppt/notesSlides/notesSlide{i}.xml']=xml(notes)
        parts[f'ppt/slides/_rels/slide{i}.xml.rels']=slide_rels.replace(b'notesSlide1.xml',f'notesSlide{i}.xml'.encode())
        parts[f'ppt/notesSlides/_rels/notesSlide{i}.xml.rels']=notes_rels.replace(b'slide1.xml',f'slide{i}.xml'.encode())
        rid=f'AulaSlide{i}';E.SubElement(listing,'{'+P+'}sldId',{'id':str(255+i),'{'+R+'}id':rid})
        E.SubElement(rels,'{'+PK+'}Relationship',Id=rid,Type=R+'/slide',Target=f'/ppt/slides/slide{i}.xml')
        for folder,name,kind in [('slides','slide','slide'),('notesSlides','notesSlide','notesSlide')]:
            E.SubElement(types,'{'+CT+'}Override',PartName=f'/ppt/{folder}/{name}{i}.xml',ContentType=f'application/vnd.openxmlformats-officedocument.presentationml.{kind}+xml')
    parts['ppt/presentation.xml']=xml(pres);parts['ppt/_rels/presentation.xml.rels']=xml(rels);parts['[Content_Types].xml']=xml(types)
    app=E.fromstring(parts['docProps/app.xml'])
    for node in app:
        if E.QName(node).localname in ('Slides','Notes'):node.text=str(len(data['slides']))
    parts['docProps/app.xml']=xml(app)
    output=io.BytesIO()
    with ZipFile(output,'w',ZIP_DEFLATED) as archive:
        for name,content in parts.items():archive.writestr(name,content)
    return output.getvalue()

def export_presentation(data,provenance,path):
    path=Path(path)
    if path.suffix.lower()!='.pptx':raise ValueError('Usa la extensión .pptx.')
    content=presentation_bytes(data,provenance)
    with path.open('xb') as stream:stream.write(content)
