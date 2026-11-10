from pathlib import Path
h=Path(__file__).resolve().parent
code=(h/'test-addon.py').read_text()
code=code.replace("addon=root/'outputs/ForeverRoads'","addon=root/'work/world-addon'")
code=code.replace('"SetClipsChildren","SetDrawLayer"','"SetScrollChild","SetClipsChildren","SetDrawLayer"')
code=code.replace('assert(messages[#messages]:find("average"))','assert(messages[#messages-1]:find("average"))')
code=code.replace("root/'outputs/ForeverRoads-tests.json'","here/'world-legacy-tests.json'")
exec(compile(code,str(h/'test-addon.py'),'exec'),{'__file__':str(h/'test-addon.py')})
