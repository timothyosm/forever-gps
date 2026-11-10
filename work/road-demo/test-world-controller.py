from pathlib import Path
import runpy,json,time
h=Path(__file__).resolve().parent;env=runpy.run_path(str(h/'test-world-engine.py'));l=env['lua'];root=h.parent/'world-addon'
for name in ['Data.lua','Router.lua','WorldData.lua','WorldPlaces.lua','TransitData.lua','Transit.lua']:l.execute(b'local f=function(...)\n'+(root/name).read_bytes()+b'\nend;f("ForeverRoads",A)')
l.execute(b'''
now=100;currentZone=1442;px=.638;py=.559;draws=0;messages={}
function GetTime() return now end
function UnitFactionGroup() return "Horde" end
function UnitPosition() return nil end
function IsInInstance() return false end
function CreateVector2D(x,y) return {GetXY=function() return x,y end} end
C_Map={GetBestMapForUnit=function() return currentZone end,GetPlayerMapPosition=function() return CreateVector2D(px,py) end,
GetWorldPosFromMapPos=function(map,p)
 local x,y=p:GetXY();local w=A.Router.World(A.Data,map,x*A.Data.width,y*A.Data.height)
 return w.continent,CreateVector2D(-w.wy,-w.wx)
end}
C_QuestLog={GetTitleForQuestID=function() return "Test quest" end,IsComplete=function() return false end,
GetNextWaypoint=function() return currentZone,.462,.585 end,GetQuestsOnMap=function() return {} end}
C_SuperTrack={GetSuperTrackedQuestID=function() return 123 end}
A.Draw=function() draws=draws+1 end;A.Print=function(s) messages[#messages+1]=s end
A.db={enabled=true,followQuest=false,recordings={}}
''')
for name in ['Navigation.lua','WorldNavigation.lua']:l.execute(b'local f=function(...)\n'+(root/name).read_bytes()+b'\nend;f("ForeverRoads",A)')
l.execute(b'''
A.Calibrate();assert(A.liveFrames==55)
for _,z in ipairs(A.WorldCatalog.maps) do assert(A.Supported(z.id)) end
A.SetDestination({zone=1442,x=.462*A.Data.width,y=.585*A.Data.height,label="Sun Rock"},true);A.Tick()
assert(A.pathJob and not A.pendingRoute and A.route==nil)
''')
def pump():
 n=0;peak=0
 while len(l.globals()[b'queue']):
  st=time.perf_counter();l.eval(b'step')();peak=max(peak,(time.perf_counter()-st)*1000);n+=1
  assert n<10000
 return n,peak
n,peak=pump();l.execute(b'assert(A.route.status=="ok" and A.route.terrain and A.route.distance>0 and not A.pathJob)')
l.execute(b'''
A.SetDestination({zone=1442,x=.665*A.Data.width,y=.346*A.Data.height,label="Old goal"},true);A.Tick();local old=A.pathJob
A.SetDestination({zone=1442,x=.467*A.Data.width,y=.242*A.Data.height,label="Latest goal"},true);A.Tick()
assert(old.cancelled and A.pathJob~=old)
''');pump();l.execute(b'assert(A.route.status=="ok" and A.db.goal.label=="Latest goal")')
l.execute(b'''
A.SetDestination({zone=1442,x=.462*A.Data.width,y=.585*A.Data.height,label="Paused goal"},true);A.Tick()
local job=A.pathJob;A.db.enabled=false;A.Tick();assert(job.cancelled and not A.pathJob)
A.db.enabled=true;combat=true;A.pendingRoute=true;A.Tick();assert(A.pendingRoute and not A.pathJob)
combat=false;A.Tick();assert(A.pathJob)
''');pump();l.execute(b'assert(A.route.status=="ok")')
result={'supportedMaps':55,'terrainPlanCompletes':True,'latestDestinationWins':True,'pauseCancelsSearch':True,'combatDefersSearch':True,'firstRouteFrames':n,'peakPumpMS':peak,'liveGameVerified':False}
(h/'world-controller-tests.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
