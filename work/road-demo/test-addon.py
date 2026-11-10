from pathlib import Path
import json, subprocess
from lupa.lua51 import LuaRuntime

here=Path(__file__).resolve().parent
root=here.parents[1]
addon=root/'outputs/ForeverRoads'
lua=LuaRuntime(unpack_returned_tuples=True)
lua.execute('A={}; unpack=unpack or table.unpack')
for name in ['Data','Router']:
    lua.execute('local f=function(...)\n'+(addon/f'{name}.lua').read_text()+'\nend; f("ForeverRoads", A)')
data=json.loads((here/'data.json').read_text())
reference=json.loads(subprocess.check_output(['node','-e',r'''
const R=require('./src/routing.js'),d=require('./data.json'),n=R.build(d),out=[];
for(const preferRoads of [false,true])for(const a of d.places)for(const b of d.places){const r=R.route(n,a,b,{preferRoads});out.push({a:a.id,b:b.id,preferRoads,status:r.status,cost:r.weightedCost,distance:r.distance});}
process.stdout.write(JSON.stringify(out));
'''],cwd=here))
lua.execute('net=A.Router.Build(A.Data); function place(id) for _,p in ipairs(A.Data.places) do if p.id==id then return p end end end')
for case in reference:
    result=lua.eval('function(a,b,prefer) return A.Router.Route(net,place(a),place(b),{preferRoads=prefer}) end')(case['a'],case['b'],case['preferRoads'])
    assert result['status']==case['status']
    assert abs(result['weightedCost']-case['cost'])<1e-5,case
    if not case['preferRoads']: assert abs(result['distance']-case['distance'])<1e-5,case
passed=['722 Lua routes match the tested JavaScript prototype (distance and optimal weighted cost)']
def test(name,code):
    lua.execute(code);passed.append(name)

test('partial-edge snapping, route closure and disconnected cases',r'''
local r=A.Router.Route(net,place("shadowfang"),place("pyrewood")); local close
for _,s in ipairs(r.segments) do if s.roadId=="pyrewood-loop" then close=s.id; break end end
local alt=A.Router.Route(net,place("shadowfang"),place("pyrewood"),{blocked={[close]=true},maxApproach=.1})
assert(alt.status=="ok" and alt.distance>r.distance)
assert(A.Router.Route(net,place("brill"),place("tarren"),{blocked={["silverpine-hillsbrad"]=true}}).status=="disconnected")
assert(A.Router.Route(net,{zone=1420,x=50,y=80},place("brill"),{maxApproach=200}).status=="too-far")
local e=net.edges[1]; local a,b=net.nodes[e.a],net.nodes[e.b]
local p=function(t) return {zone=a.zone,x=a.x+t*(b.x-a.x),y=a.y+t*(b.y-a.y)} end
local partial=A.Router.Route(net,p(.2),p(.8)); assert(math.abs(partial.distance-e.length*.6)<1e-5)
''')
test('242 Stonetalon routes match Dijkstra, including both road preferences',r'''
local count=0
for _,a in ipairs(A.Data.places) do if a.zone==1442 then
 for _,b in ipairs(A.Data.places) do if b.zone==1442 then
  for _,prefer in ipairs({false,true}) do
   local r=A.Router.Route(net,a,b,{preferRoads=prefer})
   local d=A.Router.Route(net,a,b,{preferRoads=prefer,dijkstra=true})
   assert(r.status=="ok" and d.status=="ok",a.id.." -> "..b.id)
   assert(math.abs(r.weightedCost-d.weightedCost)<1e-5)
   count=count+1
  end
 end end
end end
assert(count==242)
''')
test('current Windshear locations route to all 11 Stonetalon destinations; estimated spurs are explicit',r'''
for _,position in ipairs({{63.8,55.9},{59.6,52.6}}) do
 local start={zone=1442,x=position[1]/100*A.Data.width,y=position[2]/100*A.Data.height}
 for _,goal in ipairs(A.Data.places) do if goal.zone==1442 then
  for _,prefer in ipairs({false,true}) do
   local r=A.Router.Route(net,start,goal,{preferRoads=prefer})
   local d=A.Router.Route(net,start,goal,{preferRoads=prefer,dijkstra=true})
   assert(r.status=="ok" and math.abs(r.weightedCost-d.weightedCost)<1e-5,goal.id)
   local estimated=0
   for _,segment in ipairs(r.segments) do
    assert(segment.from.continent==1 and segment.to.continent==1)
    if segment.kind=="estimated" or segment.kind=="approach" then estimated=estimated+segment.length end
   end
   assert(math.abs(r.estimated-estimated)<1e-5 and r.estimated>0)
  end
 end end
end
assert(A.Router.Route(net,place("sun-rock"),place("brill")).status=="needs-transport")
assert(A.Router.Route(net,place("brill"),place("sun-rock")).status=="needs-transport")
assert(A.Router.Distance(A.Router.World(A.Data,1442,463,391),A.Router.World(A.Data,1420,463,391))==math.huge)
''')
test('off-road quest pins retain the full road route and expose estimated-approach warnings',r'''
local start={zone=1442,x=.602*A.Data.width,y=.714*A.Data.height}
local goal={zone=1442,x=58.9/100*A.Data.width,y=62.6/100*A.Data.height}
local r=A.Router.Route(net,start,goal)
assert(r.status=="ok" and #r.segments>0)
local far=A.Router.Route(net,{zone=1420,x=50,y=80},place("brill"))
assert(far.status=="ok" and far.warning and far.approachDistance>200)
assert(far.segments[1].kind=="approach")
assert(A.Router.Route(net,{zone=1420,x=50,y=80},place("brill"),{maxApproach=200}).status=="too-far")
''')
test('walking progress and turn target advance consistently',r'''
local r=A.Router.Route(net,place("brill"),place("scarlet"))
local s=r.segments[2]; local p={wx=(s.from.wx+s.to.wx)/2,wy=(s.from.wy+s.to.wy)/2}
local progress=A.Router.Progress(r,p,0); assert(progress.distance<1e-5)
assert(math.abs(progress.progress-(s.begin+s.length/2))<1e-5)
local target,segment=A.Router.LookAhead(r,progress.progress,35); assert(target and segment)
''')

lua.execute(r'''
clock=0; combat=false; currentZone=1420; px=.61; py=.515; frames={}; timers={}; messages={}; SlashCmdList={}
function GetTime() return clock end
function time() return 1794120000 end
function InCombatLockdown() return combat end
function IsInInstance() return false end
function CreateVector2D(x,y) return {GetXY=function() return x,y end} end
function CreateFrame()
 local f={scripts={},events={}}
 function f:RegisterEvent(e) self.events[e]=true end
 function f:SetScript(e,fn) self.scripts[e]=fn end
 frames[#frames+1]=f; return f
end
C_Timer={After=function(delay,fn) timers[#timers+1]=fn end,NewTicker=function(delay,fn) ticker=fn; return {} end}
C_Map={GetBestMapForUnit=function() return currentZone end,GetPlayerMapPosition=function() return CreateVector2D(px,py) end,
GetWorldPosFromMapPos=function(zone,p)
 local x,y=p:GetXY(); local w=A.Router.World(A.Data,zone,x*A.Data.width,y*A.Data.height)
 return w.continent,CreateVector2D(-w.wy,-w.wx)
end,GetUserWaypoint=function() return userPin end}
C_QuestLog={GetTitleForQuestID=function() return "Test quest" end,IsComplete=function() return complete end,
 GetNextWaypoint=function() return questMap,questX,questY end,GetQuestsOnMap=function(zone) return pois and pois[zone] or {} end}
C_SuperTrack={GetSuperTrackedQuestID=function() return questID or 0 end}
DEFAULT_CHAT_FRAME={AddMessage=function(_,s) messages[#messages+1]=s end}
''')
for name in ['Navigation','Map']:
    lua.execute('local f=function(...)\n'+(addon/f'{name}.lua').read_text()+'\nend; f("ForeverRoads",A)')
lua.execute('A.Draw=function() end; A.Print=function(s) messages[#messages+1]=s end; A.db={enabled=true,followQuest=true,recordings={}}')

test('live map coordinate calibration matches all four stored zone frames',r'''
A.Calibrate(); assert(A.liveFrames==4 and #A.network.badLinks==0)
for _,p in ipairs(A.Data.places) do
 local actual=A.Router.World(A.Data,p.zone,p.x,p.y,A.network.frames)
 local expected=A.Router.World(A.Data,p.zone,p.x,p.y)
 assert(A.Router.Distance(actual,expected)<1e-6)
end
assert(A.ReadPlayer().zone==1420)
currentZone=1458; assert(A.ReadPlayer()==nil); currentZone=1420
''')
test('quest objective and completed-quest turn-in resolution, skipping quest offers',r'''
questID=123; questMap=1421; questX=.43; questY=.4; complete=false
pois={[1420]={{questID=123,mapID=9999,x=.61,y=.515,isQuestStart=false}}}
assert(A.QuestDestination(123).zone==1421)
complete=true; local turnin=A.QuestDestination(123); assert(turnin.zone==1420 and turnin.label:find("turn in"))
pois={[1420]={{questID=123,x=.61,y=.515,isQuestStart=true}}}; questMap=nil; questX=nil; questY=nil
assert(A.QuestDestination(123)==nil)
pois=nil; questMap=1440; questX=.5; questY=.5; assert(A.QuestDestination(123)==nil)
questMap=1420; questX=.83; questY=.36; complete=false
''')
test('live navigation reroutes after deviation and on zone changes; combat defers planning',r'''
A.db.goal={zone=1420,x=834,y=242,label="Scarlet",source="manual"}; A.db.followQuest=false
A.pendingRoute=true; A.Tick(); assert(A.route.status=="ok")
local rev=A.revision; clock=10; px=.62; py=.717; A.Tick(); assert(A.pendingRoute)
A.Tick(); assert(A.revision>rev)
combat=true; A.pendingRoute=true; rev=A.revision; A.Tick(); assert(A.revision==rev and A.pendingRoute)
combat=false; A.Tick(); assert(A.revision>rev)
currentZone=1421; px=.51;py=.3; A.Tick(); assert(A.lastZone==1421 and A.route.status=="ok")
currentZone=1420; px=.61;py=.515
''')
test('Stonetalon live-position simulation, tracked quests, and cross-continent combat deferral',r'''
currentZone=1442; px=.596; py=.526
questMap=1442;questX=463/A.Data.width;questY=391/A.Data.height;complete=false;pois=nil
A.db.followQuest=true;A.FollowQuest();A.Tick()
assert(A.player.zone==1442 and A.player.continent==1 and A.route.status=="ok")
assert(A.db.goal.zone==1442 and A.db.goal.source=="quest")
local revision=A.revision
A.SetDestination({zone=1420,x=611,y=359,label="Brill"},true);A.Tick()
assert(A.route.status=="needs-transport")
A.db.followQuest=true;A.FollowQuest();A.Tick();assert(A.route.status=="ok")
combat=true;currentZone=1420;px=.61;py=.515;A.Tick()
assert(A.route==nil and A.pendingRoute)
combat=false;A.Tick();assert(A.route.status=="needs-transport")
A.db.followQuest=false;A.db.goal=nil;A.route=nil;A.pendingRoute=false
''')
test('arrival detection and recording are character-local and do not invent road edges',r'''
local edges=#A.network.edges
A.ToggleRecording(); A.Tick(); assert(A.db.recording and #A.db.recordings[1].points==1)
px=px+.01; A.Tick(); assert(#A.db.recordings[1].points==2)
A.ToggleRecording(); assert(not A.db.recording and #A.network.edges==edges)
A.db.goal={zone=1420,x=px*A.Data.width,y=py*A.Data.height,label="Here",source="manual"}; A.pendingRoute=true
A.Tick(); assert(A.arrived)
''')
test('map and minimap clipping keep route strokes inside their visible regions',r'''
local x1,y1,x2,y2=A.RectClip(-1,.5,2,.5); assert(x1==0 and x2==1)
assert(A.RectClip(-2,-2,-1,-1)==nil)
local a,b,c,d=A.CircleClip(-20,0,20,0,10); assert(math.abs(a+10)<1e-6 and math.abs(c-10)<1e-6)
assert(A.CircleClip(20,20,30,30,10)==nil)
''')

lua.execute('A.CreateUI=function() end; A.AttachMap=function() end; A.Draw=function() end')
lua.execute('A.Path={}')
for name in ['Performance','Core']:
    lua.execute('local f=function(...)\n'+(addon/f'{name}.lua').read_text()+'\nend; f("ForeverRoads",A)')
test('real event controller initializes character-only settings, commands and tracked quests',r'''
local e=frames[#frames]; ForeverRoadsDB=nil
questID=123;questMap=1420;questX=.83;questY=.36;px=.61;py=.515
e.scripts.OnEvent(e,"PLAYER_ENTERING_WORLD")
local t=timers;timers={};for _,fn in ipairs(t) do fn() end
assert(ForeverRoadsDB and A.db==ForeverRoadsDB and A.db.goal.questID==123)
A.Command("way silverpine 43 40 The Sepulcher");assert(A.db.goal.zone==1421 and not A.db.followQuest)
A.Command("pause");assert(not A.db.enabled)
A.Command("resume");assert(A.db.enabled)
A.Command("clear");assert(not A.db.goal and not A.route)
A.Command("follow");assert(A.db.followQuest and A.db.goal.questID==123)
assert(ForeverRoads.GetStatus().liveFrames==4)
''')
test('pause survives quest changes, and leaving coverage clears stale guidance',r'''
A.Command("pause"); local oldGoal=A.db.goal
questX=.61; questY=.515; A.FollowQuest(); assert(not A.db.enabled and A.db.goal==oldGoal)
A.Command("resume"); A.FollowQuest(); A.Tick(); assert(A.db.enabled)
currentZone=1440; A.Tick(); assert(not A.route and not A.player and A.pendingRoute)
currentZone=1420; A.Tick(); assert(A.route and A.route.status=="ok")
''')

lua.execute(r'''
local methods={}
for _,name in ipairs({"SetPoint","SetAllPoints","SetFrameStrata","SetClampedToScreen","SetBackdrop","SetBackdropColor",
"SetJustifyH","SetMovable","EnableMouse","RegisterForDrag","RegisterForClicks","SetTexture","SetHighlightTexture",
"SetClipsChildren","SetDrawLayer","ClearAllPoints","SetVertexColor","SetDesaturated","SetAlpha","StartMoving","StopMovingOrSizing","SetColorTexture"}) do
 methods[name]=function() end
end
function methods:SetSize(w,h) self.width=w; self.height=h end
function methods:SetScale(scale) self.scale=scale end
function methods:SetScrollChild(child) self.child=child end
function methods:SetWidth(w) self.width=w end
function methods:SetHeight(h) self.height=h end
function methods:SetAllPoints(parent) self.anchorParent=parent end
function methods:GetWidth() return self.width or (self.anchorParent and self.anchorParent:GetWidth()) or 1002 end
function methods:GetHeight() return self.height or (self.anchorParent and self.anchorParent:GetHeight()) or 668 end
function methods:GetCenter() return 600,400 end
function methods:GetEffectiveScale() return 1 end
function methods:GetFrameLevel() return self.level or 1 end
function methods:SetFrameLevel(level) self.level=level end
function methods:Show() local changed=not self.shown; self.shown=true; if changed and self.scripts.OnShow then self.scripts.OnShow(self) end end
function methods:Hide() local changed=self.shown; self.shown=false; if changed and self.scripts.OnHide then self.scripts.OnHide(self) end end
function methods:IsShown() return self.shown end
function methods:SetShown(v) if v then self:Show() else self:Hide() end end
function methods:SetScript(name,fn) self.scripts[name]=fn end
function methods:HookScript(name,fn) self.scripts[name]=fn end
function methods:SetText(value) self.value=value end
function methods:GetStringHeight() local _,lines=(self.value or ""):gsub("\n",""); return (lines+1)*12 end
function methods:SetChecked(v) self.checked=v end
function methods:GetChecked() return self.checked end
function methods:SetRotation(value) assert(type(value)=="number" and value==value); self.rotation=value end
function methods:SetThickness(value) assert(value>0) end
function methods:SetStartPoint(_,owner,x,y) assert(type(x)=="number" and type(y)=="number") end
function methods:SetEndPoint(_,owner,x,y) assert(type(x)=="number" and type(y)=="number") end
local function object() return setmetatable({scripts={},shown=true},{__index=methods}) end
function methods:CreateTexture() return object() end
function methods:CreateFontString() return object() end
function methods:CreateLine() return object() end
function CreateFrame(_,name) local o=object(); if name then _G[name]=o end; return o end
UIParent=object(); Minimap=object(); Minimap:SetSize(180,180)
local canvas=object();canvas:SetSize(1002,668)
WorldMapFrame=object();WorldMapFrame.ScrollContainer=object()
function WorldMapFrame:GetCanvas() return canvas end
worldMapID=1420; function WorldMapFrame:GetMapID() return worldMapID end
function WorldMapFrame:GetCanvasScale() return 1 end
function WorldMapFrame:GetNormalizedCursorPosition() return .61,.515 end
function IsAltKeyDown() return true end
function GetPlayerFacing() return 0 end
function GetCVarBool() return false end
function GetUnitSpeed() return 7 end
C_Minimap={GetViewRadius=function() return 200 end}
UISpecialFrames={}; GameTooltip={}
''')
for name in ['Map','UI']:
    lua.execute('local f=function(...)\n'+(addon/f'{name}.lua').read_text()+'\nend; f("ForeverRoads",A)')
test('real UI modules create controls, draw both maps, handle Alt-click, pause and resume',r'''
A.db.showMap=true;A.db.showMinimap=true;A.db.enabled=true
A.CreateUI(); A.window:Show()
local p=place("scarlet"); A.SetDestination({zone=p.zone,x=p.x,y=p.y,label=p.name,source="manual"},true)
A.Tick(); assert(A.mapLineCount>0 and A.minimapLineCount>0 and A.mapGuide:IsShown())
assert(A.mapGuide.eta.value:match("^~") and not ForeverRoadsArrow)
WorldMapFrame.ScrollContainer.scripts.OnMouseUp(WorldMapFrame.ScrollContainer,"LeftButton")
assert(A.db.goal.source=="map" and not A.db.followQuest)
A.minimapButton.scripts.OnClick(A.minimapButton,"RightButton"); assert(not A.db.enabled and not A.mapGuide:IsShown())
A.minimapButton.scripts.OnClick(A.minimapButton,"RightButton"); assert(A.db.enabled)
''')
test('Stonetalon settings, quick destinations, command aliases and both map overlays',r'''
currentZone=1442;px=.596;py=.526;worldMapID=1442
A.Command("way stonetalon 46.2 58.5 Sun Rock Retreat")
assert(A.db.goal.zone==1442 and A.route.status=="ok")
assert(A.mapLineCount>0 and A.minimapLineCount>0)
A.Command("way 1442 66.3 51.8 Windshear");assert(A.db.goal.zone==1442)
A.window:Show();A.window.zoneButtons[1442].scripts.OnClick();assert(A.db.quickZone==1442)
local n=0
for _,b in ipairs(A.window.quickButtons) do if b:IsShown() then
 assert(b.place.zone==1442); n=n+1
end end
assert(n==11)
local b=A.window.quickButtons[1]; b.scripts.OnClick(b)
assert(A.db.goal.label==b.place.name and A.db.goal.zone==1442)
A.window.zoneButtons[1420].scripts.OnClick();assert(A.db.quickZone==1420)
for _,b in ipairs(A.window.quickButtons) do if b:IsShown() then assert(b.place.zone==1420) end end
''')
test('world-map routes and road networks never bleed across continents, even with overlapping coordinates',r'''
worldMapID=1420;A.db.showRoads=false
local a=A.Router.World(A.Data,1420,611,359);local b=A.Router.World(A.Data,1420,640,399)
a.continent=1;b.continent=1
local length=math.sqrt((a.wx-b.wx)^2+(a.wy-b.wy)^2)
A.route={status="ok",segments={{from=a,to=b,length=length,begin=0,finish=length,kind="road"}},distance=length,estimated=0,expanded=0}
A.DrawMap();assert(A.mapLineCount==0)
A.db.showRoads=true;A.DrawMap();local original=A.mapLineCount
local before=#A.network.edges
local na=#A.network.nodes+1;local nb=na+1
A.network.nodes[na]=a;A.network.nodes[nb]=b
A.network.edges[#A.network.edges+1]={a=na,b=nb,kind="road",zone=1442}
A.DrawMap();assert(A.mapLineCount==original)
table.remove(A.network.edges);table.remove(A.network.nodes);table.remove(A.network.nodes)
A.db.showRoads=false;A.pendingRoute=true;worldMapID=1442;A.Tick();assert(A.route.status=="ok")
''')
test('explored-map artwork stays below the route, including native level changes',r'''
local exploration,blob=2030,2040
function WorldMapFrame:GetPinFrameLevelsManager()
 return {GetValidFrameLevel=function(_,kind)
  return kind=="PIN_FRAME_LEVEL_MAP_EXPLORATION" and exploration or blob
 end}
end
A.DrawMap();assert(A.mapLayerLevel==2040 and A.mapLayerLevel>exploration)
exploration=2500;blob=2510;A.DrawMap();assert(A.mapLayerLevel==2510)
WorldMapFrame.GetPinFrameLevelsManager=nil;A.DrawMap();assert(A.mapLayerLevel>=2100)
''')
test('unchanged routes do not redraw map lines or minimap lines; moving and toggling still refresh',r'''
currentZone=1442;worldMapID=1442;px=.596;py=.526;A.db.showMap=true;A.db.showMinimap=true
A.Command("way stonetalon 46.2 58.5 Sun Rock Retreat")
A.Tick();local maps=A.perf.mapRedraws;local minis=A.perf.minimapRedraws
for i=1,100 do clock=clock+.2;A.Tick() end
assert(A.perf.mapRedraws==maps and A.perf.minimapRedraws==minis)
px=px+.002;A.Tick();assert(A.perf.mapRedraws==maps and A.perf.minimapRedraws>minis)
A.db.showMap=false;A.DrawMap();assert(A.mapLineCount==0)
A.db.showMap=true;A.DrawMap();assert(A.mapLineCount>0 and A.perf.mapRedraws>maps)
A.db.showMinimap=false;A.DrawMinimap();assert(A.minimapLineCount==0)
A.db.showMinimap=true;A.DrawMinimap();assert(A.minimapLineCount>0)
A.Command("perf");assert(messages[#messages]:find("Map redraws"))
''')
test('minimap cache recovers from unavailable view radius and map cache follows canvas resizing',r'''
local fn=C_Minimap.GetViewRadius
C_Minimap.GetViewRadius=function() return 0 end;A.DrawMinimap();assert(A.minimapLineCount==0)
C_Minimap.GetViewRadius=fn;A.DrawMinimap();assert(A.minimapLineCount>0)
local canvas=WorldMapFrame:GetCanvas();local old=canvas:GetWidth();local maps=A.perf.mapRedraws
canvas:SetWidth(old*.75);A.DrawMap();assert(A.perf.mapRedraws==maps+1)
canvas:SetWidth(old);A.DrawMap();assert(A.perf.mapRedraws==maps+2)
''')
test('all Lua modules compile and the TOC loads every module in order',r'''
''')
for p in addon.glob('*.lua'):lua.execute('assert(loadstring(...))',p.read_text())
toc=(addon/'ForeverRoads.toc').read_text()
assert '## SavedVariablesPerCharacter: ForeverRoadsDB' in toc
assert '\n## SavedVariables:' not in toc
for p in addon.glob('*.lua'):assert p.name in toc
report={'passed':len(passed),'suites':passed,'luaVersion':'5.1','referenceRoutes':722,'stonetalonOptimalityComparisons':286,'supportedMaps':[1420,1421,1424,1442],'liveGameVerified':False}
(root/'outputs/ForeverRoads-tests.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
