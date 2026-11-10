"""Load the actual TOC in order, then exercise real world routing and UI using simulated client frames."""
from pathlib import Path
from lupa.lua51 import LuaRuntime
import ast,json,zlib,base64,time
h=Path(__file__).resolve().parent;root=h.parent/'world-addon'
version=next(line.removeprefix('## Version: ') for line in (root/'ForeverRoads.toc').read_text().splitlines() if line.startswith('## Version: '))
l=LuaRuntime(unpack_returned_tuples=True,encoding=None);g=l.globals()
g[b'pyclock']=lambda:time.perf_counter()*1000
g[b'pydecode']=base64.b64decode;g[b'pyinflate']=lambda s,m:zlib.decompress(s)
tree=ast.parse((h/'test-addon.py').read_text())
mock=next(n.value.args[0].value for n in tree.body if isinstance(n,ast.Expr) and isinstance(n.value,ast.Call) and n.value.args and isinstance(n.value.args[0],ast.Constant) and isinstance(n.value.args[0].value,str) and 'local methods={}' in n.value.args[0].value)
mock=mock.replace('function CreateFrame(_,name) local o=object(); if name then _G[name]=o end; return o end',
'''frames={};function CreateFrame(_,name,parent) local o=object();o.events={};o.parent=parent;frames[#frames+1]=o;if name then _G[name]=o end;return o end
function methods:RegisterEvent(name) self.events[name]=true end
function methods:UnregisterEvent(name) self.events[name]=nil end
function fire(name,...)
 for _,f in ipairs(frames) do if f.events[name] and f.scripts.OnEvent then f.scripts.OnEvent(f,name,...) end end
end''')
l.execute(mock.encode())
l.execute(b'''
A={};Enum={CompressionMethod={Zlib=0}};C_EncodingUtil={DecodeBase64=pydecode,DecompressString=pyinflate};debugprofilestop=pyclock
now=0;timers={};combat=false;currentZone=1442;px=.638;py=.559;pz=nil;messages={};ticks=0
function GetTime() return now end;function time() return 1794100000+now end
function GetFramerate() return mockFPS or 60 end
function InCombatLockdown() return combat end
function hooksecurefunc(name,callback) assert(name=="TakeTaxiNode");taxiSelectionHook=callback end
function TakeTaxiNode(slot) if taxiSelectionHook then taxiSelectionHook(slot) end end
function UnitFactionGroup() return faction or "Horde" end
function CreateVector2D(x,y) return {GetXY=function() return x,y end} end
function UnitPosition() local w=A.Router.World(A.Data,currentZone,px*1002,py*668);return -w.wy,-w.wx,pz,w.continent end
function geterrorhandler() return function(err) error(err) end end
function GetPlayerFacing() return facing or 0 end
C_Timer={After=function(delay,fn) timers[#timers+1]={at=now+delay,fn=fn} end,
 NewTicker=function(delay,fn) ticker=fn;return {Cancel=function() ticker=nil end} end}
function frame()
 now=now+1/60
 local old=timers;timers={};for _,t in ipairs(old) do if t.at<=now then t.fn() else timers[#timers+1]=t end end
 ticks=ticks+1;if ticks%12==0 and ticker then ticker() end
end
C_Map={GetBestMapForUnit=function() return currentZone end,GetPlayerMapPosition=function() if not readable then return nil end;return CreateVector2D(px,py) end,
GetWorldPosFromMapPos=function(zone,p) local x,y=p:GetXY();local w=A.Router.World(A.Data,zone,x*1002,y*668);return w.continent,CreateVector2D(-w.wy,-w.wx) end,
GetUserWaypoint=function() return userPin end}
C_QuestLog={GetTitleForQuestID=function() return "Test quest" end,IsComplete=function() return false end,GetNextWaypoint=function() return questZone,questX,questY end,
GetQuestsOnMap=function() return {} end}
C_SuperTrack={GetSuperTrackedQuestID=function() return questID or 0 end}
readable=true;SlashCmdList={};DEFAULT_CHAT_FRAME={AddMessage=function(_,s) messages[#messages+1]=s end}
''')
toc=[s.strip() for s in (root/'ForeverRoads.toc').read_text().splitlines() if s.strip() and not s.startswith('#')]
assert len(toc)==len(set(toc)),'Duplicate TOC modules'
assert set(toc)=={str(p.relative_to(root)) for p in root.rglob('*.lua')},'Unloaded or missing module'
start=time.perf_counter()
for name in toc:
 l.execute(b'local f=function(...)\n'+(root/name).read_bytes()+b'\nend;f("ForeverRoads",A)')
load_ms=(time.perf_counter()-start)*1000
l.execute(b'''
userPin={uiMapID=1442,position=CreateVector2D(.638,.559)}
fire("PLAYER_ENTERING_WORLD");for i=1,14 do frame() end
assert(A.ready and A.liveFrames==55 and A.window and not ForeverRoadsArrow)
assert(A.db.goal and A.db.goal.source=="pin","An existing pin should load on startup with no saved destination")
userPin=nil;fire("USER_WAYPOINT_UPDATED");frame()
assert(not A.db.goal and not A.pathJob)
''')
passed=[]
def test(name,code):l.execute(code.encode());passed.append(name)
def pump():
 n=0;peak=0
 while l.eval(b'A.pathJob~=nil'):
  st=time.perf_counter();l.eval(b'frame')();peak=max(peak,(time.perf_counter()-st)*1000);n+=1
  assert n<20000,'Search did not settle'
 return n,peak
test('missing terrain chunks are detected before navigation starts', '''
assert(A.CheckTerrain())
local p=ForeverRoadsTerrainData[0].packed.graph;local key,blocks=next(p);p[key]=nil
local ok,map=A.CheckTerrain();assert(not ok and map==0);p[key]=blocks;assert(A.CheckTerrain())
''')
test('manifest loads all modules once; UI exposes all 55 maps', '''
local n=0;for _ in pairs(A.window.zoneButtons) do n=n+1 end;assert(n==55)
assert(A.window.zoneScroll.child:GetHeight()>210)
A.window:Show();assert(A.window:IsShown());A.window:Hide()
''')
test('Stonetalon command starts an asynchronous search', '''A.Command("way Stonetalon Mountains 46.2 58.5 Sun Rock Retreat");assert(A.pathJob and not A.route)''')
n,peak=pump()
test('both maps render the real terrain path and the world map shows ETA and steps', '''
assert(A.perf.phases["Itinerary elapsed"].count>0)
worldMapID=1442
function WorldMapFrame:GetPinFrameLevelsManager() return {GetValidFrameLevel=function(_,kind) return kind=="PIN_FRAME_LEVEL_MAP_EXPLORATION" and 2030 or 2040 end} end
A.Draw();assert(A.route.status=="ok" and A.mapLineCount>0 and A.minimapLineCount>0 and A.mapLayerLevel>2030)
local guide=A.mapGuide
assert(guide.parent==WorldMapFrame.ScrollContainer and guide:GetFrameLevel()>A.mapLayerLevel and guide:IsShown())
assert(guide.steps.value:match("^|T.*StepRun%.tga:14:14|t Run to Sun Rock Retreat$"))
local cost,progress=A.route.weightedCost,A.progress
A.route.weightedCost=243*A.Transit.walkSpeed;A.progress=0;A.Draw()
assert(guide.eta.value=="~4m 3s")
A.progress=A.route.distance/2;A.Draw();assert(guide.eta.value=="~2m 2s")
A.route.weightedCost=cost;A.progress=progress
WorldMapFrame:Hide();assert(not guide:IsShown())
WorldMapFrame:Show();A.Draw();assert(guide:IsShown())
A.db.showMap=false;A.Draw();assert(not guide:IsShown() and A.minimapLineCount>0)
A.db.showMap=true;A.Draw();assert(guide:IsShown())
local maps=A.perf.mapRedraws;local minis=A.perf.minimapRedraws
local builds=A.perf.smoothingBuilds
for i=1,120 do frame() end
assert(A.perf.mapRedraws==maps and A.perf.minimapRedraws==minis)
assert(A.perf.smoothingBuilds==builds)
px=px+.001;A.Tick();assert(A.perf.smoothingBuilds==builds and A.perf.minimapRedraws>minis)
minis=A.perf.minimapRedraws;facing=1;A.DrawMinimap();assert(A.perf.minimapRedraws==minis)
local rotate=GetCVarBool;GetCVarBool=function() return true end
A.DrawMinimap();assert(A.perf.minimapRedraws>minis and A.perf.smoothingBuilds==builds)
minis=A.perf.minimapRedraws;facing=1.2;A.DrawMinimap();assert(A.perf.minimapRedraws>minis and A.perf.smoothingBuilds==builds)
GetCVarBool=rotate;facing=0;A.DrawMinimap()
''')
test('new destination cancels old search; pause cancels; resume restarts', '''
A.Command("way stonetalon 66.5 34.6 Old");local old=A.pathJob
A.Command("way stonetalon 46.2 58.5 Latest");assert(old.cancelled and A.pathJob~=old)
old=A.pathJob;A.Command("pause");assert(old.cancelled and not A.pathJob and not A.mapGuide:IsShown())
A.Command("resume");assert(A.pathJob)
''');pump()
test('combat defers new jobs and suspends a running search', '''
combat=true;A.Command("way stonetalon 46.7 24.2 Combat");assert(not A.pathJob and A.pendingRoute)
combat=false;fire("PLAYER_REGEN_ENABLED");for i=1,16 do frame() end;assert(A.pathJob)
combat=true;frame();assert(A.pathJob and not A.pathJob.done)
combat=false;fire("PLAYER_REGEN_ENABLED")
''');pump()
test('unreadable position cancels search and recovers when coordinates return', '''
A.Command("way stonetalon 46.2 58.5 Readable");readable=false;A.Tick();assert(not A.player and not A.route and not A.pathJob)
readable=true;A.Tick();assert(A.pathJob)
''');pump()
test('bounded performance log, adaptive frame budget and no same-continent restart', '''
A.Command("perf")
local found=false
for _,message in ipairs(messages) do if message:find("Terrain search:") then found=true end end
assert(found)
A.Command("perf start")
A.Command("way stonetalon 46.7 24.2 Profile")
local job=A.pathJob
assert(job and A.Path.frameBudget()==2.5)
mockFPS=28;now=now+.6;assert(A.Path.frameBudget()==1)
mockFPS=nil;now=now+.6;assert(A.Path.frameBudget()==2.5)
fire("ZONE_CHANGED_NEW_AREA");fire("PLAYER_ENTERING_WORLD")
for i=1,16 do frame() end
local requests=0
for _,entry in ipairs(A.tracePerf.entries) do
    if entry:find("Route requested",1,true) then requests=requests+1 end
end
assert(requests==1,"Entering a new area restarted route planning")
for i=1,64 do A.TracePerf("test",tostring(i)) end
A.Command("perf stop")
local trace=A.db.performanceTrace
assert(not A.tracePerf and #trace.entries==48 and trace.entries[#trace.entries]:find("stopped"))
local phase=trace.summary["Terrain search"]
assert(phase.count>0 and phase.peak>0)
local count=phase.count;frame();assert(phase.count==count)
A.Command("perf log");assert(messages[#messages]:find("samples"))
''');pump()
audit=json.loads((h/'world-coverage-audit.json').read_text());catalog={z['id']:z for z in json.loads((h/'all-zone-catalog.json').read_text())['maps']}
routes=[]
for z in audit['maps']:
 a,b=z['checkedPair'];bounds=catalog[z['id']]['bounds']
 def ui(p):return (bounds[3]-p['y'])/(bounds[3]-bounds[1]),(bounds[2]-p['x'])/(bounds[2]-bounds[0])
 x,y=ui(a);tx,ty=ui(b)
 l.execute(('currentZone=%d;worldMapID=%d;px=%.12f;py=%.12f;pz=%s;A.lastZone=nil;A.Command("way %d %.9f %.9f Coverage")'%(z['id'],z['id'],x,y,a['z'],z['id'],tx*100,ty*100)).encode())
 frames,p=pump();peak=max(peak,p)
 l.execute(b'A.Draw();assert(A.route and A.route.status=="ok" and A.mapLineCount>0, "No route drawn on map "..currentZone);A.window.zoneButtons[currentZone].scripts.OnClick();A.RefreshSettings(true)')
 routes.append({'id':z['id'],'name':z['name'],'frames':frames,'mapLines':l.eval(b'A.mapLineCount')})
passed.append('real package routes and renders within all 55 zone maps')
test('vertical progress distinguishes floors; cross-continent distance is infinite', '''
local route={segments={{from={wx=0,wy=0,z=0},to={wx=0,wy=0,z=100},kind="lift",length=100,begin=0,finish=100}},distance=100}
assert(math.abs(A.Router.Progress(route,{wx=0,wy=0,z=50},0).progress-50)<.001)
assert(A.Router.Distance({wx=0,wy=0,continent=0},{wx=0,wy=0,continent=1})==math.huge)
''')
result={'version':version,'loadMS':load_ms,'passed':len(passed),'suites':passed,'maps':routes,'firstSearchFrames':n,'peakSimulatedFrameMS':peak,'searchPeakMS':l.eval(b'A.perf.phases["Terrain search"].peak'),'tickerPeakMS':l.eval(b'A.perf.phases.Update.peak'),'liveGameVerified':False}
(h/'world-package-tests.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
