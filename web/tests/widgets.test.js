import {test} from 'node:test';import assert from 'node:assert/strict';import {visibleWidgets,modes} from '../src/widgets.js';
test('shared screens exclude private widgets',()=>{assert.deepEqual(visibleWidgets('overview',true),['clock','status']);assert.ok(visibleWidgets('overview',false).includes('quota'));assert.equal(modes.length,5)})

test('display layouts keep shared-screen privacy across layout choices',async()=>{const {displayWidgets}=await import('../src/widgets.js');assert.deepEqual(displayWidgets('quota',false),['quota']);assert.deepEqual(displayWidgets('clock-quota',false),['clock','quota']);for(const layout of ['quota','clock-quota','unknown'])assert.deepEqual(displayWidgets(layout,true),['clock','status'])})
