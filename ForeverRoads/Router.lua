local _, A = ...
local R = {}; A.Router=R
local sqrt, abs, min, max = math.sqrt,math.abs,math.min,math.max
local function distance(a,b)
    if a.continent~=nil and b.continent~=nil and a.continent~=b.continent then return math.huge end
    return sqrt((a.wx-b.wx)^2+(a.wy-b.wy)^2+(a.z and b.z and (a.z-b.z)^2 or 0))
end
R.Distance=distance

function R.World(data, zone, x, y, frames)
    local frame=frames and frames[zone]
    if frame then return {zone=zone,x=x,y=y,continent=frame.continent,wx=frame.wx+x/data.width*frame.dx,wy=frame.wy+y/data.height*frame.dy} end
    for _,z in ipairs(data.zones) do
        if z.id==zone then
            local b=z.bounds
            return {zone=zone,x=x,y=y,continent=z.continent,wx=-b[4]+x/data.width*(b[4]-b[2]),wy=-b[3]+y/data.height*(b[3]-b[1])}
        end
    end
    error("Unsupported map: "..tostring(zone))
end

function R.Build(data,frames)
    local net={data=data,frames=frames,nodes={},edges={},adj={},badLinks={}}
    local lookup={}
    local function node(zone,x,y)
        local key=string.format("%d:%.4f:%.4f",zone,x,y)
        if not lookup[key] then
            local id=#net.nodes+1; lookup[key]=id
            net.nodes[id]=R.World(data,zone,x,y,frames); net.nodes[id].id=id; net.adj[id]={}
        end
        return lookup[key]
    end
    local function edge(a,b,meta)
        if a==b then return end
        meta.a,meta.b,meta.length=a,b,distance(net.nodes[a],net.nodes[b])
        if meta.kind=="border" and meta.length>80 then net.badLinks[#net.badLinks+1]=meta.name; return end
        net.edges[#net.edges+1]=meta
        table.insert(net.adj[a],{to=b,edge=meta}); table.insert(net.adj[b],{to=a,edge=meta})
    end
    for _,road in ipairs(data.roads) do
        local prev
        for i,p in ipairs(road.points) do
            local id=node(road.zone,p[1],p[2])
            if prev then edge(prev,id,{id=road.id..":"..(i-1),roadId=road.id,name=road.name,kind=road.kind,zone=road.zone}) end
            prev=id
        end
    end
    for _,link in ipairs(data.links) do edge(node(unpack(link.from)),node(unpack(link.to)),{id=link.id,roadId=link.id,name=link.name,kind="border"}) end
    return net
end

function R.Project(net,point,blocked)
    local p=point.wx and point or R.World(net.data,point.zone,point.x,point.y,net.frames)
    local best
    for _,edge in ipairs(net.edges) do
        if edge.kind~="border" and edge.zone==p.zone and not (blocked and blocked[edge.id]) then
            local a,b=net.nodes[edge.a],net.nodes[edge.b]
            local vx,vy=b.wx-a.wx,b.wy-a.wy
            local t=max(0,min(1,((p.wx-a.wx)*vx+(p.wy-a.wy)*vy)/(vx*vx+vy*vy)))
            local q=R.World(net.data,p.zone,a.x+t*(b.x-a.x),a.y+t*(b.y-a.y),net.frames)
            local d=distance(p,q)
            if not best or d<best.distance then best={point=q,edge=edge,t=t,distance=d} end
        end
    end
    return best
end

function R.Route(net,start,goal,opts)
    opts=opts or {}; local blocked=opts.blocked or {}
    local startWorld=R.World(net.data,start.zone,start.x,start.y,net.frames)
    local goalWorld=R.World(net.data,goal.zone,goal.x,goal.y,net.frames)
    if startWorld.continent~=goalWorld.continent then
        return {status="needs-transport",message="Destination is on another continent. Boats, zeppelins and other transport are not mapped yet."}
    end
    local from,to=R.Project(net,start,blocked),R.Project(net,goal,blocked)
    if not from or not to then return {status="unmapped",message="No mapped roads for that location."} end
    local limit=opts.maxApproach
    if limit and (from.distance>limit or to.distance>limit) then
        return {status="too-far",message=string.format("A pin is %.0f yd from mapped roads (limit %d yd).",max(from.distance,to.distance),limit),from=from,to=to}
    end
    -- The immutable graph is shared. Only the two projected endpoint nodes
    -- and their small adjacency lists belong to this query.
    local nodes=setmetatable({}, {__index=net.nodes})
    local extras={};local nextNode=#net.nodes
    local function connect(a,b,edge,length)
        local copy={}; for k,v in pairs(edge) do copy[k]=v end
        copy.a,copy.b,copy.length=a,b,length
        extras[a]=extras[a] or {};extras[b]=extras[b] or {}
        table.insert(extras[a],{to=b,edge=copy});table.insert(extras[b],{to=a,edge=copy})
    end
    local function endpoint(p)
        if p.t<=1e-7 then return p.edge.a end
        if p.t>=1-1e-7 then return p.edge.b end
        nextNode=nextNode+1;local id=nextNode;nodes[id]=p.point
        connect(id,p.edge.a,p.edge,p.edge.length*p.t); connect(id,p.edge.b,p.edge,p.edge.length*(1-p.t))
        return id
    end
    local s,g=endpoint(from),endpoint(to)
    if from.edge.id==to.edge.id and s~=g then connect(s,g,from.edge,from.edge.length*abs(to.t-from.t)) end
    local function heuristic(id) return opts.dijkstra and 0 or distance(nodes[id],nodes[g]) end
    local heap={}
    local function push(v)
        local i=#heap+1
        while i>1 do local p=math.floor(i/2); if heap[p].f<=v.f then break end; heap[i]=heap[p]; i=p end
        heap[i]=v
    end
    local function pop()
        local first,last=heap[1],table.remove(heap)
        if #heap==0 then return first end
        local i=1
        while i*2<=#heap do
            local c=i*2; if c+1<=#heap and heap[c+1].f<heap[c].f then c=c+1 end
            if last.f<=heap[c].f then break end; heap[i]=heap[c]; i=c
        end
        heap[i]=last; return first
    end
    local scores,previous,closed={[s]=0},{},{}
    local expanded=0; push({id=s,g=0,f=heuristic(s)})
    while #heap>0 do
        local current=pop(); local u=current.id
        if not closed[u] and current.g<=scores[u]+1e-7 then
            closed[u]=true; expanded=expanded+1
            if u==g then break end
            local base,extra=net.adj[u] or {},extras[u] or {}
            for i=1,#base+#extra do
                local entry=i<=#base and base[i] or extra[i-#base]
                local e,v=entry.edge,entry.to
                if not blocked[e.id] then
                    local cost=e.length*(opts.preferRoads and (e.kind=="trail" or e.kind=="estimated") and 1.45 or 1)
                    local nextScore=current.g+cost
                    if nextScore+1e-7<(scores[v] or math.huge) then
                        scores[v]=nextScore;previous[v]={id=u,edge=e}
                        push({id=v,g=nextScore,f=nextScore+heuristic(v)})
                    end
                end
            end
        end
    end
    if not closed[g] then return {status="disconnected",message="No connected road route to this destination.",expanded=expanded} end
    local segments={}; local cur=g
    while cur~=s do
        local p=previous[cur]; local e=p.edge
        table.insert(segments,1,{from=nodes[p.id],to=nodes[cur],length=e.length,kind=e.kind,name=e.name,id=e.id,roadId=e.roadId})
        cur=p.id
    end
    if from.distance>1e-7 then table.insert(segments,1,{from=startWorld,to=from.point,length=from.distance,kind="approach",name="Estimated road approach"}) end
    if to.distance>1e-7 then table.insert(segments,{from=to.point,to=goalWorld,length=to.distance,kind="approach",name="Estimated destination approach"}) end
    local total,estimated=0,from.distance+to.distance
    for _,e in ipairs(segments) do
        e.begin=total; total=total+e.length; e.finish=total
        if e.kind=="estimated" then estimated=estimated+e.length end
    end
    local approach=max(from.distance,to.distance)
    return {status="ok",segments=segments,distance=total,estimated=estimated,weightedCost=scores[g],expanded=expanded,
        approachDistance=approach,warning=approach>200 and string.format("Estimated off-road approach: %.0f yd. Check terrain along gold dashes.",approach) or nil}
end

function R.Progress(route,p,previous)
    local best; previous=previous or 0
    local lo,hi=1,#route.segments
    while lo<=hi do local mid=math.floor((lo+hi)/2);if route.segments[mid].finish<previous-25 then lo=mid+1 else hi=mid-1 end end
    for i=lo,#route.segments do
        local s=route.segments[i]
        if s.begin>previous+400 then break end
        if s.kind~="border" then
            local dx,dy=s.to.wx-s.from.wx,s.to.wy-s.from.wy
            local dz=p.z and s.from.z and s.to.z and (s.to.z-s.from.z) or 0
            local t=max(0,min(1,((p.wx-s.from.wx)*dx+(p.wy-s.from.wy)*dy+(dz~=0 and (p.z-s.from.z)*dz or 0))/max(dx*dx+dy*dy+dz*dz,1e-8)))
            local q={wx=s.from.wx+t*dx,wy=s.from.wy+t*dy,z=p.z and s.from.z and s.to.z and (s.from.z+t*dz) or nil}
            local d=distance(p,q)
            if not best or d<best.distance then best={distance=d,progress=s.begin+t*s.length,index=i} end
        end
    end
    return best
end

function R.LookAhead(route,progress,yards)
    local wanted=min(route.distance,progress+(yards or 35))
    local lo,hi=1,#route.segments
    while lo<=hi do local mid=math.floor((lo+hi)/2);if route.segments[mid].finish<wanted then lo=mid+1 else hi=mid-1 end end
    local s=route.segments[lo]
    if s then
        local t=s.length>1e-7 and (wanted-s.begin)/s.length or 1
        return {wx=s.from.wx+t*(s.to.wx-s.from.wx),wy=s.from.wy+t*(s.to.wy-s.from.wy)},s
    end
end
