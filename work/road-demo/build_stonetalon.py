"""Original hand tracing of the 1002x668 Forever Stonetalon map.
Unpictured access paths are explicitly estimated, never called surveyed roads.
"""
from pathlib import Path
import json
here=Path(__file__).resolve().parent
roads=[]
def road(id,name,kind,points):
    roads.append(dict(id='stone-'+id,zone=1442,name=name,kind=kind,points=points))
road('south','Greatwood Vale road','road',[[817,667],[810,643],[804,620],[791,607],[775,596],[758,591],[744,590],[728,586],[714,580],[699,578],[686,578],[669,569],[651,559],[637,551],[623,541],[612,530],[602,519],[597,505],[597,492],[598,475]])
road('webwinder','Webwinder Path','road',[[598,475],[590,465],[584,449],[573,439],[558,431],[546,425],[539,421],[533,411],[531,403],[532,384],[528,373],[524,362],[527,347],[522,337],[516,326],[506,318],[495,312],[475,306],[464,298],[461,292],[457,280],[459,260],[467,242]])
road('peak','Stonetalon Peak trail','trail',[[467,242],[470,228],[468,211],[466,195],[461,181],[455,169],[451,151],[448,137],[443,126],[435,118],[428,115],[417,112],[408,112],[398,119],[387,124],[379,126],[366,129],[354,128],[343,126],[333,122],[324,116],[320,109],[314,101],[300,98]])
road('charred','Charred Vale trail','trail',[[457,280],[440,281],[421,280],[405,280],[391,282],[379,291],[373,306],[368,324],[366,346],[361,364],[352,383],[343,403],[334,421],[327,439],[321,460],[317,480],[307,494],[300,510],[288,526],[285,548],[279,570]])
road('sunrock','Sun Rock Retreat access (estimated)','estimated',[[532,384],[520,389],[508,398],[494,409],[480,414],[466,410],[455,399],[463,391]])
road('windshear-entry','Windshear approach trail','trail',[[598,475],[607,463],[614,447],[620,431],[626,413]])
road('windshear','Windshear Crag access (estimated)','estimated',[[626,413],[629,400],[637,385],[645,374],[652,365],[659,354],[665,346]])
road('windshear-west','Western Windshear access (estimated)','estimated',[[645,374],[628,370],[614,360],[603,351],[595,347],[591,333]])
road('windshear-east','Eastern Windshear access (estimated)','estimated',[[665,346],[680,348],[695,353],[710,362],[725,378],[742,392]])
road('ziz','Ziz Fizziks access (estimated)','estimated',[[626,413],[611,416],[595,418]])
road('boulderslide','Boulderslide entrance access (estimated)','estimated',[[714,580],[722,595],[724,614],[726,634]])
road('sishir','Sishir Canyon approach (estimated)','estimated',[[602,519],[591,524],[577,531],[562,538]])
places=[]
def place(id,name,x,y):places.append(dict(id=id,zone=1442,name=name,x=x,y=y))
place('sun-rock','Sun Rock Retreat',463,391)
place('windshear','Windshear Crag',665,346)
place('ziz-fizziks','Ziz Fizziks approach',595,418)
place('stonetalon-peak','Stonetalon Peak approach',366,129)
place('charred-vale','The Charred Vale',317,480)
place('mirkfallon','Mirkfallon Lake road',467,242)
place('greatwood','Greatwood Vale',686,578)
place('boulderslide','Boulderslide cave approach',726,634)
place('sishir','Sishir Canyon approach',562,538)
place('barrens-border','Barrens border approach',810,643)
place('desolace-border','Desolace border approach',279,570)
data=dict(zone=dict(id=1442,name='Stonetalon Mountains',shortName='Stonetalon',subtitle='Sun Rock Retreat · Windshear Crag · Stonetalon Peak',continent=1,bounds=[-340,-1637,2917,3246]),roads=roads,places=places)
(here/'stonetalon-data.json').write_text(json.dumps(data,indent=2)+'\n')
print(len(roads),'Stonetalon roads/trails/access paths;',len(places),'destinations')
