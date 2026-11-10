(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.RoadRouter = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';
  const EPS = 1e-7;
  const distance = (a, b) => Math.hypot(a.wx - b.wx, a.wy - b.wy);
  function world(data, zone, x, y) {
    const z = data.zones.find(z => z.id === Number(zone));
    if (!z) throw new Error('Unknown zone ' + zone);
    const [minNorth, minWest, maxNorth, maxWest] = z.bounds;
    return { zone: z.id, x, y, wx: -maxWest + x / data.width * (maxWest - minWest),
      wy: -maxNorth + y / data.height * (maxNorth - minNorth) };
  }
  function build(data) {
    const nodes = [], edges = [], adj = [], lookup = new Map();
    function node(zone, x, y) {
      const key = `${zone}:${x.toFixed(4)}:${y.toFixed(4)}`;
      if (!lookup.has(key)) {
        const id = nodes.length; lookup.set(key, id);
        nodes.push({ ...world(data, zone, x, y), id }); adj.push([]);
      }
      return lookup.get(key);
    }
    function edge(a, b, meta) {
      if (a === b) return;
      const e = { a, b, ...meta, length: distance(nodes[a], nodes[b]) };
      edges.push(e); adj[a].push({ to: b, edge: e }); adj[b].push({ to: a, edge: e });
    }
    for (const r of data.roads) {
      const ids = r.points.map(p => node(r.zone, p[0], p[1]));
      for (let i = 1; i < ids.length; i++) edge(ids[i - 1], ids[i], {
        id: `${r.id}:${i}`, roadId: r.id, name: r.name, kind: r.kind, zone: r.zone });
    }
    for (const l of data.links) edge(node(...l.from), node(...l.to), {
      id: l.id, roadId: l.id, name: l.name, kind: 'border' });
    return { data, nodes, edges, adj };
  }
  function project(network, point, blocked = new Set()) {
    const p = world(network.data, point.zone, point.x, point.y);
    let best = null;
    for (const e of network.edges) {
      if (e.kind === 'border' || e.zone !== p.zone || blocked.has(e.id)) continue;
      const a = network.nodes[e.a], b = network.nodes[e.b];
      const vx = b.wx - a.wx, vy = b.wy - a.wy;
      const t = Math.max(0, Math.min(1, ((p.wx - a.wx) * vx + (p.wy - a.wy) * vy) / (vx * vx + vy * vy)));
      const q = world(network.data, p.zone, a.x + t * (b.x - a.x), a.y + t * (b.y - a.y));
      const d = distance(p, q);
      if (!best || d < best.distance) best = { point: q, edge: e, t, distance: d };
    }
    return best;
  }
  class Heap {
    constructor() { this.items = []; }
    push(v) {
      const a = this.items; let i = a.length; a.push(v);
      while (i > 0) { const p = (i - 1) >> 1; if (a[p].f <= v.f) break; a[i] = a[p]; i = p; }
      a[i] = v;
    }
    pop() {
      const a = this.items, first = a[0], last = a.pop();
      if (!a.length) return first;
      let i = 0;
      while (i * 2 + 1 < a.length) {
        let c = i * 2 + 1;
        if (c + 1 < a.length && a[c + 1].f < a[c].f) c++;
        if (last.f <= a[c].f) break; a[i] = a[c]; i = c;
      }
      a[i] = last; return first;
    }
  }
  function route(network, start, goal, options = {}) {
    const now = () => typeof performance !== 'undefined' ? performance.now() : Date.now();
    const begun = now(), blocked = options.blocked || new Set();
    const from = project(network, start, blocked), to = project(network, goal, blocked);
    if (!from || !to) return { status: 'unmapped', message: 'No mapped roads in the selected zone.' };
    const limit = options.maxApproach === undefined ? 200 : options.maxApproach;
    if (from.distance > limit || to.distance > limit) return {
      status: 'too-far', message: `That pin is ${Math.round(Math.max(from.distance, to.distance))} yd from a mapped road. Choose a point within ${limit} yd of the network.`, from, to };
    const nodes = network.nodes.slice(), adj = network.adj.map(a => a.filter(e => !blocked.has(e.edge.id)));
    function connect(a, b, edge, length) {
      const e = { ...edge, a, b, length };
      adj[a].push({ to: b, edge: e }); adj[b].push({ to: a, edge: e });
    }
    function endpoint(p) {
      if (p.t <= EPS) return p.edge.a;
      if (p.t >= 1 - EPS) return p.edge.b;
      const id = nodes.length; nodes.push({ ...p.point, id }); adj.push([]);
      connect(id, p.edge.a, p.edge, p.edge.length * p.t);
      connect(id, p.edge.b, p.edge, p.edge.length * (1 - p.t)); return id;
    }
    const s = endpoint(from), g = endpoint(to);
    if (from.edge.id === to.edge.id && s !== g) connect(s, g, from.edge, from.edge.length * Math.abs(to.t - from.t));
    const score = new Map([[s, 0]]), previous = new Map(), closed = new Set(), expanded = [], heap = new Heap();
    const heuristic = id => options.dijkstra ? 0 : distance(nodes[id], nodes[g]);
    heap.push({ id: s, g: 0, f: heuristic(s) });
    const trailWeight = options.preferRoads ? 1.45 : 1;
    while (heap.items.length) {
      const current = heap.pop(), u = current.id;
      if (closed.has(u) || current.g > score.get(u) + EPS) continue;
      closed.add(u); expanded.push(nodes[u]);
      if (u === g) break;
      for (const { to: v, edge: e } of adj[u]) {
        const cost = e.length * (e.kind === 'trail' ? trailWeight : 1), next = current.g + cost;
        if (next + EPS < (score.get(v) ?? Infinity)) {
          score.set(v, next); previous.set(v, { id: u, edge: e });
          heap.push({ id: v, g: next, f: next + heuristic(v) });
        }
      }
    }
    if (!closed.has(g)) return { status: 'disconnected', message: 'No connected road route. Reopen a closed segment or choose another destination.', expanded, from, to };
    const segments = []; let cur = g;
    while (cur !== s) {
      const p = previous.get(cur);
      segments.push({ from: nodes[p.id], to: nodes[cur], ...p.edge }); cur = p.id;
    }
    segments.reverse();
    const startWorld = world(network.data, start.zone, start.x, start.y), goalWorld = world(network.data, goal.zone, goal.x, goal.y);
    if (from.distance > EPS) segments.unshift({ from: startWorld, to: from.point, length: from.distance,
      kind: 'approach', roadId: 'start-approach', name: 'Estimated approach to the road' });
    if (to.distance > EPS) segments.push({ from: to.point, to: goalWorld, length: to.distance,
      kind: 'approach', roadId: 'goal-approach', name: 'Estimated approach to the quest pin' });
    return { status: 'ok', segments, from, to, expanded, weightedCost: score.get(g),
      distance: segments.reduce((n, s) => n + s.length, 0), estimated: from.distance + to.distance,
      roadDistance: segments.filter(s => s.kind !== 'approach').reduce((n, s) => n + s.length, 0), ms: now() - begun };
  }
  function itinerary(result) {
    if (result.status !== 'ok') return [];
    const groups = [];
    for (const s of result.segments) {
      const last = groups[groups.length - 1];
      if (last && last.roadId === s.roadId) { last.length += s.length; last.to = s.to; }
      else groups.push({ roadId: s.roadId, name: s.name, kind: s.kind, zone: s.from.zone, to: s.to, length: s.length });
    }
    return groups;
  }
  return { build, world, distance, project, route, itinerary };
});
