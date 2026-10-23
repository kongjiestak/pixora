// Device-local, foreground-only rules. Never infer task completion from idle.
export const alertDefaults=Object.freeze({enabled:false,low:10,recover:20,cooldown:30,quiet:false,start:22,end:7})
export function alertSettings(value={}){
 const v={...alertDefaults,...value},number=(x,lo,hi,f)=>Number.isInteger(Number(x))&&Number(x)>=lo&&Number(x)<=hi?Number(x):f
 v.enabled=value.enabled===true;v.quiet=value.quiet===true
 v.low=number(v.low,1,50,10);v.recover=number(v.recover,v.low+1,100,Math.max(20,v.low+1));v.cooldown=number(v.cooldown,1,1440,30)
 v.start=number(v.start,0,23,22);v.end=number(v.end,0,23,7);return v
}
export function quietNow(settings,date){
 if(!settings.quiet||settings.start===settings.end)return false
 const h=date.getHours();return settings.start<settings.end?h>=settings.start&&h<settings.end:h>=settings.start||h<settings.end
}
export function evaluateQuota(data,previous,rawSettings,date=new Date()){
 const settings=alertSettings(rawSettings),state={},events=[],time=date.getTime()
 for(const key of Object.keys(previous||{}).slice(0,64)){
  const old=previous[key];if(!/^codex:[0-9.]+$/.test(key)||!Number.isFinite(old?.observed))continue
  state[key]={low:old.low===true,observed:old.observed,sent:{}}
  for(const kind of ['low','recovered'])if(Number.isFinite(old.sent?.[kind]))state[key].sent[kind]=old.sent[kind]
 }
 if(!settings.enabled||data?.mode!=='real'||!data.device_id)return {state,events}
 for(const provider of data.providers||[]){
  const observed=Date.parse(provider.observed_at||provider.collected_at),age=time-observed
  if(provider.provider!=='codex'||provider.source!=='codex-app-server'||provider.mode!=='real'||provider.status!=='ok'||provider.stale||!Number.isFinite(observed)||age< -60000||age>Math.min(600,Number(data.stale_after_seconds)||600)*1000)continue
  for(const w of provider.windows||[]){
   const remaining=100-w.used_percent,duration=Number(w.duration_minutes)
   if(!Number.isFinite(w.used_percent)||remaining<0||remaining>100||!Number.isFinite(duration)||duration<=0||w.resets_at&&(!Number.isFinite(Date.parse(w.resets_at))||Date.parse(w.resets_at)<=time))continue
   const key=provider.provider+':'+duration,old=state[key]
   if(old&&observed<=old.observed)continue
   // Same duration changing reset timestamp remains the same stream.
   let low=old?.low===true,kind=null
   if(remaining<=settings.low&&!low){low=true;kind='low'}
   else if(remaining>=settings.recover&&low){low=false;kind='recovered'}
   const sent={...(old?.sent||{})};state[key]={low,observed,sent}
   if(kind&&!quietNow(settings,date)&&(!Number.isFinite(sent[kind])||time-sent[kind]>=settings.cooldown*60000)){
    sent[kind]=time;events.push({id:key+':'+observed+':'+kind,kind,provider:'codex',duration,remaining:Math.round(remaining),at:time})
   }
  }
 }
 return {state,events}
}
export function loadAlerts(storage,key){
 try{const v=JSON.parse(storage?.getItem(key)||'null');if(v?.version===1)return {settings:alertSettings(v.settings),state:typeof v.state==='object'&&v.state||{},events:Array.isArray(v.events)?v.events.filter(x=>['low','recovered'].includes(x?.kind)&&Number.isFinite(x.at)&&Number.isFinite(x.duration)&&Number.isFinite(x.remaining)).slice(0,20):[]}}catch{}
 return {settings:alertSettings(),state:{},events:[]}
}
