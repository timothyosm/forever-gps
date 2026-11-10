from pathlib import Path
import base64, json

here=Path(__file__).resolve().parent
out=here.parents[1]/'outputs'
data=json.loads((here/'data.json').read_text())
images={str(z['id']):'data:image/webp;base64,'+base64.b64encode((here/f'{z["id"]}.webp').read_bytes()).decode() for z in data['zones']}
page=(here/'src/index.template.html').read_text()
for token,content in {'@@DATA@@':json.dumps(data,separators=(',',':')),'@@IMAGES@@':json.dumps(images,separators=(',',':')),
                      '@@ROUTER@@':(here/'src/routing.js').read_text(),'@@APP@@':(here/'src/app.js').read_text()}.items():
    page=page.replace(token,content)
assert '@@' not in page
(out/'Forever-Road-Route-Lab.html').write_text(page)
(out/'forever-road-data.json').write_text(json.dumps(data,indent=2)+'\n')
print(f'Built standalone HTML ({len(page):,} bytes), with {len(images)} embedded maps and road data.')
