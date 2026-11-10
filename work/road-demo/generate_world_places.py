from pathlib import Path
import json
h=Path(__file__).resolve().parent
catalog={z['id']:z for z in json.loads((h/'all-zone-catalog.json').read_text())['maps']}
audit=json.loads((h/'world-coverage-audit.json').read_text())
assert len(audit['maps'])==55 and all(z['routeChecked'] for z in audit['maps'])
lines=['-- Terrain-checked waypoints; generated from the coverage audit, not guessed landmarks.','local _,A=...']
for z in audit['maps']:
 a,b,c,d=catalog[z['id']]['bounds']
 for i,p in enumerate(z['checkedPair'],1):
  x=(d-p['y'])/(d-b)*1002;y=(c-p['x'])/(c-a)*668
  assert 0<=x<=1002 and 0<=y<=668
  lines.append('A.Data.places[#A.Data.places+1]={zone=%d,x=%.9f,y=%.9f,z=%s,name="Path waypoint %d"}'%(z['id'],x,y,p['z'],i))
(h.parent/'world-addon/WorldPlaces.lua').write_text('\n'.join(lines)+'\n')
print('Added 110 terrain-checked waypoints covering all 55 zone maps.')
