use forge_navbuild::geom::parse::{parse_mh2o,LiquidInfo};
struct Legacy;
impl LiquidInfo for Legacy {
 fn kind(&self,_:u32)->Result<u8,String>{Ok(1)}
 fn lvf(&self,_:u32,_:u32)->Result<u32,String>{Ok(0)}
}
fn put32(b:&mut[u8],at:usize,v:u32){b[at..at+4].copy_from_slice(&v.to_le_bytes());}
fn fixture(depth_only:bool,flat:bool)->Vec<u8>{
 let base=3072;let exists=base+24;let vertex=exists+8;let count=if depth_only{81}else{405};let attr=vertex+count;
 let mut b=vec![0u8;attr+16];put32(&mut b,0,base as u32);put32(&mut b,4,1);put32(&mut b,8,attr as u32);
 b[base..base+2].copy_from_slice(&2u16.to_le_bytes());b[base+2..base+4].copy_from_slice(&42u16.to_le_bytes());
 if !flat {b[base+8..base+12].copy_from_slice(&1f32.to_le_bytes());}
 b[base+14]=8;b[base+15]=8;put32(&mut b,base+16,exists as u32);put32(&mut b,base+20,vertex as u32);
 b[exists..exists+8].fill(255);
 b
}
#[test] fn flat_legacy_ocean_with_depth_only_stream(){let m=parse_mh2o(Some(&fixture(true,true)),&Legacy).unwrap();assert_eq!(m.ty[0],1);assert_eq!(m.z[0],0.0);}
#[test] fn flat_height_depth_stream_remains_valid(){let m=parse_mh2o(Some(&fixture(false,true)),&Legacy).unwrap();assert_eq!(m.ty[0],1);}
#[test] fn nonflat_truncated_heights_are_rejected(){assert!(parse_mh2o(Some(&fixture(true,false)),&Legacy).is_err());}
