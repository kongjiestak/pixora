import test from 'node:test'
import assert from 'node:assert/strict'
import {dashboardWidgets} from '../src/widgets.js'
import {resetCountdown,compactReset} from '../src/format.js'
const t=(key,args)=>[key,args]
test('dashboard mode switching preserves public-screen constraints',()=>{
 assert.ok(dashboardWidgets('focus',false,'system').includes('system'))
 for(const view of ['overview','ai','system']){
  assert.equal(dashboardWidgets('overview',true,view).includes('system'),false)
  assert.equal(dashboardWidgets('public',false,view).includes('quota'),false)
 }
})
test('countdown handles long windows, expired values and missing reset',()=>{
 const clock=new Date('2026-10-20T00:00:00Z')
 assert.deepEqual(resetCountdown('2026-10-22T03:00:00Z',clock,t),['widget.countdownDays',{days:2,hours:3}])
 assert.deepEqual(resetCountdown('2026-10-20T01:05:00Z',clock,t),['widget.countdownHours',{hours:1,minutes:5}])
 assert.deepEqual(resetCountdown('2026-10-19T00:00:00Z',clock,t),['widget.minutes',{count:0}])
 assert.deepEqual(resetCountdown(null,clock,t),['widget.unknownTime',undefined])
 assert.equal(compactReset(null,'en-US','Unknown'),'Unknown')
})
