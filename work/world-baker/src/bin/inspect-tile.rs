use std::path::Path;
use forge_navbuild::geom::{ClientSource,Tables,Source,continent_tiles,parse::chunks};
fn main()->Result<(),String>{
 let a:Vec<String>=std::env::args().collect();let map=a[1].parse::<u32>().unwrap();let col=a[2].parse::<i32>().unwrap();let row=a[3].parse::<i32>().unwrap();
 let client=forge_gamedata::Client::open(Path::new("/Applications/World of Warcraft"),"wowf",Path::new("work/wowdbdefs"))?;
 let tables=Tables::from_csv(|n|{let t=client.table(n,"enUS")?;String::from_utf8(forge_gamedata::csv::write_table(&t)).map_err(|e|e.to_string())})?;
 let src=ClientSource::open(Path::new("/Applications/World of Warcraft"),"wowf")?;
 let tiles=continent_tiles(&src,&tables,map)?;let tile=tiles.iter().find(|t|t.col==col&&t.row==row).ok_or("no tile")?;
 let data=src.get(tile.root)?.ok_or("missing")?;
 for c in chunks(&data,0)?{if &c.tag==b"MH2O" {std::fs::write("work/road-demo/liquid-debug.bin",c.data).map_err(|e|e.to_string())?;println!("MH2O {} bytes",c.data.len());}}
 Ok(())}
