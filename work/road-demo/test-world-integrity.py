from pathlib import Path
from lupa.lua51 import LuaRuntime
import base64,csv,json,zlib,time
h=Path(__file__).resolve().parent;root=h.parent/'world-addon';l=LuaRuntime(encoding=None)
l.execute(b'A={};C_Timer={After=function() end}')
for name in json.loads((h/'terrain-toc.json').read_text()):
 if not name.startswith(('Terrain/Nav','Terrain/Choke','Terrain/ExtraChoke')):continue
 l.execute(b'local f=function(...)\n'+(root/name).read_bytes()+b'\nend;f("ForeverRoads",A)')
native={int(m['ID']) for m in csv.DictReader((h/'UiMap-70862.csv').open()) if int(m['Type']) in [3,6]}
catalog=json.loads((h/'all-zone-catalog.json').read_text())
assert native=={m['id'] for m in catalog['maps']} and len(native)==55
maps=[];start=time.perf_counter()
for map,data in sorted(l.globals()[b'ForeverRoadsTerrainData'].items()):
 entry={'map':map,'fields':{},'blocks':0,'decodedBytes':0}
 for field,want in data[b'counts'].items():
  records=data[b'packed'][field];assert len(list(records.keys()))==want
  entry['fields'][field.decode()]=want
  for key,blocks in records.items():
   assert isinstance(key,(int,float)) and 1<=key<=data[b'nx']*data[b'ny']
   assert len(blocks)>0
   for block in blocks.values():
    encoded=block if data[b'blocks']==b'zlib' else base64.b64decode(block,validate=True)
    decoder=zlib.decompressobj();raw=decoder.decompress(encoded)+decoder.flush()
    assert decoder.eof and not decoder.unused_data and raw
    entry['blocks']+=1;entry['decodedBytes']+=len(raw)
 maps.append(entry)
result={'clientMapIDsComplete':True,'zoneMapCount':55,'terrainMaps':maps,'seconds':time.perf_counter()-start,'allCompressedBlocksValid':True,'liveGameVerified':False}
(h/'world-integrity-tests.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
