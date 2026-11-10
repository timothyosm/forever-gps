"""List every playable zone map in the installed Forever build, using client tables."""
from pathlib import Path
import csv,json
here=Path(__file__).resolve().parent
maps=list(csv.DictReader((here/'UiMap-70862.csv').open()))
assignments=list(csv.DictReader((here/'UiMapAssignment-70862.csv').open()))
zones=[]
for m in maps:
 if int(m['Type']) not in [3,6]:continue
 parts=[a for a in assignments if a['UiMapID']==m['ID']]
 assert parts,m
 a=parts[0]
 zones.append(dict(id=int(m['ID']),name=m['Name_lang'],mapType=int(m['Type']),parent=int(m['ParentUiMapID']),continent=int(a['MapID']),areaID=int(a['AreaID']),
  bounds=[float(a['Region_0']),float(a['Region_1']),float(a['Region_3']),float(a['Region_4'])],source='UiMap and UiMapAssignment, installed client 1.60.1.70862'))
result=dict(build='1.60.1.70862',source='https://wago.tools/db2/UiMap/csv?build=1.60.1.70862',maps=zones)
(here/'all-zone-catalog.json').write_text(json.dumps(result,indent=2)+'\n')
print(len(zones),'playable maps:',len([z for z in zones if z['mapType']==3]),'zone/city maps and',len([z for z in zones if z['mapType']==6]),'battleground/island maps.')
