"""Embed the GPL terrain router and explicitly licensed navigation maps.
All changes are mechanical namespace/packaging changes, recorded in the manifest.
"""
from pathlib import Path
import json,hashlib,re,shutil
here=Path(__file__).resolve().parent;root=here.parent;source=root/'polestar/addon';dest=root/'world-addon';terrain=dest/'Terrain';terrain.mkdir(exist_ok=True)
records=[];toc=[]
def put(p,name=None,strip_part=False):
 data=p.read_bytes();patched=data.replace(b'PolestarPathData',b'ForeverRoadsTerrainData').replace(b'PolestarNavChokepoints',b'ForeverRoadsChokepoints').replace(b'Polestar_NavCosts',b'ForeverRoadsCosts')
 if strip_part:patched=re.sub(rb'\tpart = "[^"]+",\n',b'',patched)
 # Keep all original copyright/license headers; identify our change.
 patched=b'-- ForeverRoads: embedded copy; namespace and packaging adapted 2026-11-08.\n'+patched
 name=name or p.name;(terrain/name).write_bytes(patched);toc.append('Terrain/'+name)
 records.append(dict(source=str(p.relative_to(root/'polestar')),target='Terrain/'+name,sourceSHA256=hashlib.sha256(data).hexdigest(),installedSHA256=hashlib.sha256(patched).hexdigest()))
for map in [0,1,2991]:
 put(source/f'Polestar_Nav/Nav/Nav{map}.lua',strip_part=True)
 partdir=source/('Polestar_Nav_EK' if map==0 else 'Polestar_Nav_Kalimdor' if map==1 else 'Polestar_Nav/Nav')
 for p in sorted(partdir.glob(f'Nav{map}_*.lua'),key=lambda p:int(p.stem.split('_')[1])):put(p)
put(source/'Polestar_Nav/Nav/Chokepoints.lua')
for name in ['Costs','PathGrid','Path','PathJobs']:put(source/f'Polestar_Nav/Routing/{name}.lua')
shutil.copyfile(source/'Polestar_Nav/LICENSE',terrain/'LICENSE');shutil.copyfile(source/'Polestar_Nav/CREDITS.md',terrain/'UPSTREAM-CREDITS.md')
(dest/'LICENSE').write_bytes((source/'Polestar_Nav/LICENSE').read_bytes())
(terrain/'PROVENANCE.json').write_text(json.dumps({'project':'https://github.com/fitzforge/polestar','revision':'f174784d71856460b9fdef9ff9b7dc24519152fe','license':'GPL-3.0-or-later','files':records},indent=2)+'\n')
(here/'terrain-toc.json').write_text(json.dumps(toc,indent=2)+'\n')
print('Embedded',len(toc),'files;',round(sum((terrain/Path(p).name).stat().st_size for p in toc)/1024/1024,1),'MB of source, compressed terrain and router.')
