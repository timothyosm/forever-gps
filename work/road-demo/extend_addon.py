from pathlib import Path
root=Path(__file__).resolve().parents[2]/'outputs/ForeverRoads'
p=root/'Map.lua';s=p.read_text()
s=s.replace('s.kind=="approach"','(s.kind=="approach" or s.kind=="estimated")')
p.write_text(s)
p=root/'UI.lua';s=p.read_text()
s=s.replace('37 traced roads/trails • %d nodes • %d/3 maps calibrated live','%d roads/trails/access paths • %d nodes • %d/%d maps calibrated live')
s=s.replace('end or "No connected route', 'end or "No connected route')
s=s.replace('estimated approach • %d A* nodes explored','estimated path • %d A* nodes explored')
s=s.replace('#A.network.nodes,A.liveFrames,#(A.db.recordings or {})','#A.Data.roads,#A.network.nodes,A.liveFrames,#A.Data.zones,#(A.db.recordings or {})')
s=s.replace('    for key,b in pairs(A.window.checks)', '''    local quickZone=A.db.quickZone or (p and p.zone) or A.Data.zones[1].id
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
    for key,b in pairs(A.window.checks)''')
s=s.replace('segment.kind=="approach"','(segment.kind=="approach" or segment.kind=="estimated")')
start=s.index('    for i,p in ipairs(A.Data.places) do',s.index('function A.CreateUI'))
end=s.index('    w.record=button',start)
s=s[:start]+'''    w.zoneButtons={}; w.quickButtons={}
    for i,z in ipairs(A.Data.zones) do
        local b=button(w,z.shortName or z.name:gsub(" Glades",""):gsub(" Forest",""):gsub(" Foothills",""),18+(i-1)*162,-278,154,function()
            A.db.quickZone=z.id; A.RefreshSettings()
        end)
        b.zoneName=z.shortName or z.name:gsub(" Glades",""):gsub(" Forest",""):gsub(" Foothills","")
        w.zoneButtons[z.id]=b
    end
    for i=1,12 do
        local col=(i-1)%3; local row=math.floor((i-1)/3)
        local b=button(w,"",18+col*216,-313-row*33,208,function(self)
            local p=self.place
            if p then A.SetDestination({zone=p.zone,x=p.x,y=p.y,label=p.name,source="place"},true); A.Tick() end
        end)
        w.quickButtons[i]=b
    end
''' +s[end:]
s=s.replace('Gold dashes are unverified approaches.','Gold dashes are estimated paths/approaches.')
p.write_text(s)
p=root/'Core.lua';s=p.read_text().replace('version="1.0.0"','version="1.1.0"')
s=s.replace('hillsbrad=1424,','hillsbrad=1424,stonetalon=1442,stone=1442,["1442"]=1442,')
s=s.replace('tirisfal|silverpine|hillsbrad x y','tirisfal|silverpine|hillsbrad|stonetalon x y')
s=s.replace('%d/3 live map frames','%d/%d live map frames').replace('A.route.expanded,A.liveFrames))','A.route.expanded,A.liveFrames,#A.Data.zones))')
s=s.replace('Loaded for Tirisfal, Silverpine and Hillsbrad.','Loaded for Tirisfal, Silverpine, Hillsbrad and Stonetalon.')
p.write_text(s)
p=root/'ForeverRoads.toc';s=p.read_text().replace('Three-zone road navigation for Tirisfal, Silverpine and Hillsbrad.','Road navigation for Tirisfal, Silverpine, Hillsbrad and Stonetalon.').replace('1.0.0','1.1.0');p.write_text(s)
