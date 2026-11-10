(() => {
  'use strict';
  const $ = id => document.getElementById(id), R = RoadRouter, data = ROAD_DATA, network = R.build(data);
  const W = data.width, H = data.height, svg = $('map'), overlay = $('overlays');
  const byPlace = id => data.places.find(p => p.id === id);
  const zoneName = id => data.zones.find(z => z.id === Number(id)).name;
  const copyPlace = p => ({ zone: p.zone, x: p.x, y: p.y, name: p.name, place: p.id });
  const esc = s => String(s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const fmt = n => Math.round(n).toLocaleString('en-US');
  const time = seconds => seconds < 60 ? Math.ceil(seconds) + ' sec' : Math.floor(seconds / 60) + 'm ' + Math.round(seconds % 60) + 's';
  let start = copyPlace(byPlace('brill')), goal = copyPlace(byPlace('scarlet')), zone = 1420, mode = 'goal';
  let result, groups = [], blocked = new Set(), view = { x: 0, y: 0, w: W, h: H };
  let playing = false, traveled = 0, actor = null, lastFrame = 0, previousActorZone = null, drag = null;
  let frameHandle = 0;

  for (const select of [$('start-select'), $('goal-select')]) {
    const custom = document.createElement('option'); custom.value = ''; custom.textContent = 'Custom map pin'; select.appendChild(custom);
    for (const z of data.zones) {
      const group = document.createElement('optgroup'); group.label = z.name;
      for (const p of data.places.filter(p => p.zone === z.id)) {
        const option = document.createElement('option'); option.value = p.id; option.textContent = p.name; group.appendChild(option);
      }
      select.appendChild(group);
    }
  }
  for (const z of data.zones) {
    const b = document.createElement('button'); b.textContent = z.name; b.dataset.zone = z.id;
    b.addEventListener('click', () => setZone(z.id)); $('zone-tabs').appendChild(b);
  }
  function setView() { svg.setAttribute('viewBox', `${view.x} ${view.y} ${view.w} ${view.h}`); }
  function setZone(id, resetView = true) {
    zone = Number(id); $('map-image').setAttribute('href', MAP_IMAGES[zone]);
    $('map-title').textContent = zoneName(zone) + ' road map'; svg.setAttribute('aria-label', 'Interactive ' + zoneName(zone) + ' road map');
    $('map-caption').textContent = data.zones.find(z => z.id === zone).subtitle;
    document.querySelectorAll('[data-zone]').forEach(b => { b.classList.toggle('active', Number(b.dataset.zone) === zone); b.setAttribute('aria-pressed', Number(b.dataset.zone) === zone); });
    if (resetView) { view = { x: 0, y: 0, w: W, h: H }; setView(); }
    render();
  }
  function stop(reset = false) {
    playing = false; cancelAnimationFrame(frameHandle); frameHandle = 0; lastFrame = 0;
    if (reset) { traveled = 0; actor = null; previousActorZone = null; }
    $('walk').textContent = traveled && result && traveled < result.distance ? '▶ Continue walk' : '▶ Walk route';
  }
  function refresh() {
    stop(true);
    $('start-select').value = start.place || ''; $('goal-select').value = goal.place || '';
    for (const [type, point] of [['start', start], ['goal', goal]]) {
      $(type + '-coord').textContent = `${zoneName(point.zone)} · ${(point.x / W * 100).toFixed(1)}, ${(point.y / H * 100).toFixed(1)}`;
    }
    result = R.route(network, start, goal, { blocked, preferRoads: $('prefer-roads').checked });
    groups = R.itinerary(result); $('steps').replaceChildren();
    $('reopen').disabled = blocked.size === 0; $('reopen').textContent = `Reopen closed segments (${blocked.size})`;
    $('progress-fill').style.width = '0%'; $('sim-status').textContent = 'Simulation · 12× walking speed';
    $('walk').disabled = result.status !== 'ok' || result.distance < .1;
    $('route-note').className = ''; $('route-status').className = '';
    if (result.status === 'ok') {
      $('distance').textContent = fmt(result.distance); $('eta').textContent = time(result.distance / 7);
      $('route-status').textContent = 'Route found';
      const crossing = new Set(result.segments.map(s => s.from.zone)).size > 1;
      $('route-note').textContent = result.estimated > 3
        ? `${fmt(result.estimated)} yd of estimated off-road approach. These dashed sections are not terrain-checked.`
        : crossing ? 'Connected across zone borders. The map changes as your simulated player travels.' : 'Both pins connect to the traced road network.';
      $('route-note').classList.toggle('warning', result.estimated > 3);
      for (const g of groups) {
        const li = document.createElement('li'), name = document.createElement('div'), detail = document.createElement('div');
        name.textContent = g.kind === 'border' ? 'Continue into ' + zoneName(g.to.zone) : g.name;
        detail.textContent = g.kind === 'border' ? 'Zone connection' : `${fmt(g.length)} yd · ${zoneName(g.zone)}${g.kind === 'trail' ? ' · trail' : ''}`;
        detail.className = 'step-meta'; li.append(name, detail); $('steps').appendChild(li);
      }
      $('search-stats').textContent = `${result.expanded.length} nodes explored · ${result.ms.toFixed(2)} ms`;
      $('notice').textContent = crossing ? `Route to ${goal.name} crosses ${new Set(result.segments.flatMap(s => [s.from.zone, s.to.zone])).size} zones.` : `Road route to ${goal.name}. Drag a pin to recalculate.`;
    } else {
      $('distance').textContent = '—'; $('eta').textContent = '—'; $('route-status').textContent = 'No road route';
      $('route-status').className = 'no-route'; $('route-note').textContent = result.message;
      $('route-note').classList.add('warning'); $('notice').textContent = result.message;
      $('search-stats').textContent = `${result.expanded?.length || 0} nodes explored`;
    }
    updateProgress(); render();
  }
  function poly(a, b, stroke, width, extra = '') {
    return `<path d="M${a.x},${a.y} L${b.x},${b.y}" fill="none" stroke="${stroke}" stroke-width="${width}" stroke-linecap="round" ${extra}/>`;
  }
  function marker(p, type, label) {
    const color = type === 'player' ? '#82beff' : '#edc574';
    const shape = type === 'player'
      ? `<circle r="9" fill="#183c5b" stroke="${color}" stroke-width="2.5"/><path d="M0 -5 L4 4 L0 2 L-4 4Z" fill="white"/>`
      : `<path d="M0 -12 L10 0 L0 12 L-10 0Z" fill="#3f3219" stroke="${color}" stroke-width="2.5"/><text y="4" text-anchor="middle" font-size="12" font-weight="bold" fill="#ffe7a2">!</text>`;
    const dx = p.x > 810 ? -16 : 16, anchor = p.x > 810 ? 'end' : 'start', dy = p.y < 28 ? 25 : -15;
    return `<g class="endpoint" data-endpoint="${type}" transform="translate(${p.x},${p.y})"><circle r="16" fill="${color}" opacity=".16"/>${shape}<title>${esc(label)} — drag to move</title><text x="${dx}" y="${dy}" text-anchor="${anchor}" class="map-label">${esc(label)}</text></g>`;
  }
  function render() {
    if (!result) return;
    const chunks = ['<g class="network-lines">'];
    for (const e of network.edges.filter(e => e.zone === zone)) {
      const a = network.nodes[e.a], b = network.nodes[e.b], shut = blocked.has(e.id);
      chunks.push(poly(a, b, '#292016', 4, 'opacity=".45"'));
      chunks.push(`<g><title>${esc(e.name)}</title>` + poly(a, b, shut ? '#ff7f70' : '#f6d78e', shut ? 3.8 : 1.6,
        `${shut ? 'stroke-dasharray="4 3"' : ''} opacity="${shut ? 1 : e.kind === 'trail' ? .55 : .8}"`) + '</g>');
    }
    chunks.push('</g><g class="search-nodes">');
    for (const n of result.expanded || []) if (n.zone === zone) chunks.push(`<circle cx="${n.x}" cy="${n.y}" r="3" fill="#88ffff" opacity=".65"/>`);
    chunks.push('</g>');
    if (result.status === 'ok') {
      for (const s of result.segments) {
        if (s.from.zone !== zone || s.to.zone !== zone) continue;
        chunks.push(poly(s.from, s.to, '#111b19', 7, 'opacity=".8"'));
        chunks.push(poly(s.from, s.to, s.kind === 'approach' ? '#fff1cc' : '#71f6d9', 3.2,
          s.kind === 'approach' ? 'stroke-dasharray="5 5"' : ''));
      }
      for (const s of result.segments.filter(s => s.kind === 'border')) {
        const at = s.from.zone === zone ? s.from : s.to.zone === zone ? s.to : null;
        if (at) {
          const label = at.zone === s.from.zone ? 'Continue in ' + zoneName(s.to.zone) : 'From ' + zoneName(s.from.zone);
          chunks.push(`<g transform="translate(${at.x},${at.y})"><circle r="7" fill="#182a27" stroke="#7ce8cf" stroke-width="2"/><text x="12" y="4" class="map-label">${esc(label)}</text></g>`);
        }
      }
    }
    chunks.push('<g class="place-markers">');
    for (const p of data.places.filter(p => p.zone === zone)) {
      if ([start, goal, actor].filter(Boolean).some(e => e.zone === zone && Math.hypot(e.x - p.x, e.y - p.y) < 25)) continue;
      chunks.push(`<g><circle cx="${p.x}" cy="${p.y}" r="3" fill="#f0d39a" stroke="#493923"/><text class="place-label" x="${p.x + 7}" y="${p.y - 5}">${esc(p.name.replace(' approach', ''))}</text></g>`);
    }
    chunks.push('</g>');
    if (start.zone === zone && actor) chunks.push(`<circle cx="${start.x}" cy="${start.y}" r="4" fill="#82beff" opacity=".55"/>`);
    const player = actor || start;
    if (player.zone === zone) chunks.push(marker(player, 'player', actor ? 'Player · simulated' : 'Player'));
    if (goal.zone === zone) chunks.push(marker(goal, 'goal', 'Quest'));
    overlay.innerHTML = chunks.join('');
  }
  function updateProgress() {
    const total = result?.status === 'ok' ? result.distance : 0;
    $('progress-fill').style.width = `${total ? Math.min(100, traveled / total * 100) : 0}%`;
    let sum = 0;
    [...$('steps').children].forEach((li, i) => {
      const end = sum + groups[i].length;
      li.classList.toggle('current', traveled >= sum && (traveled < end || i === groups.length - 1)); sum = end;
    });
  }
  function animate(timestamp) {
    if (!playing || result.status !== 'ok') return;
    if (lastFrame) traveled = Math.min(result.distance, traveled + Math.min(.1, (timestamp - lastFrame) / 1000) * 84);
    lastFrame = timestamp;
    let left = traveled, current = result.segments[result.segments.length - 1];
    for (const s of result.segments) { current = s; if (left <= s.length) break; left -= s.length; }
    if (current) {
      const t = current.length < 1e-7 ? 1 : Math.min(1, left / current.length);
      actor = current.from.zone !== current.to.zone ? { ...(t < .5 ? current.from : current.to) }
        : { zone: current.from.zone, x: current.from.x + t * (current.to.x - current.from.x), y: current.from.y + t * (current.to.y - current.from.y) };
      if (previousActorZone !== null && actor.zone !== previousActorZone) setZone(actor.zone);
      previousActorZone = actor.zone;
    }
    $('sim-status').textContent = traveled >= result.distance ? 'Arrived at the quest pin · simulation complete' : `${fmt(result.distance - traveled)} yd remaining · simulation 12×`;
    updateProgress(); render();
    if (traveled >= result.distance) { stop(); $('walk').textContent = '↺ Walk again'; }
    else frameHandle = requestAnimationFrame(animate);
  }
  $('walk').addEventListener('click', () => {
    if (playing) { stop(); return; }
    if (traveled >= result.distance) traveled = 0;
    previousActorZone = start.zone; if (!traveled) setZone(start.zone);
    playing = true; lastFrame = 0; $('walk').textContent = 'Ⅱ Pause walk'; frameHandle = requestAnimationFrame(animate);
  });
  function zoom(factor, center = { x: view.x + view.w / 2, y: view.y + view.h / 2 }) {
    const width = Math.max(W / 5, Math.min(W, view.w * factor)), ratio = width / view.w;
    view = { x: center.x - (center.x - view.x) * ratio, y: center.y - (center.y - view.y) * ratio, w: width, h: width / 1.5 };
    view.x = Math.max(0, Math.min(W - view.w, view.x)); view.y = Math.max(0, Math.min(H - view.h, view.y)); setView();
  }
  $('zoom-in').addEventListener('click', () => zoom(.75)); $('zoom-out').addEventListener('click', () => zoom(1.333));
  $('fit').addEventListener('click', () => { view = { x: 0, y: 0, w: W, h: H }; setView(); });
  function coordinates(event) { return new DOMPoint(event.clientX, event.clientY).matrixTransform(svg.getScreenCTM().inverse()); }
  function movePoint(type, p) {
    const point = { zone, x: Math.max(0, Math.min(W, p.x)), y: Math.max(0, Math.min(H, p.y)), name: 'Custom ' + (type === 'player' ? 'player position' : 'quest pin') };
    if (type === 'player') start = point; else goal = point; refresh();
  }
  svg.addEventListener('pointerdown', e => {
    if (e.button !== 0 && e.button !== 1) return;
    const endpoint = e.target.closest('[data-endpoint]');
    drag = { type: endpoint ? endpoint.dataset.endpoint : mode, initial: coordinates(e), clientX: e.clientX, clientY: e.clientY, view: { ...view }, moved: false };
    if (e.button === 1) drag.type = 'pan';
    if (endpoint) stop(true);
    svg.setPointerCapture(e.pointerId); e.preventDefault();
  });
  svg.addEventListener('pointermove', e => {
    const p = coordinates(e); $('mouse-coord').textContent = `Map coordinates: ${(p.x / W * 100).toFixed(1)}, ${(p.y / H * 100).toFixed(1)}`;
    if (!drag) return;
    if (Math.hypot(e.clientX - drag.clientX, e.clientY - drag.clientY) > 4) drag.moved = true;
    if (drag.type === 'pan') {
      const rect = svg.getBoundingClientRect();
      view.x = Math.max(0, Math.min(W - view.w, drag.view.x - (e.clientX - drag.clientX) / rect.width * drag.view.w));
      view.y = Math.max(0, Math.min(H - view.h, drag.view.y - (e.clientY - drag.clientY) / rect.height * drag.view.h)); setView();
    } else if (drag.moved && (drag.type === 'player' || drag.type === 'goal')) movePoint(drag.type, p);
  });
  svg.addEventListener('pointerup', e => {
    if (!drag) return;
    const p = coordinates(e), type = drag.type, moved = drag.moved; drag = null;
    if (svg.hasPointerCapture(e.pointerId)) svg.releasePointerCapture(e.pointerId);
    if (type === 'player' || type === 'goal') movePoint(type, p);
    else if (type === 'close' && !moved) {
      const near = R.project(network, { zone, x: p.x, y: p.y });
      if (near && near.distance < 75) { if (blocked.has(near.edge.id)) blocked.delete(near.edge.id); else blocked.add(near.edge.id); refresh(); }
      else $('notice').textContent = 'Click closer to a visible road or trail to close a segment.';
    }
  });
  svg.addEventListener('pointercancel', () => { drag = null; });
  svg.addEventListener('wheel', e => { e.preventDefault(); zoom(e.deltaY > 0 ? 1.15 : .87, coordinates(e)); }, { passive: false });
  document.querySelectorAll('[data-mode]').forEach(b => b.addEventListener('click', () => {
    mode = b.dataset.mode; document.querySelectorAll('[data-mode]').forEach(x => { x.classList.toggle('active', x === b); x.setAttribute('aria-pressed', x === b); });
    svg.className.baseVal = 'map ' + (mode === 'pan' ? 'pan' : mode === 'close' ? 'closed' : 'place');
    $('mode-instructions').textContent = { player: 'Click the map to move your player pin. The route recalculates immediately.',
      goal: 'Click the map to move the quest pin, or drag either marker.', pan: 'Drag to pan the map. Use the wheel to zoom, or Fit to reset.', close: 'Click a road segment to close or reopen it. A disconnected graph gives no route, never a straight-line substitute.' }[mode];
  }));
  for (const [type, select] of [['player', $('start-select')], ['goal', $('goal-select')]]) select.addEventListener('change', () => {
    if (!select.value) return;
    const p = copyPlace(byPlace(select.value)); if (type === 'player') start = p; else goal = p;
    setZone(p.zone); refresh();
  });
  function example(which) {
    blocked.clear(); $('prefer-roads').checked = false;
    const ids = { local: ['brill', 'scarlet'], regional: ['lordaeron', 'tarren'], loop: ['shadowfang', 'pyrewood'] }[which];
    start = copyPlace(byPlace(ids[0])); goal = copyPlace(byPlace(ids[1])); setZone(start.zone); refresh();
  }
  document.querySelectorAll('[data-example]').forEach(b => b.addEventListener('click', () => example(b.dataset.example)));
  $('reset').addEventListener('click', () => example('local'));
  $('reopen').addEventListener('click', () => { blocked.clear(); refresh(); });
  $('roads-toggle').addEventListener('change', e => document.body.classList.toggle('hide-network', !e.target.checked));
  $('places-toggle').addEventListener('change', e => document.body.classList.toggle('hide-places', !e.target.checked));
  $('search-toggle').addEventListener('change', e => document.body.classList.toggle('show-search', e.target.checked));
  $('prefer-roads').addEventListener('change', refresh);
  $('export').addEventListener('click', () => {
    const url = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' }));
    const a = document.createElement('a'); a.href = url; a.download = 'forever-road-data.json'; a.click(); setTimeout(() => URL.revokeObjectURL(url), 2000);
  });
  $('network-stats').textContent = `${data.zones.length} maps · ${data.roads.length} roads / trails · ${network.nodes.length} graph nodes`;
  // Read-only diagnostics for browser verification; no external communication.
  window.RouteLab = { getState: () => ({ zone, mode, start: { ...start }, goal: { ...goal }, status: result.status,
    distance: result.distance, explored: result.expanded?.length || 0, playing, traveled, closedSegments: blocked.size }) };
  refresh(); setZone(zone);
})();
