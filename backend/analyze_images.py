#!/usr/bin/env python3
"""Convert HEIC workshop photos to JPEG and optionally analyze them with a local vision LLM.

Examples:
  python backend/analyze_images.py --convert-only
  VISION_LLM_BASE_URL=http://127.0.0.1:8001/v1 \
  VISION_LLM_MODEL=my-vision-model \
  python backend/analyze_images.py --analyze

The analyzer writes:
  data/image_catalog.json       structured activity objects
  data/image_chunks.json        text chunks consumable by the RAG
  data/drive_corpus_jpg/*.jpg   browser/model friendly versions
"""
from __future__ import annotations
import argparse, base64, json, os, re
from pathlib import Path
from typing import Any
import httpx
from PIL import Image
from pillow_heif import register_heif_opener

register_heif_opener()
ROOT=Path(__file__).resolve().parent.parent
SRC=ROOT/'data'/'drive_corpus'
JPG=ROOT/'data'/'drive_corpus_jpg'
CAT=ROOT/'data'/'image_catalog.json'
CHUNKS=ROOT/'data'/'image_chunks.json'

LANG='es'
SYSTEM='''You are a meticulous innovation-workshop archivist. Analyze only what is supported by the image. Do not invent hidden steps. If something cannot be inferred, use null or an empty list. Return strict JSON only.'''
PROMPT='''Analyze this photo from Alberto Munoz's Innovaction materials and convert it into a reusable innovation-activity object.
Return exactly this JSON shape:
{
  "title": string|null,
  "short_description": string,
  "objective": string|null,
  "when_to_use": string|null,
  "participants": string|null,
  "duration": string|null,
  "materials": [string],
  "visible_text": [string],
  "observed_steps": [string],
  "outputs": [string],
  "facilitator_notes": [string],
  "tags": [string],
  "confidence": "high"|"medium"|"low"
}
Write all descriptive fields in Spanish. Preserve visible labels in their original language when quoting them. Distinguish observed content from inferred use; do not fabricate missing instructions.'''

def convert(path:Path)->Path:
    JPG.mkdir(parents=True,exist_ok=True)
    out=JPG/(path.stem+'.jpg')
    if out.exists() and out.stat().st_mtime>=path.stat().st_mtime: return out
    with Image.open(path) as im:
        im=im.convert('RGB')
        max_side=2200
        scale=min(1,max_side/max(im.size))
        if scale<1: im=im.resize((int(im.width*scale),int(im.height*scale)))
        im.save(out,'JPEG',quality=88,optimize=True)
    return out

def as_data_url(path:Path)->str:
    return 'data:image/jpeg;base64,'+base64.b64encode(path.read_bytes()).decode()

def parse_json(text:str)->dict[str,Any]:
    text=text.strip(); text=re.sub(r'^```(?:json)?\s*|\s*```$','',text,flags=re.I|re.M)
    return json.loads(text)

def analyze_one(path:Path)->dict[str,Any]:
    base=os.getenv('VISION_LLM_BASE_URL','').rstrip('/')
    model=os.getenv('VISION_LLM_MODEL','')
    if not base or not model: raise RuntimeError('Set VISION_LLM_BASE_URL and VISION_LLM_MODEL')
    key=os.getenv('VISION_LLM_API_KEY','local')
    payload={'model':model,'temperature':0.15,'messages':[
      {'role':'system','content':SYSTEM},
      {'role':'user','content':[{'type':'text','text':PROMPT},{'type':'image_url','image_url':{'url':as_data_url(path)}}]}
    ]}
    with httpx.Client(timeout=180) as c:
        r=c.post(base+'/chat/completions',headers={'Authorization':f'Bearer {key}'},json=payload)
        r.raise_for_status(); txt=r.json()['choices'][0]['message']['content']
    return parse_json(txt)

def make_chunk(item:dict[str,Any])->dict[str,Any]:
    text='\n'.join([
      f"DINAMICA: {item.get('title') or 'No identificada'}",
      f"DESCRIPCION: {item.get('short_description') or ''}",
      f"OBJETIVO: {item.get('objective') or ''}",
      f"CUANDO USARLA: {item.get('when_to_use') or ''}",
      f"PARTICIPANTES: {item.get('participants') or ''}",
      f"DURACION: {item.get('duration') or ''}",
      'MATERIALES: '+'; '.join(item.get('materials') or []),
      'TEXTO VISIBLE: '+'; '.join(item.get('visible_text') or []),
      'PASOS OBSERVADOS: '+'; '.join(item.get('observed_steps') or []),
      'ENTREGABLES: '+'; '.join(item.get('outputs') or []),
      'NOTAS FACILITADOR: '+'; '.join(item.get('facilitator_notes') or []),
    ]).strip()
    return {'id':'image:'+item['source_image'],'text':text,'source':item['source_image'],'page':1,'tags':item.get('tags') or [],'source_type':'image-analysis','confidence':item.get('confidence','low')}

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--convert-only',action='store_true'); ap.add_argument('--analyze',action='store_true'); ap.add_argument('--limit',type=int,default=0); a=ap.parse_args()
    srcs=sorted(list(SRC.glob('*.HEIC'))+list(SRC.glob('*.heic')))
    if a.limit: srcs=srcs[:a.limit]
    print(f'Found {len(srcs)} HEIC files')
    jpgs=[]
    for i,p in enumerate(srcs,1):
        out=convert(p); jpgs.append(out); print(f'[{i}/{len(srcs)}] {p.name} -> {out.name}')
    if a.convert_only or not a.analyze:
        print(f'Converted {len(jpgs)} images into {JPG}')
        return
    existing={}
    if CAT.exists():
        for x in json.loads(CAT.read_text(encoding='utf-8')): existing[x.get('source_image')]=x
    for i,p in enumerate(jpgs,1):
        src=p.stem+'.HEIC'
        if src in existing: print(f'[{i}/{len(jpgs)}] cached {src}'); continue
        print(f'[{i}/{len(jpgs)}] analyzing {src}...')
        try:
            obj=analyze_one(p); obj['source_image']=src; obj['jpeg_path']=str(p.relative_to(ROOT)); existing[src]=obj
        except Exception as e: print(f'WARN {src}: {e}')
        CAT.write_text(json.dumps(list(existing.values()),ensure_ascii=False,indent=2),encoding='utf-8')
    items=list(existing.values()); CHUNKS.write_text(json.dumps([make_chunk(x) for x in items],ensure_ascii=False,indent=2),encoding='utf-8')
    print(f'Cataloged {len(items)} images -> {CAT}')
    print(f'RAG image chunks -> {CHUNKS}')
if __name__=='__main__': main()
