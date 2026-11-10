local _,A=...
local clock=debugprofilestop
local phases={"Update","Terrain search","World map","Minimap","Transit graph","Transit comparison","Terrain cleanup","Terrain decompression","Itinerary elapsed"}
local p={phases={},caches={}}
A.perf=p

function A.TracePerf(event,detail)
    if not A.tracePerf then return end
    local log=A.tracePerf.entries
    if #log>=48 then table.remove(log,1) end
    log[#log+1]=string.format("+%.2fs %s · %s",GetTime()-A.traceStarted,event,detail)
end

local function record(phase,elapsed)
    local row=p.phases[phase]
    if not row then row={count=0,total=0,peak=0,loggedAt=-math.huge};p.phases[phase]=row end
    row.count=row.count+1;row.total=row.total+elapsed;row.peak=math.max(row.peak,elapsed)
    return row
end

function A.CountPerf(counter,count)
    p.caches[counter]=(p.caches[counter] or 0)+(count or 1)
end

function A.RecordItinerary(seconds)
    record("Itinerary elapsed",seconds*1000)
    if A.tracePerf then A.TracePerf("Itinerary ready",string.format("%.2f s from request",seconds)) end
end

function A.MeasurePerf(phase,start)
    if not start then return end
    local elapsed=clock()-start
    local row=record(phase,elapsed)
    if A.tracePerf and elapsed>=3 and GetTime()-row.loggedAt>=1 then
        row.loggedAt=GetTime()
        local fps=GetFramerate and GetFramerate() or 0
        A.TracePerf(phase,string.format("%.2f ms at %.0f FPS",elapsed,fps))
    end
    return elapsed
end

function A.PerformanceCommand(command)
    if command=="start" then
        p.phases={};p.caches={}
        A.traceStarted=GetTime()
        A.tracePerf={version=ForeverRoads.version,entries={},summary=p.phases,caches=p.caches}
        A.db.performanceTrace=A.tracePerf
        A.Path.traceDecoding=true
        A.TracePerf("Recording started","choose a destination or repeat the slow action")
        A.Print("Performance recording started. Use /froads perf stop when finished.")
    elseif command=="stop" then
        if not A.tracePerf then A.Print("No performance recording is active.");return end
        A.TracePerf("Recording stopped","use /froads perf log to see recent entries")
        local summary={}
        for phase,row in pairs(p.phases) do
            summary[phase]={count=row.count,total=row.total,peak=row.peak}
        end
        A.tracePerf.summary=summary
        local caches={}
        for counter,count in pairs(p.caches) do caches[counter]=count end
        A.tracePerf.caches=caches
        A.tracePerf=nil
        A.Path.traceDecoding=false
        A.Print("Performance recording saved. /froads perf log shows the captured timings.")
    elseif command=="" or command=="log" then
        local saved=command=="log" and A.db.performanceTrace
        if command=="log" then
            if not saved then A.Print("No recording saved. Use /froads perf start.");return end
            for i=math.max(1,#saved.entries-9),#saved.entries do A.Print(saved.entries[i]) end
        end
        local timings=saved and saved.summary or p.phases
        for _,phase in ipairs(phases) do
            local row=timings[phase]
            if row and row.count>0 then
                A.Print(string.format("%s: %.2f ms average, %.2f ms peak (%d samples).",phase,row.total/row.count,row.peak,row.count))
            end
        end
        local caches=saved and saved.caches or not saved and p.caches
        if caches and (caches.graphLookups or caches.arrivalLookups) then
            A.Print(string.format("Cache: %d/%d transport graphs, %d/%d destinations, %d arrival, %d departure and %d quick-check results reused.",
                caches.graphHits or 0,caches.graphLookups or 0,caches.arrivalHits or 0,caches.arrivalLookups or 0,
                caches.arrivalCosts or 0,caches.originCosts or 0,caches.retryCosts or 0))
        end
        if command=="" then
            A.Print(string.format("Map redraws since login: %d world map, %d minimap. /froads perf start|stop|log",
                p.mapRedraws or 0,p.minimapRedraws or 0))
        end
    else A.Print("Usage: /froads perf [start|stop|log]") end
end

A.Path.profile=A.MeasurePerf
A.Path.progressSeconds=.1

-- The budget is a soft limit. A single terrain block can take longer than one slice.
local sampleAt,activeBudget=-math.huge,2.5
A.Path.frameBudget=function()
    if not A.pathJob then return A.Path.budget end
    local now=GetTime()
    if now-sampleAt>=.5 then
        sampleAt=now
        local fps=GetFramerate and GetFramerate() or 60
        activeBudget=fps>=50 and 2.5 or fps>=35 and 1.75 or 1
    end
    return activeBudget
end

local drawMap,drawMinimap=A.DrawMap,A.DrawMinimap
function A.DrawMap()
    local start=clock and clock()
    drawMap()
    A.MeasurePerf("World map",start)
end
function A.DrawMinimap()
    local start=clock and clock()
    drawMinimap()
    A.MeasurePerf("Minimap",start)
end
