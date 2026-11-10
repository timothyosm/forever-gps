-- ForeverRoads world navigation adapter. Terrain is searched in bounded frame slices.
local _,A=...
local R=A.Router
local T=A.Transit
local trace=A.TracePerf or function() end
local measure=A.MeasurePerf or function() end
local clock=A.MeasurePerf and debugprofilestop
local generation=0
local arrivalCache={}
local activeApproaches,itineraryStarted
A.Path.budget=1 -- ms per frame; decoded blocks can slightly exceed this soft target.
A.Path.cacheKB=8192;A.Path.graphKB=16384;A.Path.graphRestKB=1024

local function samePoint(a,b)
    return a.map==b.map and a.x==b.x and a.y==b.y and a.z==b.z
end

local function arrivalEntry(point,graphKey)
    local terrain=ForeverRoadsTerrainData[point.map]
    for i,entry in ipairs(arrivalCache) do
        if samePoint(entry.point,point) and entry.graphKey==graphKey and entry.terrain==terrain then
            if i>1 then table.remove(arrivalCache,i);table.insert(arrivalCache,1,entry) end
            return entry
        end
    end
end

local function settledCosts(job)
    if not job or not job.valid or job.reason then return end
    local result={costs={},yards={},count=0}
    for i,cost in pairs(job.costs) do
        if type(cost)=="number" or (cost==false and job.done) then
            result.costs[i],result.yards[i]=cost,job.yards[i]
            result.count=result.count+1
        end
    end
    if result.count>0 then return result end
end

local function saveApproaches()
    local active=activeApproaches
    activeApproaches=nil
    if not active then return end
    local entry=arrivalEntry(active.destination,active.graphKey)
    local arrivals=settledCosts(active.target)
    if not entry then
        if not arrivals then return end
        entry={point=active.destination,graphKey=active.graphKey,
            terrain=ForeverRoadsTerrainData[active.destination.map]}
        if #arrivalCache==16 then table.remove(arrivalCache) end
        table.insert(arrivalCache,1,entry)
    end
    entry.result=arrivals or entry.result
    local origin=settledCosts(active.source)
    if origin then
        entry.origin={point=active.start,terrain=ForeverRoadsTerrainData[active.start.map],result=origin}
    end
end

local function itineraryReady()
    if itineraryStarted and A.RecordItinerary then A.RecordItinerary(GetTime()-itineraryStarted) end
    itineraryStarted=nil
end

function A.CheckTerrain()
    for _,map in ipairs({0,1,2991,2997,30,489,529}) do
        local data=ForeverRoadsTerrainData and ForeverRoadsTerrainData[map]
        if not data or type(data.counts)~="table" or type(data.packed)~="table" then return false,map end
        for field,want in pairs(data.counts) do
            local count=0
            for _,blocks in pairs(data.packed[field] or {}) do
                if type(blocks)~="table" or #blocks==0 then return false,map end
                count=count+1
            end
            if count~=want then return false,map end
        end
    end
    return true
end

function A.Supported(zone)
    return A.Number(zone) and A.ZoneByID[zone]~=nil
end
function A.ZoneName(zone)
    local z=A.ZoneByID[zone]
    return z and z.name or "Unknown map"
end
function A.ReadPlayer()
    local zone=C_Map.GetBestMapForUnit("player")
    if not A.Supported(zone) then return nil,"Waiting for a supported zone map and readable player position." end
    local p=C_Map.GetPlayerMapPosition(zone,"player")
    if not p then return nil,"The client is not exposing your position on this map." end
    local x,y=p:GetXY()
    if not A.Number(x) or not A.Number(y) or x<0 or x>1 or y<0 or y>1 then return nil,"Waiting for readable map coordinates." end
    local point=R.World(A.Data,zone,x*A.Data.width,y*A.Data.height,A.network.frames)
    if UnitPosition then
        local north,west,z,map=UnitPosition("player")
        if A.Number(north) and A.Number(west) and A.Number(z) and A.Number(map) and map==point.continent then point.z=z end
    end
    return point
end
function A.StopWalkPreview(mapOnly)
    if A.walkPreviewJob and (not mapOnly or not A.walkPreviewJob.crossing) then
        A.Path.Cancel(A.walkPreviewJob)
        A.walkPreviewJob=nil
    end
end

function A.CancelPlan(keepCrossing)
    if A.pathJob then trace("Search cancelled",A.routeReason or "navigation changed") end
    generation=generation+1
    saveApproaches()
    itineraryStarted=nil
    if not keepCrossing then A.crossing=nil end
    A.StopWalkPreview()
    for _,job in ipairs(A.pathJobs or {}) do A.Path.Cancel(job) end
    A.pathJobs=nil
    if A.pathJob then A.Path.Cancel(A.pathJob);A.pathJob=nil end
    A.journey=nil
end
local priorDestination=A.SetDestination
function A.SetDestination(goal,manual)
    local ok=priorDestination(goal,manual)
    if ok then
        A.db.goal.z=A.Number(goal.z) and goal.z or nil
        A.routeReason="destination selected"
        A.CancelPlan(A.crossing~=nil);A.route=nil;A.lastProgress=nil;A.progressPlayer=nil
    end
    return ok
end
local priorFollow=A.FollowQuest
function A.FollowQuest()
    priorFollow()
    if not A.db.goal and (A.pathJob or A.journey) then A.CancelPlan(A.crossing~=nil);A.pendingRoute=false end
end
local reasons={nodata="Terrain data is unavailable for this map.",outside="This point lies outside the mapped terrain.",offmesh="A selected point is not on reachable ground. Try a nearby path.",unreachable="No walkable connection was found. A boat, portal or other crossing may be needed.",error="Terrain search failed; see the game error log."}
function A.TerrainRoute(points,cost,job)
    local route={status="ok",segments={},distance=0,estimated=0,weightedCost=cost,expanded=job and job.expansions or 0,
        terrain=true,hubs=job and job.hubs,searchFrames=job and job.frames,searchCPU=job and job.cpu}
    local previous
    for _,p in ipairs(points) do
        local point={wx=-p.y,wy=-p.x,continent=p.map,z=p.z}
        if previous then
            local length=R.Distance(previous,point)
            local planar=math.sqrt((previous.wx-point.wx)^2+(previous.wy-point.wy)^2)
            local vertical=previous.z and point.z and math.abs(previous.z-point.z)>15 and planar<5
            if vertical then length=math.max(length,math.abs(previous.z-point.z)) end
            if length>0.05 then
                local s={from=previous,to=point,length=length,begin=route.distance,kind=vertical and "lift" or "terrain",
                    name=vertical and "Take the lift to the other landing" or "Follow mapped roads and paths"}
                route.distance=route.distance+length;s.finish=route.distance;route.segments[#route.segments+1]=s
            end
        end
        previous=point
    end
    if route.hubs and #route.hubs>0 then route.warning="Route enters a hostile settlement; check the map." end
    return route
end
local function native(p) return {map=p.continent,x=-p.wy,y=-p.wx,z=p.z} end
local function world(p) return {continent=p.map,wx=-p.y,wy=-p.x,z=p.z} end
local function options()
    return {profile=UnitFactionGroup and UnitFactionGroup("player") or nil,style=A.db.preferRoads and "roads" or "balanced"}
end

function A.PreviewWalks(journey,continent,crossing)
    if A.walkPreviewJob and A.walkPreviewJob.crossing and not crossing then return end
    if not journey or A.pathJob or (continent and A.walkPreviewJob and A.walkPreviewJob.map~=continent) then A.StopWalkPreview() end
    if crossing and A.walkPreviewJob then A.walkPreviewJob.crossing=true end
    if not journey or A.pathJob or A.walkPreviewJob then return end
    local last=crossing and math.min(journey.index+1,#journey.legs) or #journey.legs
    for i=journey.index+1,last do
        local leg=journey.legs[i]
        if leg.kind=="walk" and (not continent or leg.from.map==continent) and leg.preview==nil then
            local started=GetTime()
            A.walkPreviewJob=A.Path.Find(leg.from.map,leg.from,leg.to,function(points,cost,job)
                if A.walkPreviewJob~=job then return end
                A.walkPreviewJob=nil
                if A.journey~=journey or not A.db.enabled then return end
                leg.preview=points and A.TerrainRoute(points,cost,job) or false
                if A.tracePerf then trace("Map walking preview",string.format("%.2fs elapsed · %.1f ms search · %d slices",
                    GetTime()-started,job.cpu,job.frames)) end
                journey.previewRevision=(journey.previewRevision or 0)+1
                A.DrawMap()
            end,options())
            A.walkPreviewJob.crossing=crossing
            return
        end
    end
end

local function failed(reason,message)
    trace("Route failed",reason or "error")
    A.StopWalkPreview()
    itineraryStarted=nil
    A.pathJob=nil;A.journey=nil;A.route={status=reason or "error",message=message or reasons[reason] or reasons.error}
    A.status=A.route.message;A.Draw()
end
local function valid(serial,goal) return serial==generation and A.db.goal==goal and A.db.enabled end
local function apply(points,cost,job)
    A.pathJob=nil;A.revision=(A.revision or 0)+1;A.progress=0;A.lastProgress=nil;A.progressPlayer=nil
    A.route=A.TerrainRoute(points,cost,job)
    local j=A.journey;local leg=j and j.legs[j.index]
    local ride=j and T.DisplayLegs(j)[2]
    local destination=leg and (leg.to.name or A.db.goal.label)
    if ride then destination=destination.." • "..T.Label(ride) end
    A.status=leg and ("Walk to "..destination) or ("Following mapped paths to "..A.db.goal.label)
    if A.route.warning then A.status=A.status.." — "..A.route.warning end
    A.db.diagnostics={version="2.1.17",zone=A.player and A.player.zone,destination=A.db.goal.label,distance=A.route.distance,
        terrain=true,frames=job.frames,cpuMS=job.cpu,expanded=job.expansions,journeyLeg=j and j.index,journeyLegs=j and #j.legs}
    if A.tracePerf then trace("Walking line ready",string.format("%.2fs elapsed · %.1f ms search · %d slices · %d path segments",
        GetTime()-A.lastPlan,job.cpu,job.frames,#A.route.segments)) end
    itineraryReady()
    A.Draw()
end
local function showRide(leg)
    A.route={status="transport",message=T.Label(leg)}
    local instruction=leg.kind=="flight" and "Choose this destination at the flight master." or "Board manually."
    if leg.kind=="portal" then instruction="Enter the portal." end
    if leg.from.towerApproach then instruction="Climb the tower and board manually." end
    A.status=T.Label(leg)..". "..instruction
end
local function startLeg(player,serial,goal)
    A.StopWalkPreview()
    local j=A.journey;local leg=j and j.legs[j.index]
    if not leg then A.journey=nil;A.pendingRoute=true;return end
    A.pendingRoute=false
    trace("Journey step",leg.kind)
    A.progress=0;A.lastProgress=nil;A.progressPlayer=nil;A.lastPlan=GetTime();A.lastPlanPosition=player
    if leg.kind~="walk" then
        showRide(T.DisplayLegs(j)[1]);A.Draw();return
    end
    if player.continent~=leg.to.map then A.journey=nil;A.pendingRoute=true;return end
    A.route=nil;A.status="Finding walking leg "..j.index.."/"..#j.legs.."…"
    A.pathJob=A.Path.Find(player.continent,native(player),leg.to,function(points,cost,job)
        if not valid(serial,goal) then return end
        if points then apply(points,cost,job) else failed(cost) end
    end,options())
end
local function planJourney(player,target,serial,goal,direct,shortcut,retry)
    local opts=options()
    local started=clock and clock()
    local graph=T.Graph(opts.profile,opts.style)
    measure("Transit graph",started)
    local start,destination=native(player),native(target)
    local sourcePoints,sourceIDs=T.Nodes(player.continent,graph)
    local targetPoints,targetIDs=T.Nodes(target.continent,graph,true)
    local directSeconds=shortcut and shortcut.seconds or direct and direct.cost/T.walkSpeed or math.huge
    local sourceSeed=retry and retry.graphKey==graph.key and retry.source
    local entry=arrivalEntry(destination,graph.key)
    local targetSeed=entry and entry.result
    if A.CountPerf then
        A.CountPerf("arrivalLookups")
        if targetSeed then A.CountPerf("arrivalHits");A.CountPerf("arrivalCosts",targetSeed.count) end
        if sourceSeed then A.CountPerf("retryCosts",sourceSeed.count) end
    end
    local origin=entry and entry.origin
    if not sourceSeed and origin and samePoint(origin.point,start) and origin.terrain==ForeverRoadsTerrainData[start.map] then
        sourceSeed=origin.result
        if A.CountPerf then A.CountPerf("originCosts",sourceSeed.count) end
    end
    local sourceCosts,targetCosts=sourceSeed and sourceSeed.costs or {},targetSeed and targetSeed.costs or {}
    local sourceJob,targetJob;local finished=false;local lastEvaluation=-math.huge
    local journey,sourceRevision,targetRevision
    local function resolve(a,b,timeOnly)
        local stamp=clock and clock()
        local result=T.Resolve(start,destination,sourceIDs,a,targetIDs,b,opts.profile,opts.style,graph,timeOnly)
        measure("Transit comparison",stamp)
        return result
    end
    local function bounds(point,nodes)
        local costs={}
        for i,node in ipairs(nodes) do costs[i]=A.Path.LowerBound(point.map,point,node,opts.style) end
        return costs
    end
    local sourceBounds,targetBounds=bounds(start,sourcePoints),bounds(destination,targetPoints)
    local function optimistic(costs,minimums,job)
        local result={}
        for i,bound in ipairs(minimums) do
            local cost=costs[i]
            if cost~=nil then result[i]=cost
            elseif job and job.done then result[i]=false
            else result[i]=math.max(bound,job and job.radius or 0) end
        end
        return result
    end
    local function finish(journey)
        finished=true
        if A.tracePerf then
            local cpu=(sourceJob and sourceJob.cpu or 0)+(targetJob and targetJob.cpu or 0)
            trace("Route decided",string.format("%.2fs elapsed · %.1f ms comparing terrain approaches · %s",
                GetTime()-A.lastPlan,cpu,journey and journey.seconds<directSeconds and "with transport" or
                shortcut and "checking direct walk" or direct and "walking" or "no connection"))
        end
        saveApproaches()
        local fallback=shortcut and {graphKey=graph.key,source=settledCosts(sourceJob)}
        for _,job in ipairs(A.pathJobs or {}) do A.Path.Cancel(job) end
        A.pathJob=nil;A.pathJobs=nil
        if journey and journey.seconds<directSeconds then
            A.journey=journey
            itineraryReady()
            startLeg(A.player or player,serial,goal)
        elseif shortcut then
            shortcut.walk(fallback)
        elseif direct then
            apply(direct.points,direct.cost,direct.job)
        else
            failed("needs-transport","No accessible crossing was found. Local guidance resumes when you reach a connected map.")
        end
    end
    -- Skip the terrain batches when even their lower bound cannot beat walking.
    local first=resolve(optimistic(sourceCosts,sourceBounds),optimistic(targetCosts,targetBounds),true)
    if not first or first>=directSeconds then finish();return end
    if sourceSeed and targetSeed then
        local cached=resolve(sourceCosts,targetCosts)
        if cached and cached.seconds<=first then finish(cached);return end
    end
    -- Publish the selected route only after the transport comparison is settled.
    local function evaluate(force)
        if finished or not valid(serial,goal) then return end
        local now=GetTime();if not force and now-lastEvaluation<.1 then return end;lastEvaluation=now
        if shortcut and now-A.lastPlan>.75 then finish();return end
        sourceCosts=sourceJob and sourceJob.costs or sourceCosts;targetCosts=targetJob and targetJob.costs or targetCosts
        local sr=sourceJob.done and -1 or sourceJob.revision
        local tr=targetJob.done and -1 or targetJob.revision
        if sr~=sourceRevision or tr~=targetRevision then
            journey=resolve(sourceCosts,targetCosts)
            sourceRevision,targetRevision=sr,tr
        end
        local complete=sourceJob and sourceJob.done and targetJob and targetJob.done
        if complete then finish(journey);return end
        local lower=resolve(optimistic(sourceCosts,sourceBounds,sourceJob),optimistic(targetCosts,targetBounds,targetJob),true)
        local best=math.min(directSeconds,journey and journey.seconds or math.huge)
        if not lower or lower>=best then finish(journey) end
    end
    local jobs={}
    local function batch(point,points,reverse,seed)
        if seed and seed.count==#points then return {costs=seed.costs,done=true} end
        local job=A.Path.FindMany(point.map,point,points,function() evaluate(true) end,
            opts,reverse,function() evaluate(false) end)
        -- FindMany skips settled targets. Copy the seeds before its first slice.
        if seed then
            for i,cost in pairs(seed.costs) do job.costs[i],job.yards[i]=cost,seed.yards[i] end
        end
        jobs[#jobs+1]=job
        return job
    end
    sourceJob=batch(start,sourcePoints,false,sourceSeed)
    targetJob=batch(destination,targetPoints,true,targetSeed)
    activeApproaches={start=start,destination=destination,graphKey=graph.key,source=sourceJob,target=targetJob}
    A.pathJob=jobs[1];A.pathJobs=jobs
    if not A.pathJob then evaluate(true) end
end

-- Near both ends of a ride, try proving it faster than the minimum possible
-- walking time. If the proof takes too long, continue with the full comparison.
local function nearbyRide(start,destination,seconds,faction)
    if seconds<=0 then return false end
    local nodes=A.TransitData.nodes
    local known=A.db.knownFlights or {}
    local function close(point,node)
        return point.map==node.map and (point.x-node.x)^2+(point.y-node.y)^2<=50^2 and
            (not node.faction or node.faction==faction) and (not node.taxi or known[node.taxi]==true)
    end
    for _,edge in ipairs(A.TransitData.edges) do
        if edge.seconds<seconds and (not edge.faction or edge.faction==faction) and
            close(start,nodes[edge.a]) and close(destination,nodes[edge.b]) then return true end
    end
    return false
end

function A.Plan(player,fromCrossing)
    if InCombatLockdown() then A.pendingRoute=true;A.status="Route update queued until combat ends.";return end
    A.CancelPlan(fromCrossing)
    trace("Route requested",A.routeReason or "refresh")
    A.routeReason=nil
    local serial=generation;local goal=A.db.goal
    if not goal then return end
    itineraryStarted=GetTime()
    local target=R.World(A.Data,goal.zone,goal.x,goal.y,A.network.frames);target.z=goal.z
    A.pendingRoute=false;A.lastPlan=GetTime();A.lastPlanPosition=player;A.arrived=false;A.progress=0;A.lastProgress=nil;A.progressPlayer=nil
    A.route=nil;A.status="Planning route…"
    if player.continent~=target.continent then planJourney(player,target,serial,goal);return end
    local start,destination=native(player),native(target)
    local opts=options()
    local function walk(retry)
        A.pathJob=A.Path.Find(start.map,start,destination,function(points,cost,job)
            if not valid(serial,goal) then return end
            if points then planJourney(player,target,serial,goal,{points=points,cost=cost,job=job},nil,retry)
            elseif cost=="unreachable" then planJourney(player,target,serial,goal,nil,nil,retry)
            else failed(cost) end
        end,opts)
    end
    local seconds=A.Path.LowerBound(start.map,start,destination,opts.style)/T.walkSpeed
    if nearbyRide(start,destination,seconds,opts.profile) then
        planJourney(player,target,serial,goal,nil,{seconds=seconds,walk=walk})
    else walk() end
end

local function followTaxi()
    local started=not A.wasOnTaxi
    if started then A.taxi=T.ConsumeTaxiSelection() end
    A.wasOnTaxi=true
    A.player=nil
    if not A.db.goal then A.Draw();return end
    local taxi=A.taxi
    if taxi and (taxi.goal~=A.db.goal or A.pendingRoute) then
        local j=A.journey
        local i=j and j.index
        local leg=i and j.legs[i]
        if leg and leg.kind=="walk" then i=i+1;leg=j.legs[i] end
        if leg and leg.kind=="flight" and (taxi.from==taxi.to or leg.from==taxi.from) and
            j.legs[T.FlightEnd(j.legs,i)].to==taxi.to then
            -- Boarding can beat the next ticker update of the walk to the flight master.
            if A.pathJob then A.Path.Cancel(A.pathJob);A.pathJob=nil end
            j.index=i;A.pendingRoute=false;taxi.goal=A.db.goal;taxi.onward=false
            A.route={status="transport"};A.status="In flight to "..taxi.to.name
        elseif not InCombatLockdown() then
            taxi.goal=A.db.goal;taxi.onward=true
            local landing=world(taxi.to)
            landing.zone=taxi.to.zone
            A.Plan(landing)
            if not A.route and not A.journey then
                A.status="In flight to "..taxi.to.name..". Planning route from landing…"
            end
        else
            A.status="In flight to "..taxi.to.name..". Onward route queued until combat ends."
        end
    elseif not taxi and (started or not A.route) then
        if A.pathJob then A.CancelPlan() end
        local leg=A.journey and T.DisplayLegs(A.journey)[1]
        A.route={status="transport"}
        A.status=leg and leg.kind=="flight" and ("In flight to "..leg.to.name) or "In flight. Guidance resumes after landing."
    end
    A.Draw()
end

local function surfaceRide(leg)
    return leg and (leg.kind=="boat" or leg.kind=="zeppelin" or leg.kind=="skycutter")
end

local function updateCrossing(player)
    local j=A.journey
    local leg=j and j.legs[j.index]
    local crossing=A.crossing
    if not crossing then
        if not surfaceRide(leg) or not player then return end
        local departure=world(leg.from)
        if R.Distance(player,departure)>75 then return end
        crossing={leg=leg,goal=A.db.goal,departure=departure,exit=world(leg.to)}
        A.crossing=crossing
    end
    leg=crossing.leg
    local exit=crossing.exit
    local exitDistance=player and R.Distance(player,exit)
    if exitDistance and exitDistance<=50 then
        A.crossing=nil
        if crossing.onward then
            if exitDistance>15 or crossing.goal~=A.db.goal or
                not (A.pathJob or j or (A.route and A.route.status=="ok")) then
                A.routeReason="docking position changed";A.CancelPlan();A.pendingRoute=true
            end
            A.lastZone=player.zone;A.lastContinent=player.continent
        end
        return
    end
    if player then
        local now=GetTime()
        local previous=crossing.position
        local departureDistance=R.Distance(player,crossing.departure)
        if player.continent~=leg.from.map and player.continent==leg.to.map then
            crossing.departed=true
        elseif crossing.gap and departureDistance>75 then
            crossing.departed=true
        elseif not crossing.departed and previous and previous.continent==player.continent then
            local elapsed=now-crossing.sampleAt
            local speed=GetUnitSpeed and GetUnitSpeed("player")
            local distance=math.sqrt((player.wx-previous.wx)^2+(player.wy-previous.wy)^2)
            if elapsed>=.1 and elapsed<=2 and distance<100 and A.Number(speed) and distance/elapsed>math.max(12,speed+6) then
                crossing.motion=(crossing.motion or 0)+1
                if crossing.motion>=2 then crossing.departed=true end
            elseif elapsed>=.1 then crossing.motion=0 end
        end
        if not crossing.sampleAt or now-crossing.sampleAt>=.1 then
            crossing.position,crossing.sampleAt=player,now
        end
        crossing.gap=nil
        if not crossing.departed and (departureDistance>160 or crossing.onward) then
            A.routeReason="left the boarding area";A.CancelPlan();A.pendingRoute=true
            return
        end
    else
        crossing.gap=true
    end
    if not A.db.goal then return end
    if crossing.goal~=A.db.goal or (crossing.onward and A.pendingRoute) then
        if player and not crossing.departed then A.crossing=nil;return end
        if not InCombatLockdown() then
            crossing.goal=A.db.goal;crossing.onward=true
            A.player=nil
            exit.zone=leg.to.zone
            A.Plan(exit,true)
            if not A.route and not A.journey then A.status="Planning route from "..leg.to.name.."…" end
        end
        A.Draw();return true
    end
    if crossing.onward then A.player=nil;A.Draw();return true end
    A.PreviewWalks(j,leg.to.map,true)
    if not player then A.Draw();return true end
end

function A.Tick()
    if not A.db or not A.network then return end
    if not A.db.enabled then
        if A.pathJob or A.journey or A.crossing then A.CancelPlan();A.pendingRoute=A.db.goal~=nil end
        A.status="Guidance paused."
        if not A.db.recording then A.Draw();return end
    end
    local onTaxi=UnitOnTaxi and UnitOnTaxi("player")
    if A.db.enabled and A.Public(onTaxi) and onTaxi then
        followTaxi();return
    end
    local player,reason=A.ReadPlayer();A.player=player
    if A.db.enabled and (A.db.goal or A.crossing) and not A.wasOnTaxi and updateCrossing(player) then return end
    if not player then
        if A.wasOnTaxi and A.taxi and A.taxi.onward then A.Draw();return end
        if A.pathJob then A.CancelPlan() end
        -- A transport may briefly hide position during its loading screen. Keep its next landing.
        A.status=reason;A.route=nil
        if not A.journey then A.pendingRoute=A.db.goal~=nil end
        A.Draw();return
    end
    local flightEnded=A.wasOnTaxi
    local taxi=A.taxi
    A.wasOnTaxi=nil;A.taxi=nil
    A.Record(player)
    if not A.db.enabled or not A.db.goal then A.Draw();return end
    if A.pathJob and A.lastPlanPosition and A.lastPlanPosition.continent~=player.continent then
        A.routeReason="changed continent";A.CancelPlan();A.pendingRoute=true
    end
    local j=A.journey;local leg=j and j.legs[j.index]
    if flightEnded and taxi and taxi.onward then
        if taxi.goal==A.db.goal and R.Distance(player,world(taxi.to))<=15 and
            (A.pathJob or j or (A.route and A.route.status=="ok")) then
            A.lastZone=player.zone;A.lastContinent=player.continent
        else
            A.routeReason="landing position changed";A.CancelPlan();A.pendingRoute=true;j=nil;leg=nil
        end
    elseif flightEnded then
        local landing,closest
        if leg and leg.kind=="flight" then
            for i=j.index,T.FlightEnd(j.legs,j.index) do
                local distance=R.Distance(player,world(j.legs[i].to))
                if distance<=65 and (not closest or distance<closest) then landing,closest=i,distance end
            end
        end
        if landing then
            j.index=landing;leg=j.legs[landing]
        else
            A.routeReason="landed at a different stop";A.CancelPlan();A.pendingRoute=true;j=nil;leg=nil
        end
    end
    if leg and leg.kind~="walk" then
        local destination=world(leg.to)
        if R.Distance(player,destination)<=(leg.kind=="flight" and 65 or 50) then
            if InCombatLockdown() then A.status="Transport arrived. Walking route queued until combat ends."
            else j.index=j.index+1;startLeg(player,generation,A.db.goal) end
        elseif not A.route then showRide(T.DisplayLegs(j)[1]) end
        A.lastZone=player.zone;A.Draw();return
    end
    if A.lastZone and A.lastZone~=player.zone and not A.pathJob then
        if not j and A.lastContinent~=player.continent then A.pendingRoute=true;A.routeReason="changed continent" end
    end
    A.lastZone=player.zone;A.lastContinent=player.continent
    if A.pendingRoute then A.Plan(player) end
    if A.pathJob then A.Draw();return end
    local route=A.route
    if route and route.status=="ok" then
        j=A.journey;leg=j and j.legs[j.index]
        local goal=leg and world(leg.to) or R.World(A.Data,A.db.goal.zone,A.db.goal.x,A.db.goal.y,A.network.frames)
        if not leg then goal.z=A.db.goal.z end
        if R.Distance(player,goal)<=15 then
            if leg and j.index<#j.legs then
                if not InCombatLockdown() then j.index=j.index+1;startLeg(player,generation,A.db.goal) end
            else A.arrived=true;A.progress=route.distance;A.status="Destination reached: "..A.db.goal.label end
        else
            A.arrived=false
            if route.segments[1] and route.segments[1].from.continent~=player.continent then
                A.pendingRoute=true;A.routeReason="changed continent"
            else
                local previous=A.progressPlayer;local progress
                if A.progressRevision~=A.revision or not previous or R.Distance(previous,player)>=1 then
                    progress=R.Progress(route,player,A.progress);A.progressPlayer=player;A.progressRevision=A.revision
                else progress=A.lastProgress end
                A.lastProgress=progress
                if progress then
                    A.progress=math.max(A.progress or 0,progress.progress)
                end
                if (not progress or progress.distance>55) and GetTime()-(A.lastPlan or 0)>2 and
                    A.lastPlanPosition and R.Distance(player,A.lastPlanPosition)>15 then
                    A.pendingRoute=true;A.routeReason="moved off route"
                end
            end
        end
    elseif route and GetTime()-(A.lastPlan or 0)>3 and A.lastPlanPosition and R.Distance(player,A.lastPlanPosition)>12 then
        A.pendingRoute=true;A.routeReason="moved after failed search"
    end
    A.Draw()
end
