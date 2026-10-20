import test from 'node:test'
import assert from 'node:assert/strict'
import {dashboardWidgets,displayWidgets} from '../src/widgets.js'
test('developer and personal widgets preserve shared display boundaries',()=>{
 assert.ok(dashboardWidgets('focus',false,'developer').includes('github'))
 assert.ok(dashboardWidgets('focus',false,'personal').includes('tasks'))
 for(const mode of ['developer','personal','system','overview']){
  for(const id of ['github','rss','tasks']){
   assert.equal(dashboardWidgets('overview',true,mode).includes(id),false)
   assert.equal(displayWidgets(mode,true).includes(id),false)
  }
 }
})
