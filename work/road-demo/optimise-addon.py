from pathlib import Path
root=Path(__file__).resolve().parents[2]/'outputs/ForeverRoads'
p=root/'Map.lua';s=p.read_text().replace('local lines,miniLines={},{}','local lines,miniLines={},{}\nlocal mapCache,miniCache={},{}')
a=s.index('local function line(');b=s.index('local function rectClip',a)
s=s[:a]+'''local function shown(frame,want)
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
''' +s[b:]
s=s.replace('mapLayer:SetFrameLevel(level); A.mapLayerLevel=level','if A.mapLayerLevel~=level then mapLayer:SetFrameLevel(level); A.mapLayerLevel=level end')
s=s.replace('mapHost:HookScript("OnHide",function() mapLayer:Hide() end)','mapHost:HookScript("OnHide",function() shown(mapLayer,false);mapCache.valid=false;A.mapLineCount=0 end)')
s=s.replace('    A.mapLineCount=0\n    A.AttachMap()','    A.AttachMap()')
s=s.replace('if not mapHost:IsShown() or not A.db.showMap or not A.db.enabled then mapLayer:Hide(); return end','if not mapHost:IsShown() or not A.db.showMap or not A.db.enabled then shown(mapLayer,false);mapCache.valid=false;A.mapLineCount=0;return end')
s=s.replace('    mapLayer:Show(); local used=0\n    local scale=mapHost:GetCanvasScale() or 1','''    shown(mapLayer,true)
    local scale=mapHost:GetCanvasScale() or 1
    if mapCache.valid and mapCache.zone==zone and mapCache.route==A.route and mapCache.goal==A.db.goal and
        mapCache.w==w and mapCache.h==h and mapCache.scale==scale and mapCache.roads==A.db.showRoads and
        mapCache.network==A.network and mapCache.edges==#A.network.edges then return end
    mapCache={valid=true,zone=zone,route=A.route,goal=A.db.goal,w=w,h=h,scale=scale,roads=A.db.showRoads,network=A.network,edges=#A.network.edges}
    A.perf=A.perf or {};A.perf.mapRedraws=(A.perf.mapRedraws or 0)+1
    local used=0''')
s=s.replace('    A.minimapLineCount=0\n    if not miniLayer then','    if not miniLayer then')
s=s.replace('then miniLayer:Hide(); return end','then shown(miniLayer,false);miniCache.valid=false;A.minimapLineCount=0;return end')
s=s.replace('    miniLayer:Show()','    shown(miniLayer,true)')
s=s.replace('    local rotate=GetCVarBool("rotateMinimap")','''    local rotate=GetCVarBool("rotateMinimap")
    local p=A.player
    if miniCache.valid and miniCache.route==A.route and miniCache.w==w and miniCache.h==h and
        miniCache.radius==radius and miniCache.rotate==rotate and math.abs(miniCache.facing-facing)<.015 and
        miniCache.continent==p.continent and (miniCache.wx-p.wx)^2+(miniCache.wy-p.wy)^2<1 and
        math.abs(miniCache.progress-(A.progress or 0))<2 then return end
    miniCache={valid=true,route=A.route,w=w,h=h,radius=radius,rotate=rotate,facing=facing,wx=p.wx,wy=p.wy,continent=p.continent,progress=A.progress or 0}
    A.perf=A.perf or {};A.perf.minimapRedraws=(A.perf.minimapRedraws or 0)+1''')
p.write_text(s)
p=root/'UI.lua';s=p.read_text();pos=s.index('local function panel')
s=s[:pos]+'''-- Only addon-owned frames/regions are cached here.
local function setText(region,value)
    if region.frText~=value then region:SetText(value);region.frText=value end
end
local function show(frame,want)
    if want then if not frame:IsShown() then frame:Show() end
    elseif frame:IsShown() then frame:Hide() end
end
''' +s[pos:]
s=s.replace('function A.RefreshSettings()','function A.RefreshSettings(force)')
s=s.replace('    local p=A.player\n    local location=', '''    local now=GetTime()
    if not force and now<(A.lastSettingsRefresh or -1)+.5 and A.settingsStatus==A.status and A.settingsZone==A.db.quickZone then return end
    A.lastSettingsRefresh=now;A.settingsStatus=A.status;A.settingsZone=A.db.quickZone
    local p=A.player
    local location=''',1)
a=s.index('    local places={}');b=s.index('    for key,b in pairs',a)
chunk=s[a:b];s=s[:a]+'''    if A.window.renderedQuickZone~=quickZone then
        A.window.renderedQuickZone=quickZone
''' +''.join('    '+line+'\n' for line in chunk.rstrip().splitlines())+'''    end
''' +s[b:]
s=s.replace('then hud:Hide(); return end','then show(hud,false); return end')
s=s.replace('    hud:Show(); hud.arrow:Hide()','    show(hud,true)')
s=s.replace('hud.instruction:SetText(A.status or "Waiting for a route"); hud.distance:SetText(""); return','setText(hud.instruction,A.status or "Waiting for a route");setText(hud.distance,"");show(hud.arrow,false);return')
s=s.replace('if A.arrived then hud.instruction:SetText("|cff77eebbDestination reached|r"); hud.distance:SetText("Within 15 yards"); return end','if A.arrived then setText(hud.instruction,"|cff77eebbDestination reached|r");setText(hud.distance,"Within 15 yards");show(hud.arrow,false);return end')
s=s.replace('hud.title:SetText(A.db.goal.label)','setText(hud.title,A.db.goal.label)')
s=s.replace('hud.arrow:SetRotation(-bearing-facing); hud.arrow:Show()','local rotation=-bearing-facing\n            if not hud.arrow.frRotation or math.abs(rotation-hud.arrow.frRotation)>.005 then hud.arrow:SetRotation(rotation);hud.arrow.frRotation=rotation end\n            show(hud.arrow,true)')
s=s.replace('    end\n    hud.instruction:SetText(segment and','    else show(hud.arrow,false) end\n    setText(hud.instruction,segment and')
s=s.replace('hud.distance:SetText(string.format','setText(hud.distance,string.format')
p.write_text(s)
p=root/'Navigation.lua';s=p.read_text()
s=s.replace('    if A.pendingRoute then A.Plan(player) end','    local revision=A.revision\n    if A.pendingRoute then A.Plan(player) end')
s=s.replace('            local progress=R.Progress(route,player,A.progress)','''            local previous=A.progressPlayer
            local progress
            if A.progressRevision~=A.revision or not previous or previous.zone~=player.zone or R.Distance(previous,player)>=1 then
                progress=R.Progress(route,player,A.progress)
                A.progressPlayer=player;A.progressRevision=A.revision
            else progress=A.lastProgress end
            A.lastProgress=progress''')
# Remove unused local created above; revision tracking lives on A.
s=s.replace('    local revision=A.revision\n','')
p.write_text(s)
for name in ['Core.lua','Navigation.lua','ForeverRoads.toc','README.md']:
 p=root/name;s=p.read_text().replace('1.1.2','1.1.3').replace('NewTicker(.15','NewTicker(.2');p.write_text(s)
