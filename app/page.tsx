'use client';
import { useMemo, useState } from 'react';
import { jsPDF } from 'jspdf';
import { languages, tr } from '@/lib/i18n';
import type { InnovationPlan, Language } from '@/lib/types';

export default function Home(){
  const [lang,setLang]=useState<Language>('es'); const ui=useMemo(()=>tr(lang),[lang]);
  const [objective,setObjective]=useState(''); const [organization,setOrganization]=useState(''); const [audience,setAudience]=useState('');
  const [participants,setParticipants]=useState(8); const [minutes,setMinutes]=useState(90); const [maturity,setMaturity]=useState(''); const [constraints,setConstraints]=useState('');
  const [plan,setPlan]=useState<InnovationPlan|null>(null); const [loading,setLoading]=useState(false); const [error,setError]=useState('');
  const rtl=['ar','he'].includes(lang);
  async function generate(){
    if(!objective.trim()) return; setLoading(true);setError('');
    try{ const r=await fetch('/api/generate',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({language:lang,objective,organization,audience,durationMinutes:minutes,participants,maturity,constraints})}); if(!r.ok) throw new Error(await r.text()); setPlan(await r.json()); }
    catch(e:any){setError(e.message||'Error');} finally{setLoading(false)}
  }
  function pdf(){ if(!plan) return; const d=new jsPDF({unit:'pt',format:'a4'}); const margin=48; let y=56; d.setFont('helvetica','bold');d.setFontSize(22);d.text(plan.title,margin,y); y+=30; d.setFont('helvetica','normal');d.setFontSize(10); d.text('Innovaction in Action · Alberto Muñoz',margin,y); y+=28;
    const add=(title:string,lines:string[])=>{ d.setFont('helvetica','bold');d.setFontSize(13);d.text(title,margin,y);y+=18;d.setFont('helvetica','normal');d.setFontSize(10); for(const line of lines){const arr=d.splitTextToSize(line,500);if(y+arr.length*14>790){d.addPage();y=52;}d.text(arr,margin,y);y+=arr.length*14+6;} y+=8; };
    add('Objective',[plan.objective]); add('Rationale',[plan.rationale]); plan.activities.forEach((a,i)=>add(`${i+1}. ${a.title} · ${a.minutes} min`,[a.purpose,...a.instructions.map((x,j)=>`${j+1}) ${x}`),`Output: ${a.output}`])); add('Metrics',plan.metrics); add('Risks',plan.risks); add('Next steps',plan.nextSteps); d.save('innovaction-in-action.pdf');
  }
  return <main dir={rtl?'rtl':'ltr'}>
    <nav><div className="brand"><img src="/innovaction-logo.svg" alt="Innovaction logo"/><span>Innovaction in Action</span></div><select value={lang} onChange={e=>setLang(e.target.value as Language)}>{languages.map(l=><option key={l.code} value={l.code}>{l.label}</option>)}</select></nav>
    <section className="hero"><div className="tag">{ui.tag}</div><h1>{ui.title}</h1><p>{ui.subtitle}</p></section>
    <section className="grid"><div className="card input"><label>{ui.objective}</label><textarea value={objective} onChange={e=>setObjective(e.target.value)} placeholder={ui.placeholder}/><div className="fields"><input value={organization} onChange={e=>setOrganization(e.target.value)} placeholder={ui.organization}/><input value={audience} onChange={e=>setAudience(e.target.value)} placeholder={ui.audience}/><input value={maturity} onChange={e=>setMaturity(e.target.value)} placeholder={ui.maturity}/><input value={constraints} onChange={e=>setConstraints(e.target.value)} placeholder={ui.constraints}/><label>{ui.participants}<input type="number" min="1" max="100" value={participants} onChange={e=>setParticipants(+e.target.value)}/></label><label>{ui.minutes}<input type="number" min="15" max="480" value={minutes} onChange={e=>setMinutes(+e.target.value)}/></label></div><button onClick={generate} disabled={loading||!objective.trim()}>{loading?ui.working:ui.generate}</button>{error&&<p className="error">{error}</p>}</div>
    <div className="card output">{plan?<><div className="resultHead"><div><div className="tag">AI + RAG + Spark</div><h2>{plan.title}</h2></div><button className="ghost" onClick={pdf}>{ui.report}</button></div><p>{plan.rationale}</p><div className="timeline">{plan.activities.map((a,i)=><article key={i}><div className="num">{i+1}</div><div><h3>{a.title}<small>{a.minutes} min</small></h3><p>{a.purpose}</p><ul>{a.instructions.map((x,j)=><li key={j}>{x}</li>)}</ul><strong>Output:</strong> {a.output}</div></article>)}</div></>:<div className="empty"><img src="/innovaction-logo.svg" alt=""/><h2>Innovation = invention × value</h2><p>Your tailored dynamic will appear here.</p></div>}</div></section>
    <footer>Innovaction in Action · Knowledge-grounded innovation dynamics · Alberto Muñoz</footer>
  </main>
}
