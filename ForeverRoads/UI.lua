local _, A = ...
-- Only addon-owned frames/regions are cached here.
local function panel(name,w,h)
    local f=CreateFrame("Frame",name,UIParent,"BackdropTemplate")
    f:SetSize(w,h); f:SetPoint("CENTER"); f:SetFrameStrata("DIALOG"); f:SetClampedToScreen(true)
    f:SetBackdrop({bgFile="Interface/Tooltips/UI-Tooltip-Background",edgeFile="Interface/Tooltips/UI-Tooltip-Border",tile=true,tileSize=16,edgeSize=16,insets={left=4,right=4,top=4,bottom=4}})
    f:SetBackdropColor(.035,.07,.065,.96); return f
end
local function text(parent,size,x,y,w)
    local t=parent:CreateFontString(nil,"OVERLAY",size or "GameFontHighlight")
    t:SetPoint("TOPLEFT",x,y); t:SetWidth(w); t:SetJustifyH("LEFT"); return t
end
local function button(parent,label,x,y,w,fn)
    local b=CreateFrame("Button",nil,parent,"UIPanelButtonTemplate")
    b:SetSize(w,25); b:SetPoint("TOPLEFT",x,y); b:SetText(label); b:SetScript("OnClick",fn); return b
end
local function check(parent,key,label,x,y)
    local b=CreateFrame("CheckButton",nil,parent,"UICheckButtonTemplate")
    b:SetSize(25,25); b:SetPoint("TOPLEFT",x,y)
    local t=b:CreateFontString(nil,"OVERLAY","GameFontHighlightSmall"); t:SetPoint("LEFT",b,"RIGHT",3,0); t:SetText(label)
    b:SetChecked(A.db[key]); b:SetScript("OnClick",function(self)
        A.db[key]=self:GetChecked() and true or false
        if key=="preferRoads" then A.pendingRoute=true end
        A.Draw()
    end)
    return b
end

function A.RefreshSettings(force)
    if not A.window or not A.window:IsShown() then return end
    local now=GetTime()
    if not force and now<(A.lastSettingsRefresh or -1)+.5 and A.settingsStatus==A.status and A.settingsZone==A.db.quickZone then return end
    A.lastSettingsRefresh=now;A.settingsStatus=A.status;A.settingsZone=A.db.quickZone
    local p=A.player
    local location=p and string.format("%s  %.1f, %.1f",A.ZoneName(p.zone),p.x/A.Data.width*100,p.y/A.Data.height*100) or "Position unavailable / outside coverage"
    local destination=A.db.goal and (A.db.goal.label.." — "..A.ZoneName(A.db.goal.zone)) or "Track a quest or Alt-click a supported zone map."
    A.window.status:SetText((A.db.enabled and "|cff77eebbGuidance enabled|r" or "Guidance paused").."  •  "..
        (A.db.followQuest and "Following tracked quest" or "Manual destination").."\n"..location.."\n"..destination.."\n"..(A.status or "Starting"))
    A.window.pause:SetText(A.db.enabled and "Pause" or "Resume")
    A.window.record:SetText(A.db.recording and "Stop recording" or "Record a walk")
    local points=0; for _,track in ipairs(A.db.recordings or {}) do points=points+#track.points end
    local flights=0
    for _,known in pairs(A.db.knownFlights or {}) do if known==true then flights=flights+1 end end
    local flightInfo=flights>0 and (flights.." learned flight stops for this character.") or
        "Open a flight master to import this character's learned stops."
    local route=A.route
    A.window.details:SetText(string.format("%d zone maps • terrain navigation • %d/%d maps calibrated live\n%d recorded walk(s), %d samples. %s\n%s",#A.Data.zones,A.liveFrames,#A.Data.zones,#(A.db.recordings or {}),points,flightInfo,
        route and route.status=="ok" and string.format("Current route: %.0f yd • %.0f yd estimated path • %d A* nodes explored",route.distance,route.estimated,route.expanded) or "No connected route is currently displayed."))
    local quickZone=A.db.quickZone or (p and p.zone) or A.Data.zones[1].id
    if A.window.renderedQuickZone~=quickZone then
        A.window.renderedQuickZone=quickZone
        local places={}
        for _,place in ipairs(A.Data.places) do if place.zone==quickZone then places[#places+1]=place end end
        for i,b in ipairs(A.window.quickButtons) do
            b.place=places[i]
            if b.place then b:SetText(b.place.name:gsub(" approach","")); b:Show() else b:Hide() end
        end
        for zone,b in pairs(A.window.zoneButtons) do
            local name=b.zoneName
            b:SetText(zone==quickZone and ("|cff77eebb"..name.."|r") or name)
        end
    end
    for key,b in pairs(A.window.checks) do b:SetChecked(A.db[key]) end
end

function A.Draw()
    if not A.window or not A.network then return end
    A.DrawMap(); A.DrawMinimap(); A.RefreshSettings()
end

function A.CreateUI()
    local w=panel("ForeverRoadsWindow",680,820); A.window=w
    w:SetMovable(true); w:EnableMouse(true); w:RegisterForDrag("LeftButton")
    w:SetScript("OnDragStart",w.StartMoving); w:SetScript("OnDragStop",w.StopMovingOrSizing)
    text(w,"GameFontNormalLarge",18,-16,600):SetText("Forever GPS")
    local close=CreateFrame("Button",nil,w,"UIPanelCloseButton"); close:SetPoint("TOPRIGHT",-5,-5)
    w.status=text(w,"GameFontHighlight",18,-45,640)
    button(w,"Follow tracked quest",18,-130,170,function() A.Command("follow") end)
    button(w,"Use map pin",196,-130,145,function() A.UseMapPin() end)
    w.pause=button(w,"Pause",349,-130,145,function() A.Command(A.db.enabled and "pause" or "resume") end)
    button(w,"Clear destination",502,-130,160,function() A.Clear() end)
    w.checks={showMap=check(w,"showMap","World map route and steps",18,-171),showMinimap=check(w,"showMinimap","Minimap route",230,-171),
        preferRoads=check(w,"preferRoads","Prefer roads over trails",447,-171)}
    text(w,"GameFontNormal",18,-250,640):SetText("Choose a zone — scroll for the full world list")
    w.zoneButtons={};w.quickButtons={}
    local scroll=CreateFrame("ScrollFrame",nil,w,"UIPanelScrollFrameTemplate")
    scroll:SetSize(620,210);scroll:SetPoint("TOPLEFT",18,-279)
    local list=CreateFrame("Frame",nil,scroll);list:SetSize(620,math.ceil(#A.Data.zones/3)*29)
    scroll:SetScrollChild(list);w.zoneScroll=scroll
    local zones={};for _,z in ipairs(A.Data.zones) do zones[#zones+1]=z end
    table.sort(zones,function(a,b) return a.name<b.name end)
    for i,z in ipairs(zones) do
        local col=(i-1)%3;local row=math.floor((i-1)/3)
        local b=button(list,z.name,col*205,-row*29,199,function()
            A.db.quickZone=z.id;A.RefreshSettings(true)
        end)
        b.zoneName=z.name;w.zoneButtons[z.id]=b
    end
    text(w,"GameFontNormal",18,-510,640):SetText("Destinations — quests and Alt-click map destinations also work")
    for i=1,12 do
        local col=(i-1)%3;local row=math.floor((i-1)/3)
        local b=button(w,"",18+col*216,-539-row*29,208,function(self)
            local p=self.place
            if p then A.SetDestination({zone=p.zone,x=p.x,y=p.y,z=p.z,label=p.name,source="place"},true);A.Tick() end
        end)
        w.quickButtons[i]=b
    end
    w.record=button(w,"Record a walk",18,-670,170,function() A.ToggleRecording();A.RefreshSettings(true) end)
    w.details=text(w,"GameFontHighlightSmall",18,-710,640)
    text(w,"GameFontDisableSmall",18,-792,640):SetText("Terrain searches are sliced across frames. Guidance requires readable player coordinates.")
    w:SetScript("OnShow",A.RefreshSettings); w:Hide(); UISpecialFrames[#UISpecialFrames+1]="ForeverRoadsWindow"

    local icon=CreateFrame("Button","ForeverRoadsMinimapButton",Minimap); A.minimapButton=icon
    icon:SetSize(32,32); icon:SetFrameLevel(Minimap:GetFrameLevel()+12)
    local texture=icon:CreateTexture(nil,"BACKGROUND"); texture:SetTexture("Interface/Icons/Ability_Tracking"); texture:SetSize(21,21); texture:SetPoint("CENTER")
    local border=icon:CreateTexture(nil,"OVERLAY"); border:SetTexture("Interface/Minimap/MiniMap-TrackingBorder"); border:SetSize(54,54); border:SetPoint("TOPLEFT")
    icon:SetHighlightTexture("Interface/Minimap/UI-Minimap-ZoomButton-Highlight"); icon:RegisterForClicks("LeftButtonUp","RightButtonUp"); icon:RegisterForDrag("LeftButton")
    local function position()
        local angle=math.rad(A.db.minimapAngle or 235)
        icon:ClearAllPoints(); icon:SetPoint("CENTER",Minimap,"CENTER",math.cos(angle)*(Minimap:GetWidth()/2+7),math.sin(angle)*(Minimap:GetHeight()/2+7))
    end
    position()
    icon:SetScript("OnDragStart",function(self)
        self:SetScript("OnUpdate",function()
            local x,y=GetCursorPosition(); local cx,cy=Minimap:GetCenter(); local scale=Minimap:GetEffectiveScale()
            A.db.minimapAngle=math.deg(math.atan2(y/scale-cy,x/scale-cx)); position()
        end)
    end)
    icon:SetScript("OnDragStop",function(self) self:SetScript("OnUpdate",nil); self.suppressClickUntil=GetTime()+0.2 end)
    icon:SetScript("OnClick",function(self,which)
        if self.suppressClickUntil and GetTime()<self.suppressClickUntil then return end
        if which=="RightButton" then A.Command(A.db.enabled and "pause" or "resume")
        else w:SetShown(not w:IsShown()) end
    end)
    icon:SetScript("OnEnter",function(self)
        GameTooltip:SetOwner(self,"ANCHOR_LEFT"); GameTooltip:SetText("Forever GPS")
        GameTooltip:AddLine(A.status or "Ready",1,1,1,true)
        GameTooltip:AddLine("Left-click: settings\nRight-click: pause/resume\nDrag: move button",.8,.8,.8,true); GameTooltip:Show()
    end)
    icon:SetScript("OnLeave",function() GameTooltip:Hide() end)
end
