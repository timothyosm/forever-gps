use std::path::Path;
fn main()->Result<(),String>{
 rayon::ThreadPoolBuilder::new().num_threads(1).build_global().map_err(|e|e.to_string())?;
 let grid=Path::new("work/world-map-bake/grid");let layers=Path::new("work/world-map-bake/layers");let data=Path::new("work/world-map-bake/data/forever");
 let p=forge_nav::pack::pack_nav(&forge_nav::pack::PackIn{grid,layers,area_table:Path::new("work/world-map-bake/data/sources/wago/1.60.1.70862/AreaTable.csv"),zones:&data.join("zones.json"),map_frames:&data.join("map-frames.json"),aids:None,cells:128,date:"2026-11-08",continents:&[30,489,529,2997],generator:"ForeverRoads world-map build (Polestar Forge GPL toolchain)",leffe:None,zlib_literals:false,log:&|s|eprintln!("{s}")})?;
 let (files,_)=forge_nav::pack::ship_pack(&p,Path::new("work/world-map-bake/packed"))?;
 println!("Packed {} files",files.len());Ok(())}
