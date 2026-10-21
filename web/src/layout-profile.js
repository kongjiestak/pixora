export const defaultProfile=Object.freeze({show_clock:true,show_weather:true,density:'comfortable',focus_window:'primary'})
export function layoutProfile(value){
 const p=value&&typeof value==='object'?value:{}
 return {show_clock:typeof p.show_clock==='boolean'?p.show_clock:true,show_weather:typeof p.show_weather==='boolean'?p.show_weather:true,density:['comfortable','compact'].includes(p.density)?p.density:'comfortable',focus_window:['primary','weekly'].includes(p.focus_window)?p.focus_window:'primary'}
}
export function storedProfile(value){try{const p=JSON.parse(value);return p&&typeof p==='object'&&!Array.isArray(p)?layoutProfile(p):null}catch{return null}}
// A policy may remove either window. Never relabel a surviving weekly window as 5h.
export function quotaSlots(windows=[]){
 let primary=null,weekly=null
 for(const w of windows){
  if((w.duration_minutes??0)>=1440||/weekly|secondary/i.test(w.name||'')){weekly??=w}
  else if(!primary)primary=w
  else if(!weekly)weekly=w
 }
 return [primary,weekly]
}
