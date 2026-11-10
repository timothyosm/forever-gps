-- A journey alternates terrain approaches and usable rides. Taxi discoveries
-- come from this character's flight map, never from the static node catalogue.
local _,A=...
local T={walkSpeed=7};A.Transit=T
local taxiNodes={}
local graphs={}
local taxiSlots,taxiDeparture,observedFlight
for _,node in ipairs(A.TransitData.nodes) do
    if node.taxi then taxiNodes[node.taxi]=node end
end

function T.RefreshKnownFlights()
    if not (GetTaxiMapID and C_TaxiMap and C_TaxiMap.GetAllTaxiNodes) then return false end
    local map=GetTaxiMapID()
    if not A.Number(map) or map<=0 then return false end
    local ok,list=pcall(C_TaxiMap.GetAllTaxiNodes,map)
    if not ok or not A.Public(list) or type(list)~="table" then return false end
    local states=Enum and Enum.FlightPathState
    local current=states and states.Current or 0
    local reachable=states and states.Reachable or 1
    local faction=UnitFactionGroup("player")
    local known=A.db.knownFlights
    local changed=false
    taxiSlots,taxiDeparture={},nil
    for _,info in ipairs(list) do
        if A.Public(info) and type(info)=="table" and A.Number(info.nodeID) and A.Number(info.state) then
            local node=taxiNodes[info.nodeID]
            if node and (not node.faction or node.faction==faction) and (info.state==current or info.state==reachable) then
                if info.state==current then taxiDeparture=node
                elseif A.Number(info.slotIndex) and A.Public(info.isMapLayerTransition) and not info.isMapLayerTransition then
                    taxiSlots[info.slotIndex]=node
                end
                if known[info.nodeID]~=true then
                    known[info.nodeID]=true
                    changed=true
                end
            end
        end
    end
    return changed
end

function T.ResetTaxiMap()
    taxiSlots,taxiDeparture,observedFlight=nil,nil,nil
end

-- Secure post-hook for the player's native flight selection. A click only
-- becomes the active flight when the client reports that takeoff succeeded.
function T.ObserveTaxiSelection(slot)
    if not A.Number(slot) then return end
    local landing=taxiSlots and taxiSlots[slot]
    observedFlight=landing and {kind="flight",from=taxiDeparture or landing,to=landing,selectedAt=GetTime()}
end

function T.ConsumeTaxiSelection()
    local flight=observedFlight
    observedFlight=nil
    if flight and GetTime()-flight.selectedAt<=15 then return flight end
end

function T.Label(leg)
    if leg.kind=="flight" then return "Fly to "..leg.to.name end
    return leg.name or ("Take the "..leg.kind.." to "..leg.to.name)
end

function T.FlightEnd(legs,index)
    while legs[index+1] and legs[index+1].kind=="flight" do index=index+1 end
    return index
end

-- Flight connections remain in the navigation plan. The map shows one flight
-- from the original departure to the final landing, with the remaining ETA.
function T.DisplayLegs(journey)
    if journey.displayIndex==journey.index then return journey.displayLegs end
    local display,legs={},journey.legs
    local index=journey.index
    while index<=#legs do
        local leg=legs[index]
        if leg.kind=="flight" then
            local first,last=index,T.FlightEnd(legs,index)
            while first>1 and legs[first-1].kind=="flight" do first=first-1 end
            local seconds=0
            for i=index,last do seconds=seconds+legs[i].seconds end
            display[#display+1]={kind="flight",from=legs[first].from,to=legs[last].to,seconds=seconds}
            index=last+1
        else
            display[#display+1]=leg
            index=index+1
        end
    end
    journey.displayIndex,journey.displayLegs=journey.index,display
    return display
end

function T.Graph(profile,style)
    local data=A.TransitData
    local n=#data.nodes
    local known=A.db and A.db.knownFlights or {}
    local keyParts={profile or "",style}
    for _,node in ipairs(data.nodes) do
        if node.taxi and known[node.taxi]==true then keyParts[#keyParts+1]=node.taxi end
    end
    local key=table.concat(keyParts,":")
    if A.CountPerf then A.CountPerf("graphLookups") end
    for i,graph in ipairs(graphs) do
        if graph.key==key then
            if i>1 then table.remove(graphs,i);table.insert(graphs,1,graph) end
            if A.CountPerf then A.CountPerf("graphHits") end
            return graph
        end
    end
    local graph={key=key,count=n,board={},arrival={},adj={},boardingLists={},arrivalLists={}}
    local function allowed(node)
        return (not node.faction or node.faction==profile) and (not node.taxi or known[node.taxi]==true)
    end
    local function arc(a,b,cost,ride)
        local row=graph.adj[a]
        if not row then row={};graph.adj[a]=row end
        row[#row+1]={to=b,seconds=cost,ride=ride}
    end
    for _,edge in ipairs(data.edges) do
        if (not edge.faction or edge.faction==profile) and allowed(data.nodes[edge.a]) and allowed(data.nodes[edge.b]) then
            graph.board[edge.a]=true
            graph.arrival[edge.b]=true
            arc(edge.a,n+edge.b,edge.seconds,edge)
        end
    end
    local walks=data.walks[(profile or "Horde")..":"..style] or {}
    for id in pairs(graph.arrival) do
        for target,cost in pairs(walks[id] or {}) do
            if graph.board[target] and type(cost)=="number" then arc(n+id,target,cost/T.walkSpeed) end
        end
        if graph.board[id] then arc(n+id,id,0) end
    end
    if #graphs==4 then table.remove(graphs) end
    table.insert(graphs,1,graph)
    return graph
end

function T.Nodes(map,graph,arrivals)
    local lists=graph and (arrivals and graph.arrivalLists or graph.boardingLists)
    local cached=lists and lists[map]
    if cached then return cached.points,cached.ids end
    local points,ids={},{}
    local allowed=graph and (arrivals and graph.arrival or graph.board)
    for _,node in ipairs(A.TransitData.nodes) do
        if node.map==map and (not allowed or allowed[node.id]) then
            points[#points+1]=node
            ids[#ids+1]=node.id
        end
    end
    if lists then lists[map]={points=points,ids=ids} end
    return points,ids
end

function T.Resolve(start,goal,sourceIDs,sourceCosts,targetIDs,targetCosts,profile,style,graph,timeOnly)
    graph=graph or T.Graph(profile,style)
    local n=graph.count
    local finish=n*2+1
    local dist,closed,egress={},{},{}
    local previous=not timeOnly and {}
    for i,id in ipairs(sourceIDs) do
        if graph.board[id] and type(sourceCosts[i])=="number" then
            dist[id]=sourceCosts[i]/T.walkSpeed
            if previous then previous[id]={from=0,seconds=dist[id]} end
        end
    end
    for i,id in ipairs(targetIDs) do
        if graph.arrival[id] and type(targetCosts[i])=="number" then
            egress[n+id]=targetCosts[i]/T.walkSpeed
        end
    end
    while true do
        local best,value
        for id,cost in pairs(dist) do
            if not closed[id] and (not value or cost<value) then best,value=id,cost end
        end
        if not best then return nil end
        if best==finish then break end
        closed[best]=true
        for _,edge in ipairs(graph.adj[best] or {}) do
            local id,cost=edge.to,value+edge.seconds
            if not dist[id] or cost<dist[id] then
                dist[id]=cost
                if previous then previous[id]={from=best,seconds=edge.seconds,ride=edge.ride} end
            end
        end
        local cost=egress[best]
        if cost and (not dist[finish] or value+cost<dist[finish]) then
            dist[finish]=value+cost
            if previous then previous[finish]={from=best,seconds=cost} end
        end
    end
    if timeOnly then return dist[finish] end
    local nodes=A.TransitData.nodes
    local function point(id)
        if id==0 then return start end
        if id==finish then return goal end
        return nodes[id>n and id-n or id]
    end
    local reversed={}
    local id=finish
    while id~=0 do
        local edge=previous[id]
        local from,to=point(edge.from),point(id)
        if from~=to then
            local ride=edge.ride
            local leg={from=from,to=to,kind=ride and ride.kind or "walk",seconds=edge.seconds,transport=ride}
            if ride then leg.name=T.Label(leg) end
            reversed[#reversed+1]=leg
        end
        id=edge.from
    end
    local legs={}
    for i=#reversed,1,-1 do legs[#legs+1]=reversed[i] end
    return {legs=legs,index=1,seconds=dist[finish]}
end
