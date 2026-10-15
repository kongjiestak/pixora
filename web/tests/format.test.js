import {test} from 'node:test'
import assert from 'node:assert/strict'
import {remaining, stamp, windowLabel} from '../src/format.js'
test('unknown never becomes zero',()=>{assert.equal(remaining(null),'未知');assert.equal(stamp(null),'尚未采集')})
test('remaining clamps and subtracts used',()=>{assert.equal(remaining(25),'75%');assert.equal(remaining(150),'0%');assert.equal(remaining(-10),'100%')})
test('window labels use actual duration',()=>{assert.equal(windowLabel(300),'5 小时窗口');assert.equal(windowLabel(10080),'7.0 天窗口')})
