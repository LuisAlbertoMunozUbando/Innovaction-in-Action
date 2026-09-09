import json, os, re
from pathlib import Path
from typing import List, Optional
import httpx
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel
from prompts import SYSTEM_PROMPT

ROOT=Path(__file__).resolve().parent.parent
TEXT_DATA=ROOT/'data'/'chunks.json'
IMAGE_DATA=ROOT/'data'/'image_chunks.json'
app=FastAPI(title='Innovaction in Action API',version='0.2.1')

class Req(BaseModel):
    language:str='es'; objective:str; organization:Optional[str]=None; audience:Optional[str]=None
    durationMinutes:int=90; participants:int=8; maturity:Optional[str]=None; constraints:Optional[str]=None
class Activity(BaseModel):
    title:str; minutes:int; purpose:str; instructions:List[str]; output:str; sourceTags:List[str]=[]
class Plan(BaseModel):
    title:str; objective:str; rationale:str; activities:List[Activity]; materials:List[str]; metrics:List[str]; risks:List[str]; nextSteps:List[str]; references:List[str]=[]

def check(key):
    expected=os.getenv('SPARK_INNOVACTION_API_KEY','')
    if expected and key!=expected: raise HTTPException(401,'invalid api key')

def load_chunks():
    out=[]
    for path in (TEXT_DATA,IMAGE_DATA):
        if not path.exists(): continue
        try:
            data=json.loads(path.read_text(encoding='utf-8'))
            if isinstance(data,list): out.extend(data)
        except Exception as e:
            print(f'WARN loading {path}: {e}')
    return out

def tokenize(text):
    return set(re.findall(r'[\wáéíóúñü]+', (text or '').lower(), flags=re.UNICODE))

def retrieve(query,k=10):
    chunks=load_chunks(); q=tokenize(query); ranked=[]
    for c in chunks:
        text=c.get('text',''); words=tokenize(text)
        overlap=len(q & words)
        tags=[str(t).lower() for t in c.get('tags',[])]
        tag_score=sum(3 for tag in tags if any(tok in tag or tag in tok for tok in q))
        title_boost=2 if any(tok in text[:250].lower() for tok in q) else 0
        source_boost=1 if c.get('source_type')=='image-analysis' else 0
        confidence=(c.get('confidence') or '').lower()
        confidence_boost={'high':4,'medium':1,'low':-2}.get(confidence,0)
        score=overlap+tag_score+title_boost+source_boost+confidence_boost
        if score>0: ranked.append((score,c))
    ranked.sort(key=lambda x:x[0],reverse=True)
    seen=set(); result=[]
    for _,c in ranked:
        key=(c.get('source'),c.get('page'))
        if key in seen: continue
        seen.add(key); result.append(c)
        if len(result)>=k: break
    return result

@app.get('/health')
def health():
    chunks=load_chunks()
    return {'ok':True,'service':'innovaction-in-action','version':'0.2.1','knowledge_chunks':len(chunks)}

@app.get('/knowledge/status')
def knowledge_status():
    chunks=load_chunks(); by_type={}; by_confidence={}
    for c in chunks:
        t=c.get('source_type','unknown'); by_type[t]=by_type.get(t,0)+1
        conf=c.get('confidence','n/a'); by_confidence[conf]=by_confidence.get(conf,0)+1
    return {'total_chunks':len(chunks),'by_type':by_type,'by_confidence':by_confidence,'text_file':TEXT_DATA.exists(),'image_file':IMAGE_DATA.exists()}

@app.post('/generate',response_model=Plan)
async def generate(req:Req,x_api_key:str|None=Header(default=None)):
    check(x_api_key)
    query=' '.join(filter(None,[req.objective,req.organization,req.audience,req.maturity,req.constraints]))
    ctx=retrieve(query)
    context='\n\n'.join(
        f"SOURCE {c.get('source','Innovaction')} | type={c.get('source_type','unknown')} | tags={','.join(c.get('tags',[]))} | confidence={c.get('confidence','n/a')}\n{c.get('text','')}"
        for c in ctx
    )
    schema=Plan.model_json_schema()
    user={**req.model_dump(),'retrieved_context':context,'json_schema':schema,
          'instructions':'Use the retrieved Innovaction sources as the primary methodological basis. Prefer high-confidence sources over low-confidence ones. Compose a practical sequence rather than copying one activity blindly. Cite the source image/file names used in references. Return every user-facing field in the requested language.'}
    base=os.getenv('SPARK_LLM_BASE_URL','http://127.0.0.1:8001/v1').rstrip('/')
    model=os.getenv('SPARK_LLM_MODEL','Qwen/Qwen2.5-7B-Instruct')
    key=os.getenv('SPARK_LLM_API_KEY','local')
    async with httpx.AsyncClient(timeout=180) as client:
        r=await client.post(base+'/chat/completions',headers={'Authorization':f'Bearer {key}'},json={
            'model':model,'temperature':0.35,'max_tokens':2600,
            'messages':[{'role':'system','content':SYSTEM_PROMPT},{'role':'user','content':json.dumps(user,ensure_ascii=False)}]
        })
        if r.status_code>=400: raise HTTPException(502,f'Composer LLM error {r.status_code}: {r.text[:1000]}')
        txt=r.json()['choices'][0]['message']['content'].strip()
    txt=re.sub(r'^```(?:json)?\s*|\s*```$','',txt,flags=re.M).strip()
    try:
        return Plan.model_validate(json.loads(txt))
    except Exception as e:
        raise HTTPException(502,f'Invalid JSON from composer: {e}; preview={txt[:800]}')
