import json, os, re
from pathlib import Path
from typing import List, Optional
import httpx
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel
from prompts import SYSTEM_PROMPT

ROOT=Path(__file__).resolve().parent.parent
DATA=ROOT/'data'/'chunks.json'
app=FastAPI(title='Innovaction in Action API',version='0.1.0')

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

def retrieve(query,k=7):
    if not DATA.exists(): return []
    chunks=json.loads(DATA.read_text(encoding='utf-8'))
    q=set(re.findall(r'[\wáéíóúñü]+',query.lower()))
    ranked=[]
    for c in chunks:
        words=set(re.findall(r'[\wáéíóúñü]+',c['text'].lower()))
        score=len(q & words)+sum(2 for tag in c.get('tags',[]) if tag.lower() in query.lower())
        if score: ranked.append((score,c))
    return [c for _,c in sorted(ranked,key=lambda x:x[0],reverse=True)[:k]]

@app.get('/health')
def health(): return {'ok':True,'service':'innovaction-in-action'}

@app.post('/generate',response_model=Plan)
async def generate(req:Req,x_api_key:str|None=Header(default=None)):
    check(x_api_key)
    ctx=retrieve(' '.join(filter(None,[req.objective,req.organization,req.audience,req.maturity,req.constraints])))
    context='\n\n'.join(f"SOURCE {c.get('source','Innovaction')} p.{c.get('page','?')} tags={','.join(c.get('tags',[]))}: {c['text']}" for c in ctx)
    schema=Plan.model_json_schema()
    user={**req.model_dump(),'retrieved_context':context,'json_schema':schema}
    base=os.getenv('SPARK_LLM_BASE_URL','http://127.0.0.1:8000/v1').rstrip('/')
    model=os.getenv('SPARK_LLM_MODEL','Qwen/Qwen3.8-27B-FP8')
    key=os.getenv('SPARK_LLM_API_KEY','local')
    async with httpx.AsyncClient(timeout=120) as client:
        r=await client.post(base+'/chat/completions',headers={'Authorization':f'Bearer {key}'},json={'model':model,'temperature':0.45,'messages':[{'role':'system','content':SYSTEM_PROMPT},{'role':'user','content':json.dumps(user,ensure_ascii=False)}]})
        r.raise_for_status(); txt=r.json()['choices'][0]['message']['content'].strip()
    txt=re.sub(r'^```(?:json)?|```$','',txt,flags=re.M).strip()
    return Plan.model_validate(json.loads(txt))
