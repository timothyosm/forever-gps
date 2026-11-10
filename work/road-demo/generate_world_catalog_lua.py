from pathlib import Path
import json
h=Path(__file__).resolve().parent;d=json.loads((h/'all-zone-catalog.json').read_text());out=h.parent/'world-addon/WorldData.lua'
def lua(v):
 if v is None:return 'nil'
 if isinstance(v,bool):return str(v).lower()
 if isinstance(v,(float,int)):return repr(v)
 if isinstance(v,str):return json.dumps(v,ensure_ascii=False)
 if isinstance(v,list):return '{'+','.join(map(lua,v))+'}'
 return '{'+','.join('['+lua(k)+']='+lua(value) for k,value in v.items())+'}'
for z in d['maps']:z['title']=z['name'];z['city']=z['id'] in [1453,1454,1455,1456,1457,1458]
out.write_text('-- Generated from the installed Forever client map tables, build '+d['build']+'.\nlocal _,A=...\nA.WorldCatalog='+lua(d)+'\nA.ZoneByID={}\nfor _,zone in ipairs(A.WorldCatalog.maps) do A.ZoneByID[zone.id]=zone end\nA.Data.zones=A.WorldCatalog.maps\n')
print('Generated',len(d['maps']),'map definitions.')
