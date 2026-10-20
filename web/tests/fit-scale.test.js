import test from 'node:test'
import assert from 'node:assert/strict'
import {fitScale} from '../src/fit-scale.js'
test('fits available space independent of DPR and permits readable overflow',()=>{
 assert.equal(fitScale(880,280,880,320),.875)
 assert.equal(fitScale(956,320,956,300),1)
 assert.equal(fitScale(390,600,390,900),null)
 assert.equal(fitScale(880,280,880,320,2),null)
 assert.equal(fitScale(0,280,880,320),null)
})
