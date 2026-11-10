local addon,A=...
local events=CreateFrame("Frame")
local questQueued=false
local observedQuestID
function A.Print(message) DEFAULT_CHAT_FRAME:AddMessage("|cff66eebbForever GPS:|r "..tostring(message)) end
function A.Clear(keepCrossing)
    if A.CancelPlan then A.CancelPlan(keepCrossing) end
    A.db.goal=nil; A.db.followQuest=false; A.route=nil; A.progress=0; A.arrived=false
    A.status="Destination cleared. Place a map pin, track a quest with /froads follow, or Alt-click a zone map."; A.Draw()
end

local function pinDestination(zone,position,z)
    if not A.Public(position) or not position then return end
    local x,y=position.x,position.y
    if not (A.Number(x) and A.Number(y)) and position.GetXY then x,y=position:GetXY() end
    if A.ValidDestination(zone,x,y) then
        return {zone=zone,x=x*A.Data.width,y=y*A.Data.height,z=A.Number(z) and z or nil,label="Map pin",source="pin"}
    end
end

local function readMapPin()
    local pin=C_Map.GetUserWaypoint and C_Map.GetUserWaypoint()
    if not A.Public(pin) then return nil,true end
    if not pin and not (C_Map.HasUserWaypoint and C_Map.HasUserWaypoint()) then return nil,false end
    local zone,z=pin and pin.uiMapID,pin and pin.z
    local goal=pin and pinDestination(zone,pin.position,z)
    if goal then return goal end
    local project=C_Map.GetUserWaypointPositionForMap
    local function projected(map)
        if project and A.Supported(map) then return pinDestination(map,project(map),z) end
    end
    goal=projected(zone)
    if not goal and pin and A.Number(zone) and A.Public(pin.position) and pin.position and C_Map.GetMapPosFromWorldPos then
        local continent,world=C_Map.GetWorldPosFromMapPos(zone,pin.position)
        if A.Number(continent) and A.Public(world) and world then
            local map,position=C_Map.GetMapPosFromWorldPos(continent,world)
            goal=pinDestination(map,position,z) or projected(map)
        end
    end
    if not goal and WorldMapFrame and WorldMapFrame.GetMapID then goal=projected(WorldMapFrame:GetMapID()) end
    return goal,true
end

local function updateMapPin(automatic)
    local goal,present=readMapPin()
    local previous=A.db.goal
    if not goal then
        if not present and automatic and previous and previous.source=="pin" then A.Clear() end
        if not automatic then A.Print("Place a map pin on a supported zone map, then try /froads pin again.") end
        return
    end
    if automatic and not A.db.enabled then return end
    if automatic and previous and previous.source=="pin" and previous.zone==goal.zone and
        previous.x==goal.x and previous.y==goal.y and previous.z==goal.z then return true end
    return A.SetDestination(goal,true)
end

function A.UseMapPin()
    if updateMapPin(false) then A.Tick() end
end

local function pinSelected()
    local selected=C_SuperTrack.IsSuperTrackingUserWaypoint and C_SuperTrack.IsSuperTrackingUserWaypoint()
    return A.Public(selected) and selected
end

local function followTrackedQuest()
    if A.db.goal and A.db.goal.source=="pin" then A.Clear(A.crossing~=nil) end
    A.db.followQuest=true
    A.FollowQuest(); A.Tick()
end
local aliases={tirisfal=1420,silverpine=1421,hillsbrad=1424,stonetalon=1442,stone=1442,barrens=1413}
local function zoneKey(name) return name:lower():gsub("[%s%p]","") end
for _,z in ipairs(A.Data.zones) do aliases[tostring(z.id)]=z.id;aliases[zoneKey(z.name)]=z.id end
local function resolveZone(name)
    name=(name or ""):gsub('^"(.-)"$','%1')
    return aliases[name:lower()] or aliases[zoneKey(name)]
end

function A.Command(input)
    local cmd,rest=(input or ""):match("^%s*(%S*)%s*(.-)%s*$"); cmd=cmd:lower()
    if cmd=="pause" then A.db.enabled=false; A.Tick()
    elseif cmd=="resume" then
        A.db.enabled=true
        if A.db.goal and A.db.goal.source=="pin" then updateMapPin(true) end
        A.pendingRoute=A.db.goal~=nil; A.Tick()
    elseif cmd=="clear" then A.Clear()
    elseif cmd=="follow" then
        A.db.enabled=true; followTrackedQuest()
    elseif cmd=="pin" then A.UseMapPin()
    elseif cmd=="record" then A.ToggleRecording(); A.Draw()
    elseif cmd=="way" then
        local zone,x,y,label=rest:match("^(.-)%s+([%d%.]+)%s+([%d%.]+)%s*(.*)$")
        zone=zone and resolveZone(zone); x,y=tonumber(x),tonumber(y)
        if zone and x and y and A.ValidDestination(zone,x/100,y/100) then
            A.SetDestination({zone=zone,x=x/100*A.Data.width,y=y/100*A.Data.height,label=label~="" and label or "Manual destination",source="command"},true); A.Tick()
        else A.Print("Usage: /froads way zone-name-or-map-ID x y [name]  (coordinates 0–100)") end
    elseif cmd=="status" then
        A.Print(A.status or "Starting"); if A.route and A.route.status=="ok" then A.Print(string.format("%.0f yd • %d A* nodes • %d/%d live map frames",A.route.distance,A.route.expanded,A.liveFrames,#A.Data.zones)) end
        if A.journey then
            for _,leg in ipairs(A.Transit.DisplayLegs(A.journey)) do
                if leg.kind~="walk" then A.Print(A.Transit.Label(leg)) end
            end
        end
    elseif cmd=="perf" then
        A.PerformanceCommand(rest:lower())
    else A.window:SetShown(not A.window:IsShown()) end
end
local function initialize()
    if A.ready then return end
    A.ready=true
    ForeverRoadsDB=ForeverRoadsDB or {schema=1,enabled=true,followQuest=true,showMap=true,showMinimap=true,showRoads=false,preferRoads=false,recordings={}}
    A.db=ForeverRoadsDB
    if A.db.schema~=1 then A.Print("Unsupported saved settings version; addon not started."); return end
    if A.CheckTerrain then
        local complete,map=A.CheckTerrain()
        if not complete then A.db.enabled=false;A.Print("Terrain files are incomplete for map "..tostring(map)..". Reinstall the complete ForeverRoads folder.");return end
    end
    A.db.recordings=A.db.recordings or {}; A.db.recording=false
    if type(A.db.knownFlights)~="table" then A.db.knownFlights={} end
    A.db.showRoads=false -- The old four-zone preview is superseded by full terrain routing.
    if A.db.goal and not A.ValidDestination(A.db.goal.zone,A.db.goal.x/A.Data.width,A.db.goal.y/A.Data.height) then A.db.goal=nil end
    A.Calibrate(); A.CreateUI(); A.AttachMap(); A.status="Place a map pin, track a quest, or Alt-click a zone map."
    if A.Transit and hooksecurefunc and TakeTaxiNode then
        hooksecurefunc("TakeTaxiNode",A.Transit.ObserveTaxiSelection)
    end
    A.pendingRoute=A.db.goal~=nil
    SLASH_FOREVERROADS1="/froads"; SlashCmdList.FOREVERROADS=A.Command
    -- Read-only status can also be inspected by /dump ForeverRoads.GetStatus().
    ForeverRoads={version="2.1.17",GetStatus=function()
        return {status=A.status,enabled=A.db.enabled,followQuest=A.db.followQuest,player=A.player,goal=A.db.goal,
            routeStatus=A.route and A.route.status,remaining=A.route and A.route.status=="ok" and (A.route.distance-(A.progress or 0)),
            mapLines=A.mapLineCount or 0,mapLayerLevel=A.mapLayerLevel,minimapLines=A.minimapLineCount or 0,liveFrames=A.liveFrames,recording=A.db.recording,
            performance=A.perf}
    end}
    A.ticker=C_Timer.NewTicker(.2,function()
        local ok,err=pcall(A.Tick)
        if not ok then
            A.db.enabled=false; A.status="Navigation error: "..tostring(err)
            if A.lastError~=A.status then A.Print(A.status); A.lastError=A.status end
            if A.mapGuide then A.mapGuide:Hide() end
        end
    end)
    local goal=A.db.goal
    observedQuestID=A.TrackedQuestID()
    if (goal and goal.source=="pin") or
        (A.db.enabled and A.db.followQuest and (pinSelected() or (not goal and not observedQuestID))) then
        updateMapPin(true)
    end
    A.FollowQuest(); A.Tick()
    A.Print("Loaded world-wide terrain navigation. Place a map pin or use /froads to open settings.")
end
local tick=A.Tick
function A.Tick()
    local start=debugprofilestop and debugprofilestop()
    tick()
    A.MeasurePerf("Update",start)
end
local taxiScanQueued,pinUpdated,trackingUpdated=false,false,false
local function queueMapSelection(event)
    local queued=pinUpdated or trackingUpdated
    if event=="USER_WAYPOINT_UPDATED" then pinUpdated=true else trackingUpdated=true end
    if queued then return end
    C_Timer.After(0,function()
        local pinChanged,trackingChanged=pinUpdated,trackingUpdated
        pinUpdated,trackingUpdated=false,false
        local selectedPin=trackingChanged and pinSelected()
        local selectedQuest
        if trackingChanged then
            local id=A.TrackedQuestID()
            selectedQuest=id and id~=observedQuestID and not selectedPin
            observedQuestID=id
        end
        if selectedQuest and A.db.enabled then
            followTrackedQuest()
        elseif pinChanged or selectedPin then
            if updateMapPin(true) then A.Tick() end
        else
            A.FollowQuest(); A.Tick()
        end
    end)
end
events:SetScript("OnEvent",function(_,event,name)
    if event=="PLAYER_ENTERING_WORLD" then
        C_Timer.After(.2,function()
            if not A.ready then initialize()
            elseif A.db and A.network then A.FollowQuest(); A.Tick() end
        end)
    elseif event=="ADDON_LOADED" and name=="Blizzard_WorldMap" and A.db then A.AttachMap()
    elseif event=="TAXIMAP_OPENED" or event=="TAXI_NODE_STATUS_CHANGED" then
        if event=="TAXIMAP_OPENED" and A.Transit then A.Transit.ResetTaxiMap() end
        if not A.db or not A.db.knownFlights or taxiScanQueued then return end
        taxiScanQueued=true
        C_Timer.After(0,function()
            taxiScanQueued=false
            if A.Transit.RefreshKnownFlights() then
                local journey=A.journey
                local leg=journey and journey.legs[journey.index]
                if A.db.goal and A.db.enabled and (not leg or leg.kind=="walk") then
                    A.pendingRoute=true;A.routeReason="learned flights changed"
                    A.Tick()
                end
                A.RefreshSettings(true)
            end
        end)
    elseif A.network then
        if event=="USER_WAYPOINT_UPDATED" or event=="SUPER_TRACKING_CHANGED" then
            queueMapSelection(event)
        elseif not questQueued then
            questQueued=true
            C_Timer.After(.25,function() questQueued=false; A.FollowQuest(); A.Tick() end)
        end
    end
end)
for _,event in ipairs({"ADDON_LOADED","PLAYER_ENTERING_WORLD","SUPER_TRACKING_CHANGED","QUEST_LOG_UPDATE",
    "QUEST_POI_UPDATE","QUEST_WATCH_LIST_CHANGED","QUEST_TURNED_IN","ZONE_CHANGED_NEW_AREA",
    "PLAYER_REGEN_ENABLED","USER_WAYPOINT_UPDATED","MINIMAP_UPDATE_ZOOM",
    "TAXIMAP_OPENED","TAXI_NODE_STATUS_CHANGED"}) do
    pcall(events.RegisterEvent,events,event)
end
