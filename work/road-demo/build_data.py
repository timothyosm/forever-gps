from pathlib import Path
import json

zones = [
    {'id':1420,'name':'Tirisfal Glades','subtitle':'Brill · Deathknell · Scarlet Monastery','bounds':[825,-1485,3837,3033]},
    {'id':1421,'name':'Silverpine Forest','subtitle':'The Sepulcher · Shadowfang · Ambermill','bounds':[-1133,-750,1667,3450]},
    {'id':1424,'name':'Hillsbrad Foothills','subtitle':'Tarren Mill · Southshore · Durnholde','bounds':[-1733,-2133,400,1067]},
]
roads=[]
def road(zone, ident, name, coords, kind='road'):
    roads.append({'id':ident,'zone':zone,'name':name,'kind':kind,
                  'points':[[float(n) for n in p.split(',')] for p in coords.split()]})

road(1420,'deathknell','Deathknell road','300,485 315,466 320,447 322,424 333,409 351,394 365,384 367,373 386,369 402,369 418,367 436,365')
road(1420,'brill-road','Road to Brill','436,365 450,376 468,383 485,388 503,389 523,377 535,363 549,355 570,348 588,347 603,350 611,359 618,370 629,375 639,386 640,399')
road(1420,'agamand','Agamand Mills road','436,365 433,353 430,340 432,318 443,310 458,305 472,295 480,281 486,265 491,250 493,238')
road(1420,'solliden','Solliden farm road','430,340 414,336 401,332 390,324 376,322 362,321 350,321')
road(1420,'western-loop','Western farm loop','390,324 391,344 401,355 402,369')
road(1420,'garrens','Garren’s Haunt trail','588,347 586,334 590,324 595,316 592,306 583,298 577,290 575,281 580,267 584,253 588,240','trail')
road(1420,'brill-inn','Brill inn approach','603,350 611,344 620,344','trail')
road(1420,'ruins','Ruins of Lordaeron road','640,399 626,406 618,416 618,430 621,441 618,454 619,467 620,479')
road(1420,'silverpine-exit','Silverpine approach','626,406 611,414 594,419 577,427 565,435 559,449 557,468 550,480 544,482')
road(1420,'bulwark','The Bulwark road','640,399 663,399 687,404 710,416 731,433 752,450 774,467 795,480 813,480 835,475 852,471')
road(1420,'balnir','Balnir Farmstead approach','731,433 746,418 758,413 770,399','trail')
road(1420,'scarlet','Scarlet Monastery trail','640,399 663,391 686,386 707,376 724,356 738,339 744,325 764,316 784,310 800,299 812,285 814,268 826,256 834,242','trail')
road(1420,'crusader','Crusader Outpost trail','724,356 746,360 766,366 791,372','trail')
road(1420,'scarlet-watch','Scarlet Watch Post trail','784,310 782,296 777,282','trail')
road(1420,'manor','Cold Hearth Manor approach','535,363 536,379 532,398','trail')

road(1421,'silverpine-north','Northern Silverpine road','684.405,0.63 682,19 674,34 660,47 645,54 625,61 603,67 585,76 568,90 555,107 548,122 535,139 526,153 516,169 509,186 498,205 496,224')
road(1421,'silverpine-central','The Sepulcher road','496,224 503,240 513,251 523,264 529,283 530,302 526,317 521,336 520,357 523,378 529,399 537,421 539,445 538,466 535,484')
road(1421,'silverpine-south','Road to Hillsbrad','535,484 543,499 556,510 577,518 599,521 621,523 642,526')
road(1421,'sepulcher','The Sepulcher approach','513,251 490,258 475,267 462,277 448,282 431,277')
road(1421,'ivars','Ivar’s Patch trail','548,122 533,137 523,143 503,151 485,145 474,135 457,136','trail')
road(1421,'olsen','Northern farm trail','585,76 578,70 570,73','trail')
road(1421,'farmstead','Farmstead trail','516,169 532,165 540,166','trail')
road(1421,'pyrewood-east','Pyrewood road','535,484 514,480 493,479 479,475 470,462 469,450')
road(1421,'pyrewood-loop','Pyrewood village loop','469,450 461,458 455,471 441,476 434,491 447,503 465,509 483,503 495,490 514,480')
road(1421,'shadowfang','Shadowfang Keep approach','461,458 445,458 432,452 420,450','trail')
road(1421,'ambermill','Ambermill road','537,421 559,423 583,424 608,422 632,422')
road(1421,'ambermill-south','Southern Ambermill road','608,422 614,441 621,463 627,484 632,505 642,526')
road(1421,'deep-elem','Deep Elem trail','520,357 508,366 495,366 491,348','trail')

# The western point and its Silverpine counterpart share world coordinates.
b=zones[1]['bounds']; north=b[2]-(526/668)*(b[2]-b[0]); west=b[3]-(642/1002)*(b[3]-b[1])
h=zones[2]['bounds']; hx=(h[3]-west)/(h[3]-h[1])*1002; hy=(h[2]-north)/(h[2]-h[0])*668
road(1424,'hillsbrad-west','Western Hillsbrad road',f'{hx},{hy} 116,304 144,308 171,308 197,311 221,314 243,321 267,326 291,332 319,333 342,329 367,320 391,310 417,297 442,281 467,267 489,262 516,262 540,255 562,249 578,246')
road(1424,'hillsbrad-east','Road over the river bridge','578,246 592,257 608,266 625,275 640,280 658,283 678,293 701,306 724,320 746,333 768,347 791,359 812,368')
road(1424,'tarren-mill','Tarren Mill road','562,249 558,229 555,209 554,188 554,165 557,146 565,132 581,130 590,143 605,141 618,134 632,132')
road(1424,'alterac','Northern Alterac road','557,146 551,124 552,106 551,82 542,62 542,43 535,29')
road(1424,'southshore','Southshore road','516,262 509,282 508,303 507,325 506,348 502,369 500,390 500,410 500,431 500,449')
road(1424,'hillsbrad-fields','Hillsbrad Fields trail','319,333 318,320 322,306 325,289 325,272 333,259 332,242','trail')
road(1424,'azurelode','Azurelode Mine approach','267,326 265,349 260,370 253,388 250,401 252,413','trail')
road(1424,'durnholde','Durnholde Keep approach','724,320 731,309 738,298 749,288 760,282 769,276','trail')
road(1424,'dun-garok','Dun Garok trail','812,368 802,386 788,400 775,414 760,428 746,439 731,456 718,473 705,487 690,494 677,499','trail')

places=[]
def place(id,zone,name,x,y,kind='place',quest=None):
    places.append(dict(id=id,zone=zone,name=name,x=x,y=y,kind=kind,quest=quest))
place('brill',1420,'Brill',611,344,'hub','A Rogue’s Deal — turn in')
place('lordaeron',1420,'Ruins of Lordaeron',620,479,'hub')
place('deathknell',1420,'Deathknell',322,424,'hub')
place('agamand',1420,'Agamand Mills',493,238,'quest','The Mills Overrun — objective area')
place('scarlet',1420,'Scarlet Monastery approach',834,242,'quest','Example destination — entrance approach')
place('bulwark',1420,'The Bulwark',852,471,'place')
place('balnir',1420,'Balnir Farmstead',770,399,'quest','Illustrative quest destination')
place('solliden',1420,'Solliden Farmstead',350,321,'quest','Fields of Grief — objective area')
place('sepulcher',1421,'The Sepulcher',431,277,'hub')
place('shadowfang',1421,'Shadowfang Keep approach',420,450,'quest','Example destination — entrance approach')
place('pyrewood',1421,'Pyrewood Village',447,503,'quest','Illustrative quest destination')
place('ambermill',1421,'Ambermill',632,422,'quest','Illustrative quest destination')
place('ivars',1421,'Ivar’s Patch',457,136,'place')
place('tarren',1424,'Tarren Mill',632,132,'hub')
place('southshore',1424,'Southshore',500,390,'hub')
place('fields',1424,'Hillsbrad Fields',332,242,'quest','Battle of Hillsbrad — objective area')
place('durnholde',1424,'Durnholde Keep approach',769,276,'quest','Example destination — entrance approach')
place('azurelode',1424,'Azurelode Mine approach',252,413,'place')
place('dungarok',1424,'Dun Garok approach',677,499,'place')

data={'version':1,'width':1002,'height':668,'zones':zones,'roads':roads,'places':places,
 'links':[{'id':'tirisfal-silverpine','from':[1420,544,482],'to':[1421,684.405,0.63],'name':'Tirisfal ↔ Silverpine'},
          {'id':'silverpine-hillsbrad','from':[1421,642,526],'to':[1424,hx,hy],'name':'Silverpine ↔ Hillsbrad'}],
 'provenance':{'roads':'Original manual tracing from the supplied zone artwork. Approximate, not verified against in-game collision.',
 'mapArtwork':'© Blizzard Entertainment; Forever build 1.60.1.69893, served by Warcraft Forever.',
 'maps':'https://warcraftforever.games/maps/tirisfal-glades',
 'bounds':'https://github.com/cjber/shortest-path-forever/blob/660e14a81724560abba1d619d9e791b72b136f86/Data/Zones.lua',
 'questPins':'Illustrative area/approach pins. Not live quest POIs or authoritative NPC positions.'}}
Path(__file__).with_name('data.json').write_text(json.dumps(data,separators=(',',':')))
print(f'{len(roads)} traced roads/trails; {sum(len(r["points"]) for r in roads)} control points; {len(places)} places')
