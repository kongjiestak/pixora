import test from 'node:test'
import assert from 'node:assert/strict'
import {alertSettings,evaluateQuota,quietNow,loadAlerts} from '../src/quota-alerts.js'
const clock=new Date('2026-10-23T04:00:00Z'),on={enabled:true}
function sample(left=8,date=clock){return {mode:'real',device_id:'device-a',stale_after_seconds:600,providers:[{provider:'codex',mode:'real',source:'codex-app-server',status:'ok',stale:false,observed_at:date.toISOString(),windows:[{name:'primary',duration_minutes:300,used_percent:100-left,resets_at:new Date(+date+3600000).toISOString()}]}]}}
test('opt in; low once, duplicates/out of order ignored; recovery needs a real low',()=>{
 assert.equal(evaluateQuota(sample(),{},{} ,clock).events.length,0)
 const a=evaluateQuota(sample(),{},on,clock);assert.equal(a.events[0].kind,'low')
 assert.equal(evaluateQuota(sample(),a.state,on,clock).events.length,0)
 const later=new Date(+clock+120000),b=evaluateQuota(sample(25,later),a.state,on,later);assert.equal(b.events[0].kind,'recovered')
 assert.equal(evaluateQuota(sample(25),{},on,clock).events.length,0)
 assert.equal(evaluateQuota(sample(),b.state,on,later).events.length,0)
})
test('hysteresis and per-event cooldown prevent polling and flapping noise',()=>{
 let r=evaluateQuota(sample(),{},on,clock)
 for(const [minutes,left,kind] of [[1,15,null],[2,21,'recovered'],[3,7,null],[4,25,null],[35,7,'low']]){
  const d=new Date(+clock+minutes*60000);r=evaluateQuota(sample(left,d),r.state,on,d);assert.equal(r.events[0]?.kind??null,kind)
 }
})
test('demo, unavailable, stale, future, expired reset and unknown values never notify',()=>{
 for(const modify of [d=>d.mode='demo',d=>d.device_id=null,d=>d.providers[0].stale=true,d=>d.providers[0].mode='demo',d=>d.providers[0].status='error',d=>d.providers[0].source='demo',d=>d.providers[0].observed_at=new Date(+clock-601000).toISOString(),d=>d.providers[0].observed_at=new Date(+clock+61000).toISOString(),d=>d.providers[0].windows[0].used_percent=NaN,d=>d.providers[0].windows[0].resets_at=clock.toISOString()]){const d=sample();modify(d);assert.equal(evaluateQuota(d,{},on,clock).events.length,0)}
})
test('quiet hours suppress rather than queue; overnight and equal boundaries',()=>{
 const q=alertSettings({...on,quiet:true,start:22,end:7}),night=new Date(2026,9,23,23)
 assert.equal(quietNow(q,night),true);assert.equal(quietNow(q,new Date(2026,9,23,7)),false);assert.equal(quietNow({...q,end:22},night),false)
 const a=evaluateQuota(sample(8,night),{},q,night);assert.equal(a.events.length,0)
 const morning=new Date(2026,9,24,8);assert.equal(evaluateQuota(sample(8,morning),a.state,q,morning).events.length,0)
})
test('window reset timestamp changing does not duplicate low reminders',()=>{
 const a=evaluateQuota(sample(),{},on,clock),next=new Date(+clock+60000),d=sample(5,next);d.providers[0].windows[0].resets_at=new Date(+next+7200000).toISOString()
 assert.equal(evaluateQuota(d,a.state,on,next).events.length,0)
})
test('device-local restart keeps dedup; storage corruption and settings are bounded',()=>{
 const a=evaluateQuota(sample(),{},on,clock),store={getItem:()=>JSON.stringify({version:1,settings:on,state:a.state,events:a.events})},loaded=loadAlerts(store,'a')
 assert.equal(evaluateQuota(sample(),loaded.state,loaded.settings,clock).events.length,0)
 assert.equal(loadAlerts({getItem(){throw Error()}},'a').settings.enabled,false)
 assert.equal(loadAlerts({getItem:()=>'{bad'},'a').events.length,0)
 const cfg=alertSettings({enabled:'true',low:50,recover:4,cooldown:0});assert.equal(cfg.enabled,false);assert.equal(cfg.recover,51);assert.equal(cfg.cooldown,30)
})
