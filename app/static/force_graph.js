/* GPU Server v5.2 Force Graph Renderer
 * D3-based interactive graph used by Event Detail and Global Graph pages.
 * - force-directed moving layout
 * - draggable nodes
 * - zoom/pan
 * - curved directed edges
 * - risk/novelty-aware styling
 */
(function(){
  function esc(s){return String(s??'').replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]))}
  function cssClass(d){
    const risk = Number(d.semantic_risk ?? d.vlm_risk ?? d.risk ?? 0);
    const nov = Number(d.novelty_score ?? d.novelty ?? 0);
    if(risk >= 0.65) return 'risky';
    if(nov >= 0.9 || d.is_new) return 'new';
    if(nov >= 0.55 || d.is_rare) return 'rare';
    return 'normal';
  }
  function normalizeEventGraph(data){
    const graph = data.event_graph || data || {nodes:[],edges:[]};
    const nodes = (graph.nodes||[]).map(n=>({
      id: n.id || n.node_id || n.label,
      label: n.label || n.node_label || n.id,
      type: n.type || 'object',
      count: n.count,
      confidence: n.confidence,
      bbox: n.bbox,
      crop_url: n.crop_url,
      crop_path: n.crop_path,
      raw: n
    }));
    const nodeSet = new Set(nodes.map(n=>n.id));
    const links = (graph.edges||[]).map((e,i)=>{
      const s = e.subject_id || e.source || e.subject || e.subject_label;
      const t = e.object_id || e.target || e.object || e.object_label;
      return {
        id: `${s}|${e.relation||'related'}|${t}|${i}`,
        source: s,
        target: t,
        subject_label: e.subject_label,
        object_label: e.object_label,
        relation: e.relation || e.label || 'related',
        confidence: e.confidence,
        novelty_score: e.novelty_score,
        semantic_risk: e.semantic_risk ?? e.vlm_risk,
        count: e.count,
        className: cssClass(e),
        evidence_url: e.evidence_url,
        raw: e
      }
    }).filter(e=>nodeSet.has(e.source) && nodeSet.has(e.target));
    return {nodes,links};
  }
  function normalizeGlobalGraph(g){
    const rawNodes = g.nodes || [];
    const rawEdges = g.edges || g.top_edges || [];
    const labelSet = new Map();
    rawNodes.forEach(n=>labelSet.set(n.node_label || n.label, {id:n.node_label||n.label, label:n.node_label||n.label, count:n.count, type:'global-node', raw:n}));
    rawEdges.forEach(e=>{
      const s=e.subject_label, o=e.object_label;
      if(s && !labelSet.has(s)) labelSet.set(s,{id:s,label:s,type:'global-node'});
      if(o && !labelSet.has(o)) labelSet.set(o,{id:o,label:o,type:'global-node'});
    });
    const nodes = Array.from(labelSet.values());
    const links = rawEdges.map((e,i)=>({
      id:`${e.subject_label}|${e.relation}|${e.object_label}|${i}`,
      source:e.subject_label,
      target:e.object_label,
      relation:e.relation,
      count:e.count,
      novelty_score:e.novelty_score,
      semantic_risk:e.vlm_risk,
      className: (Number(e.count||0)<=1 ? 'rare' : 'normal'),
      raw:e
    }));
    return {nodes,links};
  }
  function curvedPath(d, curvature){
    const sx=d.source.x, sy=d.source.y, tx=d.target.x, ty=d.target.y;
    const dx=tx-sx, dy=ty-sy;
    const dr=Math.sqrt(dx*dx+dy*dy) || 1;
    const mx=(sx+tx)/2, my=(sy+ty)/2;
    const offset = (d._curveOffset ?? curvature ?? 28);
    const cx = mx - dy/dr*offset;
    const cy = my + dx/dr*offset;
    return `M${sx},${sy} Q${cx},${cy} ${tx},${ty}`;
  }
  function assignCurveOffsets(links){
    const groups = new Map();
    links.forEach(l=>{
      const a = typeof l.source==='object'?l.source.id:l.source;
      const b = typeof l.target==='object'?l.target.id:l.target;
      const key = [a,b].sort().join('::');
      if(!groups.has(key)) groups.set(key,[]);
      groups.get(key).push(l);
    });
    groups.forEach(arr=>{
      arr.forEach((l,i)=>{
        const mid=(arr.length-1)/2;
        l._curveOffset = 24 + (i-mid)*26;
      });
    });
  }
  function renderForceGraph(container, payload, opts={}){
    const el = typeof container === 'string' ? document.getElementById(container) : container;
    if(!el) return;
    if(!window.d3){
      el.innerHTML = '<div class="graph-empty">D3.js가 로드되지 않았습니다. 네트워크 또는 CDN 접근을 확인하세요.</div>';
      return;
    }
    const data = opts.mode === 'global' ? normalizeGlobalGraph(payload) : normalizeEventGraph(payload);
    const nodes = data.nodes.map(d=>Object.assign({}, d));
    const links = data.links.map(d=>Object.assign({}, d));
    assignCurveOffsets(links);
    el.innerHTML='';
    const rect = el.getBoundingClientRect();
    const width = Math.max(760, rect.width || 1000);
    const height = Number(opts.height || rect.height || 560);
    const svg = d3.select(el).append('svg')
      .attr('viewBox', [0,0,width,height])
      .attr('class','force-svg')
      .attr('preserveAspectRatio','xMidYMid meet');

    const defs = svg.append('defs');
    defs.append('marker')
      .attr('id', opts.markerId || `arrow-${Math.random().toString(36).slice(2)}`)
      .attr('viewBox','0 -5 10 10')
      .attr('refX',18)
      .attr('refY',0)
      .attr('markerWidth',7)
      .attr('markerHeight',7)
      .attr('orient','auto')
      .append('path').attr('d','M0,-5L10,0L0,5').attr('class','arrow-path');
    const markerId = defs.select('marker').attr('id');

    const root = svg.append('g').attr('class','force-root');
    svg.call(d3.zoom().scaleExtent([0.25,3.5]).on('zoom', (event)=>root.attr('transform', event.transform)));

    const linkG = root.append('g').attr('class','force-links');
    const labelG = root.append('g').attr('class','force-link-labels');
    const nodeG = root.append('g').attr('class','force-nodes');

    const link = linkG.selectAll('path')
      .data(links)
      .join('path')
      .attr('class', d=>`force-link ${d.className||'normal'}`)
      .attr('marker-end', `url(#${markerId})`);

    const linkLabel = labelG.selectAll('text')
      .data(links)
      .join('text')
      .attr('class','force-link-label')
      .text(d=>d.count ? `${d.relation} (${d.count})` : d.relation);

    const node = nodeG.selectAll('g')
      .data(nodes)
      .join('g')
      .attr('class', d=>`force-node ${d.type||''}`)
      .call(d3.drag()
        .on('start', dragstarted)
        .on('drag', dragged)
        .on('end', dragended));

    node.append('circle')
      .attr('r', d=> opts.mode==='global' ? Math.max(18, Math.min(44, 16 + Math.sqrt(Number(d.count||1))*5)) : 28)
      .attr('class', d=> d.label==='person' ? 'person-node' : 'object-node');

    node.append('text')
      .attr('class','force-node-label')
      .attr('y',4)
      .attr('text-anchor','middle')
      .text(d=>d.label);

    node.append('title').text(d=>`${d.id}\ncount=${d.count??''}\nconfidence=${d.confidence??''}`);
    link.append('title').text(d=>`${d.source} -- ${d.relation} --> ${d.target}\ncount=${d.count??''}\nnovelty=${d.novelty_score??''}\nrisk=${d.semantic_risk??''}`);

    if(typeof opts.onNodeClick === 'function') node.on('click', (event,d)=>opts.onNodeClick(d,event));
    if(typeof opts.onLinkClick === 'function') link.on('click', (event,d)=>opts.onLinkClick(d,event));

    const simulation = d3.forceSimulation(nodes)
      .force('link', d3.forceLink(links).id(d=>d.id).distance(opts.linkDistance || (opts.mode==='global'?160:130)).strength(0.45))
      .force('charge', d3.forceManyBody().strength(opts.charge || -640))
      .force('center', d3.forceCenter(width/2, height/2))
      .force('collision', d3.forceCollide().radius(d=> opts.mode==='global' ? Math.max(36, Math.min(62, 28 + Math.sqrt(Number(d.count||1))*4)) : 48))
      .force('x', d3.forceX(width/2).strength(0.04))
      .force('y', d3.forceY(height/2).strength(0.04));

    simulation.on('tick', ()=>{
      link.attr('d', d=>curvedPath(d, opts.curvature || 30));
      linkLabel.attr('x', d=>(d.source.x+d.target.x)/2).attr('y', d=>(d.source.y+d.target.y)/2 - 8);
      node.attr('transform', d=>`translate(${d.x},${d.y})`);
    });

    function dragstarted(event,d){ if(!event.active) simulation.alphaTarget(0.35).restart(); d.fx=d.x; d.fy=d.y; }
    function dragged(event,d){ d.fx=event.x; d.fy=event.y; }
    function dragended(event,d){ if(!event.active) simulation.alphaTarget(0); if(!opts.pinOnDrag){ d.fx=null; d.fy=null; } }

    el._forceGraph = {simulation, svg, nodes, links};
    return el._forceGraph;
  }
  window.ForceGraphViz = {renderForceGraph, normalizeEventGraph, normalizeGlobalGraph};
})();
