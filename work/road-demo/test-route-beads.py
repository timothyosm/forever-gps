"""Exercise the actual texture renderer with simulated map frames."""
from pathlib import Path
from lupa.lua51 import LuaRuntime
import ast
import json
import struct

h=Path(__file__).resolve().parent
root=h.parent/'world-addon'
lua=LuaRuntime()
tree=ast.parse((h/'test-addon.py').read_text())
mock=next(n.value.args[0].value for n in tree.body if isinstance(n,ast.Expr)
          and isinstance(n.value,ast.Call) and isinstance(n.value.args[0],ast.Constant)
          and isinstance(n.value.args[0].value,str) and 'local methods={}' in n.value.args[0].value)
lua.execute(mock+r'''
textures={};lines={};frames={};moved=0
local createFrame=CreateFrame
function CreateFrame(kind,name,parent,template)
 local f=createFrame(kind,name,parent,template);f.parent=parent;frames[#frames+1]=f;return f
end
function methods:CreateTexture(_,layer,_,sublevel)
 local t=object();t.owner=self;t.layer=layer;t.sublevel=sublevel;textures[#textures+1]=t;return t
end
function methods:SetTexture(path) self.texture=path end
function methods:SetDesaturated(value) self.desaturated=value end
function methods:SetVertexColor(r,g,b) self.tint={r,g,b} end
function methods:SetPoint(_,_,_,x,y) self.x=x;self.y=y;moved=moved+1 end
function methods:CreateLine() local t=object();t.owner=self;lines[#lines+1]=t;return t end
zoom=1;viewRadius=83;facing=0;rotating=false
function WorldMapFrame:GetCanvasScale() return zoom end
function C_Minimap.GetViewRadius() return viewRadius end
function GetPlayerFacing() return facing end
function GetCVarBool() return rotating end
A={db={enabled=true,showMap=true,showMinimap=true},network={frames={[1420]={wx=0,wy=0,dx=1002,dy=668,continent=0}},edges={}},
   Number=function(x) return type(x)=="number" end}
function make(points,kinds)
 local r={status="ok",distance=0,segments={}}
 for i=1,#points-1 do
  local a,b=points[i],points[i+1]
  local d=math.sqrt((a.wx-b.wx)^2+(a.wy-b.wy)^2)
  r.segments[i]={from=a,to=b,kind=kinds and kinds[i] or "terrain",begin=r.distance,finish=r.distance+d,length=d}
  r.distance=r.distance+d
 end
 A.route=r;A.progress=0;return r
end
function p(x,y,c) return {wx=x,wy=y,continent=c or 0} end
function dots(mini,ride)
 local out={}
 for _,t in ipairs(textures) do
  local parent=mini and Minimap or canvas
  if t.owner.anchorParent==parent and t.owner:IsShown() and t:IsShown() and t.sublevel==(ride and 3 or 2) then
   assert(t.texture==[[Interface\AddOns\ForeverRoads\Media\GoldBead.tga]])
   out[#out+1]=t
  end
 end
 return out
end
function eq(a,b) assert(math.abs(a-b)<1e-6, tostring(a).." ~= "..tostring(b)) end
function steps(mini)
 local out={}
 local parent=mini and Minimap or canvas
 for _,f in ipairs(frames) do
  if f.badge and f.parent.anchorParent==parent and f:IsShown() and f.parent:IsShown() then out[#out+1]=f end
 end
 return out
end
''')
lua.execute('A.TransitData={nodes={}}')
for name in ('Transit.lua','Map.lua'):
    lua.execute('local f=function(...)\n'+(root/name).read_text()+'\nend;f("ForeverRoads",A)')
checks=[]
def check(name,code):
    lua.execute(code)
    checks.append(name)

check('world spacing stays on phase across joins and kinds, and size stays fixed on zoom', '''
make({p(100,200),p(107,200),p(110,200),p(123,200),p(150,200)},{"road","road","trail","terrain"})
for _,scale in ipairs({1,2,.5}) do
 zoom=scale;A.DrawMap();local d=dots(false)
 assert(#d==math.ceil(50*scale/10))
 for i,t in ipairs(d) do eq(t.x,100+(i-1)*10/scale);eq(t.y,-200);eq(t.width*scale,7) end
end
zoom=1
''')
check('the visible beads track the smoothed curve at ten-pixel arc intervals', '''
local r=make({p(200,200),p(220,200),p(220,240),p(260,240)})
A.DrawMap();local d=dots(false);local s,rounded=A.SmoothRouteSegments(r,1,1,8,1.25)
assert(rounded==2 and #d>=9)
local i,dist=1,0
for _,v in ipairs(s) do
 local a,b=v.from,v.to;local dx,dy=b.wx-a.wx,b.wy-a.wy
 local len=math.sqrt(dx*dx+dy*dy)
 while (i-1)*10<dist+len-1e-7 do
  local t=((i-1)*10-dist)/len
  eq(d[i].x,a.wx+t*dx);eq(d[i].y,-(a.wy+t*dy));i=i+1
 end
 dist=dist+len
end
assert(i==#d+1)
''')
check('world clips long trails to the visible viewport, including when zoomed and panned', '''
make({p(-1000000,400),p(1000000,400)})
A.DrawMap();local d=dots(false);assert(#d==99)
local pooled=0;for _,texture in ipairs(textures) do if texture.sublevel==2 then pooled=pooled+1 end end
assert(pooled<=100)
eq(d[1].x,10);eq(d[#d].x,990)
for _,t in ipairs(d) do assert(t.x>=3.5 and t.x<=1002-3.5) end
make({p(0,200),p(1002,200)})
zoom=8
local pan=2400
local canvas=WorldMapFrame:GetCanvas()
function canvas:GetRect() return 0,0,1002,668 end
function canvas:GetEffectiveScale() return zoom end
function WorldMapFrame.ScrollContainer:GetRect() return pan,3100,800,1000 end
A.DrawMap();d=dots(false)
assert(#d>=80 and #d<=96)
assert(d[1].x>=294 and d[#d].x<=406)
pan=4800;A.DrawMap();d=dots(false)
assert(#d>=80 and #d<=96 and d[1].x>=594 and d[#d].x<=706)
WorldMapFrame.ScrollContainer.GetRect=nil;canvas.GetRect=nil;canvas.GetEffectiveScale=nil;zoom=1
''')
check('a short leg near the map edge still shows one fully visible bead', '''
make({p(580,666.5),p(580,658.5)})
A.DrawMap();local d=dots(false);assert(#d==1)
eq(d[1].x,580);assert(d[1].y>=-664.5 and d[1].y<=-658.5)
''')
check('estimated legs remain separate and foreign continents do not bleed into the map', '''
make({p(200,200),p(217,200),p(260,200),p(277,200),p(310,200,1),p(370,200,1)},
 {"terrain","estimated","terrain","border","terrain"})
A.DrawMap();local d=dots(false);assert(#d==4 and #lines>1)
eq(d[1].x,200);eq(d[2].x,210);eq(d[3].x,260);eq(d[4].x,270)
''')
check('minimap clips dot bounds and reuses phase and textures while moving or rotating', '''
make({p(10,250),p(500,250)})
A.player=p(253,250);A.DrawMinimap()
local n=#textures;local draws=A.perf.minimapRedraws;local builds=A.perf.smoothingBuilds;local m=moved
for i=1,20 do A.DrawMinimap() end
assert(A.perf.minimapRedraws==draws and moved==m)
for _,x in ipairs({253,259,267}) do
 A.player=p(x,250);A.DrawMinimap();local d=dots(true);assert(#d>=15)
 for i,t in ipairs(d) do
  eq(t.y,-90);eq(t.width,7)
  assert(math.abs(t.x-90)+3.5<=83)
  eq((t.x-90+x)/10,math.floor((t.x-90+x)/10+.5))
  if i>1 then eq(t.x-d[i-1].x,10) end
 end
end
rotating=true;facing=math.pi/2;A.DrawMinimap()
for _,t in ipairs(dots(true)) do eq(t.x,90);assert(math.abs(t.y+90)+3.5<=83) end
assert(A.perf.smoothingBuilds==builds and #textures<=n+1)
A.db.showMinimap=false;A.DrawMinimap();assert(#dots(true)==0 and A.minimapLineCount==0)
''')
check('transport dots hold their size on zone, continent, world and minimap views', '''
local function stop(x,y,map) return {x=-y,y=-x,map=map} end
local function ride(kind,a,b) return {kind=kind,from=a,to=b,seconds=90} end
local first,near=stop(450,330,0),stop(550,330,0)
local foreign=stop(2100,8500,1)
local island=stop(80,250,2991)
A.network.frames[1415]={wx=-16000,wy=-7466.6001,dx=35199.9004,dy=23466.6001,continent=0}
A.network.frames[1414]={wx=-17066.5996,wy=-12799.9004,dx=36799.8105,dy=24533.2002,continent=1}
A.network.frames[2521]={wx=0,wy=0,dx=1002,dy=668,continent=2991}
C_Map={GetMapRectOnMap=function(id,top) assert(id==2521 and top==947);return .46,.50,.2,.26 end}
A.route={status="transport"};A.journey={index=1,legs={}}
local function draw(id,scale)
 worldMapID=id;zoom=scale;A.DrawMap();local beads=dots(false,true)
 assert(#beads>0)
 for _,dot in ipairs(beads) do
  eq(dot.width*zoom,7);assert(dot.desaturated and dot.tint[3]>dot.tint[2] and dot.tint[2]>dot.tint[1])
  assert(dot.x>=0 and dot.x<=1002 and dot.y>=-668 and dot.y<=0)
 end
 return beads
end
for _,kind in ipairs({"flight","boat","zeppelin","tram","portal","skycutter"}) do
 A.journey={index=1,legs={ride(kind,first,near)}}
 for _,scale in ipairs({.2,1,8}) do draw(1420,scale);draw(1415,scale);draw(947,scale) end
end
A.journey={index=1,legs={ride("boat",first,foreign),ride("zeppelin",foreign,island)}}
for _,scale in ipairs({.2,1,8}) do
 for _,id in ipairs({1420,1414,1415,2521,947}) do draw(id,scale) end
end
-- The sea crossing should reach both continent assignments on Azeroth.
A.journey={index=1,legs={ride("boat",first,foreign)}}
local world=draw(947,1)
assert(world[1].x>550 and world[#world].x<410)
local draws=A.perf.mapRedraws;A.DrawMap();assert(A.perf.mapRedraws==draws)
A.db.showMinimap=true;rotating=false;A.player=p(450,330)
for _,radius in ipairs({50,83,220}) do
 viewRadius=radius;A.DrawMinimap();local mini=dots(true,true)
 assert(#mini>0)
 for _,dot in ipairs(mini) do eq(dot.width,7);assert((dot.x-90)^2+(dot.y+90)^2<=80^2) end
end
A.journey.index=2;A.DrawMap();A.DrawMinimap()
assert(#dots(false,true)==0 and #dots(true,true)==0)
A.journey={index=1,legs={ride("portal",first,first)}}
assert(#draw(1420,.2)==1);A.DrawMinimap();assert(#dots(true,true)==1)
A.journey=nil;A.DrawMap();A.DrawMinimap()
assert(#dots(false,true)==0 and #dots(true,true)==0)
A.journey={index=1,legs={ride("flight",stop(0,200,0),stop(1002,200,0))}}
local canvas=WorldMapFrame:GetCanvas()
function canvas:GetRect() return 0,0,1002,668 end
function canvas:GetEffectiveScale() return zoom end
function WorldMapFrame.ScrollContainer:GetRect() return 4800,3100,800,1000 end
local visible=draw(1420,8)
assert(#visible<=96 and visible[1].x>=594 and visible[#visible].x<=706)
WorldMapFrame.ScrollContainer.GetRect=nil;canvas.GetRect=nil;canvas.GetEffectiveScale=nil
A.journey=nil
worldMapID=1420;zoom=1
''')
check('flight connections draw a single connector and final arrival icon on both maps', '''
local function stop(x,y,map) return {x=-y,y=-x,map=map or 0} end
local function icon(marker,index,name)
 local texture=marker.badge.icons[index]
 assert(texture and texture:IsShown() and texture.texture:match("Step"..name.."%.tga$"))
end
local start,airport,transfer,landing,goal=stop(300,330),stop(430,330),stop(500,410),stop(650,330),stop(800,360)
A.route={status="transport"}
A.journey={index=1,legs={
 {kind="walk",from=start,to=airport},
 {kind="flight",from=airport,to=transfer,seconds=60},
 {kind="flight",from=transfer,to=landing,seconds=90},
 {kind="walk",from=landing,to=goal},
}}
for _,scale in ipairs({1,8}) do
 zoom=scale;A.DrawMap();local labels=steps();assert(#labels==3)
 eq(labels[1].x,430);eq(labels[2].x,650);eq(labels[3].x,800)
 eq(labels[2].y,-330);eq(labels[3].y,-360)
 icon(labels[1],1,"Run");icon(labels[2],1,"Flight");icon(labels[3],1,"Run")
 eq(labels[2].badge.scale*zoom,1);eq(labels[3].badge.scale*zoom,1)
 local blue=dots(false,true);assert(#blue>1)
 eq(blue[1].x,430);assert(650-blue[#blue].x<=10/scale+1e-6)
 for _,dot in ipairs(blue) do eq(dot.y,-330) end
end
zoom=.2;A.DrawMap();local labels=steps()
assert(#labels==3);icon(labels[1],1,"Run");icon(labels[2],1,"Flight")
A.player=p(500,410);viewRadius=100;rotating=false;A.DrawMinimap()
assert(#steps(true)==0,"A connecting flight master should have no minimap icon")
local miniBlue=dots(true,true);assert(#miniBlue>0)
for _,dot in ipairs(miniBlue) do eq(dot.y,-90+80*83/100) end
A.player=p(430,330);viewRadius=50;rotating=false;A.DrawMinimap()
assert(#steps(true)==0,"A departure in range should have no minimap icon")
A.player=p(700,330);viewRadius=120;A.DrawMinimap()
local mini=steps(true);assert(#mini==1)
icon(mini[1],1,"Flight");eq(mini[1].x,90-50*83/120);eq(mini[1].y,-90)
rotating=true;facing=math.pi/2;A.DrawMinimap();mini=steps(true)
eq(mini[1].x,90);eq(mini[1].y,-90+50*83/120)
A.journey.index=3;zoom=1;A.DrawMap();labels=steps()
local remaining=A.Transit.DisplayLegs(A.journey)[1]
assert(#labels==2 and remaining.from==airport and remaining.to==landing and remaining.seconds==90)
icon(labels[1],1,"Flight");eq(labels[1].x,650)
A.journey.index=4;zoom=1;A.DrawMap();labels=steps()
assert(#labels==1);icon(labels[1],1,"Run");eq(labels[1].x,800)
A.player=p(800,360);A.DrawMinimap();assert(#steps(true)==0)
worldMapID=947;A.DrawMap();labels=steps();assert(#labels==1 and labels[1].x>550)
worldMapID=1420;A.journey=nil
make({p(300,330),p(800,360)});A.DrawMap();A.DrawMinimap()
assert(#steps()==1 and #steps(true)==0);icon(steps()[1],1,"Run");eq(steps()[1].x,800)
A.arrived=true;A.DrawMap();assert(#steps()==0)
A.arrived=nil;A.DrawMap();assert(#steps()==1)
WorldMapFrame:Hide();assert(#steps()==0)
WorldMapFrame:Show();A.DrawMap();assert(#steps()==1)
for kind,name in pairs({boat="Boat",zeppelin="Zeppelin",tram="Tram",portal="Portal",skycutter="Skycutter",future="Transport"}) do
 A.journey={index=1,legs={{kind=kind,from=airport,to=landing}}}
 A.player=p(650,330);A.DrawMap();A.DrawMinimap()
 assert(#steps()==1);icon(steps()[1],1,name);eq(steps()[1].x,650)
 if kind=="boat" or kind=="zeppelin" or kind=="skycutter" then
  assert(#steps(true)==1);icon(steps(true)[1],1,name);eq(steps(true)[1].x,90)
 else assert(#steps(true)==0) end
end
A.journey={index=1,legs={{kind="zeppelin",name="Take the skycutter",from=airport,to=landing}}}
A.DrawMap();icon(steps()[1],1,"Skycutter")
A.journey=nil
''')
raw=(root/'Media/GoldBead.tga').read_bytes()
w,hgt,bpp,flags=struct.unpack_from('<HHBB',raw,12)
assert raw[2]==2 and (w,hgt,bpp,flags&15)==(32,32,32,8)
assert bytes([107,203,241,255]) in raw and bytes([15,32,53,255]) in raw and bytes([0,0,0,0]) in raw
checks.append('local game texture has alpha and the approved gold and bronze colors')
for name in ('Run','Flight','Boat','Zeppelin','Tram','Portal','Skycutter','Transport'):
    raw=(root/'Media'/f'Step{name}.tga').read_bytes()
    w,hgt,bpp,flags=struct.unpack_from('<HHBB',raw,12)
    assert raw[2]==2 and (w,hgt,bpp,flags&15)==(32,32,32,8)
    assert 0 in raw[21::4] and 255 in raw[21::4]
checks.append('all eight packaged step icons are transparent 32-bit game textures')

# Export the actual draw positions for comparison against the approved mockup.
reference=h.parent/'figma-route/route.json'
if reference.exists():
    points=json.loads(reference.read_text())['points']
    lua.globals().make(lua.table_from([lua.globals().p(x,y) for x,y in points]))
    lua.execute('A.DrawMap()')
    preview=[[t.x,-t.y] for t in lua.globals().dots(False).values()]
    (h/'route-beads-preview.json').write_text(json.dumps(preview))
result={'version':'2.0.2','checks':checks,'liveGameVerified':False}
(h/'route-beads-tests.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result))
