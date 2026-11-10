from pathlib import Path
import runpy,json,sys
beads='--beads' in sys.argv
h=Path(__file__).resolve().parent;e=runpy.run_path(str(h/'test-world-package.py'));l=e['l'];root=e['root']
l.execute(b'currentZone=1442;worldMapID=1442;px=.638;py=.559;pz=nil;A.Command("way stonetalon 46.7 24.2 Peak")')
e['pump']();l.execute(b'assert(A.route.status=="ok")')
l.execute(b'''
local methods=getmetatable(A.window).__index
for _,name in ipairs({"SetStartPoint","SetEndPoint","SetThickness","SetColorTexture","SetDrawLayer","Show","Hide","CreateLine",
                      "CreateTexture","SetPoint","ClearAllPoints","SetTexture","SetSize"}) do
 local original=methods[name]
 methods[name]=function(self,...) calls[name]=(calls[name] or 0)+1;return original(self,...) end
end
function rendererBench(moving)
 local first=A.route.segments[1].from
 A.player={zone=1442,continent=1,wx=first.wx,wy=first.wy};A.progress=0
 A.DrawMap();A.DrawMinimap();calls={}
 local builds=A.perf.smoothingBuilds;local start=os.clock()
 for i=1,500 do
  if moving then
   local progress=math.min(i*1.4,A.route.distance-30)
   local target=A.Router.LookAhead(A.route,progress,0)
   if target then A.player.wx=target.wx;A.player.wy=target.wy;A.progress=progress end
  end
  A.DrawMap();A.DrawMinimap()
 end
 local r={cpuMS=(os.clock()-start)*1000,smoothingRebuilds=(A.perf.smoothingBuilds or 0)-(builds or 0),mapLines=A.mapLineCount,minimapLines=A.minimapLineCount}
 for k,v in pairs(calls) do r[k]=v end
 return r
end
''')
baseline='bead-baseline' if beads else 'smoothing-baseline'
result={'version':'2.0.2' if beads else '2.0.1','method':'Actual Stonetalon terrain route; Lua 5.1 simulated frame APIs. 500 warm renderer updates, identical 7 yd/s positions. Timings exclude real rendering and are not FPS.','originalSegments':l.eval(b'#A.route.segments')}
for name,p in [('before',h/baseline/'Map.lua'),('after',(root if beads else h/'bead-baseline')/'Map.lua')]:
 l.execute(b'calls={};local f=function(...)\n'+p.read_bytes()+b'\nend;f("ForeverRoads",A);A.perf={}')
 # First paint is measured separately; per-update results use warm line pools.
 first=l.eval(b'function() local p=A.route.segments[1].from;A.player={zone=1442,continent=1,wx=p.wx,wy=p.wy};A.progress=0;collectgarbage("collect");local start=os.clock();A.DrawMap();A.DrawMinimap();return (os.clock()-start)*1000 end')()
 row={'firstPaintMS':first}
 for key,moving in [('stationary',False),('walking',True)]:
  value=l.globals()[b'rendererBench'](moving);row[key]={k.decode():v for k,v in value.items()}
 result[name]=row
assert result['after']['stationary']['smoothingRebuilds']==0
assert result['after']['walking']['smoothingRebuilds']==0
assert not any(result['after']['stationary'].get(k) for k in ['SetStartPoint','SetPoint','SetTexture'])
if beads:assert result['after']['walking'].get('CreateTexture',0)<=20
(h/('route-beads-performance.json' if beads else 'route-smoothing-performance.json')).write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
