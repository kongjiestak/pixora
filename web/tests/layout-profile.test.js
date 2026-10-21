import {test} from 'node:test'
import assert from 'node:assert/strict'
import {defaultProfile,layoutProfile,storedProfile,quotaSlots} from '../src/layout-profile.js'
import {persist,preference} from '../src/locale-core.js'

test('profile validates stored values and preserves false choices through reopen',()=>{
 const values=new Map(),storage={setItem:(k,v)=>values.set(k,v),getItem:k=>values.get(k)??null}
 const p=layoutProfile({show_clock:false,show_weather:false,density:'compact',focus_window:'weekly'})
 persist(storage,'pixora-profile:device-a',JSON.stringify(p))
 assert.deepEqual(storedProfile(preference(storage,'pixora-profile:device-a')),p)
 assert.equal(storedProfile(preference(storage,'pixora-profile:device-b')),null)
 assert.equal(storedProfile('null'),null);assert.equal(storedProfile('bad'),null)
 assert.deepEqual(layoutProfile({show_clock:'false',density:'bad'}),{...defaultProfile})
 // Reset removes only the local override, permitting new server recommendations.
 persist(storage,'pixora-profile:device-a','null')
 assert.equal(storedProfile(preference(storage,'pixora-profile:device-a')),null)
})
test('window restrictions cannot relabel the weekly window as the primary quota',()=>{
 const primary={name:'codex/primary',duration_minutes:300,used_percent:30}
 const weekly={name:'codex/secondary',duration_minutes:10080,used_percent:60}
 assert.deepEqual(quotaSlots([weekly]),[null,weekly])
 assert.deepEqual(quotaSlots([primary]),[primary,null])
 assert.deepEqual(quotaSlots([weekly,primary]),[primary,weekly])
 assert.deepEqual(quotaSlots([]),[null,null])
})
