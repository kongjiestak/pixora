export function weatherKind(code){
 if(code===null||!Number.isFinite(code))return 'unknown'
 if(code===0)return 'clear'
 if([1,2,3].includes(code))return 'cloud'
 if([45,48].includes(code))return 'fog'
 if([71,73,75,77,85,86].includes(code))return 'snow'
 if([95,96,99].includes(code))return 'storm'
 if([51,53,55,56,57,61,63,65,66,67,80,81,82].includes(code))return 'rain'
 return 'unknown'
}
export function weatherMetric(item,key){const n=item.metrics.find(m=>m.key==='weather.'+key)?.value;return typeof n==='number'&&Number.isFinite(n)?n:null}
