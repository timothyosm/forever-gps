local _, A = ...
local mapLayer,mapHost,miniLayer
local lines,miniLines={},{}
local mapCache,miniCache={},{}

local function shown(frame,want)
    if want then if not frame:IsShown() then frame:Show() end
    elseif frame:IsShown() then frame:Hide() end
end
local function line(pool,owner,index,x1,y1,x2,y2,color,width,outline)
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
local function rectClip(x1,y1,x2,y2)
    local dx,dy=x2-x1,y2-y1; local lo,hi=0,1
    local p={-dx,dx,-dy,dy}; local q={x1,1-x1,y1,1-y1}
    for i=1,4 do
        if math.abs(p[i])<1e-10 then if q[i]<0 then return end
        else
            local r=q[i]/p[i]
            if p[i]<0 then lo=math.max(lo,r) else hi=math.min(hi,r) end
            if lo>hi then return end
        end
    end
    return x1+lo*dx,y1+lo*dy,x1+hi*dx,y1+hi*dy
end
A.RectClip=rectClip

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

function A.AttachMap()
    if mapHost or not WorldMapFrame or not WorldMapFrame.ScrollContainer then return end
    mapHost=WorldMapFrame
    local canvas=mapHost:GetCanvas()
    if not canvas then mapHost=nil; return end
    mapLayer=CreateFrame("Frame",nil,canvas)
    mapLayer:SetAllPoints(canvas); refreshMapLevel()
    mapLayer:EnableMouse(false)
    if mapLayer.SetClipsChildren then mapLayer:SetClipsChildren(true) end
    mapLayer.goal=mapLayer:CreateTexture(nil,"OVERLAY")
    mapLayer.goal:SetTexture("Interface/GossipFrame/AvailableQuestIcon")
    mapHost:HookScript("OnHide",function() shown(mapLayer,false);mapCache.valid=false;A.mapLineCount=0 end)
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
    if not mapHost:IsShown() or not A.db.showMap or not A.db.enabled then shown(mapLayer,false);mapCache.valid=false;A.mapLineCount=0;return end
    refreshMapLevel()
    local zone=mapHost:GetMapID()
    if not A.Number(zone) then mapLayer:Hide(); return end
    local f=frameFor(zone); if not f then mapLayer:Hide(); return end
    local w,h=mapLayer:GetWidth(),mapLayer:GetHeight()
    if w<=0 or h<=0 then return end
    shown(mapLayer,true)
    local scale=mapHost:GetCanvasScale() or 1
    if mapCache.valid and mapCache.zone==zone and mapCache.route==A.route and mapCache.goal==A.db.goal and
        mapCache.w==w and mapCache.h==h and mapCache.scale==scale and mapCache.roads==A.db.showRoads and
        mapCache.network==A.network and mapCache.edges==#A.network.edges then return end
    mapCache={valid=true,zone=zone,route=A.route,goal=A.db.goal,w=w,h=h,scale=scale,roads=A.db.showRoads,network=A.network,edges=#A.network.edges}
    A.perf=A.perf or {};A.perf.mapRedraws=(A.perf.mapRedraws or 0)+1
    local used=0
    local function segment(a,b,color,width,dashed,outline)
        if a.continent~=f.continent or b.continent~=f.continent then return end
        local x1,y1=onMap(a,f); local x2,y2=onMap(b,f)
        x1,y1,x2,y2=rectClip(x1,y1,x2,y2)
        if not x1 then return end
        local count=dashed and math.max(1,math.ceil(math.sqrt(((x2-x1)*w)^2+((y2-y1)*h)^2)/8)) or 1
        for i=0,count-1 do
            local t1=i/count; local t2=dashed and (i+0.55)/count or 1
            used=used+1; line(lines,mapLayer,used,(x1+(x2-x1)*t1)*w,-(y1+(y2-y1)*t1)*h,
                (x1+(x2-x1)*t2)*w,-(y1+(y2-y1)*t2)*h,color,width/scale,outline)
        end
    end
    if A.db.showRoads then
        for _,e in ipairs(A.network.edges) do if e.kind~="border" then segment(A.network.nodes[e.a],A.network.nodes[e.b],{0.9,0.72,0.35,0.6},1.5) end end
    end
    if A.route and A.route.status=="ok" then
        for _,s in ipairs(A.route.segments) do
            if s.kind~="border" then
                segment(s.from,s.to,{0.03,0.07,0.05,0.9},7,false,true)
                segment(s.from,s.to,(s.kind=="approach" or s.kind=="estimated") and {1,0.84,0.5,1} or {0.35,1,0.75,1},4,(s.kind=="approach" or s.kind=="estimated"))
            end
        end
    end
    hideRest(lines,used+1)
    mapLayer.goal:Hide()
    if A.db.goal then
        local g=A.Router.World(A.Data,A.db.goal.zone,A.db.goal.x,A.db.goal.y,A.network.frames)
        local x,y=onMap(g,f)
        if g.continent==f.continent and x>=0 and x<=1 and y>=0 and y<=1 then
            mapLayer.goal:ClearAllPoints(); mapLayer.goal:SetPoint("CENTER",mapLayer,"TOPLEFT",x*w,-y*h)
            mapLayer.goal:SetSize(25/scale,25/scale); mapLayer.goal:Show()
        end
    end
    A.mapLineCount=used
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
    return x1+lo*dx,y1+lo*dy,x1+hi*dx,y1+hi*dy
end
A.CircleClip=circleClip

function A.DrawMinimap()
    if not miniLayer then
        miniLayer=CreateFrame("Frame",nil,Minimap); miniLayer:SetAllPoints(Minimap)
        miniLayer:SetFrameLevel(Minimap:GetFrameLevel()+4); miniLayer:EnableMouse(false)
    end
    if not A.db.enabled or not A.db.showMinimap or not A.player or not A.route or A.route.status~="ok" then shown(miniLayer,false);miniCache.valid=false;A.minimapLineCount=0;return end
    shown(miniLayer,true)
    local w,h=miniLayer:GetWidth(),miniLayer:GetHeight(); local r=math.min(w,h)/2-7
    local radius=C_Minimap.GetViewRadius()
    if not A.Number(radius) or radius<=0 then hideRest(miniLines,1);miniCache.valid=false;A.minimapLineCount=0;return end
    local facing=GetPlayerFacing() or 0; if not A.Number(facing) then facing=0 end
    local rotate=GetCVarBool("rotateMinimap")
    local p=A.player
    if miniCache.valid and miniCache.route==A.route and miniCache.w==w and miniCache.h==h and
        miniCache.radius==radius and miniCache.rotate==rotate and math.abs(miniCache.facing-facing)<.015 and
        miniCache.continent==p.continent and (miniCache.wx-p.wx)^2+(miniCache.wy-p.wy)^2<1 and
        math.abs(miniCache.progress-(A.progress or 0))<2 then return end
    miniCache={valid=true,route=A.route,w=w,h=h,radius=radius,rotate=rotate,facing=facing,wx=p.wx,wy=p.wy,continent=p.continent,progress=A.progress or 0}
    A.perf=A.perf or {};A.perf.minimapRedraws=(A.perf.minimapRedraws or 0)+1
    local cosine,sine=math.cos(facing),math.sin(facing)
    local function position(p)
        local x,y=p.wx-A.player.wx,A.player.wy-p.wy
        if rotate then x,y=x*cosine+y*sine,-x*sine+y*cosine end
        return x*r/radius,y*r/radius
    end
    local used=0
    for _,s in ipairs(A.route.segments) do
        if s.from.continent==A.player.continent and s.to.continent==A.player.continent and s.kind~="border" and s.finish>=(A.progress or 0)-20 then
            local x1,y1=position(s.from); local x2,y2=position(s.to)
            x1,y1,x2,y2=circleClip(x1,y1,x2,y2,r)
            if x1 then
                local count=(s.kind=="approach" or s.kind=="estimated") and math.max(1,math.ceil(math.sqrt((x2-x1)^2+(y2-y1)^2)/7)) or 1
                for i=0,count-1 do
                    local t1=i/count; local t2=count>1 and (i+0.55)/count or 1
                    used=used+1; line(miniLines,miniLayer,used,w/2+x1+(x2-x1)*t1,-h/2+y1+(y2-y1)*t1,
                        w/2+x1+(x2-x1)*t2,-h/2+y1+(y2-y1)*t2,(s.kind=="approach" or s.kind=="estimated") and {1,.8,.4,1} or {.3,1,.7,1},2.5)
                end
            end
        end
    end
    hideRest(miniLines,used+1); A.minimapLineCount=used
end
