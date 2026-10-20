export const systemMetric=(item,key,locale,empty)=>{
 const metric=item?.metrics?.find(m=>m.key===key)
 return Number.isFinite(metric?.value)?new Intl.NumberFormat(locale,{maximumFractionDigits:1}).format(metric.value)+'%':empty
}
export const observationExpired=(item,clock)=>!item?.expires_at||new Date(item.expires_at)<=clock
