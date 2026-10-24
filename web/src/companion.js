export function companionPreferences(value){
 let p;try{p=typeof value==='string'?JSON.parse(value):value}catch{};p=p&&typeof p==='object'?p:{}
 return {view:p.view==='pet'?'pet':'quota',mode:['auto','working','idle','error'].includes(p.mode)?p.mode:'auto',name:typeof p.name==='string'?p.name.slice(0,24):'',caption:typeof p.caption==='string'?p.caption.slice(0,48):''}
}
