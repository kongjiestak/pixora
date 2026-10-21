import {test} from 'node:test'
import assert from 'node:assert/strict'
import {themeStyle,appearance,themeNames,accentNames} from '../src/themes.js'
import {layoutProfile,storedProfile,defaultProfile} from '../src/layout-profile.js'
function luminance(hex){const rgb=hex.slice(1).match(/../g).map(x=>parseInt(x,16)/255).map(n=>n<=.04045?n/12.92:((n+.055)/1.055)**2.4);return rgb[0]*.2126+rgb[1]*.7152+rgb[2]*.0722}
function contrast(a,b){const x=luminance(a),y=luminance(b);return (Math.max(x,y)+.05)/(Math.min(x,y)+.05)}
test('theme modes resolve predictably and preserve accepted defaults',()=>{
 assert.equal(appearance({}),'dark');assert.equal(appearance({theme:'paper'}),'light')
 assert.equal(appearance({theme:'paper',appearance:'dark'}),'dark')
 assert.equal(appearance({appearance:'auto'},false),'light');assert.equal(appearance({appearance:'auto'},true),'dark')
 assert.equal(themeStyle({theme:'amoled'})['--ground'],'#000000')
 assert.equal(themeStyle({})['--ground'],'#080f11')
})
test('all theme/accent combinations retain readable text and distinct quota keys',()=>{
 for(const theme of themeNames)for(const accent of accentNames)for(const mode of ['light','dark']){
  const p=themeStyle({theme,accent,appearance:mode})
  for(const key of ['--ink','--muted','--accent','--secondary','--warning','--danger'])assert.ok(contrast(p[key],p['--ground'])>=4.5,`${theme}/${accent}/${mode}: ${key}`)
  assert.notEqual(p['--accent'],p['--secondary'])
 }
})
test('old profiles upgrade safely; new fields persist without accepting CSS injections',()=>{
 const old=storedProfile('{"show_clock":false}')
 assert.equal(old.show_clock,false);assert.equal(old.theme,'orbit')
 const p=layoutProfile({theme:'aurora',accent:'violet',text_size:'large',appearance:'auto'})
 assert.deepEqual(storedProfile(JSON.stringify(p)),p)
 assert.equal(themeStyle(p)['--type-scale'],'1.18')
 assert.deepEqual(layoutProfile({theme:'url(https://evil.example)',accent:'red;display:none',appearance:'invalid',text_size:'10000'}),{...defaultProfile})
})
