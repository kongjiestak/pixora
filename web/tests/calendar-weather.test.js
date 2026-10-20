import test from 'node:test'
import assert from 'node:assert/strict'
import {monthGrid,ringRemaining} from '../src/calendar.js'
import {weatherKind,weatherMetric} from '../src/weather.js'
import {dashboardWidgets,displayWidgets} from '../src/widgets.js'
import {deviceConfig} from '../src/locale-core.js'
test('calendar handles leap years and year boundaries with Monday first',()=>{
 const leap=monthGrid(2024,1);assert.equal(leap.length,42);assert.equal(leap.filter(d=>d.current).length,29)
 assert.deepEqual(monthGrid(2026,0)[0],{year:2025,month:11,day:29,current:false})
 assert.equal(monthGrid(2026,2).filter(d=>d.current).length,31)
})
test('rings represent remaining quota, including zero and missing values',()=>{
 assert.equal(ringRemaining(75),25);assert.equal(ringRemaining(100),0);assert.equal(ringRemaining(0),100)
 for(const value of [null,undefined,NaN,'25'])assert.equal(ringRemaining(value),null)
})
test('weather unknown values stay unknown; personal widgets hide tasks and shared weather',()=>{
 assert.equal(weatherKind(null),'unknown');assert.equal(weatherKind(0),'clear');assert.equal(weatherKind(95),'storm');assert.equal(weatherKind(999),'unknown')
 assert.equal(weatherMetric({metrics:[{key:'weather.temperature',value:null}]},'temperature'),null)
 assert.deepEqual(displayWidgets('personal',false),['calendar','weather'])
 assert.ok(dashboardWidgets('overview',false,'personal').includes('calendar'))
 assert.ok(dashboardWidgets('overview',false,'personal').includes('weather'))
 assert.equal(dashboardWidgets('overview',false).includes('tasks'),false)
 for(const shared of [dashboardWidgets('overview',true,'personal'),displayWidgets('personal',true)])assert.equal(shared.includes('weather'),false)
 const config=deviceConfig('{"motion":false,"quotaStyle":"bars"}');assert.equal(config.motion,false);assert.equal(config.quotaStyle,'bars')
})
