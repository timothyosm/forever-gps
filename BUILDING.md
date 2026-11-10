# Build and test Forever GPS

`ForeverRoads/` is the installable addon from the 2.1.17 beta archive. It contains the Lua modules, artwork, and generated navigation packs. The source and verification tools under `work/` match the build-source archive for that version.

## Offline tests

Use Python 3 with [Lupa](https://pypi.org/project/lupa/) and its Lua 5.1 runtime. From a fresh checkout:

```sh
python3 -m pip install lupa
cp -R ForeverRoads work/world-addon
python3 work/road-demo/test-world-travel.py
```

The travel test runs the package test first. The tests load the actual addon manifest against simulated WoW APIs, route and render sampled trips across the supported maps, and check flight discovery and transport handling. Generated test reports and the working addon copy are ignored by Git.

## Regenerate terrain

Check out the following upstream sources into the paths the build tools expect.

| Project | Path | Revision |
| --- | --- | --- |
| [Polestar](https://github.com/fitzforge/polestar) | `work/polestar` | `f174784d71856460b9fdef9ff9b7dc24519152fe` |
| [Shortest Path Forever](https://github.com/cjber/shortest-path-forever) | `work/shortest-path-forever` | `660e14a81724560abba1d619d9e791b72b136f86` |
| [WoWDBDefs](https://github.com/wowdev/WoWDBDefs) | `work/wowdbdefs` | `fb58b5b8ea8ce82945194cc9c4e760fd12ddd85c` |

Use a locally installed Forever client. For catalogue generation and the full terrain-integrity check, export `UiMap` and `UiMapAssignment` for build `1.60.1.70862` into `work/road-demo/UiMap-70862.csv` and `work/road-demo/UiMapAssignment-70862.csv`. Use the same build for `AreaTable.csv` under `work/world-map-bake/data/sources/wago/1.60.1.70862/`. The tools also use the community listfile at `work/world-map-bake/data/sources/listfile/community-listfile.csv`. The client files, table exports, and listfile are local inputs.

The Rust grid baker is in `work/world-baker`. `build-grid` builds maps 30, 489, 529, and 2997 from local client geometry. `pack-grid` uses the grid, map frames, area table, and road layers to write the Lua navigation packs. The modified Forge parser and its regression tests are in `work/world-toolchain/forge-navbuild`.

```sh
cargo test --manifest-path work/world-toolchain/forge-navbuild/Cargo.toml --test forever_flat_liquid
```

The build tools have macOS installation defaults. Review their input and output paths for your machine. `publish_world.py` is a local install and packaging script that writes to the WoW AddOns directory.
