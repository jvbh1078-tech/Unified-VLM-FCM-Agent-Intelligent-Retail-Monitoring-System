async function safeJson(url,fallback={}){try{const r=await fetch(url,{cache:'no-store'});if(!r.ok)return fallback;return await r.json()}catch(e){return fallback}}
function esc(s){return String(s??'').replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]))}
function asset(eventId,path){return `/api/events/${encodeURIComponent(eventId)}/assets/${path}`}
function kv(obj){return Object.entries(obj).map(([k,v])=>`<div>${esc(k)}</div><div>${esc(v)}</div>`).join('')}
function selectNode(n){
  const raw=n.raw||n;
  document.getElementById('nodePanel').innerHTML=`<h3>${esc(n.id)}</h3><div class="kv"><div>label</div><div>${esc(n.label)}</div><div>confidence</div><div>${raw.confidence??''}</div><div>bbox</div><div>${esc(JSON.stringify(raw.bbox||[]))}</div><div>source</div><div>${esc(raw.source||'')}</div></div>${n.crop_url?`<img class="preview" style="margin-top:12px" src="${n.crop_url}">`:''}`
}
function selectLink(d){
  const raw=d.raw||d;
  const body={relation:raw.relation, subject:raw.subject_label||raw.subject_id, object:raw.object_label||raw.object_id, novelty:raw.novelty_score, risk:raw.semantic_risk??raw.vlm_risk, confidence:raw.confidence};
  document.getElementById('nodePanel').innerHTML=`<h3>Relation</h3><div class="kv">${kv(body)}</div>${raw.evidence_url?`<img class="preview" style="margin-top:12px" src="${raw.evidence_url}">`:''}`
}
function mergeNoveltyAndVlm(data){
  const novs={}; (data.novelty?.edges||[]).forEach(x=>novs[x.key]=x);
  const vlms={}; (data.vlm_verification?.candidates||[]).forEach(x=>{const k=x.candidate?.key; if(k) vlms[k]=x});
  const graph=JSON.parse(JSON.stringify(data));
  const semanticEdges = (data.semantic_event_graph?.edges||[]);
  graph.event_graph = graph.event_graph || {nodes:[],edges:[]};
  graph.event_graph.edges = [...(graph.event_graph.edges||[]), ...semanticEdges].map(e=>{
    const key=`${e.subject_label}|${e.relation}|${e.object_label}`;
    const parentKey=e.metrics?.parent_key || key;
    return Object.assign({}, e, {novelty_score:novs[key]?.novelty_score||data.semantic_novelty?.edges?.find?.(x=>x.key===key)?.novelty_score||0, previous_count:novs[key]?.previous_count||0, semantic_risk:e.semantic_risk||vlms[parentKey]?.semantic_risk||0});
  });
  return graph;
}
async function load(){
 const data=await safeJson('/api/events/'+encodeURIComponent(window.EVENT_ID));
 document.getElementById('decision').innerHTML=`<p class="eyebrow">Decision</p><h2><span class="badge ${esc(data.decision)}">${esc(data.decision)}</span> score=${Number(data.score||0).toFixed(4)}</h2><p class="muted">camera=${esc(data.camera_id)} · status=${esc(data.status)} · warmup=${esc(data.global_graph_context?.warmup)}</p>`;
 const overlay=data.artifacts?.overlay; if(overlay)document.getElementById('overlay').src=asset(window.EVENT_ID,overlay);
 const frame=data.artifacts?.frame; if(frame){document.getElementById('frame').style.display='block';document.getElementById('frame').src=asset(window.EVENT_ID,frame)}
 const graphData=mergeNoveltyAndVlm(data);
 if(window.ForceGraphViz){
   ForceGraphViz.renderForceGraph('svgGraph', graphData, {mode:'event', height:580, pinOnDrag:true, onNodeClick:selectNode, onLinkClick:selectLink});
 }else{
   document.getElementById('svgGraph').innerHTML='<div class="graph-empty">그래프 라이브러리를 불러오지 못했습니다.</div>';
 }
 document.getElementById('reasonBox').innerHTML=`<div class="graph-list"><h3>Final reasons</h3>${(data.final_reason||[]).map(x=>`<p>${esc(x)}</p>`).join('')||'<p class="muted">reason 없음</p>'}</div><div class="graph-list" style="margin-top:12px"><h3>New / rare edges</h3>${(data.novelty?.edges||[]).slice(0,20).map(e=>`<p>${esc(e.key)} · novelty=${Number(e.novelty_score||0).toFixed(3)} · prev=${e.previous_count??0}</p>`).join('')||'<p class="muted">없음</p>'}</div>`;
 document.getElementById('json').textContent=JSON.stringify({eval_context:data.eval_context,novelty:data.novelty,semantic_novelty:data.semantic_novelty,vlm_relation_refinement:data.vlm_relation_refinement,fusion:data.fusion,graph:data.event_graph,semantic_graph:data.semantic_event_graph},null,2);
}
load();
