import {test} from 'node:test'
import assert from 'node:assert/strict'
import {remaining,stamp,windowLabel,currency,isStale} from '../src/format.js'
const t=(key,p)=>key+(p?':'+p.count:'')
test('missing values never become zero',()=>{assert.equal(remaining(null),'Unknown');assert.equal(remaining(null,'zh-CN','未知'),'未知');assert.equal(stamp(null),'Not collected');assert.equal(stamp('bad date'),'Not collected')})
test('remaining clamps and subtracts used',()=>{assert.equal(remaining(25),'75%');assert.equal(remaining(150),'0%');assert.equal(remaining(-10),'100%')})
test('window units and currency use Intl',()=>{assert.equal(windowLabel(300,t),'widget.hours:5');assert.equal(windowLabel(10080,t),'widget.days:7');assert.equal(currency(12.5,'USD','en-US'),'$12.50')})
test('quota becomes stale on clock advance without another fetch',()=>{const p={stale:false,observed_at:'2026-01-01T00:00:00Z',windows:[]};assert.equal(isStale(p,{stale_after_seconds:600},new Date('2026-01-01T00:05:00Z')),false);assert.equal(isStale(p,{stale_after_seconds:600},new Date('2026-01-01T00:11:00Z')),true)})
