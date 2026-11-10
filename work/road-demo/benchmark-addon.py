from pathlib import Path
import runpy,json,sys
here=Path(__file__).resolve().parent
code=(here/'test-addon.py').read_text()
if len(sys.argv)>2:
 code=code.replace("addon=root/'outputs/ForeverRoads'",'addon=Path('+repr(str(Path(sys.argv[2]).resolve()))+')')
 code=code[:code.index("test('unchanged routes")] + code[code.index("test('all Lua modules"):]

ns={'__file__':str(here/'test-addon.py')};exec(compile(code,str(here/'test-addon.py'),'exec'),ns);lua=ns['lua']
lua.execute(r'''
currentZone=1442;worldMapID=1442;px=.596;py=.526;clock=1000;combat=false
A.db.enabled=true;A.db.showMap=true;A.db.showMinimap=true;A.db.showArrow=true;A.db.showRoads=false
A.Command("way stonetalon 46.2 58.5 Sun Rock Retreat")
A.window:Hide();WorldMapFrame:Show();A.Tick()
local methods=getmetatable(A.window).__index
calls={}
for _,name in ipairs({"SetStartPoint","SetEndPoint","SetColorTexture","SetDrawLayer","SetThickness","SetFrameLevel","SetText","Show","Hide","CreateLine"}) do
 local original=methods[name]
 methods[name]=function(self,...) calls[name]=(calls[name] or 0)+1; return original(self,...) end
end
function bench(moving,mapOpen)
 WorldMapFrame:SetShown(mapOpen);A.Tick();calls={}
 local revision=A.revision;local initialRoute=A.route;local t=os.clock()
 for i=1,500 do
  clock=clock+.15
  if moving and A.route and A.route.status=="ok" then
   local target=A.Router.LookAhead(initialRoute,i*1.05,0)
   local frame=A.network.frames[1442]
   if target then px=(target.wx-frame.wx)/frame.dx;py=(target.wy-frame.wy)/frame.dy end
  end
  A.Tick()
 end
 local result={cpuMS=(os.clock()-t)*1000,replans=A.revision-revision}
 for k,v in pairs(calls) do result[k]=v end
 return result
end
''')
results={}
for name,moving,mapopen in [('stationaryMapOpen',False,True),('walkingMapOpen',True,True),('stationaryMapClosed',False,False)]:
 r=lua.eval('bench')(moving,mapopen);results[name]={k:r[k] for k in r.keys()}
Path(sys.argv[1] if len(sys.argv)>1 else here/'perf-latest.json').write_text(json.dumps(results,indent=2)+'\n')
print(json.dumps(results,indent=2))
