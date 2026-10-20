import test from 'node:test'
import assert from 'node:assert/strict'
import {displayViewport} from '../src/display-viewport.js'
test('rotation settles without touch, respects mode/zoom, and removes pending work',()=>{
 const win=new EventTarget(),visual=new EventTarget(),pending=new Map(),styles=new Map();let id=0,active=true,scrolls=0
 Object.assign(visual,{height:900,scale:1})
 Object.assign(win,{visualViewport:visual,innerHeight:900,document:{documentElement:{style:{setProperty:(k,v)=>styles.set(k,v),removeProperty:k=>styles.delete(k)}}},setTimeout:fn=>{pending.set(++id,fn);return id},clearTimeout:n=>pending.delete(n),requestAnimationFrame:fn=>{pending.set(++id,fn);return id},cancelAnimationFrame:n=>pending.delete(n),scrollTo:()=>scrolls++})
 const flush=()=>{const tasks=[...pending.values()];pending.clear();tasks.forEach(fn=>fn())}
 const control=displayViewport(win,()=>active);flush()
 visual.height=440;win.dispatchEvent(new Event('orientationchange'));flush()
 assert.equal(styles.get('--display-height'),'440px');assert.equal(scrolls,8)
 visual.scale=2;visual.height=220;visual.dispatchEvent(new Event('resize'));flush()
 assert.equal(styles.get('--display-height'),'440px')
 active=false;win.dispatchEvent(new Event('orientationchange'));flush();assert.equal(scrolls,8)
 active=true;control.settle();control.dispose();flush()
 assert.equal(pending.size,0);assert.equal(styles.has('--display-height'),false)
 win.dispatchEvent(new Event('orientationchange'));assert.equal(pending.size,0)
})
