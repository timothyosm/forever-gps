from pathlib import Path
p=Path(__file__).with_name('test-addon.py');s=p.read_text()
s=s.replace('return 0,CreateVector2D(-w.wy,-w.wx)','return w.continent,CreateVector2D(-w.wy,-w.wx)')
s=s.replace("live map coordinate calibration matches all three stored zone frames","live map coordinate calibration matches all four stored zone frames")
s=s.replace('A.liveFrames==3','A.liveFrames==4').replace('GetStatus().liveFrames==3','GetStatus().liveFrames==4')
s=s.replace('currentZone=1442; A.Tick(); assert(not A.route','currentZone=1440; A.Tick(); assert(not A.route')
s=s.replace('function WorldMapFrame:GetMapID() return 1420 end','worldMapID=1420; function WorldMapFrame:GetMapID() return worldMapID end')
point=s.index("test('walking progress")
s=s[:point]+'''test('242 Stonetalon routes match Dijkstra, including both road preferences',r\'\'\'
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
\'\'\')
test('current Windshear locations route to all 11 Stonetalon destinations; estimated spurs are explicit',r\'\'\'
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
\'\'\')
''' +s[point:]
point=s.index("test('arrival detection")
s=s[:point]+'''test('Stonetalon live-position simulation, tracked quests, and cross-continent combat deferral',r\'\'\'
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
\'\'\')
''' +s[point:]
point=s.index("test('all Lua modules")
s=s[:point]+'''test('Stonetalon settings, quick destinations, command aliases and both map overlays',r\'\'\'
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
\'\'\')
test('world-map routes and road networks never bleed across continents, even with overlapping coordinates',r\'\'\'
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
\'\'\')
''' +s[point:]
s=s.replace("'referenceRoutes':722,", "'referenceRoutes':722,'stonetalonOptimalityComparisons':286,'supportedMaps':[1420,1421,1424,1442],")
p.write_text(s)
