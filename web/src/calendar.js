// Device-local civil dates: no UTC conversion, account access or event countdown.
export function monthGrid(year,month){
 const first=new Date(year,month,1),offset=(first.getDay()+6)%7
 return Array.from({length:42},(_,i)=>{
  const date=new Date(year,month,1-offset+i)
  return {year:date.getFullYear(),month:date.getMonth(),day:date.getDate(),current:date.getMonth()===month}
 })
}
export function ringRemaining(value){return typeof value==='number'&&Number.isFinite(value)?Math.max(0,Math.min(100,100-value)):null}
