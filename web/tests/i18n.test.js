import {test} from 'node:test'
import assert from 'node:assert/strict'
import {readFileSync} from 'node:fs'
import {createI18n} from 'vue-i18n'
import {resolveLocale,preference,persist,deviceConfig} from '../src/locale-core.js'
import {registry} from '../src/widgets.js'
const en=JSON.parse(readFileSync(new URL('../src/locales/en-US.json',import.meta.url)))
const zh=JSON.parse(readFileSync(new URL('../src/locales/zh-CN.json',import.meta.url)))
const flatten=(v,p='')=>Object.keys(v).flatMap(k=>typeof v[k]==='object'?flatten(v[k],p+k+'.'):[p+k])
test('English and Chinese keys match and widgets have translated titles',()=>{assert.deepEqual(flatten(en).sort(),flatten(zh).sort());for(const w of Object.values(registry))assert.ok(flatten(en).includes(w.titleKey))})
test('language detection, explicit preference and fallback',()=>{assert.equal(resolveLocale(null,['zh-TW']),'zh-CN');assert.equal(resolveLocale('en-US',['zh-CN']),'en-US');assert.equal(resolveLocale('fr-FR',['de-DE']),'en-US');assert.equal(resolveLocale(null,['fr-FR','en-GB','zh-CN']),'en-US')})
test('manual language switch changes strings and missing messages fall back',()=>{const partial=structuredClone(zh);delete partial.widget.unknown;const i=createI18n({legacy:false,locale:'en-US',fallbackLocale:'en-US',missingWarn:false,fallbackWarn:false,messages:{'en-US':en,'zh-CN':partial}}).global;assert.equal(i.t('config.connect'),'Connect / Refresh');i.locale.value='zh-CN';assert.equal(i.t('config.connect'),'连接 / 刷新');assert.equal(i.t('widget.unknown'),'Unknown')})
test('storage errors and corrupted device config do not prevent startup',()=>{const denied={getItem(){throw Error()},setItem(){throw Error()}};assert.equal(preference(denied,'x','fallback'),'fallback');assert.doesNotThrow(()=>persist(denied,'x','value'));assert.equal(deviceConfig('null').theme,'dark');assert.equal(deviceConfig('{"shared":"false","theme":"bad"}').shared,false);assert.equal(deviceConfig('not json').layout,'overview')})

test('display preferences survive a save/reopen and report blocked storage',()=>{
 const values=new Map(),storage={getItem:k=>values.get(k)??null,setItem:(k,v)=>values.set(k,v)}
 const changed={...deviceConfig('{}'),motion:false,shared:true}
 assert.equal(persist(storage,'pixora-device',JSON.stringify(changed)),true)
 assert.equal(persist(storage,'pixora-locale','en-US'),true)
 assert.equal(deviceConfig(preference(storage,'pixora-device','{}')).motion,false)
 assert.equal(deviceConfig(preference(storage,'pixora-device','{}')).shared,true)
 assert.equal(resolveLocale(preference(storage,'pixora-locale'),['zh-CN']),'en-US')
 assert.equal(persist({setItem(){throw Error('blocked')}},'x','y'),false)
 assert.equal(persist(undefined,'x','y'),false)
})
