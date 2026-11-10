from pathlib import Path
import json,hashlib
h=Path(__file__).resolve().parent;root=h.parent;src=root/'world-map-bake/packed/Nav';dest=root/'world-addon/Terrain';toc=json.loads((h/'terrain-toc.json').read_text())
names=[]
for map in [30,489,529,2997]:
 names.append(f'Nav{map}.lua');names.extend(p.name for p in sorted(src.glob(f'Nav{map}_*.lua'),key=lambda p:int(p.stem.split('_')[1])))
names.append('Chokepoints.lua')
for name in names:
 data=(src/name).read_bytes().replace(b'PolestarPathData',b'ForeverRoadsTerrainData').replace(b'PolestarNavChokepoints',b'ForeverRoadsChokepoints')
 target=name if name!='Chokepoints.lua' else 'ExtraChokepoints.lua';(dest/target).write_bytes(data)
 if 'Terrain/'+target not in toc:toc.append('Terrain/'+target)
(h/'terrain-toc.json').write_text(json.dumps(toc,indent=2)+'\n')
# Rebuild from complete lines: substring replacement also matched WorldNavigation.lua.
p=root/'world-addon/ForeverRoads.toc'
headers='\n'.join(line for line in p.read_text().splitlines() if line.startswith('##'))
modules=['Data.lua','Router.lua','WorldData.lua','WorldPlaces.lua','TransitData.lua','Transit.lua']+toc+['Navigation.lua','Map.lua','UI.lua','Performance.lua','WorldNavigation.lua','Core.lua']
p.write_text(headers+'\n\n'+'\n'.join(modules)+'\n')
print('Added four current-client terrain maps and their navigation surfaces.')
