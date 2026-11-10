from pathlib import Path
from lupa.lua51 import LuaRuntime
import json,math,random,time
h=Path(__file__).resolve().parent;l=LuaRuntime(unpack_returned_tuples=True,encoding=None)
l.execute(b'A={};local f=function(...)\n'+(h.parent/'world-addon/Map.lua').read_bytes()+b'\nend;f("ForeverRoads",A)')
l.execute(b'''
function makeRoute(points,kind)
 local r={segments={},distance=0}
 for i=1,#points-1 do local a,b=points[i],points[i+1];local d=math.sqrt((a.wx-b.wx)^2+(a.wy-b.wy)^2+((a.z or 0)-(b.z or 0))^2)
  r.segments[i]={from=a,to=b,kind=kind or "terrain",name="Test path",begin=r.distance,finish=r.distance+d,length=d};r.distance=r.distance+d
 end;return r
end
''')
def route(points,kind='terrain'):
 return l.eval(b'makeRoute')(l.table_from([l.table_from({b'wx':p[0],b'wy':p[1],b'z':p[2] if len(p)>2 else 0,b'continent':0}) for p in points]),kind.encode())
def plain(r):
 return [((s[b'from'][b'wx'],s[b'from'][b'wy'],s[b'from'][b'z'],s[b'from'][b'continent']),
          (s[b'to'][b'wx'],s[b'to'][b'wy'],s[b'to'][b'z'],s[b'to'][b'continent']),s[b'begin'],s[b'finish'],s[b'kind']) for s in r[b'segments'].values()]
def build(r,sx=1,sy=1,radius=8,deviation=1.25):return l.globals()[b'A'][b'SmoothRouteSegments'](r,sx,sy,radius,deviation)
def distance(p,a,b):
 dx,dy=b[0]-a[0],b[1]-a[1];t=max(0,min(1,((p[0]-a[0])*dx+(p[1]-a[1])*dy)/max(dx*dx+dy*dy,1e-16)))
 return math.hypot(p[0]-a[0]-t*dx,p[1]-a[1]-t*dy)
checked=0
def verify(points,sx=1,sy=1,radius=8,deviation=1.25):
 global checked
 original=route(points);before=plain(original);segments,count=build(original,sx,sy,radius,deviation)
 assert plain(original)==before,'Navigation route mutated'
 assert len(segments)<=5*len(before)
 if before:
  assert segments[1][b'from'][b'wx']==points[0][0] and segments[len(segments)][b'to'][b'wy']==points[-1][1]
  assert abs(segments[1][b'begin'])<1e-9 and abs(segments[len(segments)][b'finish']-original[b'distance'])<1e-6
  assert segments[1][b'capStart'] is None and segments[len(segments)][b'capEnd'] is None
 for i,s in segments.items():
  assert s[b'finish']>=s[b'begin'] and s[b'from'][b'continent']==s[b'to'][b'continent']==0
  if i>1:
   previous=segments[i-1];assert abs(previous[b'finish']-s[b'begin'])<1e-6
   assert abs(previous[b'to'][b'wx']-s[b'from'][b'wx'])<1e-8 and abs(previous[b'to'][b'wy']-s[b'from'][b'wy'])<1e-8
   if s[b'capStart'] is not None:
    assert 0<=s[b'capStart']<=.7 and previous[b'capEnd']==s[b'capStart']
  for t in [0,.125,.25,.5,.75,.875,1]:
   a,b=s[b'from'],s[b'to'];p=((a[b'wx']+(b[b'wx']-a[b'wx'])*t)*sx,(a[b'wy']+(b[b'wy']-a[b'wy'])*t)*sy)
   d=min(distance(p,(a[0]*sx,a[1]*sy),(b[0]*sx,b[1]*sy)) for a,b,*_ in before)
   assert d<=deviation+1e-7,(d,deviation,p)
   checked+=1
 return segments,count
segments,count=verify([(0,0),(40,0),(40,40)]);assert count==1 and len(segments)>2
assert any(0<s[b'to'][b'wy']<5 and 35<s[b'to'][b'wx']<40 for s in segments.values())
verify([(0,0),(20,0),(20,35),(65,35)],.35,2.8)
verify([(0,0),(40,0),(40,40)],.4,.4,4,.65)
for kind in ['lift','border','estimated','approach']:
 r=route([(0,0),(40,0),(40,40)],kind);s,n=build(r);assert n==0 and len(s)==2
for points in [[(0,0),(20,0),(0,0)],[(0,0),(.05,0),(.05,.05)],[(0,0),(20,0),(40,0)]]:
 s,n=build(route(points));assert n==0
l.execute(b'''
local r=makeRoute({{wx=0,wy=0,continent=0},{wx=20,wy=0,continent=0},{wx=20,wy=20,continent=0}})
r.segments[2].from={wx=21,wy=0,continent=0};local _,n=A.SmoothRouteSegments(r,1,1,8,1.25);assert(n==0)
r.segments[2].from=r.segments[1].to;r.segments[2].to.continent=1;_,n=A.SmoothRouteSegments(r,1,1,8,1.25);assert(n==0)
r.segments[2].to.continent=0;r.segments[1].to.z=0;r.segments[2].from={wx=20,wy=0,z=40,continent=0}
_,n=A.SmoothRouteSegments(r,1,1,8,1.25);assert(n==0)
''')
random.seed(814)
for i in range(180):
 points=[(0,0)];angle=0
 for j in range(12):
  angle+=random.uniform(-2.7,2.7);length=random.uniform(.03,65)
  points.append((points[-1][0]+math.cos(angle)*length,points[-1][1]+math.sin(angle)*length))
 verify(points,random.uniform(.05,3),random.uniform(.05,3))
stress=route([(i*3,10*math.sin(i*.8)) for i in range(1000)])
start=time.perf_counter();result,corners=build(stress,.2,.2);ms=(time.perf_counter()-start)*1000
report={'roundedRightAngle':True,'navigationUnchanged':True,'endpointsAndProgressPreserved':True,'noRoundingAcrossGapsFloorsOrTransport':True,
 'metricBoundsChecked':checked,'randomRoutes':180,'maximumWorldDeviationPixels':1.25,'maximumMinimapDeviationPixels':.65,
 'stress':{'originalSegments':999,'displaySegments':len(result),'corners':corners,'buildMS':ms},'liveGameControlled':False}
(h/'route-smoothing-tests.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
