async function safeJson(url, fallback=null, opts={}){
  try{ const r=await fetch(url,Object.assign({cache:'no-store'},opts)); if(!r.ok) return fallback; return await r.json(); }
  catch(e){ return fallback; }
}
function esc(s){return String(s??'').replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]))}
function fmt(x,n=3){return (x===null||x===undefined||x==='')?'—':Number(x).toFixed(n)}
function asset(eventId,path){return `/api/events/${encodeURIComponent(eventId)}/assets/${path}`}
function card(k,v,sub=''){return `<div class="card"><span>${esc(k)}</span><b>${esc(v)}</b>${sub?`<small>${esc(sub)}</small>`:''}</div>`}
let currentRun=null;
function drawTimeline(canvas, events){
  const ctx=canvas.getContext('2d'); const W=canvas.clientWidth || canvas.width; const H=canvas.height; canvas.width=W; ctx.clearRect(0,0,W,H);
  ctx.fillStyle='#0f172a'; ctx.fillRect(0,0,W,H);
  const pad=28; const ev=(events||[]).filter(e=>e.metric_include || e.phase==='eval').slice(-300);
  if(!ev.length){ctx.fillStyle='#94a3b8'; ctx.fillText('No metric events yet',20,30); return;}
  const xs=ev.map((e,i)=>Number(e.stream_time_sec ?? i)); const ys=ev.map(e=>Number(e.final_score ?? 0));
  const minX=Math.min(...xs), maxX=Math.max(...xs); const maxY=Math.max(1, ...ys);
  ctx.strokeStyle='#334155'; ctx.lineWidth=1; for(let i=0;i<5;i++){const y=pad+(H-pad*2)*i/4; ctx.beginPath();ctx.moveTo(pad,y);ctx.lineTo(W-pad,y);ctx.stroke();}
  ctx.strokeStyle='#60a5fa'; ctx.lineWidth=2; ctx.beginPath();
  ev.forEach((e,i)=>{const x=pad+(W-pad*2)*((xs[i]-minX)/(maxX-minX||1)); const y=H-pad-(H-pad*2)*(ys[i]/maxY); if(i===0)ctx.moveTo(x,y);else ctx.lineTo(x,y);}); ctx.stroke();
  ev.forEach((e,i)=>{const x=pad+(W-pad*2)*((xs[i]-minX)/(maxX-minX||1)); const y=H-pad-(H-pad*2)*(ys[i]/maxY); ctx.fillStyle=(Number(e.y_true)===1)?'#f97316':'#22c55e'; ctx.beginPath(); ctx.arc(x,y,3,0,Math.PI*2); ctx.fill();});
  ctx.fillStyle='#cbd5e1'; ctx.fillText('score',4,18); ctx.fillText(`${Math.round(minX)}s`,pad,H-6); ctx.fillText(`${Math.round(maxX)}s`,W-pad-35,H-6);
}
function mergeGraph(data){
  const g=data.event_graph||{nodes:[],edges:[]}; const sg=data.semantic_event_graph||{nodes:[],edges:[]};
  const graph=JSON.parse(JSON.stringify(data));
  const edges=[...(g.edges||[]),...(sg.edges||[])];
  graph.event_graph={nodes:g.nodes||sg.nodes||[], edges:edges};
  return graph;
}
function renderRelationPanel(data){
  const rels=(data.vlm_relation_refinement?.candidates||data.vlm_verification?.candidates||[]);
  if(!rels.length){document.getElementById('relationPanel').innerHTML='<p class="muted">VLM relation refinement 후보 또는 결과가 아직 없습니다.</p>'; return;}
  document.getElementById('relationPanel').innerHTML=rels.slice(0,8).map(x=>`<p><b>${esc(x.candidate?.event_subject_id)} -- ${esc(x.semantic_relation||x.verified_relation)} → ${esc(x.candidate?.event_object_id)}</b><br><small>risk=${fmt(x.semantic_risk)} conf=${fmt(x.relation_confidence||x.confidence)} uncertainty=${esc(x.uncertainty)} source=${esc(x.provider)} ${x.ok?'':'· failed'}</small><br><small>${esc((x.evidence||[])[0]||x.error||'')}</small></p>`).join('');
}
async function loadRuns(){
  const runs=await safeJson('/api/eval/runs',{items:[]});
  const sel=document.getElementById('runSelect');
  const old=sel.value; sel.innerHTML=(runs.items||[]).map(r=>`<option value="${esc(r.run_id)}">${esc(r.run_id)} ${r.status?`(${esc(r.status)})`:''}</option>`).join('');
  if(old) sel.value=old; currentRun=sel.value || (runs.items||[])[0]?.run_id || null;
}
async function load(){
  if(!currentRun){await loadRuns();}
  if(!currentRun){document.getElementById('metricBox').innerHTML='<h2>No eval run</h2><p class="muted">Edge experiment mode에서 run_id가 포함된 event를 먼저 전송하세요.</p>';return;}
  document.getElementById('runState').textContent=currentRun;
  const [summary, evs]=await Promise.all([safeJson('/api/eval/runs/'+encodeURIComponent(currentRun)+'/summary',{metrics:{},events_tail:[],videos:[]}), safeJson('/api/eval/runs/'+encodeURIComponent(currentRun)+'/events?limit=500',{items:[]})]);
  const m=summary.metrics||{}; const events=evs.items||summary.events_tail||[];
  document.getElementById('metricBox').innerHTML=`<p class="eyebrow">Metrics</p><h2>F1 ${fmt(m.f1)} · AUROC ${fmt(m.auroc)}</h2><div class="kv"><div>AP</div><div>${fmt(m.average_precision)}</div><div>Accuracy</div><div>${fmt(m.accuracy)}</div><div>Precision</div><div>${fmt(m.precision)}</div><div>Recall</div><div>${fmt(m.recall)}</div></div>`;
  document.getElementById('evalCards').innerHTML=[card('events',m.num_events??events.length),card('metric events',m.num_metric_events??''),card('videos',m.num_videos??''),card('false alarms/hour',fmt(m.false_alarms_per_hour))].join('');
  drawTimeline(document.getElementById('timeline'), events);
  document.querySelector('#evalEvents tbody').innerHTML=events.slice(-80).reverse().map(e=>`<tr><td><a href="/dashboard/events/${esc(e.event_id)}">${esc(e.event_id)}</a></td><td>${esc(e.phase)}</td><td>${esc(e.video_id||'')}</td><td>${esc(e.y_true_name??e.y_true??'')}</td><td><span class="badge ${esc(e.decision||'')}">${esc(e.decision||'')}</span></td><td>${fmt(e.final_score)}</td><td>${fmt(e.graph_novelty_score)}</td><td>${fmt(e.semantic_relation_novelty)}</td><td>${fmt(e.vlm_semantic_risk)}</td></tr>`).join('');
  const latest=events.slice().reverse().find(e=>e.event_id);
  if(latest){
    const data=await safeJson('/api/events/'+encodeURIComponent(latest.event_id),{});
    const overlay=data.artifacts?.overlay||'overlay/edge_overlay_t.jpg'; const frame=data.artifacts?.frame||'frame_t.jpg';
    document.getElementById('latestPreview').innerHTML=`<h3><a href="/dashboard/events/${esc(latest.event_id)}">${esc(latest.event_id)}</a></h3><p class="muted">${esc(latest.phase)} · ${esc(latest.video_id||'')} · ${esc(latest.decision||'')}</p><img class="preview" src="${asset(latest.event_id,overlay)}" onerror="this.src='${asset(latest.event_id,frame)}'">`;
    renderRelationPanel(data);
    if(window.ForceGraphViz) ForceGraphViz.renderForceGraph('svgGraph', mergeGraph(data), {mode:'event',height:540,pinOnDrag:true,onLinkClick:(d)=>{const r=d.raw||d; document.getElementById('relationPanel').innerHTML=`<h3>${esc(r.subject_label||r.subject_id)} -- ${esc(r.relation)} → ${esc(r.object_label||r.object_id)}</h3><div class="kv"><div>source</div><div>${esc(r.source)}</div><div>confidence</div><div>${fmt(r.confidence)}</div><div>risk</div><div>${fmt(r.semantic_risk||r.vlm_risk)}</div><div>novelty</div><div>${fmt(r.novelty_score)}</div></div>${r.evidence_url?`<img class="preview" src="${r.evidence_url}">`:''}`;}});
  }
}
document.getElementById('refreshBtn').addEventListener('click',async()=>{await loadRuns(); await load();});
document.getElementById('runSelect').addEventListener('change',e=>{currentRun=e.target.value; load();});
document.getElementById('aggregateBtn').addEventListener('click',async()=>{if(!currentRun)return; await safeJson('/api/eval/runs/'+encodeURIComponent(currentRun)+'/aggregate',{}, {method:'POST'}); await load();});
loadRuns().then(load); setInterval(load,5000);
