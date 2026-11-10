"""Build the public transport and flight graph, with terrain costs for transfers."""
from pathlib import Path
import json,runpy,time,hashlib
h=Path(__file__).resolve().parent;root=h.parent/'world-addon'
env=runpy.run_path(str(h/'test-world-engine.py'));l=env['lua']
l.execute(b'T={}')
up=h.parent/'shortest-path-forever'
for name in ['Routes','Portals','Taxi']:
 l.execute(b'local f=function(...)\n'+(up/'Data'/f'{name}.lua').read_bytes()+b'\nend;f("ForeverRoads",T)')
def plain(t):
 return {k.decode() if isinstance(k,bytes) else k:(v.decode() if isinstance(v,bytes) else v) for k,v in t.items()}
t=l.globals()[b'T'];nodes=[];edges=[]
dock_names=['Ratchet','Booty Bay',"Grom’gol Zeppelin Tower",'Orgrimmar Zeppelin Tower',
            'Menethil Harbor','Theramore',"Rut’theran Village",'Auberdine','Menethil Harbor','Auberdine',
            "Grom’gol Zeppelin Tower",'Tirisfal Zeppelin Tower','Orgrimmar Zeppelin Tower','Tirisfal Zeppelin Tower',
            'Feathermoon Stronghold','The Forgotten Coast','Southshore','Steamwheedle Port','Powderfuse Port',
            'Dalaran (Alterac Mountains)','Zephras Isle','Skywatcher Plateau','Zephras Isle','Auberdine','Stormwind Harbor']
for i,p in sorted(t[b'Docks'].items()):
 p=p[b'walk'] or p;node=plain(p);node.update(id=len(nodes)+1,key='dock'+str(i),name=dock_names[i-1]);nodes.append(node)
 # The client surface is connected at the base of the two Tirisfal platforms.
 if i in (12,14):
  node['x'],node['y']=(2054.7,241.6) if i==12 else (2064,288.6)
  node.pop('z');node['towerApproach']=True
for key,route in sorted(t[b'Routes'].items()):
 stops=sorted(route[b'stops'].items());period=route[b'period']/1000
 for i,(_,stop) in enumerate(stops):
  to=stops[(i+1)%len(stops)][1]
  ride=((to[b'arrive']-stop[b'depart'])/1000)%period
  edges.append(dict(a=stop[b'dock'],b=to[b'dock'],kind=route[b'kind'].decode(),seconds=period/2+ride,
   route=key,faction=route[b'faction'].decode() if route[b'faction'] else None))
for i,p in sorted(t[b'Portals'].items()):
 if p[b'from'][b'map']!=1 or p[b'to'][b'map']!=1:continue
 a=len(nodes)+1
 for end in ['from','to']:
  node=plain(p[end.encode()]);node.update(id=len(nodes)+1,key='portal'+str(i)+end);nodes.append(node)
 edges.append(dict(a=a,b=a+1,kind='portal',seconds=p[b'seconds'],name=p[b'name'].decode()))
# The unmapped tram interior is one ride between its outdoor thresholds.
for origin,dest,city,arrival in [(5,3,'Stormwind','Ironforge'),(6,4,'Ironforge','Stormwind')]:
 a=len(nodes)+1
 nodes.append(dict(plain(t[b'Portals'][origin][b'from']),id=a,key='tram'+city,name=city+' Deeprun Tram entrance'))
 if city=='Ironforge':nodes[-1]['z']=501.9
 nodes.append(dict(plain(t[b'Portals'][dest][b'to']),id=a+1,key='tramExit'+arrival,name=arrival+' Deeprun Tram exit'))
 edges.append(dict(a=a,b=a+1,kind='tram',seconds=150,faction='Alliance',name='Take the Deeprun Tram to '+arrival))
taxi_ids={}
for i,p in sorted(t[b'TaxiNodes'].items()):
 node=plain(p);node.update(id=len(nodes)+1,key='taxi'+str(i),taxi=i)
 nodes.append(node);taxi_ids[i]=node['id']
for _,path in sorted(t[b'TaxiPaths'].items()):
 a,b=taxi_ids[path[b'from']],taxi_ids[path[b'to']]
 edges.append(dict(a=a,b=b,kind='flight',seconds=path[b'seconds']+10))
catalog=json.loads((h/'all-zone-catalog.json').read_text())['maps']
for n in nodes:
 options=[z for z in catalog if z['continent']==n['map'] and z['bounds'][0]<=n['x']<=z['bounds'][2] and z['bounds'][1]<=n['y']<=z['bounds'][3]]
 options.sort(key=lambda z:(z['bounds'][2]-z['bounds'][0])*(z['bounds'][3]-z['bounds'][1]))
 n.setdefault('name',options[0]['name'] if options else 'Transport landing')
 n['zone']=options[0]['id'] if options else None
 if n.get('towerApproach'):n['zone']=1420
for e in edges:
 if e['kind']!='flight':
  kind='skycutter' if e.get('route') in (11398,11457) else e['kind']
  e['name']=e.get('name') or ('Take the '+kind+' to '+nodes[e['b']-1]['name'])
source={'revision':'660e14a81724560abba1d619d9e791b72b136f86','project':'https://github.com/cjber/shortest-path-forever','license':'GPL-3.0-or-later',
 'files':{str(p.relative_to(up)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [up/'Data/Routes.lua',up/'Data/Portals.lua',up/'Data/Taxi.lua']},
 'tram':'Public thresholds from AreaTrigger; 150-second estimate includes an average wait and ride.'}
report={'nodes':nodes,'transports':edges,'walks':{},'provenance':source}
checkpoint=h/'multimodal-costs.json'
previous=checkpoint if checkpoint.exists() else h/'transit-costs.json'
if previous.exists():
 old=json.loads(previous.read_text())
 def location(n):return tuple(n.get(k) for k in ('id','key','map','x','y','z','faction'))
 unchanged={str(n['id']) for a,n in zip(old['nodes'],nodes) if location(a)==location(n)}
 report['walks']={key:{a:{b:v for b,v in row.items() if b in unchanged}
                      for a,row in rows.items() if a in unchanged} for key,rows in old['walks'].items()}
l.execute(b'A.Path.cacheKB=65536;A.Path.graphKB=131072')
fn=l.eval(b'function(map,from,targets,profile,style) return A.Path.FindManySync(map,from,targets,{profile=profile,style=style}) end')
start=time.perf_counter()
for profile in ['Horde','Alliance']:
 for style in ['balanced','roads']:
  key=profile+':'+style;rows=report['walks'].setdefault(key,{})
  for a in nodes:
   row=rows.setdefault(str(a['id']),{})
   targets=[b for b in nodes if b['map']==a['map'] and b!=a and str(b['id']) not in row
            and a.get('faction',profile)==profile and b.get('faction',profile)==profile]
   if not targets:continue
   lua_points=l.table_from([l.table_from({k.encode():b[k] for k in ['x','y','z'] if k in b}) for b in targets])
   st=time.perf_counter();costs,reason,expanded,yards=fn(a['map'],l.table_from({k.encode():a[k] for k in ['x','y','z'] if k in a}),lua_points,profile.encode(),style.encode())
   row.update({str(b['id']):costs[i] for i,b in enumerate(targets,1)})
   checkpoint.write_text(json.dumps(report,indent=2)+'\n')
   print(key,a['key'],sum(isinstance(c,(int,float)) and not isinstance(c,bool) for c in rows[str(a['id'])].values()),'reachable;',round(time.perf_counter()-st,2),'s',expanded,'expansions',flush=True)
def lua(v):
 if v is None:return 'nil'
 if isinstance(v,bool):return str(v).lower()
 if isinstance(v,(int,float)):return repr(v)
 if isinstance(v,str):return json.dumps(v,ensure_ascii=False)
 if isinstance(v,list):return '{'+','.join(lua(x) for x in v)+'}'
 return '{'+','.join('['+lua(k)+']='+lua(x) for k,x in v.items())+'}'
out={'nodes':nodes,'edges':edges,'walks':{key:{int(a):{int(b):cost for b,cost in row.items()} for a,row in rows.items()} for key,rows in report['walks'].items()}}
(root/'TransitData.lua').write_text('-- Public transport data adapted from Shortest Path Forever (GPL-3.0-or-later).\n-- Walking arcs baked on ForeverRoads terrain; travel/wait estimates are not live timetables.\nlocal _,A=...\nA.TransitData='+lua(out)+'\n')
(root/'Terrain/TRANSIT-PROVENANCE.json').write_text(json.dumps(source,indent=2)+'\n')
license_lines=(up/'Data/Taxi.lua').read_text().split('-- MIT License\n',1)[1].split('\n\n-- stylua',1)[0].splitlines()
(root/'Terrain/INFLIGHT-LICENSE.txt').write_text('MIT License\n'+'\n'.join(line[2:].lstrip() for line in license_lines)+'\n')
print('Baked',len(nodes),'landings,',len(edges),'transport arcs in',round(time.perf_counter()-start,1),'s',flush=True)
