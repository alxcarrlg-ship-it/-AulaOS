"""Conservative structural hints, never a claim of semantic understanding."""
W='http://schemas.openxmlformats.org/wordprocessingml/2006/main'
NS={'w':W}
def q(name):return '{'+W+'}'+name

def enrich(schema,parts):
    from templates import parse,text_of
    by_id={f['id']:f for f in schema['fields']}
    warnings=[]
    styles={}
    if 'word/styles.xml' in parts:
        styles={s.get(q('styleId')):s for s in parse(parts['word/styles.xml']).findall('w:style',NS)}
    def heading_style(name,seen=None):
        seen=set() if seen is None else seen
        if name in seen:return False
        seen.add(name)
        if name.lower().startswith(('heading','titulo','título')) or name.lower()=='title':return True
        style=styles.get(name)
        if style is None:return False
        outline=style.find('w:pPr/w:outlineLvl',NS)
        if outline is not None:return outline.get(q('val')) in tuple(map(str,range(9)))
        base=style.find('w:basedOn',NS)
        return heading_style(base.get(q('val'),''),seen) if base is not None else False
    def short(node):
        return ' '.join(text_of(node).split())[:120]
    def cells(row):
        offset=row.find('w:trPr/w:gridBefore',NS)
        col=int(offset.get(q('val'),'0')) if offset is not None else 0
        result=[]
        for cell in row.findall('w:tc',NS):
            span=cell.find('w:tcPr/w:gridSpan',NS)
            width=int(span.get(q('val'),'1')) if span is not None else 1
            result.append((cell,col,col+width));col+=width
        return result
    for name in sorted({f['id'].rsplit(':',1)[0] for f in schema['fields']}):
        root=parse(parts[name]);section='';table_hints={}
        for table in root.iter(q('tbl')):
            rows=table.findall('w:tr',NS)
            # Only a complete, short, nonempty first row is treated as a header candidate.
            header=cells(rows[0]) if rows else []
            candidate=len(header)>=2 and all(short(c) and len(text_of(c))<=120 for c,_,_ in header)
            for ri,row in enumerate(rows):
                for ci,(cell,start,end) in enumerate(cells(row)):
                    labels=[short(c) for c,a,b in header if a<end and start<b] if candidate and ri else []
                    left=cells(row)[ci-1][0] if ci else None
                    # Adjacent labels only when explicitly marked with a colon.
                    neighbor=short(left) if left is not None else ''
                    if not neighbor.endswith((':','：')):neighbor=''
                    table_hints[cell]={'row':ri+1,'column_start':start+1,'column_end':end,
                        'column_hint':' / '.join(labels)[:240],'neighbor_hint':neighbor,
                        'header_candidate':bool(candidate and ri==0)}
            if any(c.find('w:tcPr/w:vMerge',NS) is not None for c in table.iter(q('tc'))):
                warnings.append('Celdas combinadas verticalmente: revisa las pistas de columna y los campos vacíos.')
        for index,p in enumerate(root.iter(q('p'))):
            style=p.find('w:pPr/w:pStyle',NS);outline=p.find('w:pPr/w:outlineLvl',NS)
            style_name=style.get(q('val'),'') if style is not None else ''
            heading=heading_style(style_name) or (outline is not None and outline.get(q('val')) in tuple(map(str,range(9))))
            field=by_id.get(name+':'+str(index))
            if field is None:continue
            if heading and short(p):section=short(p)
            cell=next((a for a in p.iterancestors() if a.tag==q('tc')),None)
            hints=table_hints.get(cell,{})
            raw=text_of(p);inline=raw.split(':',1)[0].strip() if ':' in raw and 0<len(raw.split(':',1)[0].strip())<=60 else ''
            label=inline or hints.get('neighbor_hint','').rstrip(':：') or hints.get('column_hint','')
            field.update(section_hint=section,label_hint=label,hint_source='texto con dos puntos' if inline else 'celda anterior' if hints.get('neighbor_hint') else 'primera fila de tabla' if hints.get('column_hint') else 'sin pista',**hints)
        if root.findall('.//w:trPr/w:trHeight[@w:hRule="exact"]',NS):warnings.append('Hay filas con altura fija: el contenido más largo puede quedar oculto en Word.')
        if root.findall('.//w:txbxContent',NS):warnings.append('Hay cuadros de texto: verifica su distribución en Word.')
    schema.update(recognition_version=1,warnings=list(dict.fromkeys(warnings)))
    schema['notice']='Las etiquetas inferidas son pistas revisables, no una identificación garantizada. Puedes nombrar cada campo sin cambiar el Word. Se conservan tablas y celdas combinadas; párrafos complejos no se editan.'
    return schema
