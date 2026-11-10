from pathlib import Path
import json,zlib,base64,time
from lupa.lua51 import LuaRuntime
here=Path(__file__).resolve().parent;root=here.parent/'world-addon';lua=LuaRuntime(unpack_returned_tuples=True,encoding=None)
lua.execute(b'A={};Enum={CompressionMethod={Zlib=0}};function InCombatLockdown() return false end; C_EncodingUtil={}')
g=lua.globals();g[b'pydecode']=lambda s:base64.b64decode(s);g[b'pyinflate']=lambda s,m:zlib.decompress(s);g[b'pyclock']=lambda:time.perf_counter()*1000
lua.execute(b'C_EncodingUtil.DecodeBase64=pydecode;C_EncodingUtil.DecompressString=pyinflate;debugprofilestop=pyclock;C_Timer={After=function() end}')
start=time.perf_counter()
for name in json.loads((here/'terrain-toc.json').read_text()):lua.execute(b'local f=function(...)\n'+(root/name).read_bytes()+b'\nend;f("ForeverRoads",A)')
print('Loaded terrain in',round(time.perf_counter()-start,2),'seconds',flush=True)
lua.execute(b'A.Path.budget=1.5;function point(x,y,z) return {x=x,y=y,z=z} end')
fn=lua.eval(b'function(map,x1,y1,x2,y2) return A.Path.FindSync(map,point(x1,y1),point(x2,y2),{profile="Horde",style="roads"}) end')
# Stonetalon uses north/west UnitPosition coordinates.
catalog=json.loads((here/'all-zone-catalog.json').read_text())['maps'];z=next(z for z in catalog if z['id']==1442)
def world(z,x,y):
 a,b,c,d=z['bounds'];return c+(a-c)*y/100,d+(b-d)*x/100
s=world(z,63.8,55.9);t=world(z,46.2,58.5)
start=time.perf_counter();result=fn(1,*s,*t);points,cost,expansions,job=result
print('Stonetalon:',len(points) if points else None,cost,expansions,'in',round(time.perf_counter()-start,3),'seconds',flush=True)
assert points is not None and isinstance(cost,(float,int))
(here/'world-engine-smoke.json').write_text(json.dumps({'terrainFiles':len(json.loads((here/'terrain-toc.json').read_text())),'stonetalon':{'points':len(points),'weightedCost':cost,'expansions':expansions},'sourceBuild':'1.60.1.70532','liveGameVerified':False},indent=2)+'\n')
lua.execute(b'''
combat=false;queue={};events={};A.Path.budget=1
function InCombatLockdown() return combat end
function CreateFrame() local f={};function f:SetScript(k,fn) self[k]=fn end;function f:RegisterEvent(k) events[k]=self end;function f:UnregisterEvent(k) events[k]=nil end;return f end
function geterrorhandler() return function(err) error(err) end end
A.Path.after=function(fn) queue[#queue+1]=fn end
function step() local fn=table.remove(queue,1);if fn then fn();return true end end
function begin(map,x1,y1,x2,y2)
 answer=nil
 return A.Path.Find(map,point(x1,y1),point(x2,y2),function(points,cost,job) answer={points=points,cost=cost,frames=job.frames,cpu=job.cpu} end,{profile="Horde",style="roads"})
end
''')
lua.execute(b'A.Path.ClearCaches()')
start=time.perf_counter();job=lua.eval(b'begin')(1,*s,*t);slices=[]
while len(lua.globals()[b'queue']):
 st=time.perf_counter();lua.eval(b'step')();slices.append((time.perf_counter()-st)*1000)
 assert len(slices)<10000
answer=lua.globals()[b'answer'];assert answer and answer[b'points']
async_result={'frames':answer[b'frames'],'cpuMS':answer[b'cpu'],'peakPumpMS':max(slices),'medianPumpMS':sorted(slices)[len(slices)//2]}
print('Async:',json.dumps(async_result),flush=True)
report=json.loads((here/'world-engine-smoke.json').read_text());report['asynchronous']=async_result
(here/'world-engine-smoke.json').write_text(json.dumps(report,indent=2)+'\n')
