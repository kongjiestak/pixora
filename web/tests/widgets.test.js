import {test} from 'node:test';import assert from 'node:assert/strict';import {visibleWidgets,modes} from '../src/widgets.js';
test('shared screens exclude private widgets',()=>{assert.deepEqual(visibleWidgets('overview',true),['clock','status']);assert.ok(visibleWidgets('overview',false).includes('quota'));assert.equal(modes.length,5)})
