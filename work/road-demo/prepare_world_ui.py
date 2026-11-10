from pathlib import Path
r=Path(__file__).resolve().parent.parent/'world-addon'
p=r/'UI.lua';s=p.read_text().replace('panel("ForeverRoadsWindow",680,610)','panel("ForeverRoadsWindow",680,820)')
s=s.replace('%d roads/trails/access paths • %d nodes • %d/%d maps calibrated live','%d zone maps • terrain navigation • %d/%d maps calibrated live').replace('#A.Data.roads,#A.network.nodes,A.liveFrames,#A.Data.zones','#A.Data.zones,A.liveFrames,#A.Data.zones')
a=s.index('    text(w,"GameFontNormal",18,-250');b=s.index('    w:SetScript("OnShow"',a)
s=s[:a]+'''    text(w,"GameFontNormal",18,-250,640):SetText("Choose a zone — scroll for the full world list")
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
''' +s[b:];p.write_text(s)
p=r/'Core.lua';s=p.read_text().replace('1.1.3','2.0.0-dev')
s=s.replace('function A.Clear()','function A.Clear()\n    if A.CancelPlan then A.CancelPlan() end')
a=s.index('local aliases=');b=s.index('\nfunction A.Command',a)
s=s[:a]+'''local aliases={tirisfal=1420,silverpine=1421,hillsbrad=1424,stonetalon=1442,stone=1442,barrens=1413}
local function zoneKey(name) return name:lower():gsub("[%s%p]","") end
for _,z in ipairs(A.Data.zones) do aliases[tostring(z.id)]=z.id;aliases[zoneKey(z.name)]=z.id end
local function resolveZone(name)
    name=(name or ""):gsub('^"(.-)"$','%1')
    return aliases[name:lower()] or aliases[zoneKey(name)]
end
''' +s[b:]
s=s.replace('rest:match("^(%S+)%s+(%S+)%s+(%S+)%s*(.*)$")','rest:match("^(.-)%s+([%d%.]+)%s+([%d%.]+)%s*(.*)$")').replace('zone=zone and aliases[zone:lower()]','zone=zone and resolveZone(zone)')
s=s.replace('/froads way tirisfal|silverpine|hillsbrad|stonetalon x y [name]', '/froads way zone-name-or-map-ID x y [name]')
s=s.replace('Loaded for Tirisfal, Silverpine, Hillsbrad and Stonetalon.','Loaded world-wide terrain navigation.')
p.write_text(s)
p=r/'Navigation.lua';s=p.read_text().replace('Choose a destination in Tirisfal, Silverpine, Hillsbrad or Stonetalon.','Choose a destination on a supported zone map.');p.write_text(s)
p=r/'Map.lua';s=p.read_text().replace('Alt-click a point on a Tirisfal, Silverpine, Hillsbrad or Stonetalon zone map.','Alt-click a point on a zone map.');p.write_text(s)
p=r/'WorldNavigation.lua';s=p.read_text();pos=s.index('\nfunction A.Supported')
s=s[:pos]+'''
local after=A.Path.after
A.Path.after=function(fn)
    after(function()
        local start=debugprofilestop and debugprofilestop()
        fn()
        if start then
            local elapsed=debugprofilestop()-start
            A.perf=A.perf or {};local p=A.perf
            p.searchSlices=(p.searchSlices or 0)+1;p.searchCPU=(p.searchCPU or 0)+elapsed;p.searchPeak=math.max(p.searchPeak or 0,elapsed)
        end
    end)
end
''' +s[pos:];p.write_text(s)
