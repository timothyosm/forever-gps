local _, A = ...
local R=A.Router
function A.Public(v) return not issecretvalue or not issecretvalue(v) end
function A.Number(v) return A.Public(v) and type(v)=="number" and v==v and v~=math.huge and v~=-math.huge end
function A.Supported(zone)
    if not A.Number(zone) then return false end
    for _,z in ipairs(A.Data.zones) do if z.id==zone then return true end end
    return false
end
function A.ZoneName(zone)
    for _,z in ipairs(A.Data.zones) do if z.id==zone then return z.name end end
    return "Unsupported zone"
end

function A.Calibrate()
    local frames={}; A.liveFrames=0
    for _,z in ipairs(A.Data.zones) do
        local continent,a=C_Map.GetWorldPosFromMapPos(z.id,CreateVector2D(0,0))
        local other,b=C_Map.GetWorldPosFromMapPos(z.id,CreateVector2D(1,1))
        if A.Public(continent) and A.Public(other) and continent~=nil and continent==other and a and b then
            local x0,y0=a:GetXY(); local x1,y1=b:GetXY()
            if A.Number(x0) and A.Number(y0) and A.Number(x1) and A.Number(y1) and x0~=x1 and y0~=y1 then
                frames[z.id]={wx=-y0,wy=-x0,dx=y0-y1,dy=x0-x1,continent=continent}; A.liveFrames=A.liveFrames+1
            end
        end
    end
    A.network=R.Build(A.Data,frames)
end

function A.ReadPlayer()
    local zone=C_Map.GetBestMapForUnit("player")
    if not A.Supported(zone) then return nil,"Navigation covers Tirisfal, Silverpine, Hillsbrad and Stonetalon outdoors." end
    if IsInInstance and IsInInstance() then return nil,"Indoor dungeon routing is not included." end
    local p=C_Map.GetPlayerMapPosition(zone,"player")
    if not p then return nil,"Waiting for your map position." end
    local x,y=p:GetXY()
    if not A.Number(x) or not A.Number(y) or x<0 or x>1 or y<0 or y>1 then return nil,"Waiting for readable map coordinates." end
    return R.World(A.Data,zone,x*A.Data.width,y*A.Data.height,A.network.frames)
end

function A.ValidDestination(zone,x,y)
    return A.Supported(zone) and A.Number(x) and A.Number(y) and x>=0 and x<=1 and y>=0 and y<=1
end

function A.TrackedQuestID()
    local id=C_SuperTrack.GetSuperTrackedQuestID()
    if A.Number(id) and id>0 then return id end
end

function A.QuestDestination(questID)
    if not A.Number(questID) or questID<=0 then return nil,"Select a quest marker or place a map pin." end
    local title=C_QuestLog.GetTitleForQuestID(questID)
    if not A.Public(title) then title=nil end
    local isComplete=C_QuestLog.ReadyForTurnIn or C_QuestLog.IsComplete
    local complete=isComplete and isComplete(questID)
    if not A.Public(complete) then complete=false end
    local function destination(zone,x,y)
        if A.ValidDestination(zone,x,y) then return {zone=zone,x=x*A.Data.width,y=y*A.Data.height,
            label=(title or ("Quest "..questID))..(complete and " (turn in)" or ""),questID=questID,source="quest"} end
    end
    local map,x,y=C_QuestLog.GetNextWaypoint(questID)
    local waypoint=destination(map,x,y)
    if waypoint and not complete then return waypoint end
    local seen={}
    local function onMap(zone)
        if not A.Supported(zone) or seen[zone] then return end
        seen[zone]=true
        local x,y
        if C_QuestLog.GetNextWaypointForMap then x,y=C_QuestLog.GetNextWaypointForMap(questID,zone) end
        local scoped=destination(zone,x,y)
        if scoped and not complete then return scoped end
        local pois=C_QuestLog.GetQuestsOnMap(zone)
        if not A.Public(pois) then pois=nil end
        for _,poi in ipairs(pois or {}) do
            if A.Public(poi) and A.Number(poi.questID) and poi.questID==questID and
                A.Public(poi.isQuestStart) and not poi.isQuestStart and
                A.Public(poi.isMapIndicatorQuest) and not poi.isMapIndicatorQuest then
                -- POI x/y belong to the queried map, including child-map entries.
                local goal=destination(zone,poi.x,poi.y)
                if goal then return goal end
            end
        end
        -- Prefer turn-in POIs to a waypoint that may still point to the objective.
        waypoint=waypoint or scoped
    end
    local viewed=WorldMapFrame and WorldMapFrame.GetMapID and WorldMapFrame:GetMapID()
    local goal=onMap(viewed) or onMap(C_Map.GetBestMapForUnit("player"))
    if goal then return goal end
    for _,z in ipairs(A.Data.zones) do
        goal=onMap(z.id)
        if goal then return goal end
    end
    if waypoint then return waypoint end
    if A.Number(map) and map>0 and not A.Supported(map) then return nil,"Tracked quest destination is outside the supported zones." end
    return nil,"Waiting for this quest's map marker."
end

function A.SameDestination(a,b)
    return a and b and a.zone==b.zone and a.questID==b.questID and math.abs(a.x-b.x)<0.5 and math.abs(a.y-b.y)<0.5
end

function A.SetDestination(goal,manual)
    if not goal or not A.ValidDestination(goal.zone,goal.x/A.Data.width,goal.y/A.Data.height) then
        A.Print("Choose a destination on a supported zone map."); return false
    end
    if manual then A.db.followQuest=false end
    A.db.goal={zone=goal.zone,x=goal.x,y=goal.y,label=goal.label or "Map destination",source=goal.source or "manual",questID=goal.questID}
    A.db.enabled=true; A.arrived=false; A.pendingRoute=true; A.lastFailure=nil; return true
end

function A.FollowQuest()
    if not A.db.enabled or not A.db.followQuest or InCombatLockdown() then return end
    local id=A.TrackedQuestID()
    if not id and QuestMapFrame_GetFocusedQuestID then id=QuestMapFrame_GetFocusedQuestID() end
    local goal,reason=A.QuestDestination(id)
    if goal then
        if A.SameDestination(A.db.goal,goal) then A.db.goal.label=goal.label
        else A.SetDestination(goal,false) end
    elseif not A.db.goal or A.db.goal.source=="quest" then
        A.db.goal=nil; A.route=nil; A.status=reason; A.arrived=false
    end
end

function A.Plan(player)
    if InCombatLockdown() then A.pendingRoute=true; A.status="Route update queued until combat ends."; return end
    local now=GetTime()
    local route=R.Route(A.network,player,A.db.goal,{preferRoads=A.db.preferRoads})
    A.lastPlan=now; A.lastPlanPosition=player; A.pendingRoute=false; A.progress=0; A.arrived=false
    A.route=route; A.revision=(A.revision or 0)+1
    if route.status=="ok" then
        A.status="Following roads to "..A.db.goal.label
        if route.warning then A.status=A.status.." — "..route.warning end
        A.db.diagnostics={version="1.1.3",zone=player.zone,destination=A.db.goal.label,distance=route.distance,
            estimated=route.estimated,nodes=#A.network.nodes,liveMapFrames=A.liveFrames,badLinks=A.network.badLinks}
    else A.status=route.message end
end

function A.ToggleRecording()
    if A.db.recording then A.db.recording=false; A.Print("Recording saved for this character. Recorded walks are calibration data, not automatic route replacements.")
    else
        local player,reason=A.ReadPlayer(); if not player then A.Print(reason); return end
        A.db.recordings=A.db.recordings or {}
        local track={started=time(),points={}}
        A.db.recordings[#A.db.recordings+1]=track; A.db.recording=true
        A.Print("Recording your walk. Use /froads record again to stop.")
    end
end

function A.Record(player)
    if not A.db.recording then return end
    local track=A.db.recordings[#A.db.recordings]; local previous=track.points[#track.points]
    if not previous or previous.zone~=player.zone or R.Distance(previous,player)>=8 then
        track.points[#track.points+1]={zone=player.zone,continent=player.continent,x=player.x,y=player.y,wx=player.wx,wy=player.wy}
    end
end

function A.Tick()
    if not A.db or not A.network then return end
    if not A.db.enabled and not A.db.recording then A.status="Guidance paused."; A.Draw(); return end
    local player,reason=A.ReadPlayer(); A.player=player
    if not player then
        A.status=reason; A.route=nil; A.pendingRoute=A.db.goal~=nil
        A.Draw(); return
    end
    A.Record(player)
    if not A.db.enabled or not A.db.goal then A.Draw(); return end
    if A.route and A.route.status=="ok" and A.route.segments[1] and A.route.segments[1].from.continent~=player.continent then
        A.route=nil; A.pendingRoute=true
    end
    if A.lastZone and A.lastZone~=player.zone then A.pendingRoute=true end
    A.lastZone=player.zone
    if A.pendingRoute then A.Plan(player) end
    local route=A.route
    if route and route.status=="ok" then
        local goal=R.World(A.Data,A.db.goal.zone,A.db.goal.x,A.db.goal.y,A.network.frames)
        goal.z=A.db.goal.z
        if R.Distance(player,goal)<=15 then
            A.arrived=true; A.progress=route.distance; A.status="Destination reached: "..A.db.goal.label
        else
            A.arrived=false
            local previous=A.progressPlayer
            local progress
            if A.progressRevision~=A.revision or not previous or previous.zone~=player.zone or R.Distance(previous,player)>=1 then
                progress=R.Progress(route,player,A.progress)
                A.progressPlayer=player;A.progressRevision=A.revision
            else progress=A.lastProgress end
            A.lastProgress=progress
            if progress then
                A.progress=math.max(A.progress or 0,progress.progress)
                if progress.distance>55 and GetTime()-(A.lastPlan or 0)>2 then A.pendingRoute=true end
            else A.pendingRoute=true end
        end
    elseif route and GetTime()-(A.lastPlan or 0)>3 and A.lastPlanPosition and R.Distance(player,A.lastPlanPosition)>12 then
        A.pendingRoute=true
    end
    A.Draw()
end
