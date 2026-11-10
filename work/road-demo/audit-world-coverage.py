from pathlib import Path
import runpy,json,time
h=Path(__file__).resolve().parent;env=runpy.run_path(str(h/'test-world-engine.py'));l=env['lua'];root=h.parent/'world-addon'
for name in ['Data.lua','Router.lua','WorldData.lua']:l.execute(b'local f=function(...)\n'+(root/name).read_bytes()+b'\nend;f("ForeverRoads",A)')
l.execute(b'''
function auditAnchors()
 local G=A.PathGrid;G.Deadline(math.huge)
 local wanted={};local anchors={};local cities={}
 for _,z in ipairs(A.WorldCatalog.maps) do wanted[z.id]=z;anchors[z.id]={};if z.city then cities[#cities+1]=z end end
 local singleton={[30]=1459,[489]=1460,[529]=1461,[2997]=2524}
 local function save(zone,p)
  local list=anchors[zone];if not list or #list>=96 then return end
  local b=wanted[zone].bounds
  if p.x<b[1] or p.x>b[3] or p.y<b[2] or p.y>b[4] then return end
  local count=0
  for _,q in ipairs(list) do
   if (p.x-q.x)^2+(p.y-q.y)^2<35^2 then return end
   if q.k==p.k then count=count+1 end
  end
  if count<6 then list[#list+1]=p end
 end
 for _,map in ipairs({0,1,2991,30,489,529,2997}) do
  local st=G.State(map)
  for k=0,st.D.nx*st.D.ny-1 do
   for _,id in ipairs(G.nodesOf(st,k)) do
    local cell,layer,component=G.metadata(st,id)
    local zone=G.zoneAt(st,k,cell) or singleton[map]
    local x=st.x0+(math.floor(k/st.ny)*st.C+math.floor(cell/st.C)+.5)*st.cs
    local y=st.y0+((k%st.ny)*st.C+cell%st.C+.5)*st.cs
    local city
    for _,z in ipairs(cities) do local b=z.bounds;if z.continent==map and x>=b[1] and x<=b[3] and y>=b[2] and y<=b[4] then city=z.id end end
    local list=zone and anchors[zone]
    if (list and #list<96) or city then
     local c=G.grid(st,k);local node=G.entrance(st,id)
     if c and node then
      local class=G.CLS[string.byte(c.kind,node+1)]%8
      if class==0 or class==1 or class==5 then
       local p={map=map,x=x,y=y,z=G.zOf(c,node),class=class,component=component,k=k}
       if list and #list<96 then save(zone,p) end
       if city and class==5 then save(city,p) end
      end
     end
    end
   end
  end
 end
 if #anchors[2665]==0 then anchors[2665]=anchors[2521] end
 return anchors
end
''')
start=time.perf_counter();anchors=l.eval(b'auditAnchors')();report={'build':'1.60.1.70862','maps':[],'liveGameVerified':False}
for z in json.loads((h/'all-zone-catalog.json').read_text())['maps']:
 samples=anchors[z['id']];entry={k:z[k] for k in ['id','name','continent']};entry['samples']=[{k.decode():p[k] for k in p.keys()} for p in samples.values()];entry['routeChecked']=False
 if len(samples)>=2:
  choices=list(samples.values());choices.sort(key=lambda p:(p[b'class']!=1,p[b'class']!=5))
  entry['samples']=[{k.decode():p[k] for k in p.keys()} for p in choices]
  for a in choices[:24]:
   candidates=[b for b in choices if b is not a and b[b'component']==a[b'component'] and (b[b'x']-a[b'x'])**2+(b[b'y']-a[b'y'])**2>35**2]
   candidates.sort(key=lambda b:(b[b'x']-a[b'x'])**2+(b[b'y']-a[b'y'])**2)
   for b in candidates[:3]:
    points,cost,expanded,job=l.eval(b'function(map,a,b) return A.Path.FindSync(map,a,b,{style="roads"}) end')(z['continent'],a,b)
    entry['result']=cost.decode() if isinstance(cost,bytes) else cost
    if points:
     entry['routeChecked']=True;entry['points']=len(points);entry['checkedPair']=[{k.decode():p[k] for k in p.keys()} for p in [a,b]];break
   if entry['routeChecked']:break
 report['maps'].append(entry)
 print(z['id'],z['name'],len(samples),entry['routeChecked'],flush=True)
report['seconds']=time.perf_counter()-start;report['mapped']=sum(bool(r['samples']) for r in report['maps']);report['routeChecked']=sum(r['routeChecked'] for r in report['maps'])
(h/'world-coverage-audit.json').write_text(json.dumps(report,indent=2)+'\n');print('mapped',report['mapped'],'route-checked',report['routeChecked'],'of',len(report['maps']),'in',round(report['seconds'],1),'s')
