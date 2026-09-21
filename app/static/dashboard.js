async function safeJson(url, fallback=null){
  try{ const r=await fetch(url,{cache:'no-store'}); if(!r.ok) return fallback; return await r.json(); }
  catch(e){ return fallback; }
}
function esc(s){return String(s??'').replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]))}
function fmtScore(x){return (x===null||x===undefined||x==='')?'':Number(x).toFixed(3)}
function miniEvent(e){return `<div class="event-mini"><a href="/dashboard/events/${esc(e.event_id)}">${esc(e.event_id)}</a><small>${esc(e.camera_id)} · <span class="status-${esc(e.status)}">${esc(e.status)}</span> · ${esc(e.decision||'')}</small><small>${esc(e.updated_at||'')}</small></div>`}
function kv(obj){return Object.entries(obj).map(([k,v])=>`<div>${esc(k)}</div><div>${esc(v)}</div>`).join('')}
async function load(){
  const [health, s, ev, nodes, storage, policy, cameras] = await Promise.all([
    safeJson('/health',{}),
    safeJson('/api/events/status-summary?limit_per_group=12',{incoming:0,processing:0,done:0,failed:0,groups:{}}),
    safeJson('/api/events/recent?limit=80',[]),
    safeJson('/api/edge/nodes',{items:[]}),
    safeJson('/api/storage/stats',{}),
    safeJson('/api/detection-policy',{}),
    safeJson('/api/global-graph/cameras',[]),
  ]);
  document.getElementById('healthBox').innerHTML = `<p class="eyebrow">Health</p><h2>${health.ok?'Healthy':'Degraded'}</h2><div class="kv">${kv({service:health.service||'', events:health.events??'', status:health.status||''})}</div>`;
  document.getElementById('summary').innerHTML=['incoming','processing','done','failed'].map(k=>`<div class="card ${k}"><span>${k}</span><b>${s[k]??0}</b></div>`).join('');
  const groups=s.groups||{};
  const laneNames=[['incoming','입력 대기'],['processing','처리 중'],['done','처리 완료'],['failed','실패/복구 필요']];
  document.getElementById('lanes').innerHTML=laneNames.map(([k,title])=>`<div class="lane"><h3>${title}</h3>${(groups[k]||[]).map(miniEvent).join('')||'<p class="muted">없음</p>'}</div>`).join('');
  document.querySelector('#events tbody').innerHTML=(ev||[]).map(e=>`<tr><td><a href="/dashboard/events/${esc(e.event_id)}">${esc(e.event_id)}</a></td><td>${esc(e.camera_id)}</td><td class="status-${esc(e.status)}">${esc(e.status)}</td><td><span class="badge ${esc(e.decision||'')}">${esc(e.decision||'')}</span></td><td>${fmtScore(e.score)}</td><td>${esc(e.updated_at||'')}</td></tr>`).join('');
  const nodeItems=nodes.items||[];
  document.getElementById('edgeCards').innerHTML=nodeItems.map(n=>`<div class="edge-card ${n.is_alive?'alive':'dead'}"><h3>${esc(n.edge_id)} <span class="pill ${n.is_alive?'ok':'bad'}">${n.is_alive?'alive':'stale'}</span></h3><div class="kv">${kv({camera:n.camera_id,status:n.status,age_sec:n.age_sec?.toFixed?.(1)??'',queue:n.queue_count,failed:n.failed_count,sent:n.sent_count,stream:n.stream_status||'',frame_age:n.last_frame_age_sec??'',detector:n.detector?.model||n.detector?.model_path||''})}</div></div>`).join('')||'<p class="muted">Heartbeat 없음</p>';
  document.getElementById('storageBox').innerHTML=kv({events_mb:storage.events?.mb??'',event_files:storage.events?.files??'',db_mb:storage.database?.mb??'',wal:storage.database?.wal_exists??''});
  document.getElementById('policyBox').innerHTML=kv({policy:policy.server_side_policy||'',motion_candidate:policy.motion_candidate_enabled??false,vlm:policy.vlm?.provider||'',warmup:policy.global_graph?.warmup_events??''});
  const cam=(cameras||[])[0]?.camera_id || (ev||[])[0]?.camera_id;
  if(cam){
    const g=await safeJson('/api/global-graph/'+encodeURIComponent(cam),{});
    document.getElementById('quickGraph').innerHTML=`<div class="graph-list"><h3>${esc(cam)} nodes</h3>${(g.nodes||[]).slice(0,20).map(n=>`<p>${esc(n.node_label)} <b>${n.count}</b></p>`).join('')}</div><div class="graph-list"><h3>Frequent edges</h3>${(g.top_edges||[]).slice(0,20).map(e=>`<p>${esc(e.subject_label)} -- ${esc(e.relation)} → ${esc(e.object_label)} <b>${e.count}</b></p>`).join('')}</div><div class="graph-list"><h3>Rare edges</h3>${(g.rare_edges||[]).slice(0,20).map(e=>`<p>${esc(e.subject_label)} -- ${esc(e.relation)} → ${esc(e.object_label)} <b>${e.count}</b></p>`).join('')}</div>`;
  } else document.getElementById('quickGraph').innerHTML='<p class="muted">아직 camera graph가 없습니다.</p>';
}
document.getElementById('refreshBtn')?.addEventListener('click',load);
document.getElementById('recoverBtn')?.addEventListener('click',async()=>{await safeJson('/api/events/recover-stale?action=mark_failed',{});load();});
load(); setInterval(load,4000);
try{const ws=new WebSocket(`${location.protocol==='https:'?'wss':'ws'}://${location.host}/ws`);ws.onopen=()=>{document.getElementById('wsState').className='pill ok';document.getElementById('wsState').textContent='ws: connected'};ws.onclose=()=>{document.getElementById('wsState').className='pill bad';document.getElementById('wsState').textContent='ws: closed'};ws.onmessage=()=>load()}catch(e){document.getElementById('wsState').className='pill bad';document.getElementById('wsState').textContent='ws: unavailable'}
