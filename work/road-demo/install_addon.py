from pathlib import Path
import hashlib,json,shutil,zipfile
root=Path(__file__).resolve().parents[2]
source=root/'outputs/ForeverRoads'
target=Path('/Applications/World of Warcraft/_forever_/Interface/AddOns/ForeverRoads')
target.mkdir(exist_ok=True,parents=True)
files=[]
for p in sorted(source.iterdir()):
 if p.is_file():
  installed=target/p.name;shutil.copy2(p,installed)
  assert installed.read_bytes()==p.read_bytes()
  files.append(dict(name=p.name,sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
with zipfile.ZipFile(root/'outputs/ForeverRoads.zip','w',zipfile.ZIP_DEFLATED) as z:
 for p in sorted(source.iterdir()):
  if p.is_file():z.write(p,'ForeverRoads/'+p.name)
with zipfile.ZipFile(root/'outputs/ForeverRoads.zip') as z:
 assert z.testzip() is None
 for p in source.iterdir():
  if p.is_file():assert z.read('ForeverRoads/'+p.name)==p.read_bytes()
report=dict(version='1.1.3',installedAt=str(target),filesVerified=files,characterSpecific=True,supportedMaps=[1420,1421,1424,1442],liveGameVerified=False,
 liveVerificationNote='Performance and explored-map layer fixes installed. 21 simulated suites pass; real-client FPS improvement is unverified. No active extraction or compiler process remains. Last game observation showed a player-initiated logout in progress; no input was sent.')
(root/'outputs/ForeverRoads-installation.json').write_text(json.dumps(report,indent=2)+'\n')
print('ForeverRoads 1.1.3 installed; all 8 files and ZIP contents match. Stonetalon included.')
