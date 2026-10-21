import {test} from 'node:test'
import assert from 'node:assert/strict'
import {weatherTime,weatherTimezone} from '../src/weather.js'
test('weather model time follows the selected city, not the screen or server zone',()=>{
 const shanghai={entries:[{detail:'Asia/Shanghai'}]},houston={entries:[{detail:'America/Chicago'}]}
 const epoch=Date.UTC(2026,9,21,1,0)/1000
 assert.equal(weatherTimezone(houston),'America/Chicago')
 assert.notEqual(weatherTime(shanghai,epoch,'en-US','unknown',true),weatherTime(houston,epoch,'en-US','unknown',true))
 assert.match(weatherTime(houston,epoch,'en-US','unknown',true),/Oct 20/)
 assert.match(weatherTime(shanghai,epoch,'en-US','unknown',true),/Oct 21/)
 assert.equal(weatherTime({entries:[]},epoch,'en-US','unknown'),'unknown')
 assert.equal(weatherTimezone({entries:[{detail:'invalid-zone'}]}),null)
})
