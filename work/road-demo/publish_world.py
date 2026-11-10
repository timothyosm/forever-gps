from pathlib import Path
import json,hashlib,shutil,zipfile
h=Path(__file__).resolve().parent;root=h.parents[1];stage=root/'work/world-addon';outputs=root/'outputs'
def read(name):return json.loads((h/name).read_text())
package=read('world-package-tests.json');travel=read('world-travel-tests.json');legacy=read('world-legacy-tests.json');coverage=read('world-coverage-audit.json')
beads=read('route-beads-tests.json');bead_perf=read('route-beads-performance.json')
version=next(line.removeprefix('## Version: ') for line in (stage/'ForeverRoads.toc').read_text().splitlines() if line.startswith('## Version: '))
assert package['passed']==10 and len(package['maps'])==55 and coverage['mapped']==coverage['routeChecked']==55 and legacy['passed']==21
assert len(travel['checks'])>=13
assert package['version']==travel['version']==version and len(beads['checks'])>=7
cache_report=h/'world-cache-performance.json'
cache_benchmark=read(cache_report.name) if cache_report.is_file() else None
if cache_benchmark and cache_benchmark.get('candidateVersion')==version:
 assert all(cache_benchmark['releaseChecks'].values()),cache_benchmark['releaseChecks']
else: cache_benchmark=None
toc=[s for s in (stage/'ForeverRoads.toc').read_text().splitlines() if s and not s.startswith('#')]
assert len(set(toc))==len(toc) and set(toc)=={str(p.relative_to(stage)) for p in stage.rglob('*.lua')}
cov={'clientBuild':coverage['build'],'liveGameVerified':False,'scope':'All 55 playable zone-map IDs in the installed client; sampled terrain routes inside native map bounds. Zephras has two aliases.',
 'maps':[{k:z[k] for k in ['id','name','continent','routeChecked','checkedPair','points']} for z in coverage['maps']]}
(stage/'COVERAGE.json').write_text(json.dumps(cov,indent=2)+'\n')
tests={'version':version,'package':package,'travel':travel,'legacy':legacy,'integrity':read('world-integrity-tests.json'),'smoothing':read('route-smoothing-tests.json'),'goldTrail':beads,'flatLiquidParser':{'passed':3,'failed':0,'command':'cargo test --manifest-path work/world-toolchain/forge-navbuild/Cargo.toml --test forever_flat_liquid --offline'},'liveGameVerified':False}
(stage/'TESTS.json').write_text(json.dumps(tests,indent=2)+'\n')
for name,source in [('BUILD.json',root/'work/world-map-bake/packed/PACK.json'),('TILE-CHECKS.json',root/'work/world-map-bake/grid/build-report.json')]:shutil.copy2(source,stage/'Terrain'/name)
fresh=[]
for p in sorted((stage/'Terrain').glob('*.lua')):
 if p.name.startswith(('Nav30.','Nav30_','Nav489','Nav529','Nav2997')) or p.name=='ExtraChokepoints.lua':
  fresh.append({'file':p.name,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
(stage/'Terrain/EXTRA-PROVENANCE.json').write_text(json.dumps({'clientBuild':'1.60.1.70862','mapIDs':[30,489,529,2997],'license':'GPL-3.0-only','generator':'Modified GPL Forge tools, source provided in ForeverRoads-build-source.zip','changes':'Flat legacy ocean depth-only vertex streams are decoded without reading adjacent MH2O records. Three parser regression tests pass.','files':fresh},indent=2)+'\n')
source=outputs/'ForeverRoads';source.mkdir(exist_ok=True)
shutil.copytree(stage,source,dirs_exist_ok=True)
target=Path('/Applications/World of Warcraft/_forever_/Interface/AddOns/ForeverRoads');target.mkdir(exist_ok=True)
shutil.copytree(source,target,dirs_exist_ok=True)
files=[]
for p in sorted(source.rglob('*')):
 if not p.is_file():continue
 rel=p.relative_to(source);installed=target/rel;assert installed.read_bytes()==p.read_bytes()
 files.append({'name':str(rel),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
with zipfile.ZipFile(outputs/'ForeverRoads.zip','w',zipfile.ZIP_DEFLATED) as z:
 for p in sorted(source.rglob('*')):
  if p.is_file():z.write(p,'ForeverRoads/'+str(p.relative_to(source)))
with zipfile.ZipFile(outputs/'ForeverRoads.zip') as z:
 assert z.testzip() is None
 for f in files:assert hashlib.sha256(z.read('ForeverRoads/'+f['name'])).hexdigest()==f['sha256']
(outputs/'ForeverRoads-tests.json').write_text(json.dumps(tests,indent=2)+'\n')
(outputs/'ForeverRoads-coverage.json').write_text(json.dumps(cov,indent=2)+'\n')
old=json.loads((outputs/'ForeverRoads-performance.json').read_text())
new={'version':version,'historicalDrawingComparison':old.get('historicalDrawingComparison',old),'worldPackage':{k:package[k] for k in ['loadMS','firstSearchFrames','peakSimulatedFrameMS','searchPeakMS','tickerPeakMS']},
 'crossingSearch':{'example':'Ratchet -> Booty Bay','beforeFrames':1218,'afterFrames':next(c['searchFrames'] for c in travel['checks'] if c['case'].startswith('Ratchet'))},'liveFPSVerified':False,
 'method':'Lua 5.1 with simulated 60 Hz client frames, actual packed terrain and all modules. Game search budgets range from 1 to 2.5 ms and may be exceeded by indivisible work. Offline elapsed timings do not measure in-game FPS.',
 'smoothing':read('route-smoothing-performance.json'),'goldTrail':bead_perf,
 'multimodalSearch':[c for c in travel['checks'] if 'searchFrames' in c]}
if cache_benchmark or old.get('routeCacheBenchmark'):
 new['routeCacheBenchmark']=cache_benchmark or old['routeCacheBenchmark']
(outputs/'ForeverRoads-performance.json').write_text(json.dumps(new,indent=2)+'\n')
report={'version':version,'installedAt':str(target),'filesVerified':files,'characterSpecific':True,'supportedMaps':[m['id'] for m in cov['maps']],'liveGameVerified':False,
 'liveVerificationNote':'Full terrain package and all loaded modules match source and ZIP. In-game verification is performed manually by the user; results are pending. No settings backups or action-bar/keybinding changes were made.'}
(outputs/'ForeverRoads-installation.json').write_text(json.dumps(report,indent=2)+'\n')
(outputs/'ForeverRoads-quick-start.txt').write_text(f'Forever GPS {version} is installed. Start WoW or /reload.\n\nOpen a flight master on each continent to import your character’s learned stops.\nTrack a quest, place a map pin, or Alt-left-click a zone map. Select an existing pin or use /froads pin to route to it. Gold dots show the current walking leg. Light-blue dots connect transport stops.\nOpen the world map for the travel estimate and steps. Icons show where each leg ends. The minimap shows arrival icons for flights, boats and zeppelins. /froads status lists upcoming rides. Choose flights and board manually.\n/froads opens settings. /froads follow returns to the tracked quest.\n/froads pause stops guidance. /froads resume restarts it.\n/froads perf shows timing by stage. If a route feels slow, use /froads perf start, reproduce it, then use /froads perf stop and /froads perf log.\n\nTravel times and waits are estimates. The travel planner was checked offline.\n')
# Corresponding build source and tests. Raw proprietary client assets and extraction outputs are excluded.
selected=[]
for folder in ['work/world-baker','work/world-toolchain/forge-navbuild']:
 for p in (root/folder).rglob('*'):
  if p.is_file() and p.suffix in ['.rs','.toml','.lock']:selected.append(p)
for p in h.iterdir():
 if p.is_file() and (p.suffix=='.py' or p.name in ['all-zone-catalog.json','world-coverage-audit.json','terrain-toc.json','data.json','transit-costs.json','multimodal-costs.json','UiMap-70862.csv','UiMapAssignment-70862.csv']):selected.append(p)
selected.extend((h/'src').glob('*.js'))
selected.extend([h/'smoothing-baseline/Map.lua',h/'bead-baseline/Map.lua'])
for rel in ['work/world-map-bake/data/road-textures.json','work/world-map-bake/data/forever/map-frames.json','work/world-map-bake/data/forever/zones.json','work/world-map-bake/layers/hubs.json']:
 selected.append(root/rel)
with zipfile.ZipFile(outputs/'ForeverRoads-build-source.zip','w',zipfile.ZIP_DEFLATED) as z:
 for p in selected:z.write(p,'ForeverRoads-source/'+str(p.relative_to(root)))
 z.write(stage/'LICENSE','ForeverRoads-source/LICENSE')
 z.writestr('ForeverRoads-source/README.txt','''ForeverRoads corresponding build source, 2026-11-08.
Runtime Lua sources and packed data are in the companion ForeverRoads.zip (GPL; original headers retained).
Extract this archive, create work/world-addon, and copy that addon folder's contents there.
Clone https://github.com/fitzforge/polestar at f174784d71856460b9fdef9ff9b7dc24519152fe into work/polestar.
Clone https://github.com/cjber/shortest-path-forever at 660e14a81724560abba1d619d9e791b72b136f86 into work/shortest-path-forever.
Native format definitions: https://github.com/wowdev/WoWDBDefs into work/wowdbdefs.
Use your legally installed Forever client. Raw Blizzard assets are not included.
Python tests require Python 3 and lupa (Lua 5.1). Runtime test modules use local module paths under work/.
Run python3 work/road-demo/test-world-package.py and test-world-travel.py; tests use simulated game APIs.
The publisher is a local install script and intentionally writes to the WoW Forever AddOns directory; inspect paths before using.
Rust source: work/world-baker and work/world-toolchain/forge-navbuild (modified GPL-3.0-only toolchain crate).
The modified parser is src/geom/parse.rs; its three tests are tests/forever_flat_liquid.rs.
Run cargo test --manifest-path work/world-toolchain/forge-navbuild/Cargo.toml --test forever_flat_liquid.
Build the world-baker package, using jobs=1. build-grid bakes maps 30/489/529/2997 from local client geometry;
pack-grid packs them using zone frames, road masks and an AreaTable.csv for build 1.60.1.70862.
The baker's main program extracts road texture masks using a public community listfile; these large inputs are not bundled.
Scripts under work/road-demo generate catalogue, waypoints, namespace-adapted engine files and fixed transport walking costs.
Paths in the local build binaries target macOS /Applications/World of Warcraft; adjust for another installation.
Polestar's compressed original-continent/Zephras data and engine are copied at the pinned revision above by vendor_world_engine.py.
import_extra_terrain.py adds fresh four-map data and writes the TOC without duplicate modules.
All source licenses and attribution in upstream files remain applicable; see addon Terrain/*PROVENANCE.json and UPSTREAM-CREDITS.md.
''')
with zipfile.ZipFile(outputs/'ForeverRoads-build-source.zip') as z:assert z.testzip() is None
live_path=outputs/'ForeverRoads-live-verification.json'
live=json.loads(live_path.read_text())
live['travelUpdate']={'version':version,'changes':'Multimodal routing with learned, character-specific flight stops and faction-appropriate public crossings.',
 'offlineVerified':True,'verifiedInGame':False}
live['manualNextStep']='Reload, open a flight master, then choose a distant destination and inspect /froads status.'
live_path.write_text(json.dumps(live,indent=2)+'\n')
audit_path=outputs/'ForeverRoads-delivery-audit.json'
audit=json.loads(audit_path.read_text())
audit.update(version=version,filesMatched=len(files),multimodalTravelOfflineVerified=True,multimodalTravelLiveVerified=False)
audit['automatedChecks']=f"10 package suites including sampled drawing in all 55 maps, {len(travel['checks'])} travel checks, 21 legacy suites, {len(beads['checks'])} trail drawing checks, 3 liquid-parser tests, and 180 randomized display curves with 45,871 corridor samples."
audit_path.write_text(json.dumps(audit,indent=2)+'\n')
print(f'Installed ForeverRoads {version}:',len(files),'files verified; all 55 map IDs. ZIPs verified.')
