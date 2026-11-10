from pathlib import Path
import runpy,json,time
h=Path(__file__).resolve().parent;e=runpy.run_path(str(h/'test-world-package.py'));l=e['l'];pump=e['pump'];root=e['root']
catalog={z['id']:z for z in json.loads((h/'all-zone-catalog.json').read_text())['maps']}
def ui(zone,p):
 a,b,c,d=catalog[zone]['bounds'];return (d-p['y'])/(d-b),(c-p['x'])/(c-a)
def position(zone,p):
 x,y=ui(zone,p);l.execute(('currentZone=%d;worldMapID=%d;px=%.12f;py=%.12f;pz=%s;readable=true'%(zone,zone,x,y,p.get('z','nil'))).encode())
def destination(zone,p):
 x,y=ui(zone,p);l.execute(('A.SetDestination({zone=%d,x=%.12f*1002,y=%.12f*668,z=%s,label="Travel check"},true);A.Tick()'%(zone,x,y,p.get('z','nil'))).encode())
def py(p):return {k.decode() if isinstance(k,bytes) else k:v for k,v in p.items()}
checks=[]
for a,b in [('sepulcher','brill'),('brill','sepulcher')]:
 pa=l.eval(('function() for _,p in ipairs(A.Data.places) do if p.id=="'+a+'" then return p end end end').encode())()
 pb=l.eval(('function() for _,p in ipairs(A.Data.places) do if p.id=="'+b+'" then return p end end end').encode())()
 l.execute(('currentZone=%d;worldMapID=%d;px=%.12f;py=%.12f;pz=nil;A.SetDestination({zone=%d,x=%.12f,y=%.12f,label="Cross-zone"},true);A.Tick()'%(pa[b'zone'],pa[b'zone'],pa[b'x']/1002,pa[b'y']/668,pb[b'zone'],pb[b'x'],pb[b'y'])).encode())
 n,peak=pump();l.execute(b'assert(A.route.status=="ok" and not A.journey)')
 checks.append({'case':a+' -> '+b,'frames':n,'distance':l.eval(b'A.route.distance'),'peakMS':peak})
# Explicit faction filter test: this route's zeppelin is Horde-only.
l.execute(b'''
local T=A.Transit;local nodes=A.TransitData.nodes
local h=T.Resolve(nodes[3],nodes[4],{3},{0},{4},{0},"Horde","balanced")
local a=T.Resolve(nodes[3],nodes[4],{3},{0},{4},{0},"Alliance","balanced")
local function has(j,route) if not j then return false end;for _,leg in ipairs(j.legs) do if leg.transport and leg.transport.route==route then return true end end;return false end
assert(has(h,285));assert(not has(a,285))
''')
checks.append({'case':'Horde-only zeppelin excluded for Alliance','passed':True})
# Real Ratchet -> Booty Bay terrain access, transport wait, loading-screen position gap and arrival.
nodes=json.loads((h/'transit-costs.json').read_text())['nodes'];a,b=nodes[0],nodes[1]
position(a['zone'],a);destination(b['zone'],b);n,peak=pump()
l.execute(b'assert(A.journey and (A.route.status=="ok" or A.route.status=="transport"),A.status)')
l.execute(b'assert(A.mapGuide:IsShown() and A.mapGuide.eta.value:match("^~") and A.mapGuide.steps.value:find("Booty Bay",1,true))')
l.execute(b'local zone=worldMapID;worldMapID=947;A.DrawMap();assert(A.mapLineCount>0,"Boat crossing missing on Azeroth");worldMapID=zone;A.DrawMap()')
l.execute(b'''
local p=A.player;local goal=A.db.goal;local t=A.Router.World(A.Data,goal.zone,goal.x,goal.y,A.network.frames)
local opts={profile="Horde",style="balanced"}
local graph=A.Transit.Graph(opts.profile,opts.style)
local sPoints,sIDs=A.Transit.Nodes(p.continent,graph);local tPoints,tIDs=A.Transit.Nodes(t.continent,graph,true)
local sc=A.Path.FindManySync(p.continent,{x=-p.wy,y=-p.wx,z=p.z},sPoints,opts)
local tc=A.Path.FindManySync(t.continent,{x=-t.wy,y=-t.wx,z=goal.z},tPoints,opts,true)
local exhaustive=A.Transit.Resolve({map=p.continent,x=-p.wy,y=-p.wx,z=p.z},{map=t.continent,x=-t.wy,y=-t.wx,z=goal.z},sIDs,sc,tIDs,tc,"Horde","balanced")
assert(exhaustive and math.abs(exhaustive.seconds-A.journey.seconds)<.00001)
local seconds=A.Transit.Resolve({map=p.continent,x=-p.wy,y=-p.wx,z=p.z},{map=t.continent,x=-t.wy,y=-t.wx,z=goal.z},
    sIDs,sc,tIDs,tc,"Horde","balanced",graph,true)
assert(seconds==exhaustive.seconds)
''')
checks.append({'case':'early-stopped transport choice matches exhaustive settled costs','passed':True})
transports=[];legs=0
while l.eval(b'A.journey~=nil and not A.arrived'):
 legs+=1;assert legs<20
 leg=l.eval(b'A.journey.legs[A.journey.index]');to=py(leg[b'to'])
 if leg[b'kind']!=b'walk':
  transports.append(leg[b'name'].decode())
  l.execute(b'readable=false;A.Tick();assert(A.journey and not A.player and A.mapGuide:IsShown() and A.mapGuide.eta.value:match("^~"));readable=true')
 zone=to.get('zone') or b['zone'];position(zone,to);l.execute(b'A.Tick()');pump()
l.execute(b'assert(A.arrived and A.db.goal.zone==1434 and A.mapGuide.steps.value=="Destination reached" and A.mapGuide.eta.value=="")')
checks.append({'case':'Ratchet -> Booty Bay, automatic leg progression through simulated loading screen','searchFrames':n,'transports':transports,'legs':legs,'peakMS':peak})
audit=json.loads((h/'world-coverage-audit.json').read_text())
shore=next(z for z in audit['maps'] if z['id']==1434)['checkedPair'][0]
position(a['zone'],a);destination(1434,shore);pump()
l.execute(b'''
assert(A.journey and A.journey.legs[#A.journey.legs].kind=="walk",A.status)
worldMapID=1434;A.DrawMap();assert(A.walkPreviewJob and A.mapLineCount>0)
WorldMapFrame:Hide();assert(not A.walkPreviewJob)
WorldMapFrame:Show();A.DrawMap();blueBeforePreview=A.mapLineCount
assert(A.walkPreviewJob and A.mapGuide.steps.value:find("Run to Travel check",1,true))
''')
for _ in range(20000):
 if not l.eval(b'A.walkPreviewJob~=nil'): break
 l.eval(b'frame')()
l.execute(b'''
local j=A.journey;local final=j.legs[#j.legs]
assert(j.index<#j.legs and final.preview and #final.preview.segments>0)
assert(A.mapLineCount>blueBeforePreview,"Walking trail missing before boat arrival")
local marked=false
for _,frame in ipairs(frames) do
 if frame.badge and frame:IsShown() then
  for _,icon in ipairs(frame.badge.icons) do
   if icon:IsShown() and icon.frTexture:match("StepRun%.tga$") then marked=true end
  end
 end
end
assert(marked,"The final run needs a boot icon at the destination")
A.Clear();assert(not A.walkPreviewJob)
''')
checks.append({'case':'Destination map shows the exact gold trail before the boat arrives','passed':True})

position(a['zone'],a);destination(1434,shore);pump()
l.execute(b'''
A.StopWalkPreview();WorldMapFrame:Hide()
A.Tick();A.Tick()
assert(A.crossing and A.crossing.leg.kind=="boat" and not A.crossing.departed)
assert(A.walkPreviewJob and A.walkPreviewJob.crossing)
readable=false;A.Tick()
assert(A.crossing and A.walkPreviewJob,"A loading gap should keep the dock preview")
''')
for _ in range(20000):
    if not l.eval(b'A.walkPreviewJob~=nil'): break
    l.eval(b'frame')()
l.execute(b'''
WorldMapFrame:Show();worldMapID=1434;A.DrawMap()
assert(A.mapGuide.eta.value:find("after docking",1,true))
assert(A.journey.legs[A.journey.index+1].preview and A.mapLineCount>0)
''')
second_shore=next(z for z in audit['maps'] if z['id']==1434)['checkedPair'][1]
destination(1434,second_shore)
l.execute(b'''
assert(A.crossing.onward and A.pathJob and not A.player)
assert(math.abs(A.lastPlanPosition.wx+A.crossing.leg.to.y)<.01)
''')
pump()
l.execute(b'assert(A.route.status=="ok" and A.mapGuide.steps.value:find("Run to Travel check",1,true))')
position(b['zone'],b)
l.execute(b'''
local onward=A.route
A.Tick()
assert(not A.crossing and A.route==onward and not A.pathJob)
assert(not A.mapGuide.eta.value:find("after docking",1,true))
A.Clear()
''')
checks.append({'case':'Boat prepares its exit walk with the map closed and reroutes from the dock during a loading gap','passed':True})

# No guessed walking lines between an outdoor continent and an instanced battleground.
position(1413,a)
bg=next(z for z in audit['maps'] if z['id']==1460)['checkedPair'][0]
destination(1460,bg);pump()
l.execute(b'assert(A.route.status=="needs-transport" and not A.journey and not A.pathJob)')
checks.append({'case':'Battleground entry requires the game queue; no fabricated crossing','passed':True})
# The Darnassus portal joins disconnected terrain on the same world map.
f=nodes[25];t=nodes[26]
position(f['zone'],f);destination(t['zone'],t);n,peak=pump()
l.execute(b'assert(A.journey and (A.route.status=="ok" or A.route.status=="transport"),A.status)')
portal=False
for i in range(10):
 if l.eval(b'A.arrived'):break
 leg=l.eval(b'A.journey.legs[A.journey.index]');portal|=leg[b'kind']==b'portal';to=py(leg[b'to'])
 zone=to.get('zone') or t['zone'];position(zone,to);l.execute(b'A.Tick()');pump()
assert portal;l.execute(b'assert(A.arrived)')
checks.append({'case':'Darnassus -> Ruttheran portal on the same continent','passed':True,'frames':n,'peakMS':peak})
expanded=json.loads((h/'multimodal-costs.json').read_text())
flights={p['taxi']:p for p in expanded['nodes'] if 'taxi' in p}
l.execute(b'''
function GetTaxiMapID() return taxiMap end
function UnitOnTaxi() return onTaxi end
C_TaxiMap={GetAllTaxiNodes=function() return taxiNodes end}
function showFlights(nodes)
    taxiMap=1414;taxiNodes=nodes;fire("TAXIMAP_OPENED");frame()
end
function rideKinds()
    local kinds={}
    for _,leg in ipairs(A.journey and A.journey.legs or {}) do
        if leg.kind~="walk" then kinds[#kinds+1]=leg.kind end
    end
    return table.concat(kinds,",")
end
A.Clear()
showFlights({{nodeID=29,state=0},{nodeID=23,state=1},{nodeID=25,state=2},{nodeID=6,state=1},{nodeID=99999,state=1}})
assert(A.db.knownFlights[29] and A.db.knownFlights[23])
assert(not A.db.knownFlights[25] and not A.db.knownFlights[6] and not A.db.knownFlights[99999])
local known=A.db.knownFlights;A.db.knownFlights={}
local g=A.Transit.Graph("Horde","balanced")
for _,node in ipairs(A.TransitData.nodes) do if node.taxi then assert(not g.board[node.id] and not g.arrival[node.id]) end end
A.db.knownFlights=known
assert(A.db==ForeverRoadsDB)
''')
assert '## SavedVariablesPerCharacter: ForeverRoadsDB' in (root/'ForeverRoads.toc').read_text()
checks.append({'case':'flight map imports current and reachable nodes only, for this character and faction','passed':True})
sunrock,crossroads,orgrimmar=flights[29],flights[25],flights[23]
position(sunrock['zone'],sunrock);destination(orgrimmar['zone'],orgrimmar);n,peak=pump()
l.execute(b'assert(A.route.status=="ok" and not A.journey,A.status)')
checks.append({'case':'known endpoints cannot use an unlearned connecting flight master','searchFrames':n,'peakMS':peak})
l.execute(b'showFlights({{nodeID=29,state=0,slotIndex=1},{nodeID=25,state=1,slotIndex=5},{nodeID=23,state=1,slotIndex=7}})')
destination(crossroads['zone'],crossroads)
assert l.eval(b'A.pathJobs~=nil'), 'A ride between nearby stops should be checked before the full walk'
n,peak=pump()
l.execute(b'''
assert(rideKinds()=="flight",A.status)
local itinerary=A.journey
TakeTaxiNode(5);onTaxi=true;A.Tick()
assert(A.journey==itinerary and not A.taxi.onward and itinerary.legs[itinerary.index].kind=="flight")
''')
# Passing directly over a destination while still on a taxi must not advance the leg.
position(crossroads['zone'],crossroads);l.execute(b'A.Tick();assert(A.route.status=="transport" and A.journey.legs[A.journey.index].kind=="flight")')
l.execute(b'onTaxi=false;A.Tick()');pump();l.execute(b'A.Tick();assert(A.arrived)')
checks.append({'case':'known Sun Rock Retreat flight beats walking and waits for actual landing',
               'searchFrames':n,'peakMS':peak})

for direct_landing in (True,False):
    position(sunrock['zone'],sunrock);destination(orgrimmar['zone'],orgrimmar);pump()
    l.execute(b'''
    assert(rideKinds()=="flight,flight",A.status..": "..rideKinds())
    A.Tick();flightJourney=A.journey
    assert(flightJourney.legs[flightJourney.index].kind=="flight")
    local display=A.Transit.DisplayLegs(flightJourney)
    local first,last=flightJourney.index,A.Transit.FlightEnd(flightJourney.legs,flightJourney.index)
    assert(last==first+1 and display[1].from==flightJourney.legs[first].from and display[1].to==flightJourney.legs[last].to)
    assert(display[1].seconds==flightJourney.legs[first].seconds+flightJourney.legs[last].seconds)
    local steps=A.mapGuide.steps.value
    assert(steps:find("Catch flight to Orgrimmar",1,true) and not steps:find("Crossroads",1,true))
    local count=#messages
    A.Command("status")
    for i=count+1,#messages do assert(not messages[i]:find("Crossroads",1,true)) end
    onTaxi=true;A.Tick()
    assert(A.status:find("In flight to Orgrimmar",1,true))
    ''')
    if not direct_landing:
        position(crossroads['zone'],crossroads)
        l.execute(b'''
        onTaxi=false;A.Tick()
        assert(A.journey==flightJourney and A.status:find("Fly to Orgrimmar",1,true))
        assert(not A.mapGuide.steps.value:find("Crossroads",1,true))
        onTaxi=true;A.Tick()
        ''')
    position(orgrimmar['zone'],orgrimmar)
    l.execute(b'onTaxi=false;A.Tick();assert(A.journey==flightJourney and flightJourney.legs[flightJourney.index].kind=="walk")')
    pump();l.execute(b'A.Tick();assert(A.arrived)')
checks.append({'case':'Connecting flights show one destination and advance on intermediate or final landing','passed':True})

l.execute(b'A.Clear();faction="Horde"')
position(crossroads['zone'],crossroads)
l.execute(b'''
showFlights({{nodeID=25,state=0,slotIndex=1},{nodeID=29,state=1,slotIndex=5},{nodeID=23,state=2,slotIndex=7}})
assert(taxiSelectionHook)
TakeTaxiNode(5);A.Tick();assert(not A.wasOnTaxi,"A selection alone is not a takeoff")
onTaxi=true;A.Tick();assert(A.wasOnTaxi and A.taxi.to.taxi==29 and not A.db.goal)
now=now+20
questID=481;questZone=1442;questX=.462;questY=.585;worldMapID=1442
A.Command("follow")
local job=A.pathJob
assert(job and not A.player and A.taxi.onward and A.lastPlanPosition.continent==A.taxi.to.map)
A.Tick();assert(A.pathJob==job and not job.cancelled)
assert(A.mapGuide.steps.value:find("Planning route from landing",1,true))
flightOnlyDots=A.mapLineCount
''')
pump()
l.execute(b'''
assert(A.wasOnTaxi and A.route.status=="ok" and not A.player)
assert(A.mapGuide.eta.value:find("after landing",1,true) and A.mapGuide.steps.value:find("In flight to Sun Rock Retreat",1,true))
assert(A.mapGuide.steps.value:find("Run to Test quest",1,true))
assert(A.mapLineCount>flightOnlyDots and A.minimapLineCount==0)
local first=A.route.segments[1].from
assert(math.abs(first.wx+A.taxi.to.y)<.01 and math.abs(first.wy+A.taxi.to.x)<.01)
local old=A.route
questX=.467;questY=.242;A.FollowQuest();A.Tick()
assert(A.pathJob and A.route~=old and A.taxi.goal==A.db.goal)
''')
pump()
position(sunrock['zone'],sunrock)
l.execute(b'''
local planned=A.route
onTaxi=false;readable=false;A.Tick()
assert(A.route==planned and A.wasOnTaxi)
readable=true;A.Tick()
assert(A.route==planned and not A.pathJob and not A.taxi and A.player)
assert(not A.mapGuide.eta.value:find("after landing",1,true))
''')
checks.append({'case':'Actual selected taxi landing supports quest planning and retargeting in flight','passed':True})

position(crossroads['zone'],crossroads)
l.execute(b'''
showFlights({{nodeID=25,state=0,slotIndex=1},{nodeID=29,state=1,slotIndex=5}})
TakeTaxiNode(5);onTaxi=true;A.Tick();assert(A.taxi.onward)
''')
pump()
position(sunrock['zone'],sunrock)
l.execute(b'''
local predicted=A.lastPlanPosition
px=.462;py=.585;pz=nil;onTaxi=false;A.Tick()
assert(A.pathJob and A.lastPlanPosition~=predicted and A.lastPlanPosition.x==.462*A.Data.width)
A.Clear();questID=nil;questZone=nil;questX=nil;questY=nil
''')
checks.append({'case':'A different actual landing replans from the readable player position','passed':True})

l.execute(b'A.Clear();A.db.knownFlights[29]=nil')
position(sunrock['zone'],sunrock);destination(crossroads['zone'],crossroads);n,peak=pump()
l.execute(b'assert(A.route.status=="ok" and not A.journey,A.status)')
checks.append({'case':'same trip walks when departure has not been learned','searchFrames':n,'peakMS':peak})

l.execute(b'''
A.Clear()
showFlights({{nodeID=29,state=0},{nodeID=23,state=1},{nodeID=25,state=1}})
currentZone=1442;worldMapID=1442;px=.462;py=.585;pz=nil
''')
destination(crossroads['zone'],crossroads)
l.execute(b'''
assert(A.pathJob and not A.pathJobs,"Start outside the nearby-ride shortcut")
local compared,frames=false,0
while A.pathJob do
    if not A.journey then
        A.Draw()
        assert(not A.route and A.mapLineCount==0 and A.minimapLineCount==0,"A provisional walk leaked onto a map")
        assert(A.mapGuide.eta.value=="" and A.mapGuide.steps.value:find("Planning",1,true),
            "Show planning status until the itinerary is ready")
        compared=compared or A.pathJobs~=nil
    end
    frame();frames=frames+1;assert(frames<20000)
end
A.Draw()
assert(compared and rideKinds():find("flight"),A.status)
assert(A.mapGuide.eta.value:match("^~") and A.mapGuide.steps.value:find("Catch flight",1,true))
''')
checks.append({'case':'First published itinerary includes the flight after a full walking comparison','passed':True})

l.execute(b'''
A.Clear()
showFlights({{nodeID=29,state=0},{nodeID=23,state=1},{nodeID=25,state=1}})
showFlights({{nodeID=11,state=0},{nodeID=10,state=1},{nodeID=13,state=2}})
assert(A.db.knownFlights[10] and A.db.knownFlights[11] and A.db.knownFlights[29] and not A.db.knownFlights[13])
''')
sepulcher=flights[10]
position(sunrock['zone'],sunrock);destination(sepulcher['zone'],sepulcher);n,peak=pump()
l.execute(b'''
assert(A.journey and rideKinds():find("flight") and rideKinds():find("zeppelin"),A.status..": "..rideKinds())
local crossing
for _,leg in ipairs(A.journey.legs) do
    if leg.kind=="zeppelin" then crossing=leg;break end
end
assert(crossing.transport.route==302 and crossing.to.towerApproach)
''')
checks.append({'case':'Stonetalon to Silverpine combines known flights with the Orgrimmar–Tirisfal zeppelin',
               'rides':l.eval(b'rideKinds()').decode(),'searchFrames':n,'peakMS':peak})
zeppelin_departure=py(l.eval(b'''
    function()
        for _,leg in ipairs(A.journey.legs) do if leg.kind=="zeppelin" then return leg.from end end
    end
''')())

position(sepulcher['zone'],sepulcher);destination(sunrock['zone'],sunrock);n,peak=pump()
l.execute(b'''
assert(rideKinds():find("flight") and rideKinds():find("zeppelin"),A.status..": "..rideKinds())
for _,leg in ipairs(A.journey.legs) do
    if leg.kind=="zeppelin" then assert(leg.transport.route==302 and leg.from.towerApproach) end
end
''')
checks.append({'case':'Silverpine to Stonetalon routes to the Tirisfal tower for the reverse crossing',
               'rides':l.eval(b'rideKinds()').decode(),'searchFrames':n,'peakMS':peak})

l.execute(b'A.Clear();A.db.knownFlights={}')
position(zeppelin_departure['zone'],zeppelin_departure)
destination(sepulcher['zone'],sepulcher);pump()
l.execute(b'''
A.Tick();A.Tick()
assert(A.crossing and A.crossing.leg.kind=="zeppelin")
function GetUnitSpeed() return 0 end
for i=1,2 do now=now+.2;px=px+.003;A.Tick() end
assert(A.crossing.departed)
''')
tirisfal=next(z for z in audit['maps'] if z['id']==1420)['checkedPair'][0]
destination(1420,tirisfal)
l.execute(b'''
assert(A.crossing.onward and A.pathJob and not A.player)
assert(A.lastPlanPosition.continent==A.crossing.leg.to.map)
''')
pump()
l.execute(b'''
worldMapID=1420;A.DrawMap()
assert(A.route.status=="ok" and A.mapGuide.eta.value:find("after docking",1,true))
assert(A.mapGuide.steps.value:find("On board to",1,true) and A.mapLineCount>0)
A.Clear();GetUnitSpeed=nil
''')
checks.append({'case':'Zeppelin preserves the exit tower as the planning origin when the goal changes on board','passed':True})

l.execute(b'A.Clear();faction="Alliance"')
tram_start,tram_end=expanded['nodes'][29:31]
position(tram_start['zone'],tram_start);destination(tram_end['zone'],tram_end);n,peak=pump()
l.execute(b'assert(rideKinds()=="tram",A.status);A.Tick();assert(A.route.status=="transport");readable=false;A.Tick();assert(A.journey);readable=true')
position(tram_end['zone'],tram_end);l.execute(b'A.Tick()');pump();l.execute(b'A.Tick();assert(A.arrived)')
checks.append({'case':'Deeprun Tram is an Alliance ride between its outdoor entrances','searchFrames':n,'peakMS':peak})

l.execute(b'''
A.Clear();faction="Horde";A.db.knownFlights={}
currentZone=1442;px=.411;py=.706;pz=nil;worldMapID=1411
fire("USER_WAYPOINT_UPDATED")
userPin={uiMapID=1411,position={x=.536,y=.522}}
fire("USER_WAYPOINT_UPDATED");frame()
assert(A.pathJob and A.db.goal.source=="pin" and A.db.goal.zone==1411)
local job=A.pathJob
fire("USER_WAYPOINT_UPDATED");frame()
assert(A.pathJob==job and not job.cancelled,"Duplicate waypoint events restarted the route")
''')
n,peak=pump()
l.execute(b'''
assert(A.route.status=="ok" and not A.journey and A.mapLineCount>0 and A.minimapLineCount>0)
assert(A.mapGuide.steps.value:find("Run to Map pin",1,true))
local last=A.route.segments[#A.route.segments].to
local target=A.Router.World(A.Data,1411,.536*A.Data.width,.522*A.Data.height,A.network.frames)
assert(A.Router.Distance(last,target)<.01)
''')
checks.append({'case':'Native pin from screenshot draws a walking route from Stonetalon to Durotar',
               'searchFrames':n,'peakMS':peak})

l.execute(b'''
A.Command("pause");local old=A.db.goal
userPin={uiMapID=1411,position=CreateVector2D(.541,.525)}
fire("USER_WAYPOINT_UPDATED");frame()
assert(not A.db.enabled and A.db.goal==old and not A.pathJob)
A.Command("resume")
assert(A.pathJob and A.db.goal.x==.541*A.Data.width)
userPin=nil;fire("USER_WAYPOINT_UPDATED");frame()
assert(not A.db.goal and not A.route and not A.pathJob)

userPin={uiMapID=1411,position=CreateVector2D(.536,.522)}
C_SuperTrack.IsSuperTrackingUserWaypoint=function() return true end
fire("SUPER_TRACKING_CHANGED");frame()
assert(A.db.goal.source=="pin" and A.pathJob)
A.Command("follow")
assert(A.db.followQuest and not A.db.goal and not A.pathJob)

-- Native map projection remains usable if the raw pin coordinates are unavailable.
userPin=nil
C_Map.HasUserWaypoint=function() return true end
C_Map.GetUserWaypointPositionForMap=function(zone)
    if zone==1411 then return CreateVector2D(.536,.522) end
end
A.Command("pin")
assert(A.db.goal.source=="pin" and A.db.goal.zone==1411 and A.pathJob)
A.Clear()
''')
checks.append({'case':'Pin selection, native projection, removal, pause and return to quest tracking','passed':True})

l.execute(b'''
userPin={uiMapID=1411,position=CreateVector2D(.541,.525)}
C_SuperTrack.IsSuperTrackingUserWaypoint=function() return false end
A.Command("pin");local pinGoal=A.db.goal
questID=456
worldMapID=1411
local markerReady=false
C_QuestLog.GetNextWaypointForMap=function(id,zone)
    if markerReady and id==questID and zone==1411 then return .536,.522 end
end
fire("QUEST_LOG_UPDATE");for i=1,16 do frame() end
assert(A.db.goal==pinGoal and not A.db.followQuest,"A quest log refresh must leave the pin selected")
fire("SUPER_TRACKING_CHANGED");frame()
assert(A.db.followQuest and not A.db.goal and A.status:find("Waiting",1,true))
markerReady=true
fire("QUEST_POI_UPDATE");for i=1,16 do frame() end
assert(A.db.goal and A.db.goal.source=="quest" and A.db.goal.questID==456 and A.db.goal.zone==1411)
''')
pump()
l.execute(b'''
assert(A.route.status=="ok" and A.mapLineCount>0 and A.minimapLineCount>0)
assert(A.mapGuide.steps.value:find("Run to Test quest",1,true))
local last=A.route.segments[#A.route.segments].to
local goal=A.Router.World(A.Data,1411,.536*A.Data.width,.522*A.Data.height,A.network.frames)
assert(A.Router.Distance(last,goal)<.01)

C_QuestLog.ReadyForTurnIn=function() return true end
C_QuestLog.GetQuestsOnMap=function(zone)
    if zone~=1411 then return {} end
    return {
        {questID=456,x=.5,y=.5,isQuestStart=true},
        {questID=456,x=.55,y=.55,isMapIndicatorQuest=true},
        {questID=456,x=.541,y=.525,isQuestStart=false},
    }
end
fire("QUEST_POI_UPDATE");for i=1,16 do frame() end
assert(A.db.goal.x==.541*A.Data.width and A.db.goal.label:find("turn in",1,true))
A.Clear()
''')
checks.append({'case':'Selecting a quest marker replaces a pin and follows delayed objective and turn-in coordinates','passed':True})

l.execute(b'''
A.Clear();faction="Horde";A.db.knownFlights={[29]=true,[25]=true,[23]=true,[10]=true,[11]=true}
local T=A.Transit
local graph=T.Graph("Horde","balanced")
assert(T.Graph("Horde","balanced")==graph and T.Graph("Horde","roads")~=graph)
assert(T.Graph("Alliance","balanced")~=graph)
local points,ids=T.Nodes(0,graph,true)
local again,againIDs=T.Nodes(0,graph,true)
assert(points==again and ids==againIDs and #ids>0)
A.db.knownFlights[13]=true
assert(T.Graph("Horde","balanced")~=graph)
A.db.knownFlights[13]=nil
''')
position(sunrock['zone'],sunrock)
destination(sepulcher['zone'],sepulcher);pump()
l.execute(b'''
local goal=A.db.goal
local hits=A.perf.caches.arrivalHits or 0
local reused=A.perf.caches.arrivalCosts or 0
px=px+.0006
A.SetDestination(goal,true);A.Tick()
assert(A.perf.caches.arrivalHits==hits+1 and A.perf.caches.arrivalCosts>reused)
''')
pump()
l.execute(b'''
assert(A.journey and rideKinds():find("zeppelin"))
local originCosts=A.perf.caches.originCosts or 0
A.SetDestination(A.db.goal,true);A.Tick()
assert(A.perf.caches.originCosts>originCosts)
''')
pump()
l.execute(b'''
assert(A.journey and rideKinds():find("zeppelin"))
local goal=A.db.goal
local hits=A.perf.caches.arrivalHits
local function request(z,roads)
    A.db.preferRoads=roads
    A.SetDestination({zone=goal.zone,x=goal.x,y=goal.y,z=z,label="Cache check"},true)
    A.Tick()
end
request(goal.z+.01,false);assert(A.perf.caches.arrivalHits==hits)
request(goal.z,true);assert(A.perf.caches.arrivalHits==hits)
A.db.knownFlights[13]=true
request(goal.z,false);assert(A.perf.caches.arrivalHits==hits)
A.db.knownFlights[13]=nil

-- Seed one confirmed result per destination without running 17 identical terrain searches.
-- A floor change isolates the records while exercising real cache lookup and cancellation.
for i=1,17 do
    request(goal.z+i,false)
    local job=A.pathJobs[#A.pathJobs]
    assert(job.reverse and not job.done)
    job.valid=true;job.costs[1]=100;job.yards[1]=100
    A.Clear()
end
request(goal.z+1,false);assert(A.perf.caches.arrivalHits==hits)
request(goal.z+17,false);assert(A.perf.caches.arrivalHits==hits+1)
A.Clear()
''')
checks.append({'case':'Arrival cache reuses exact settled costs, invalidates on route inputs and evicts the oldest destination','passed':True})

l.execute(b'A.Clear();faction="Alliance";A.db.knownFlights={};A.db.preferRoads=true')
position(tram_start['zone'],tram_start);destination(tram_end['zone'],tram_end)
l.execute(b'''
local source=A.pathJobs[1]
assert(source and not source.reverse)
local matched
for i,stop in ipairs(source.targets) do
    if math.abs(stop.x-source.from.x)<1e-6 and math.abs(stop.y-source.from.y)<1e-6 then
        -- Equivalent to the co-located cost published by FindMany.
        source.valid=true;source.costs[i]=0;source.yards[i]=0;matched=true
        break
    end
end
assert(matched)
retryBefore=A.perf.caches.retryCosts or 0
now=now+1
''')
pump()
l.execute(b'assert(A.perf.caches.retryCosts>retryBefore and rideKinds()=="tram")')
checks.append({'case':'A quick ride timeout carries its settled costs into the final comparison','passed':True})

result={'version':e['version'],'checks':checks,'liveGameVerified':False}
(h/'world-travel-tests.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
