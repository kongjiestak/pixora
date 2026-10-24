import {test} from 'node:test'
import assert from 'node:assert/strict'
import {activityState} from '../src/pet-state.js'
test('activity requires a live connection, known source and a bounded fresh lifetime',()=>{
 const event={source:'codex-local-events',state:'working',observed_at:100,expires_at:115}
 assert.equal(activityState(event,101000,true),'working')
 for(const [change,time,active] of [[{},101000,false],[{},115000,true],[{source:'demo'},101000,true],[{state:'approved'},101000,true],[{expires_at:900},101000,true],[{observed_at:200},101000,true]])assert.equal(activityState({...event,...change},time,active),'unknown')
})
import {companionPreferences} from '../src/companion.js'
test('companion display preferences are bounded and cannot invent a real state',()=>{
 assert.deepEqual(companionPreferences('{broken'),{view:'quota',mode:'auto',name:'',caption:''})
 const value=companionPreferences({view:'pet',mode:'idle',name:'a'.repeat(40),caption:'b'.repeat(90)})
 assert.equal(value.mode,'idle');assert.equal(value.name.length,24);assert.equal(value.caption.length,48)
 assert.deepEqual(companionPreferences(JSON.stringify(value)),value)
 assert.equal(companionPreferences({mode:'approve-all'}).mode,'auto')
})
