import test from 'node:test'
import assert from 'node:assert/strict'
import {targetsFor,pairingUrl,errorKey,importLayout} from '../src/admin-client.js'
test('bulk targets include only selected healthy active devices and preserve revisions',()=>{
 const items=[{id:'a',revision:2,status:'active'},{id:'b',revision:3,status:'revoked'},{id:'c',revision:null,status:'active',configuration_error:true},{id:'d',revision:0,status:'active'}]
 assert.deepEqual(targetsFor(items,['a','a','b','c','missing']),[{id:'a',revision:2}])
})
test('pairing URL never includes administrator query or credentials and requires HTTPS',()=>{
 const token='x'.repeat(43),url=new URL(pairingUrl('https://testserver:2053/?admin=1',token))
 assert.equal(url.pathname,'/');assert.equal(url.search,'');assert.equal(new URLSearchParams(url.hash.slice(1)).get('token'),token)
 assert.throws(()=>pairingUrl('http://testserver',token));assert.throws(()=>pairingUrl('https://testserver','bad'))
 assert.equal(errorKey(409),'admin.conflict');assert.equal(errorKey(401),'admin.expired')
})

test('layout imports reject typos and invalid values instead of silently replacing them',()=>{
 assert.equal(importLayout('{"theme":"paper"}').theme,'paper')
 assert.equal(importLayout('{"show_clock":false}').show_clock,false)
 for(const text of ['[]','{"theme":"evil"}','{"extra":true}','{"weather_location":"4699066"}','{"__proto__":{}}'])assert.throws(()=>importLayout(text))
})
