// Forever Roads build tool: read the installed client's painted roads.
// Uses Polestar Forge's GPL-3.0-only terrain decoder; no game client files are modified.
use std::path::{Path,PathBuf};
use forge_navbuild::{geom::{ClientSource,Tables},roads};
use rustc_hash::FxHashSet;
fn main() -> Result<(),String> {
 let args:Vec<String>=std::env::args().collect();
 if args.len()<6 {return Err("usage: forever-roads-baker WOW DEFS LISTFILE ALLOWLIST OUT [map IDs separated by commas]".into())}
 rayon::ThreadPoolBuilder::new().num_threads(1).build_global().map_err(|e|e.to_string())?;
 let client=forge_gamedata::Client::open(Path::new(&args[1]),"wowf",Path::new(&args[2]))?;
 let tables=Tables::from_csv(|name| {
  if name!="Map" {return Ok("ID\n".to_string())}
  let table=client.table(name,"enUS")?;
  String::from_utf8(forge_gamedata::csv::write_table(&table)).map_err(|e|e.to_string())
 })?;
 let source=ClientSource::open(Path::new(&args[1]),"wowf")?;
 let doc:serde_json::Value=serde_json::from_slice(&std::fs::read(&args[4]).map_err(|e|e.to_string())?).map_err(|e|e.to_string())?;
 let mut allow:FxHashSet<String>=doc["textures"].as_array().into_iter().flatten().filter_map(|v|v.as_str()).map(roads::texture_key).collect();
 roads::scan_listfile(Path::new(&args[3]),|_,path| {
  let key=roads::texture_key(path);
  if key.starts_with("tileset/") && ["road","path","cobble","street","trail"].iter().any(|word|key.contains(word)) {allow.insert(key);}
 })?;
 let maps:Vec<u32>=args.get(6).map(|s|s.as_str()).unwrap_or("0,1,2991,2997,30,489,529").split(',').map(|s|s.parse::<u32>().map_err(|e|e.to_string())).collect::<Result<_,_>>()?;
 let output=PathBuf::from(&args[5]);std::fs::create_dir_all(&output).map_err(|e|e.to_string())?;
 let mut report=Vec::new();
 for map in maps {
  match roads::build_roads(&source,&tables,&client.storage.version,&[map],&output,Path::new(&args[3]),&allow,&|s|eprintln!("{s}")) {
   Ok(stats)=>for s in stats {eprintln!("map {}: {} tiles, {} road tiles, {} road cells",s.c,s.tiles,s.road_tiles,s.road_columns);report.push(serde_json::json!({"map":s.c,"tiles":s.tiles,"roadTiles":s.road_tiles,"roadCells":s.road_columns,"seconds":s.seconds}));},
   Err(reason)=>{eprintln!("map {map} failed: {reason}");report.push(serde_json::json!({"map":map,"error":reason}));}
  }
 }
 std::fs::write(output.join("bake-report.json"),serde_json::to_vec_pretty(&serde_json::json!({"build":client.storage.version,"maps":report})).map_err(|e|e.to_string())?).map_err(|e|e.to_string())?;
 Ok(())
}
