use std::path::PathBuf;
fn main()->Result<(),String>{
 use forge_navbuild::build::{run,Client,Opts};
 let opts=Opts{out:PathBuf::from("work/world-map-bake/grid"),client:Client::Install{wow:PathBuf::from("/Applications/World of Warcraft"),defs:PathBuf::from("work/wowdbdefs")},product:"wowf".into(),data:PathBuf::from("work/world-map-bake/data/forever"),continents:Some(vec![30,489,529,2997]),force:false,jobs:1};
 let out=run(&opts,&|m|eprintln!("{m}"))?;
 for warning in &out.warnings {eprintln!("warning: {warning}");}
 std::fs::write("work/world-map-bake/grid/build-report.json",serde_json::to_vec_pretty(&serde_json::json!({"build":out.build,"warnings":out.warnings})).unwrap()).map_err(|e|e.to_string())?;
 Ok(())}
