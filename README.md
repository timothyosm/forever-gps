# Forever GPS

Find the quickest route across Azeroth in World of Warcraft: Forever. Set a destination and see where to run, where to board, and how long the trip should take.

Forever GPS combines terrain routes with your character’s learned flight paths, boats, zeppelins, skycutters, the Deeprun Tram, and supported portals. It draws gold dots for running and light-blue dots for transport.

## Install

Copy the `ForeverRoads` folder into `World of Warcraft/_forever_/Interface/AddOns/`, then start the game or type `/reload`. This snapshot matches the **2.1.17 beta** addon package for WoW Forever 1.60.1.

- Track a quest or place a native map pin to set your destination.
- Hold Alt and left-click a zone map to choose a point.
- Open a flight master to import your learned flight stops.
- Type `/froads` or click the minimap button for settings.

See the [addon guide](ForeverRoads/README.md) for commands and coverage. The [build and test notes](BUILDING.md) describe the corresponding tools and client inputs.

## License and credits

See the [GNU GPL](LICENSE), [upstream credits](ForeverRoads/Terrain/UPSTREAM-CREDITS.md), and [terrain provenance](ForeverRoads/Terrain/PROVENANCE.json). Terrain routing is adapted from Polestar and Shortest Path Forever, with navigation-map contributions credited in the package.
