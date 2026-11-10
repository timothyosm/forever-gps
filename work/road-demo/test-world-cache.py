"""Compare the shipped planner with a staged build using actual terrain and simulated client frames."""
import argparse
import json
from pathlib import Path
from statistics import median
from time import perf_counter

HERE = Path(__file__).resolve().parent
CATALOG = {z['id']: z for z in json.loads((HERE/'all-zone-catalog.json').read_text())['maps']}
AUDIT = {z['id']: z for z in json.loads((HERE/'world-coverage-audit.json').read_text())['maps']}
NODES = json.loads((HERE/'multimodal-costs.json').read_text())['nodes']
FLIGHTS = {node['taxi']: node for node in NODES if 'taxi' in node}
LOADER = HERE/'test-world-package.py'

def stop(node, zone=None):
    zone = zone or node['zone']
    a, b, c, d = CATALOG[zone]['bounds']
    return zone, (d-node['y'])/(d-b), (c-node['x'])/(c-a), node.get('z')

def field(zone, index=0):
    return stop(AUDIT[zone]['checkedPair'][index], zone)

CASES = [
    ('Stonetalon local run', (1442, .638, .559, None), (1442, .462, .585, None), [], 'Horde', 'way'),
    ('Durotar quest', (1442, .411, .706, None), (1411, .536, .522, None), [], 'Horde', 'quest'),
    ('Silverpine pin', stop(FLIGHTS[29]), field(1421), [29, 25, 23, 10, 11], 'Horde', 'pin'),
    ('Orgrimmar connecting flights', stop(FLIGHTS[29]), stop(FLIGHTS[23]), [29, 25, 23], 'Horde', 'way'),
    ('Booty Bay boat', stop(NODES[0]), field(1434), [], 'Horde', 'way'),
    ('Silverpine zeppelin', stop(FLIGHTS[29]), stop(FLIGHTS[10]), [29, 25, 23, 10, 11], 'Horde', 'way'),
    ('Deeprun Tram', stop(NODES[29]), stop(NODES[30]), [], 'Alliance', 'way'),
]

def load(addon):
    source = LOADER.read_text().split('passed=[]')[0]
    source = source.replace("root=h.parent/'world-addon'", 'root=addon_path')
    env = {'__file__': str(LOADER), 'addon_path': addon.resolve()}
    exec(compile(source, str(LOADER), 'exec'), env)
    return env['l']

def version(addon):
    return next(line.removeprefix('## Version: ') for line in (addon/'ForeverRoads.toc').read_text().splitlines()
                if line.startswith('## Version: '))

def lua_number(value):
    return 'nil' if value is None else repr(value)

def run_trip(lua, case, offset):
    _, (zone, x, y, z), (target_zone, tx, ty, tz), flights, faction, source = case
    known = ','.join(f'[{node}]=true' for node in flights)
    lua.execute(f'''
        A.Clear()
        currentZone={zone};worldMapID={zone};px={x+offset};py={y};pz={lua_number(z)}
        faction="{faction}";A.db.knownFlights={{{known}}};A.db.enabled=true
        questID=nil;userPin=nil
        if "{source}"=="quest" then
            questID=123;questZone={target_zone};questX={tx};questY={ty}
            A.Command("follow")
        elseif "{source}"=="pin" then
            userPin={{uiMapID={target_zone},position=CreateVector2D({tx},{ty}),z={lua_number(tz)}}}
            A.Command("pin")
        else
            A.SetDestination({{zone={target_zone},x={tx}*1002,y={ty}*668,z={lua_number(tz)},label="Benchmark"}},true)
            A.Tick()
        end
    '''.encode())
    frames = []
    decision = None
    frame = lua.eval(b'frame')
    busy = lua.eval(b'function() return A.pathJob~=nil end')
    decided = lua.eval(b'function() return A.journey~=nil or A.route~=nil end')
    while busy():
        start = perf_counter()
        frame()
        frames.append((perf_counter()-start)*1000)
        if decision is None and decided():
            decision = len(frames)
        assert len(frames)<20000, case[0]
    seconds, signature, segments = lua.eval(b'''
        function()
            local rides={}
            if A.journey then
                for _,leg in ipairs(A.journey.legs) do
                    if leg.kind~="walk" then rides[#rides+1]=leg.kind..":"..leg.from.id..":"..leg.to.id end
                end
            end
            assert(A.route and (A.route.status=="ok" or A.route.status=="transport"),A.status)
            return A.journey and A.journey.seconds or A.route.weightedCost/A.Transit.walkSpeed,
                table.concat(rides,","), A.route.segments and #A.route.segments or 0
        end
    ''')()
    return {'decisionFrames': len(frames) if decision is None else decision, 'completeFrames': len(frames),
            'peakFrameMS': max(frames, default=0), 'frameP95MS': percentile(frames,.95) if frames else 0, 'routeSeconds': seconds,
            'rides': signature.decode(), 'segments': segments}

def minimap_samples(lua):
    # Replay a real long walking route using simulated map APIs and positions along it.
    return lua.eval(b'''
        function()
            local durations={}
            local segments=A.route.segments
            for _,segment in ipairs(segments) do
                A.player={continent=segment.from.continent,wx=segment.from.wx,wy=segment.from.wy}
                A.progress=segment.begin
                local start=debugprofilestop()
                A.DrawMinimap()
                durations[#durations+1]=debugprofilestop()-start
            end
            return durations
        end
    ''')().values()

def percentile(values, p):
    ordered = sorted(values)
    return ordered[max(0, int(len(ordered)*p+.999999)-1)]

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('baseline',type=Path)
    parser.add_argument('candidate',type=Path)
    parser.add_argument('--repeats',type=int,default=5)
    args = parser.parse_args()
    report = {'baselineVersion': version(args.baseline), 'candidateVersion': version(args.candidate),
              'cases': {}, 'method': 'Real terrain, simulated 60 Hz client, median of interleaved paired runs',
              'repeats': args.repeats}
    for case in CASES:
        modes_to_test = ('cold','warm','afterIdle')
        results = {key: {mode: [] for mode in modes_to_test} for key in ('baseline','candidate')}
        for iteration in range(args.repeats):
            variants = [('baseline',args.baseline),('candidate',args.candidate)]
            if iteration%2:
                variants.reverse()
            for key, addon in variants:
                lua = load(addon)
                results[key]['cold'].append(run_trip(lua,case,0))
                results[key]['warm'].append(run_trip(lua,case,.0006))
                if case[0]=='Durotar quest':
                    row=results[key]['warm'][-1]
                    row['minimapP95MS']=percentile(minimap_samples(lua),.95)
                lua.execute(b'A.Clear();now=now+61;frame()')
                results[key]['afterIdle'].append(run_trip(lua,case,.0006))
            for mode in modes_to_test:
                old,new=(results[key][mode][-1] for key in ('baseline','candidate'))
                assert old['rides']==new['rides'] and abs(old['routeSeconds']-new['routeSeconds'])<.001, (case[0],mode,old,new)
        result = {}
        for key, modes in results.items():
            result[key] = {}
            for mode, rows in modes.items():
                result[key][mode] = {field: median(row[field] for row in rows) for field in rows[0] if field!='rides'}
        report['cases'][case[0]]=result
        result['transport']=bool(results['baseline']['cold'][0]['rides'])
        print(case[0],[(mode,result['baseline'][mode]['decisionFrames'],result['candidate'][mode]['decisionFrames'])
                       for mode in modes_to_test],flush=True)
    def total(mode, variant, transport_only=False):
        return sum(row[variant][mode]['decisionFrames'] for row in report['cases'].values()
                   if not transport_only or row['transport'])
    def ratio(mode, transport_only=False):
        return total(mode,'candidate',transport_only)/total(mode,'baseline',transport_only)
    report['summary'] = {
        'allColdChangePct': (ratio('cold')-1)*100,
        'allWarmChangePct': (ratio('warm')-1)*100,
        'allAfterIdleChangePct': (ratio('afterIdle')-1)*100,
        'transportAfterIdleChangePct': (ratio('afterIdle',True)-1)*100,
        'worstColdDecisionRatio': max(row['candidate']['cold']['decisionFrames']/row['baseline']['cold']['decisionFrames']
                                      for row in report['cases'].values()),
        'coldPeakRatio': max(row['candidate']['cold']['peakFrameMS'] for row in report['cases'].values())/
                         max(row['baseline']['cold']['peakFrameMS'] for row in report['cases'].values()),
        'worstColdP95Ratio': max(row['candidate']['cold']['frameP95MS']/row['baseline']['cold']['frameP95MS']
                                 for row in report['cases'].values()),
    }
    summary=report['summary']
    report['releaseChecks']={
        'repeatTransportAfterTerrainIdle': summary['transportAfterIdleChangePct']<=-25,
        'coldDecisionWithin10Pct': summary['worstColdDecisionRatio']<=1.10,
        'coldPeakWithin10Pct': summary['coldPeakRatio']<=1.10 and summary['worstColdP95Ratio']<=1.10,
    }
    (HERE/'world-cache-performance.json').write_text(json.dumps(report,indent=2)+'\n')

if __name__=='__main__':
    main()
