from pathlib import Path
import json

here=Path(__file__).resolve().parent
data=json.loads((here/'data.json').read_text())
for zone in data['zones']:
    zone['continent']=0
stone=json.loads((here/'stonetalon-data.json').read_text())
data['zones'].append(stone['zone'])
data['roads'].extend(stone['roads'])
data['places'].extend(stone['places'])
data['version']=2
(here/'addon-data.json').write_text(json.dumps(data)+'\n')
def lua(v):
    if v is None:return 'nil'
    if isinstance(v,bool):return 'true' if v else 'false'
    if isinstance(v,(int,float)):return repr(v)
    if isinstance(v,str):return json.dumps(v,ensure_ascii=False)
    if isinstance(v,list):return '{'+','.join(lua(x) for x in v)+'}'
    return '{'+','.join('['+lua(k)+']='+lua(x) for k,x in v.items())+'}'
out=here.parents[1]/'outputs/ForeverRoads/Data.lua'
out.write_text('-- Original manually traced road network from the HTML proof of concept.\n-- Map art is not redistributed; the addon draws on the game maps.\nlocal _, A = ...\nA.Data = '+lua(data)+'\n')
print('Generated',out)
