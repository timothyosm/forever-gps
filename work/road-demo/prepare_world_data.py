from pathlib import Path
import csv,json
here=Path(__file__).resolve().parent;root=here.parent/'world-map-bake/data/forever';root.mkdir(parents=True,exist_ok=True)
maps=list(csv.DictReader((here/'UiMap-70862.csv').open()));assign=list(csv.DictReader((here/'UiMapAssignment-70862.csv').open()));frames={};zones={}
for m in maps:
 id=m['ID'];zones[id]={'name':m['Name_lang'],'type':int(m['Type'])}
 parts=[a for a in assign if a['UiMapID']==id]
 if not parts:continue
 p=parts[0];frames[id]={'c':int(p['MapID']),'top':float(p['Region_3']),'bottom':float(p['Region_0']),'left':float(p['Region_4']),'right':float(p['Region_1'])}
(root/'map-frames.json').write_text(json.dumps({'era':{},'forever':frames})+'\n');(root/'zones.json').write_text(json.dumps(zones)+'\n')
print('Prepared client map frames and zone names.')
