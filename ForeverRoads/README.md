# Forever GPS 2.1.17

Terrain and road guidance for every playable zone map exposed by the installed WoW Forever 1.60.1.70862 client (Interface 16001). No other addon is required.

## Start

The addon is installed in `_forever_/Interface/AddOns/ForeverRoads`. Start WoW, or use `/reload` if it is already running. Left-click the minimap button or type `/froads` for settings. Right-click the minimap button to pause/resume; drag it to move it.

Track a quest to follow its objective or turn-in when the game supplies coordinates. **Alt-left-click** a zone map to choose a manual destination. `/froads follow` returns to the tracked quest. Gold dots show walking trails. Light-blue dots connect boarding and arrival points on zone maps, continent maps, the Azeroth overview, and the minimap where position is available. World map icons mark where each leg ends. A gold boot marks the end of a run. Nearby destinations can share a badge when zoomed out. The minimap shows arrival icons for flights, boats and zeppelins, including skycutters.

Place a native map pin to route to it automatically while guidance is enabled. To use an existing pin, select it, choose **Use map pin** in settings, or type `/froads pin`. Moving the active pin updates the route and removing it clears the route. Select a different active quest marker to switch back to quest guidance. Use `/froads follow` to route to a quest that is already selected.

The zone selector scrolls through all 55 map IDs. Each map has two terrain-checked path waypoints for testing. These are generic path locations, not invented NPC or town coordinates. Older named quick destinations remain available in the original four zones. You can always choose your own map point or tracked quest.

All settings, destinations, positions and recorded walks are **character-specific**. The addon does not change action bars or keybindings and does not create setup backups.

## Commands

| Command | Action |
| --- | --- |
| `/froads` | Open settings |
| `/froads follow` | Follow the super-tracked quest |
| `/froads pin` | Use the game's user map pin |
| `/froads way Stonetalon Mountains 46.2 58.5 Sun Rock Retreat` | Choose zone coordinates |
| `/froads way silverpine 43 40 The Sepulcher` | Short original aliases also work |
| `/froads way 1413 51.5 30 Crossroads` | Numeric map IDs also work |
| `/froads pause` / `/froads resume` | Pause/resume guidance |
| `/froads clear` | Clear the destination |
| `/froads status` | Print route status |
| `/froads perf` | Show timing by stage and map redraw counts |
| `/froads perf start` | Start a bounded performance recording for this character |
| `/froads perf stop` | Save the current recording |
| `/froads perf log` | Show recent recorded events and the timing summary |
| `/froads record` | Start/stop recording a walked path for calibration |

Coordinates are map percentages from 0 to 100. Full zone names may contain spaces; quotes are optional.

## Coverage

The package contains navigation terrain for both original continents, Zephras Isle, Darkspear Islands, Alterac Valley, Warsong Gulch and Arathi Basin. Their 55 UI map IDs cover the original zones, six capitals, Mount Hyjal, Riverglades, Shen'dralas and the islands/battlegrounds. Two IDs are aliases for Zephras Isle; they are not two different islands. `COVERAGE.json` lists every map and its checked route.

Roads, trails, slopes, water, buildings and multiple floors are represented where present in the terrain data. The planner prefers traversable ground and can price roads more favorably using the settings option. It uses a hierarchical terrain search rather than drawing a straight line from you to a road. Terrain gaps or unreachable points produce a clear status instead of a fabricated route. For a marker on an unreachable object or roof, try Alt-clicking nearby ground.

The planner compares direct terrain routes with journeys that combine walking, learned flight paths, public boats, zeppelins, skycutters, the Deeprun Tram and Darnassus/Rut'theran portals. It filters rides by faction and estimates travel time using terrain costs and average waits. Walk to the indicated landing, board or select the flight manually, and guidance advances after arrival. The trail shows the **current walking leg** and the world map lists the upcoming steps. `/froads status` also lists the rides ahead.

Open a flight master on each continent you want to fly in. The addon imports the flight master's current and reachable stops and remembers them separately for each character. Each flight leg requires learned stops at both ends, including intermediate connections. Consecutive flights appear as one step and one dotted connector from departure to the final landing. The estimate includes the remaining connections. Before the first import, guidance uses walking and public transport. Check actual departure times and fares in game. Hearthstones and class teleports are outside the public travel planner.

When you choose a flight to a supported stop, the addon can use that landing to plan the rest of your route while you fly. The world map labels estimates calculated this way as “after landing.” If your actual landing is elsewhere, guidance recalculates from your ground position.

On a planned boat or zeppelin crossing, the world map shows the onward walking trail from the planned exit. It labels the remaining estimate as “after docking.” The exit stays available during the crossing if position data briefly disappears.

Battleground and introductory-island entrances still require the game's queue, quest or transport. Local terrain routing works after entry if the client exposes player position. A connection absent from the public transport network is reported explicitly. Some boarding towers and interior passages have disconnected navigation surfaces, so an alternative crossing may be selected or no crossing reported. The addon never invents a stair or boat connection to cover a data gap.

Dungeon/raid interiors have no zone map definitions in this client catalogue and are not included. Route coverage is not a claim that every point is accessible or that every quest location has been walked in game. Hierarchical search and terrain resolution can produce a near-optimal route rather than the mathematically shortest continuous-world path. When a map goal has no height, its intended floor can be ambiguous.

## Performance

Terrain searches share a **1–2.5 ms budget per frame**, adjusted to the frame rate. A single decoded block or garbage collection can exceed this soft target. The planner can skip expensive transport approaches when their best possible time cannot beat a confirmed walk. Searches pause in combat. Changing the destination or pausing guidance cancels obsolete work.

Packed terrain is loaded with the addon, then decoded on demand. Decoded grid/graph caches are limited and trimmed while idle. The package occupies roughly 39 MB on disk; game memory includes packed strings, active search state and caches. It does not load another large addon in the middle of play.

The addon keeps exact walking costs from transport arrivals to its 16 most recent destinations for the current session. It also remembers each destination's latest departure costs for an exact repeat from the same spot and floor. The transport graph is reused for the same faction, route preference, and learned flight stops. A quick ride check carries settled costs into the full comparison if it times out. `/froads perf` shows cache hits, itinerary latency, and separate search and drawing timings.

Map and minimap corners use short, cached curves. Their rounding stays within the original line stroke, with a 1.25-pixel world-map and 0.65-pixel minimap centerline tolerance. Original navigation points, terrain decisions, distances and arrival checks remain the routing authority. Curves do not join across lifts, map changes, gaps or estimated approaches.

The normal guidance ticker runs five times a second. The world map draws trail dots around the visible area and reuses them during small pans. The minimap skips completed parts of the trail. The world map shows “Planning route…” while the addon compares walking and transport, then shows the selected itinerary. Active searches use a small adaptive budget based on frame rate, and decoded terrain stays warm between legs. Performance recording measures map drawing, route searches, transport comparisons and terrain work without enabling global script profiling. It stores the latest 48 events for this character and leaves out character names and exact coordinates.

## Verification

The actual TOC is loaded in order by the Lua 5.1 test harness. Automated checks route and render between terrain-checked points in all 55 maps. Separate travel tests cover flight discovery, unlearned connections, landing detection, a Stonetalon-to-Silverpine journey with flights and a zeppelin, Ratchet–Booty Bay by boat, the Deeprun Tram, the Darnassus portal and battleground-entry limits.

The 21 earlier regression suites still pass, including 722 reference graph routes and 286 Stonetalon comparisons. These legacy comparisons verify the original small graph; the 55-map terrain checks are reported separately. The current-client liquid parser fix has three Rust regression tests.

`TESTS.json` and the chat's separate reports distinguish simulation from live checks. Simulated route/drawing tests do not establish actual in-game FPS or prove every zone was visited. All in-game checks are performed manually by the player; `PLAYER-CHECKLIST.txt` gives the steps. The player confirmed that version 2.0.0 works well. The gold dotted trail uses the approved Figma bead artwork and reuses its textures as the minimap moves. Estimated sections keep their separate dashed treatment. The 2.0.2 appearance is verified offline and can be checked after a normal player-run `/reload`.

## Recorded walks

`/froads record` saves public player coordinates every eight yards or on zone changes. Recording stops on reload. These samples are calibration records, not automatic new route edges: a teleport or unusual jump must not create a false road connection.

## Credits and source

Forever GPS is distributed under the GNU GPL; see `LICENSE`. Terrain navigation code and the packed Eastern Kingdoms, Kalimdor and Zephras maps are adapted from [Polestar](https://github.com/fitzforge/polestar/tree/f174784d71856460b9fdef9ff9b7dc24519152fe) (GPL-3.0-or-later), based on Cillian Berragan's Shortest Path Forever and Leffe's navigation maps. Original headers and credits are retained in `Terrain/UPSTREAM-CREDITS.md`. Namespace and packaging adaptations are recorded in `Terrain/PROVENANCE.json`.

Four additional terrain maps were baked from the locally installed Forever 1.60.1.70862 client with the GPL Forge tools and a corrected flat-liquid decoder. The original three packed world maps identify build 1.60.1.70532; their coverage was checked against the current client map catalogue. Provenance and tile reports are included alongside the terrain. Public transport and directed flight data are adapted from [Shortest Path Forever](https://github.com/cjber/shortest-path-forever/tree/660e14a81724560abba1d619d9e791b72b136f86), whose generated inputs cite build 70862, CMaNGOS and InFlight travel times. Walking transfer costs were rebaked on the shipped terrain. The InFlight license is in `Terrain/INFLIGHT-LICENSE.txt`.

The accompanying `ForeverRoads-build-source.zip` contains our build tools, parser changes and verification scripts, with pinned upstream-source instructions. It excludes proprietary raw client assets. Native game art and icons are referenced from the installed client and are not copied into this addon.
