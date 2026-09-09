import json,re,sys
from pathlib import Path
from pypdf import PdfReader

def chunk(text,size=1300,overlap=180):
    text=re.sub(r'\s+',' ',text).strip(); out=[]; i=0
    while i<len(text): out.append(text[i:i+size]); i+=size-overlap
    return out

def tags(text):
    keys=['Innovation Games','Design Thinking','Canvas','Customer Journey','TRL','MVP','POC','patent','propiedad intelectual','vigilancia tecnológica','triple hélice','ISO 560','sustentabilidad','inteligencia artificial','Industria 4.0','métricas']
    return [k for k in keys if k.lower() in text.lower()]

pdf=Path(sys.argv[1]); dest=Path(sys.argv[2]) if len(sys.argv)>2 else Path('../data/chunks.json')
r=PdfReader(str(pdf)); items=[]
for n,p in enumerate(r.pages,1):
    try: text=p.extract_text() or ''
    except Exception: text=''
    for idx,c in enumerate(chunk(text)):
        if len(c)>120: items.append({'id':f'{pdf.stem}-p{n}-{idx}','source':pdf.name,'page':n,'text':c,'tags':tags(c)})
dest.parent.mkdir(parents=True,exist_ok=True);dest.write_text(json.dumps(items,ensure_ascii=False),encoding='utf-8');print(f'wrote {len(items)} chunks to {dest}')
