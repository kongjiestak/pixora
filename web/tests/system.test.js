import test from 'node:test'
import assert from 'node:assert/strict'
import {systemMetric,observationExpired} from '../src/system-format.js'
import {displayWidgets,visibleWidgets} from '../src/widgets.js'
test('system metrics preserve missing values and expiry',()=>{
 const item={expires_at:'2026-01-01T00:10:00Z',metrics:[{key:'cpu.used',value:0},{key:'memory.used',value:null}]}
 assert.equal(systemMetric(item,'cpu.used','en-US','Unknown'),'0%')
 assert.equal(systemMetric(item,'memory.used','en-US','Unknown'),'Unknown')
 assert.equal(systemMetric(item,'disk.used','en-US','Unknown'),'Unknown')
 assert.equal(observationExpired(item,new Date('2026-01-01T00:10:01Z')),true)
})
test('system display never appears on shared screens',()=>{
 assert.deepEqual(displayWidgets('system',false),['clock','system'])
 assert.equal(displayWidgets('system',true).includes('system'),false)
 assert.equal(visibleWidgets('overview',true).includes('system'),false)
})
