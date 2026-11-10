local _, A = ...
local mapLayer,mapHost,miniLayer
local lines,miniLines={},{}
local beads,miniBeads={},{}
local rideBeads,miniRideBeads={},{}
local stepMarkers,miniStepMarkers={},{}
local mapCache,miniCache={},{}
local mapGeometry,miniGeometry={},{}
local beadSize,beadSpacing=7,10
local beadTexture="Interface\\AddOns\\ForeverRoads\\Media\\GoldBead.tga"
local stepTextureRoot="Interface\\AddOns\\ForeverRoads\\Media\\Step"
local stepIcons={walk="Run",flight="Flight",boat="Boat",zeppelin="Zeppelin",tram="Tram",portal="Portal",skycutter="Skycutter"}
local minimapStepIcons={flight=true,boat=true,zeppelin=true,skycutter=true}

local function stepTexture(kind,name)
    if kind=="zeppelin" and name and name:find("skycutter",1,true) then kind="skycutter" end
    return stepTextureRoot..(stepIcons[kind] or "Transport")..".tga"
end

local function stepPrefix(kind,name)
    return "|T"..stepTexture(kind,name)..":14:14|t "
end

local function mix(a,b,t)
    return {wx=a.wx+(b.wx-a.wx)*t,wy=a.wy+(b.wy-a.wy)*t,
        z=a.z and b.z and (a.z+(b.z-a.z)*t) or nil,continent=a.continent}
end
local function solid(s)
    return s.kind=="terrain" or s.kind=="road" or s.kind=="trail"
end
-- Round only the display polyline. The original route still supplies navigation,
-- distances and terrain decisions. Scale measures visible pixels per world yard.
-- Each curve stays inside maxDeviation pixels of its original two segments.
function A.SmoothRouteSegments(route,scaleX,scaleY,maxRadius,maxDeviation)
    local source=route.segments;local corners={};local rounded=0
    for i=1,#source-1 do
        local a,b=source[i],source[i+1]
        if solid(a) and solid(b) and a.kind==b.kind and a.from.continent==a.to.continent and
            b.from.continent==b.to.continent and a.to.continent==b.from.continent and math.abs(a.finish-b.begin)<.001 and
            math.abs(a.to.wx-b.from.wx)<.001 and math.abs(a.to.wy-b.from.wy)<.001 and
            (not a.to.z or not b.from.z or math.abs(a.to.z-b.from.z)<.001) then
            local ux,uy=(a.to.wx-a.from.wx)*scaleX,(a.to.wy-a.from.wy)*scaleY
            local vx,vy=(b.to.wx-b.from.wx)*scaleX,(b.to.wy-b.from.wy)*scaleY
            local before,after=math.sqrt(ux*ux+uy*uy),math.sqrt(vx*vx+vy*vy)
            if before>.01 and after>.01 then
                local cosine=math.max(-1,math.min(1,(ux*vx+uy*vy)/(before*after)))
                -- Preserve reversals and tiny bends; never create a looping spline.
                if cosine>-.8 and cosine<.9997 then
                    local sine=math.sqrt(math.max(0,1-cosine*cosine))
                    local radius=math.min(maxRadius,before*.35,after*.35,4*maxDeviation/math.max(sine,1e-8))
                    if radius>=.6 then
                        local t1,t2=radius/before,radius/after
                        local curvature=radius*math.sqrt((1-cosine)/2)
                        corners[i]={entry=mix(a.to,a.from,t1),exit=mix(b.from,b.to,t2),control=a.to,
                            first=a.finish-a.length*t1,last=b.begin+b.length*t2,
                            steps=curvature>2.8 and 4 or 2}
                        rounded=rounded+1
                    end
                end
            end
        end
    end
    local result={}
    local function append(a,b,first,last,s,roundStart,roundEnd)
        if (a.wx-b.wx)^2+(a.wy-b.wy)^2<1e-12 and (not a.z or not b.z or math.abs(a.z-b.z)<1e-6) then return end
        result[#result+1]={from=a,to=b,begin=first,finish=last,length=last-first,kind=s.kind,name=s.name,
            minWX=math.min(a.wx,b.wx),maxWX=math.max(a.wx,b.wx),minWY=math.min(a.wy,b.wy),maxWY=math.max(a.wy,b.wy),
            roundStart=roundStart,roundEnd=roundEnd}
    end
    for i,s in ipairs(source) do
        local previous,corner=corners[i-1],corners[i]
        append(previous and previous.exit or s.from,corner and corner.entry or s.to,
            previous and previous.last or s.begin,corner and corner.first or s.finish,s,previous~=nil,corner~=nil)
        if corner then
            local a,b,c=corner.entry,corner.control,corner.exit;local last=a
            for j=1,corner.steps do
                local t=j/corner.steps;local u=1-t
                local point=j==corner.steps and c or {wx=u*u*a.wx+2*u*t*b.wx+t*t*c.wx,
                    wy=u*u*a.wy+2*u*t*b.wy+t*t*c.wy,
                    z=a.z and b.z and c.z and (u*u*a.z+2*u*t*b.z+t*t*c.z) or nil,continent=a.continent}
                append(last,point,corner.first+(corner.last-corner.first)*(j-1)/corner.steps,
                    corner.first+(corner.last-corner.first)*t,s,true,true)
                last=point
            end
        end
    end
    -- Butt-ended line quads leave tiny wedges between curve chords. A cached,
    -- angle-sized overlap closes these seams without adding textures or frames.
    for i=1,#result-1 do
        local a,b=result[i],result[i+1]
        if a.roundEnd and b.roundStart then
            local ux,uy=(a.to.wx-a.from.wx)*scaleX,(a.to.wy-a.from.wy)*scaleY
            local vx,vy=(b.to.wx-b.from.wx)*scaleX,(b.to.wy-b.from.wy)*scaleY
            local product=math.sqrt((ux*ux+uy*uy)*(vx*vx+vy*vy))
            if product>1e-12 then
                local cosine=math.max(-1,math.min(1,(ux*vx+uy*vy)/product))
                local cap=math.min(.7,.5*math.sqrt(math.max(0,1-cosine)/math.max(1e-8,1+cosine)))
                a.capEnd=cap;b.capStart=cap
            end
        end
    end
    return result,rounded
end
local function geometry(cache,route,sx,sy,radius,deviation)
    if cache.route~=route or cache.sx~=sx or cache.sy~=sy then
        cache.route,cache.sx,cache.sy=route,sx,sy
        cache.segments,cache.corners=A.SmoothRouteSegments(route,sx,sy,radius,deviation)
        -- Cache arc length, not individual dots. Clipping selects the visible
        -- samples without rephasing the trail when the player or map moves.
        local previous,distance=nil,0
        for _,s in ipairs(cache.segments) do
            if solid(s) and s.from.continent==s.to.continent then
                if not previous or previous.to.continent~=s.from.continent or math.abs(previous.finish-s.begin)>.001 or
                    math.abs(previous.to.wx-s.from.wx)>.001 or math.abs(previous.to.wy-s.from.wy)>.001 or
                    (previous.to.z and s.from.z and math.abs(previous.to.z-s.from.z)>.001) then distance=0 end
                local x,y=(s.to.wx-s.from.wx)*sx,(s.to.wy-s.from.wy)*sy
                s.beadLength=math.sqrt(x*x+y*y);s.beadBegin=distance
                distance=distance+s.beadLength;previous=s
            else previous=nil end
        end
        A.perf=A.perf or {};A.perf.smoothingBuilds=(A.perf.smoothingBuilds or 0)+1
    end
    return cache.segments
end

local function shown(frame,want)
    if want then if not frame:IsShown() then frame:Show() end
    elseif frame:IsShown() then frame:Hide() end
end
local function line(pool,owner,index,x1,y1,x2,y2,color,width,outline,capStart,capEnd)
    if capStart or capEnd then
        local dx,dy=x2-x1,y2-y1;local length=math.sqrt(dx*dx+dy*dy)
        if length>1e-8 then
            local a,b=width*(capStart or 0)/length,width*(capEnd or 0)/length
            x1,y1,x2,y2=x1-dx*a,y1-dy*a,x2+dx*b,y2+dy*b
        end
    end
    local l=pool[index]
    if not l then l=owner:CreateLine(nil,"OVERLAY"); pool[index]=l; l.fr={} end
    local old=l.fr
    if old.outline~=outline or not old.layerSet then
        l:SetDrawLayer(outline and "ARTWORK" or "OVERLAY",outline and 0 or 7); old.outline=outline;old.layerSet=true
    end
    local alpha=color[4] or 1
    if old.r~=color[1] or old.g~=color[2] or old.b~=color[3] or old.a~=alpha then
        l:SetColorTexture(color[1],color[2],color[3],alpha);old.r,old.g,old.b,old.a=color[1],color[2],color[3],alpha
    end
    if old.width~=width then l:SetThickness(width);old.width=width end
    if old.x1~=x1 or old.y1~=y1 then l:SetStartPoint("TOPLEFT",owner,x1,y1);old.x1,old.y1=x1,y1 end
    if old.x2~=x2 or old.y2~=y2 then l:SetEndPoint("TOPLEFT",owner,x2,y2);old.x2,old.y2=x2,y2 end
    shown(l,true)
end
local function hideRest(pool,first)
    for i=first,pool.used or #pool do shown(pool[i],false) end
    pool.used=first-1
end
local function drawBead(pool,owner,index,size,x,y,ride)
    local dot=pool[index]
    if not dot then
        dot=owner:CreateTexture(nil,"OVERLAY",nil,ride and 3 or 2)
        dot:SetTexture(beadTexture);dot.fr={};pool[index]=dot
        if ride then
            dot:SetDesaturated(true)
            dot:SetVertexColor(.61,.86,1)
        end
    end
    local old=dot.fr
    if old.size~=size then dot:SetSize(size,size);old.size=size end
    if old.x~=x or old.y~=y then
        dot:ClearAllPoints();dot:SetPoint("CENTER",owner,"TOPLEFT",x,y);old.x,old.y=x,y
    end
    shown(dot,true)
end
local function drawBeads(pool,owner,used,s,size,x1,y1,x2,y2,lo,hi,ride)
    local first,length=s.beadBegin,s.beadLength
    if not lo or length<1e-8 then return used end
    local start=math.ceil((first+lo*length-1e-7)/beadSpacing)
    local finish=math.min(math.floor((first+hi*length+1e-7)/beadSpacing),
        math.ceil((first+length-1e-7)/beadSpacing)-1)
    for i=start,finish do
        local t=(i*beadSpacing-first)/length
        used=used+1
        drawBead(pool,owner,used,size,x1+(x2-x1)*t,y1+(y2-y1)*t,ride)
    end
    return used
end

local function drawRide(pool,owner,used,size,scale,x1,y1,x2,y2,lo,hi)
    if not lo then return used end
    local dx,dy=x2-x1,y2-y1
    local length=math.sqrt(dx*dx+dy*dy)*scale
    local count=drawBeads(pool,owner,used,{beadBegin=0,beadLength=length},size,x1,y1,x2,y2,lo,hi,true)
    if count==used then
        local middle=(lo+hi)/2
        drawBead(pool,owner,used+1,size,x1+dx*middle,y1+dy*middle,true)
        return used+1
    end
    return count
end
local function clipAxis(origin,delta,low,high,lo,hi)
    if low>high then return end
    if math.abs(delta)<1e-10 then
        if origin>=low and origin<=high then return lo,hi end
        return
    end
    local a,b=(low-origin)/delta,(high-origin)/delta
    if a>b then a,b=b,a end
    lo,hi=math.max(lo,a),math.min(hi,b)
    if lo<=hi then return lo,hi end
end
local function rectClip(x1,y1,x2,y2,insetX,insetY,left,top,right,bottom)
    local dx,dy=x2-x1,y2-y1
    local lo,hi=clipAxis(x1,dx,math.max(insetX or 0,left or 0),math.min(1-(insetX or 0),right or 1),0,1)
    if lo then lo,hi=clipAxis(y1,dy,math.max(insetY or 0,top or 0),math.min(1-(insetY or 0),bottom or 1),lo,hi) end
    if not lo then return end
    return x1+lo*dx,y1+lo*dy,x1+hi*dx,y1+hi*dy,lo,hi
end
A.RectClip=rectClip

local function visibleMapBounds(viewport,canvas)
    if not viewport.GetRect or not canvas.GetRect then return 0,0,1,1 end
    local x,y,w,h=canvas:GetRect()
    local left,bottom,width,height=viewport:GetRect()
    if not x or not y or not w or not h or not left or not bottom or not width or not height or w<=0 or h<=0 then
        return 0,0,1,1
    end
    local scale=canvas:GetEffectiveScale()
    local ratio=viewport:GetEffectiveScale()/scale
    -- Round out to screen-space blocks so short pans can reuse the same dots.
    local block=32/scale
    local function bounds(low,high,origin,size)
        return math.max(0,(math.floor((low-origin)/block)-1)*block/size),
            math.min(1,(math.ceil((high-origin)/block)+1)*block/size)
    end
    local x1,x2=bounds(left*ratio,(left+width)*ratio,x,w)
    local y1,y2=bounds(bottom*ratio,(bottom+height)*ratio,y,h)
    return x1,1-y2,x2,1-y1
end

local function frameFor(zone)
    local f=A.network.frames[zone]; if f then return f end
    local map,a=C_Map.GetWorldPosFromMapPos(zone,CreateVector2D(0,0))
    local other,b=C_Map.GetWorldPosFromMapPos(zone,CreateVector2D(1,1))
    if not A.Public(map) or not A.Public(other) or map==nil or map~=other or not a or not b then return end
    local x0,y0=a:GetXY(); local x1,y1=b:GetXY()
    if A.Number(x0) and A.Number(y0) and A.Number(x1) and A.Number(y1) and x0~=x1 and y0~=y1 then
        return {wx=-y0,wy=-x0,dx=y0-y1,dy=x0-x1,continent=map}
    end
end
local function onMap(point,frame) return (point.wx-frame.wx)/frame.dx,(point.wy-frame.wy)/frame.dy end

local worldMapID=947
-- The two UiMapAssignment rectangles for Azeroth in the Forever client (build 70862).
-- World axes here are west and north negated, matching Router.World.
local worldFrames={
    [0]={wx=-8000,wy=-6933.2998,dx=15466.7002,dy=22933.2998,left=.5505,right=.8966,top=.0994,bottom=.8691},
    [1]={wx=-6933.2998,wy=-12266.7002,dx=16533.2998,dy=25066.7002,left=.0399,right=.4083,top=.0855,bottom=.9234},
}
local islandLink
local function worldFrame(continent)
    if continent~=2991 or worldFrames[continent] then return worldFrames[continent] end
    local islandMap=2521
    local frame=frameFor(islandMap)
    if frame and C_Map.GetMapRectOnMap then
        local l,r,t,b=C_Map.GetMapRectOnMap(islandMap,worldMapID)
        if A.Number(l) and A.Number(r) and A.Number(t) and A.Number(b) and r>l and b>t then
            worldFrames[continent]={wx=frame.wx,wy=frame.wy,dx=frame.dx,dy=frame.dy,left=l,right=r,top=t,bottom=b}
        end
    end
    return worldFrames[continent]
end

local function worldPosition(point)
    local f=worldFrame(point.continent)
    if f then
        local x,y=onMap(point,f)
        return {wx=f.left+x*(f.right-f.left),wy=f.top+y*(f.bottom-f.top)}
    end
    if point.continent==2991 and C_Map.GetMapLinksForMap then
        if islandLink==nil then
            islandLink=false
            for _,link in ipairs(C_Map.GetMapLinksForMap(worldMapID) or {}) do
                if link.linkedUiMapID==2521 or link.linkedUiMapID==2665 then
                    local x,y=link.position:GetXY()
                    if A.Number(x) and A.Number(y) then islandLink={wx=x,wy=y};break end
                end
            end
        end
        return islandLink or nil
    end
end

local function ridePoints(leg,continent)
    local a,b=leg.from,leg.to
    if continent and a.map~=continent and b.map~=continent then return end
    local from={wx=-a.y,wy=-a.x,continent=a.map}
    local to={wx=-b.y,wy=-b.x,continent=b.map}
    if not continent then
        local x,y=worldPosition(from),worldPosition(to)
        return x or y,y or x
    end
    if a.map==b.map then return from,to end

    local frame=worldFrame(continent)
    local localPoint=a.map==continent and from or to
    local foreign=worldPosition(a.map==continent and to or from)
    if not frame or not foreign then return localPoint,localPoint end
    local projected={wx=frame.wx+(foreign.wx-frame.left)/(frame.right-frame.left)*frame.dx,
        wy=frame.wy+(foreign.wy-frame.top)/(frame.bottom-frame.top)*frame.dy}
    if a.map==continent then return from,projected end
    return projected,to
end

local function addStepIcon(groups,x,y,texture,scale)
    for _,group in ipairs(groups) do
        if math.abs(x-group.x)*scale<22 and math.abs(y-group.y)*scale<18 then
            for _,icon in ipairs(group.icons) do if icon==texture then return end end
            group.icons[#group.icons+1]=texture
            return
        end
    end
    groups[#groups+1]={x=x,y=y,icons={texture}}
end

local function onwardRide()
    if not A.db.goal then return end
    if A.wasOnTaxi and A.taxi and A.taxi.onward and A.taxi.goal==A.db.goal then return A.taxi end
    local crossing=A.crossing
    if crossing and crossing.onward and crossing.goal==A.db.goal then return crossing.leg end
end

local function visitStepEnds(journey,add,minimap)
    local ride=not minimap and onwardRide()
    if ride then
        add({wx=-ride.to.y,wy=-ride.to.x,continent=ride.to.map},stepTexture(ride.kind,ride.name))
    end
    if journey then
        for _,leg in ipairs(A.Transit.DisplayLegs(journey)) do
            if not minimap or minimapStepIcons[leg.kind] then
                local point=leg.to
                add({wx=-point.y,wy=-point.x,continent=point.map},stepTexture(leg.kind,leg.name))
            end
        end
    elseif not minimap and not A.arrived and A.route and A.route.status=="ok" then
        local last=A.route.segments[#A.route.segments]
        if last then add(last.to,stepTexture("walk")) end
    end
end

local function drawStepMarker(pool,owner,index,group,scale,w,h,radius)
    local anchor=pool[index]
    if not anchor then
        anchor=CreateFrame("Frame",nil,owner)
        anchor:SetSize(1,1)
        anchor:EnableMouse(false)
        local badge=CreateFrame("Frame",nil,anchor,"BackdropTemplate")
        badge:EnableMouse(false)
        badge:SetBackdrop({bgFile="Interface/Buttons/WHITE8X8",edgeFile="Interface/Tooltips/UI-Tooltip-Border",
            edgeSize=8,insets={left=2,right=2,top=2,bottom=2}})
        badge:SetBackdropColor(.06,.09,.09,.97)
        badge.icons={}
        anchor.badge=badge
        pool[index]=anchor
    end
    local x,y=group.x,group.y
    anchor:ClearAllPoints()
    anchor:SetPoint("CENTER",owner,"TOPLEFT",x,y)
    local badge=anchor.badge
    badge:SetFrameLevel(owner:GetFrameLevel()+2)
    badge:SetScale(1/scale)
    for i,texture in ipairs(group.icons) do
        local icon=badge.icons[i]
        if not icon then
            icon=badge:CreateTexture(nil,"OVERLAY")
            icon:SetSize(16,16)
            icon:SetPoint("LEFT",badge,"LEFT",3+(i-1)*17,0)
            badge.icons[i]=icon
        end
        if icon.frTexture~=texture then icon:SetTexture(texture);icon.frTexture=texture end
        shown(icon,true)
    end
    hideRest(badge.icons,#group.icons+1)
    local width=5+#group.icons*17
    badge:SetSize(width,21)
    badge:ClearAllPoints()
    if radius then
        local px,py=x-w/2,y+h/2
        local cx,cy=px,py+14
        local limit=math.max(0,radius-math.sqrt(width^2+21^2)/2)
        local distance=math.sqrt(cx*cx+cy*cy)
        if distance>limit then cx,cy=cx*limit/distance,cy*limit/distance end
        badge:SetPoint("CENTER",anchor,"CENTER",cx-px,cy-py)
    else
        local offset=math.max(width/2-x*scale,math.min(0,(w-x)*scale-width/2))
        if -y*scale>=26 then badge:SetPoint("BOTTOM",anchor,"CENTER",offset,4)
        else badge:SetPoint("TOP",anchor,"CENTER",offset,-4) end
    end
    shown(anchor,true)
end

local function drawStepMarkers(frame,journey,w,h,scale,left,top,right,bottom)
    local groups={}
    visitStepEnds(journey,function(point,texture)
        local x,y
        if frame then
            if point.continent~=frame.continent then return end
            x,y=onMap(point,frame)
        else
            local projected=worldPosition(point)
            if not projected then return end
            x,y=projected.wx,projected.wy
        end
        if x<left or x>right or y<top or y>bottom then return end
        addStepIcon(groups,x*w,-y*h,texture,scale)
    end)
    for i,group in ipairs(groups) do drawStepMarker(stepMarkers,mapLayer,i,group,scale,w,h) end
    hideRest(stepMarkers,#groups+1)
end

-- Exploration art lives on map pins around frame level 2000, independently
-- of the canvas. Read the native level manager; never register or edit pins.
local function refreshMapLevel()
    local level=mapHost:GetCanvas():GetFrameLevel()+1
    local manager=mapHost.GetPinFrameLevelsManager and mapHost:GetPinFrameLevelsManager()
    if manager and manager.GetValidFrameLevel then
        local exploration=manager:GetValidFrameLevel("PIN_FRAME_LEVEL_MAP_EXPLORATION")
        local route=manager:GetValidFrameLevel("PIN_FRAME_LEVEL_QUEST_BLOB")
        if A.Number(exploration) then level=math.max(level,exploration+1) end
        if A.Number(route) then level=math.max(level,route) end
    else level=math.max(level,2100) end
    if A.mapLayerLevel~=level then mapLayer:SetFrameLevel(level); A.mapLayerLevel=level end
end

local function formatETA(seconds)
    seconds=math.ceil(math.max(0,seconds))
    if seconds<60 then return string.format("~%ds",seconds) end
    return string.format("~%dm %ds",math.floor(seconds/60),seconds%60)
end

local function guideText(maxSteps)
    local journey,route=A.journey,A.route
    local walking=route and route.status=="ok"
    local ride=onwardRide()
    local crossing=A.crossing
    local currentCrossing=crossing and not crossing.onward and crossing.goal==A.db.goal and journey and
        journey.legs[journey.index]==crossing.leg and crossing.leg
    local suffix=(currentCrossing or (ride and ride.kind~="flight")) and " after docking" or ride and " after landing" or ""
    local rideStep=ride and (stepPrefix(ride.kind,ride.name)..(ride.kind=="flight" and "In flight to " or "On board to ")..ride.to.name)
    if not journey and not walking then return "",A.status or "Finding a route…" end
    if A.arrived then return "","Destination reached" end

    local seconds=0
    local instruction
    if walking then
        local progress=A.progress or 0
        local fraction=route.distance>0 and math.max(0,1-progress/route.distance) or 0
        seconds=(route.weightedCost or route.distance)*fraction/(A.Transit and A.Transit.walkSpeed or 7)
        local _,segment=A.Router.LookAhead(route,progress,35)
        if segment and segment.kind=="lift" then instruction=segment.name end
    end
    if not journey then
        local step=stepPrefix("walk")..(instruction or ("Run to "..A.db.goal.label))
        if rideStep then step=rideStep.."\n"..step end
        return formatETA(seconds)..suffix,step
    end

    local steps={}
    if rideStep then steps[1]=rideStep end
    local display=A.Transit.DisplayLegs(journey)
    for i,leg in ipairs(display) do
        if leg~=currentCrossing and (i~=1 or not walking or leg.kind~="walk") then seconds=seconds+leg.seconds end
        if #steps<maxSteps then
            local label
            if leg.kind=="walk" then label="Run to "..(leg.to.name or A.db.goal.label)
            elseif leg.kind=="flight" then label="Catch flight to "..leg.to.name
            else label=A.Transit.Label(leg) end
            if i==1 then
                if instruction then label=instruction
                elseif leg.kind=="flight" and A.wasOnTaxi and not ride then label="In flight to "..leg.to.name
                elseif leg==currentCrossing and crossing.departed then label="On board to "..leg.to.name
                elseif leg.from.towerApproach and leg.kind~="walk" then label="Climb the tower and board: "..label end
                label="|cffffcf77"..label.."|r"
            end
            steps[#steps+1]=stepPrefix(leg.kind,leg.name)..label
        end
    end
    local hidden=#display-#steps+(ride and 1 or 0)
    if hidden>0 then steps[#steps+1]="+"..hidden..(hidden==1 and " more step" or " more steps") end
    return formatETA(seconds)..suffix,table.concat(steps,"\n")
end

local function drawMapGuide()
    local guide=A.mapGuide
    if not A.db.goal then
        if guide then shown(guide,false) end
        return
    end
    -- Anchor to the viewport so the instructions stay put while the canvas pans or zooms.
    local viewport=mapHost.ScrollContainer
    local width=math.min(300,viewport:GetWidth()-40)
    if width<60 then
        if guide then shown(guide,false) end
        return
    end
    if not guide then
        guide=CreateFrame("Frame",nil,viewport,"BackdropTemplate")
        guide:SetPoint("TOPLEFT",viewport,"TOPLEFT",20,-20)
        guide:EnableMouse(false)
        guide:SetBackdrop({bgFile="Interface/Tooltips/UI-Tooltip-Background",edgeFile="Interface/Tooltips/UI-Tooltip-Border",
            edgeSize=12,insets={left=3,right=3,top=3,bottom=3}})
        guide:SetBackdropColor(.035,.045,.04,.90)
        guide.eta=guide:CreateFontString(nil,"OVERLAY","GameFontNormalLarge")
        guide.eta:SetPoint("TOPLEFT",12,-10)
        guide.steps=guide:CreateFontString(nil,"OVERLAY","GameFontHighlightSmall")
        guide.steps:SetJustifyH("LEFT")
        A.mapGuide=guide
    end
    local level=math.max(viewport:GetFrameLevel(),A.mapLayerLevel)+12
    if guide:GetFrameLevel()~=level then guide:SetFrameLevel(level) end
    local maxSteps=math.max(1,math.min(8,math.floor((viewport:GetHeight()-74)/26)))
    local eta,steps=guideText(maxSteps)
    local changed=guide.stepText~=steps or guide:GetWidth()~=width or (eta=="")~=(guide.etaText=="")
    if guide.etaText~=eta then
        guide.eta:SetText(eta)
        guide.etaText=eta
    end
    if changed then
        local top=eta=="" and 10 or 31
        guide:SetWidth(width)
        guide.steps:SetWidth(width-24)
        guide.steps:ClearAllPoints()
        guide.steps:SetPoint("TOPLEFT",12,-top)
        guide.steps:SetText(steps)
        guide.stepText=steps
        guide:SetHeight(top+guide.steps:GetStringHeight()+10)
    end
    shown(guide,true)
end

function A.AttachMap()
    if mapHost or not WorldMapFrame or not WorldMapFrame.ScrollContainer then return end
    mapHost=WorldMapFrame
    local canvas=mapHost:GetCanvas()
    if not canvas then mapHost=nil; return end
    mapLayer=CreateFrame("Frame",nil,canvas)
    mapLayer:SetAllPoints(canvas); refreshMapLevel()
    mapLayer:EnableMouse(false)
    if mapLayer.SetClipsChildren then mapLayer:SetClipsChildren(true) end
    mapLayer.goal=mapLayer:CreateTexture(nil,"OVERLAY",nil,7)
    mapLayer.goal:SetTexture("Interface/GossipFrame/AvailableQuestIcon")
    mapHost:HookScript("OnHide",function()
        shown(mapLayer,false);mapCache.valid=false;A.mapLineCount=0
        if A.mapGuide then shown(A.mapGuide,false) end
        if A.StopWalkPreview then A.StopWalkPreview(true) end
    end)
    mapHost.ScrollContainer:HookScript("OnMouseUp",function(_,button)
        if button~="LeftButton" or not IsAltKeyDown() or InCombatLockdown() then return end
        local active=(ChatFrameUtil and ChatFrameUtil.GetActiveWindow) or ChatEdit_GetActiveWindow
        if active and active() then return end
        local zone=mapHost:GetMapID()
        local x,y=mapHost:GetNormalizedCursorPosition()
        if A.ValidDestination(zone,x,y) then
            A.SetDestination({zone=zone,x=x*A.Data.width,y=y*A.Data.height,label="Map destination",source="map"},true)
            A.Tick(); A.Print("Road route selected. /froads follow returns to tracked quests.")
        else A.Print("Alt-click a point on a zone map.") end
    end)
end

function A.DrawMap()
    A.AttachMap()
    if not mapLayer then return end
    if not mapHost:IsShown() or not A.db.showMap or not A.db.enabled then
        shown(mapLayer,false);mapCache.valid=false;A.mapLineCount=0
        if A.mapGuide then shown(A.mapGuide,false) end
        if A.StopWalkPreview then A.StopWalkPreview(true) end
        return
    end
    refreshMapLevel()
    drawMapGuide()
    local zone=mapHost:GetMapID()
    if not A.Number(zone) then
        mapLayer:Hide()
        if A.StopWalkPreview then A.StopWalkPreview(true) end
        return
    end
    local f=zone~=worldMapID and frameFor(zone) or nil
    if not f and zone~=worldMapID then
        mapLayer:Hide()
        if A.StopWalkPreview then A.StopWalkPreview(true) end
        return
    end
    local w,h=mapLayer:GetWidth(),mapLayer:GetHeight()
    if w<=0 or h<=0 then return end
    shown(mapLayer,true)
    local scale=mapHost:GetCanvasScale() or 1
    local left,top,right,bottom=visibleMapBounds(mapHost.ScrollContainer,mapHost:GetCanvas())
    local journey=not A.arrived and A.journey or nil
    local ride=onwardRide()
    local index=journey and journey.index
    local previewRevision=journey and journey.previewRevision
    if A.PreviewWalks then A.PreviewWalks(journey,f and f.continent) end
    if mapCache.valid and mapCache.zone==zone and mapCache.route==A.route and mapCache.goal==A.db.goal and
        mapCache.journey==journey and mapCache.ride==ride and mapCache.index==index and mapCache.previewRevision==previewRevision and mapCache.arrived==A.arrived and
        mapCache.w==w and mapCache.h==h and mapCache.scale==scale and mapCache.roads==A.db.showRoads and
        mapCache.left==left and mapCache.top==top and mapCache.right==right and mapCache.bottom==bottom and
        mapCache.network==A.network and mapCache.edges==#A.network.edges then return end
    mapCache={valid=true,zone=zone,route=A.route,goal=A.db.goal,w=w,h=h,scale=scale,roads=A.db.showRoads,network=A.network,
        edges=#A.network.edges,left=left,top=top,right=right,bottom=bottom,journey=journey,ride=ride,index=index,
        previewRevision=previewRevision,arrived=A.arrived}
    A.perf=A.perf or {};A.perf.mapRedraws=(A.perf.mapRedraws or 0)+1
    local used,dots=0,0
    local function segment(frame,a,b,color,width,dashed,outline,capStart,capEnd)
        if a.continent~=frame.continent or b.continent~=frame.continent then return end
        local x1,y1=onMap(a,frame); local x2,y2=onMap(b,frame)
        local oldX1,oldY1,oldX2,oldY2=x1,y1,x2,y2
        x1,y1,x2,y2=rectClip(x1,y1,x2,y2,nil,nil,left,top,right,bottom)
        if not x1 then return end
        if math.abs(x1-oldX1)>1e-9 or math.abs(y1-oldY1)>1e-9 then capStart=nil end
        if math.abs(x2-oldX2)>1e-9 or math.abs(y2-oldY2)>1e-9 then capEnd=nil end
        local count=dashed and math.max(1,math.ceil(math.sqrt(((x2-x1)*w)^2+((y2-y1)*h)^2)/8)) or 1
        for i=0,count-1 do
            local t1=i/count; local t2=dashed and (i+0.55)/count or 1
            used=used+1; line(lines,mapLayer,used,(x1+(x2-x1)*t1)*w,-(y1+(y2-y1)*t1)*h,
                (x1+(x2-x1)*t2)*w,-(y1+(y2-y1)*t2)*h,color,width/scale,outline,capStart,capEnd)
        end
    end
    if f and A.db.showRoads then
        for _,e in ipairs(A.network.edges) do if e.kind~="border" then segment(f,A.network.nodes[e.a],A.network.nodes[e.b],{0.9,0.72,0.35,0.6},1.5) end end
    end
    local function drawWalking(route,cache)
        local first=route.segments[1]
        if not first then return end
        local continent=first.from.continent
        local frame=f
        if frame and frame.continent~=continent then return end
        if not frame then
            local world=worldFrame(continent)
            if not world then return end
            local dx=world.dx/(world.right-world.left)
            local dy=world.dy/(world.bottom-world.top)
            frame={continent=continent,dx=dx,dy=dy,wx=world.wx-world.left*dx,wy=world.wy-world.top*dy}
        end
        local display=geometry(cache,route,math.abs(w/frame.dx*scale),math.abs(h/frame.dy*scale),8,1.25)
        local size=beadSize/scale
        local insetX,insetY=size/(2*w),size/(2*h)
        local firstDot=dots
        local fallbackX,fallbackY
        for _,s in ipairs(display) do
            if s.beadLength then
                if insetX<.5 and insetY<.5 and s.from.continent==frame.continent then
                    local x1,y1=onMap(s.from,frame);local x2,y2=onMap(s.to,frame)
                    local _,_,_,_,lo,hi=rectClip(x1,y1,x2,y2,insetX,insetY,left,top,right,bottom)
                    dots=drawBeads(beads,mapLayer,dots,s,size,x1*w,-y1*h,x2*w,-y2*h,lo,hi)
                    if lo and dots==firstDot and not fallbackX and s.beadLength>1e-8 then
                        local t=(lo+hi)/2
                        fallbackX,fallbackY=(x1+(x2-x1)*t)*w,-(y1+(y2-y1)*t)*h
                    end
                end
            elseif s.kind~="border" then
                segment(frame,s.from,s.to,{0.03,0.07,0.05,0.9},7,false,true,s.capStart,s.capEnd)
                segment(frame,s.from,s.to,(s.kind=="approach" or s.kind=="estimated") and {1,0.84,0.5,1} or {0.35,1,0.75,1},4,(s.kind=="approach" or s.kind=="estimated"),false,s.capStart,s.capEnd)
            end
        end
        -- A very short visible leg can land entirely between two samples.
        if dots==firstDot and fallbackX then
            dots=dots+1
            drawBead(beads,mapLayer,dots,size,fallbackX,fallbackY)
        end
    end
    if A.route and A.route.status=="ok" then drawWalking(A.route,mapGeometry) end
    local blue=0
    local size=beadSize/scale
    local function drawTransport(leg)
        local a,b=ridePoints(leg,f and f.continent)
        if not a or not b then return end
        local x1,y1,x2,y2=a.wx,a.wy,b.wx,b.wy
        if f then x1,y1=onMap(a,f);x2,y2=onMap(b,f) end
        local _,_,_,_,lo,hi=rectClip(x1,y1,x2,y2,size/(2*w),size/(2*h),left,top,right,bottom)
        blue=drawRide(rideBeads,mapLayer,blue,size,scale,x1*w,-y1*h,x2*w,-y2*h,lo,hi)
    end
    if ride then drawTransport(ride) end
    if journey then
        for i,leg in ipairs(A.Transit.DisplayLegs(journey)) do
            if leg.kind=="walk" and i>1 and leg.preview then
                leg.previewGeometry=leg.previewGeometry or {}
                drawWalking(leg.preview,leg.previewGeometry)
            elseif leg.kind~="walk" then
                drawTransport(leg)
            end
        end
    end
    hideRest(lines,used+1)
    hideRest(beads,dots+1)
    hideRest(rideBeads,blue+1)
    drawStepMarkers(f,journey,w,h,scale,left,top,right,bottom)
    mapLayer.goal:Hide()
    if f and A.db.goal and A.db.goal.source~="pin" then
        local g=A.Router.World(A.Data,A.db.goal.zone,A.db.goal.x,A.db.goal.y,A.network.frames)
        local x,y=onMap(g,f)
        if g.continent==f.continent and x>=0 and x<=1 and y>=0 and y<=1 then
            mapLayer.goal:ClearAllPoints(); mapLayer.goal:SetPoint("CENTER",mapLayer,"TOPLEFT",x*w,-y*h)
            mapLayer.goal:SetSize(25/scale,25/scale); mapLayer.goal:Show()
        end
    end
    A.mapLineCount=used+dots+blue
end

local function circleClip(x1,y1,x2,y2,radius)
    local dx,dy=x2-x1,y2-y1; local aa=dx*dx+dy*dy
    if aa<1e-9 then return end
    local bb=2*(x1*dx+y1*dy); local cc=x1*x1+y1*y1-radius*radius
    local discriminant=bb*bb-4*aa*cc
    if discriminant<0 then return end
    local root=math.sqrt(discriminant)
    local lo=math.max(0,(-bb-root)/(2*aa)); local hi=math.min(1,(-bb+root)/(2*aa))
    if lo>hi then return end
    return x1+lo*dx,y1+lo*dy,x1+hi*dx,y1+hi*dy,lo,hi
end
A.CircleClip=circleClip

function A.DrawMinimap()
    if not miniLayer then
        miniLayer=CreateFrame("Frame",nil,Minimap); miniLayer:SetAllPoints(Minimap)
        miniLayer:SetFrameLevel(Minimap:GetFrameLevel()+4); miniLayer:EnableMouse(false)
    end
    local walking=A.route and A.route.status=="ok"
    local journey=not A.arrived and A.journey or nil
    local index=journey and journey.index
    if not A.db.enabled or not A.db.showMinimap or not A.player or not (walking or journey) then shown(miniLayer,false);miniCache.valid=false;A.minimapLineCount=0;return end
    shown(miniLayer,true)
    local w,h=miniLayer:GetWidth(),miniLayer:GetHeight(); local r=math.min(w,h)/2-7
    local radius=C_Minimap.GetViewRadius()
    if not A.Number(radius) or radius<=0 or r<=beadSize/2 then
        hideRest(miniLines,1);hideRest(miniBeads,1);hideRest(miniRideBeads,1);hideRest(miniStepMarkers,1)
        miniCache.valid=false;A.minimapLineCount=0;return
    end
    local facing=GetPlayerFacing() or 0; if not A.Number(facing) then facing=0 end
    local rotate=GetCVarBool("rotateMinimap")
    local p=A.player
    if miniCache.valid and miniCache.route==A.route and miniCache.w==w and miniCache.h==h and
        miniCache.journey==journey and miniCache.index==index and miniCache.arrived==A.arrived and
        miniCache.radius==radius and miniCache.rotate==rotate and (not rotate or math.abs(miniCache.facing-facing)<.015) and
        miniCache.continent==p.continent and (miniCache.wx-p.wx)^2+(miniCache.wy-p.wy)^2<1 and
        math.abs(miniCache.progress-(A.progress or 0))<2 then return end
    miniCache={valid=true,route=A.route,w=w,h=h,radius=radius,rotate=rotate,facing=facing,wx=p.wx,wy=p.wy,continent=p.continent,
        progress=A.progress or 0,journey=journey,index=index,arrived=A.arrived}
    A.perf=A.perf or {};A.perf.minimapRedraws=(A.perf.minimapRedraws or 0)+1
    local cosine,sine=math.cos(facing),math.sin(facing)
    local function position(p)
        local x,y=p.wx-A.player.wx,A.player.wy-p.wy
        if rotate then x,y=x*cosine+y*sine,-x*sine+y*cosine end
        return x*r/radius,y*r/radius
    end
    local used,dots=0,0
    local display=walking and geometry(miniGeometry,A.route,r/radius,r/radius,4,.65)
    local cutoff=(A.progress or 0)-20
    local lastSegment=display and #display or 0
    local first,last=1,lastSegment
    while first<=last do
        local mid=math.floor((first+last)/2)
        if display[mid].finish<cutoff then first=mid+1 else last=mid-1 end
    end
    for i=first,lastSegment do
        local s=display[i]
        if s.from.continent==p.continent and s.to.continent==p.continent and s.kind~="border" and
            s.maxWX>=p.wx-radius and s.minWX<=p.wx+radius and s.maxWY>=p.wy-radius and s.minWY<=p.wy+radius then
            local x1,y1=position(s.from); local x2,y2=position(s.to)
            if s.beadLength then
                local _,_,_,_,lo,hi=circleClip(x1,y1,x2,y2,r-beadSize/2)
                dots=drawBeads(miniBeads,miniLayer,dots,s,beadSize,w/2+x1,-h/2+y1,w/2+x2,-h/2+y2,lo,hi)
            else
                x1,y1,x2,y2=circleClip(x1,y1,x2,y2,r)
                if x1 then
                    local estimated=s.kind=="approach" or s.kind=="estimated"
                    local count=estimated and math.max(1,math.ceil(math.sqrt((x2-x1)^2+(y2-y1)^2)/7)) or 1
                    local color=estimated and {1,.8,.4,1} or {.3,1,.7,1}
                    for i=0,count-1 do
                        local t1=i/count; local t2=count>1 and (i+0.55)/count or 1
                        used=used+1; line(miniLines,miniLayer,used,w/2+x1+(x2-x1)*t1,-h/2+y1+(y2-y1)*t1,
                            w/2+x1+(x2-x1)*t2,-h/2+y1+(y2-y1)*t2,color,2.5,false)
                    end
                end
            end
        end
    end
    local blue=0
    if journey then
        local limit=r-beadSize/2
        for _,leg in ipairs(A.Transit.DisplayLegs(journey)) do
            if leg.kind~="walk" then
                local a,b=ridePoints(leg,p.continent)
                if a and b then
                    local x1,y1=position(a);local x2,y2=position(b)
                    local _,_,_,_,lo,hi=circleClip(x1,y1,x2,y2,limit)
                    if not lo and (x1-x2)^2+(y1-y2)^2<1e-9 and x1*x1+y1*y1<=limit*limit then lo,hi=0,0 end
                    blue=drawRide(miniRideBeads,miniLayer,blue,beadSize,1,w/2+x1,-h/2+y1,w/2+x2,-h/2+y2,lo,hi)
                end
            end
        end
    end
    hideRest(miniLines,used+1);hideRest(miniBeads,dots+1);hideRest(miniRideBeads,blue+1)
    local groups={}
    visitStepEnds(journey,function(point,texture)
        if point.continent~=p.continent then return end
        local x,y=position(point)
        if x*x+y*y<=r*r then addStepIcon(groups,w/2+x,-h/2+y,texture,1) end
    end,true)
    for i,group in ipairs(groups) do drawStepMarker(miniStepMarkers,miniLayer,i,group,1,w,h,r) end
    hideRest(miniStepMarkers,#groups+1)
    A.minimapLineCount=used+dots+blue
end
