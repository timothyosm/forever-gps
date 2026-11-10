"""Prepare the scalable road router in staging, without changing the installed addon."""
from pathlib import Path
p=Path(__file__).resolve().parents[1]/'world-addon/Router.lua'
s=p.read_text()
a=s.index('    local nodes,adj={},{}');b=s.index('    local function connect',a)
s=s[:a]+'''    -- The immutable graph is shared. Only the two projected endpoint nodes
    -- and their small adjacency lists belong to this query.
    local nodes=setmetatable({}, {__index=net.nodes})
    local extras={};local nextNode=#net.nodes
''' +s[b:]
s=s.replace('        table.insert(adj[a],{to=b,edge=copy}); table.insert(adj[b],{to=a,edge=copy})','''        extras[a]=extras[a] or {};extras[b]=extras[b] or {}
        table.insert(extras[a],{to=b,edge=copy});table.insert(extras[b],{to=a,edge=copy})''')
s=s.replace('        local id=#nodes+1; nodes[id]=p.point; adj[id]={}','        nextNode=nextNode+1;local id=nextNode;nodes[id]=p.point')
a=s.index('            for _,entry in ipairs(adj[u]) do');b=s.index('\n        end\n    end',a)
s=s[:a]+'''            local base,extra=net.adj[u] or {},extras[u] or {}
            for i=1,#base+#extra do
                local entry=i<=#base and base[i] or extra[i-#base]
                local e,v=entry.edge,entry.to
                if not blocked[e.id] then
                    local cost=e.length*(opts.preferRoads and (e.kind=="trail" or e.kind=="estimated") and 1.45 or 1)
                    local nextScore=current.g+cost
                    if nextScore+1e-7<(scores[v] or math.huge) then
                        scores[v]=nextScore;previous[v]={id=u,edge=e}
                        push({id=v,g=nextScore,f=nextScore+heuristic(v)})
                    end
                end
            end''' +s[b:]
p.write_text(s)
