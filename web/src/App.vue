<script setup>
import {ref, computed, watch, onMounted, onUnmounted} from 'vue'
import {useI18n} from 'vue-i18n'
import Widget from './Widget.vue'
import OrbitDisplay from './OrbitDisplay.vue'
import {displayViewport} from './display-viewport.js'
import {dashboardWidgets} from './widgets.js'
import {stamp,isStale} from './format.js'
import {observationExpired} from './system-format.js'
import {deviceConfig, persist, preference} from './locale-core.js'
import {defaultProfile,layoutProfile,storedProfile} from './layout-profile.js'
import {appearance,themeStyle,themeNames,accentNames} from './themes.js'
const {t,locale}=useI18n()
let storage;try{storage=window.localStorage}catch{}
const config=ref(deviceConfig(preference(storage,'pixora-device',preference(storage,'apm-device','{}'))))
if(config.value.layout==='public'){config.value.shared=true;config.value.layout='overview'}
const secureSession=location.protocol==='https:'
const rememberDevice=ref(secureSession),remembered=ref(false),sessionExpiry=ref(''),authBusy=ref(false),logoutPending=ref(preference(storage,'pixora-logout-pending','')==='1')
const token=ref(''),mode=ref('real'),data=ref(null),error=ref(null),connected=ref(false),busy=ref(false),clock=ref(new Date()),kiosk=ref(new URLSearchParams(location.search).has('kiosk'))
const wakeState=ref('idle'),management=ref(false),pollStarted=ref(Date.now())
function manage(){management.value=true;exit()}
const pageVisible=ref(!document.hidden)
function visibilityChanged(){pageVisible.value=!document.hidden;wakeScreen()}
const activeView=ref('system')
const profile=ref({...defaultProfile}),deviceProfile=ref(null),localProfile=ref(false)
const systemDark=ref(window.matchMedia?.('(prefers-color-scheme: dark)').matches??true)
const cityQuery=ref(''),cityResults=ref([]),citySearching=ref(false),cityError=ref(''),weatherBusy=ref(false),weatherError=ref(false)
const canChooseCity=computed(()=>!config.value.shared&&mode.value==='real'&&deviceProfile.value?.providers.includes('weather')&&!deviceProfile.value?.public_only)
const selectedCity=computed(()=>data.value?.observations?.find(o=>o.provider==='weather')?.entries?.[0]?.title)
let cityController,weatherController,weatherRequest=0,searchRequest=0
function stopWeather(){weatherRequest++;searchRequest++;weatherController?.abort();cityController?.abort();weatherBusy.value=false;citySearching.value=false;weatherError.value=false;cityResults.value=[];cityError.value=''}
function clearWeather(){if(data.value)data.value={...data.value,observations:(data.value.observations||[]).filter(o=>o.provider!=='weather')}}
async function searchCity(query=cityQuery.value){
 if(!canChooseCity.value)return
 cityQuery.value=query;cityController?.abort();const request=++searchRequest,abort=new AbortController();cityController=abort
 citySearching.value=true;cityError.value='';cityResults.value=[];const timeout=setTimeout(()=>abort.abort(),22000)
 try{
  const r=await fetch('/api/v2/weather/locations?'+new URLSearchParams({name:query,language:locale.value==='zh-CN'?'zh':'en'}),{credentials:'same-origin',headers:token.value?{Authorization:'Bearer '+token.value}:{},signal:abort.signal})
  if(!r.ok)throw Error('unavailable')
  const result=await r.json();if(request!==searchRequest)return
  cityResults.value=result.locations;if(!result.locations.length)cityError.value='city.noResults'
 }catch{if(request===searchRequest)cityError.value='city.searchError'}
 finally{clearTimeout(timeout);if(request===searchRequest)citySearching.value=false}
}
function chooseCity(id){profile.value.weather_location=id;saveLayout();cityResults.value=[];clearWeather();if(id===null)load();else refreshWeather()}
async function refreshWeather(){
 const id=profile.value.weather_location
 weatherController?.abort();const request=++weatherRequest
 if(!canChooseCity.value||id===null){weatherBusy.value=false;weatherError.value=false;return}
 const abort=new AbortController();weatherController=abort;const timeout=setTimeout(()=>abort.abort(),35000)
 weatherBusy.value=true;weatherError.value=false
 try{
  const r=await fetch('/api/v2/weather/'+id+'?language='+(locale.value==='zh-CN'?'zh':'en'),{credentials:'same-origin',headers:token.value?{Authorization:'Bearer '+token.value}:{},signal:abort.signal})
  if(!r.ok){if(request===weatherRequest&&[401,403].includes(r.status))clearWeather();throw Error('unavailable')}
  const result=await r.json()
  if(request!==weatherRequest||profile.value.weather_location!==id||config.value.shared||!data.value)return
  data.value={...data.value,observations:[...(data.value.observations||[]).filter(o=>o.provider!=='weather'),result.observation]}
 }catch{if(request===weatherRequest)weatherError.value=true}
 finally{clearTimeout(timeout);if(request===weatherRequest)weatherBusy.value=false}
}
let colorMedia
function colorChanged(){systemDark.value=colorMedia.matches}
const themeVars=computed(()=>themeStyle(profile.value,systemDark.value))
const resolvedAppearance=computed(()=>appearance(profile.value,systemDark.value))
function chooseTheme(name){profile.value.theme=name;saveLayout()}

function saveLayout(){
 if(!deviceProfile.value||config.value.shared)return
 localProfile.value=true;saved.value=persist(storage,'pixora-profile:'+deviceProfile.value.device_id,JSON.stringify(profile.value))
 viewport?.settle()
}
function resetLayout(){
 if(!deviceProfile.value)return
 profile.value=layoutProfile(deviceProfile.value.profile);localProfile.value=false
 saved.value=persist(storage,'pixora-profile:'+deviceProfile.value.device_id,'null');viewport?.settle();clearWeather();load()
}
function exportLayout(){
 const url=URL.createObjectURL(new Blob([JSON.stringify(profile.value,null,2)],{type:'application/json'}))
 const a=document.createElement('a');a.href=url;a.download='pixora-layout.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000)
}
function applyProfile(remote){
 if(remote?.device_id!==deviceProfile.value?.device_id){
  const local=storedProfile(preference(storage,'pixora-profile:'+remote?.device_id,'null'))
  localProfile.value=!!local;profile.value=local||layoutProfile(remote?.profile)
 }else if(!localProfile.value)profile.value=layoutProfile(remote?.profile)
 deviceProfile.value=remote
}

const systemHistory=ref([]),historyNext=ref(null),historyError=ref(false)
const widgets=computed(()=>dashboardWidgets('overview',config.value.shared,activeView.value).filter(id=>!['clock','calendar','weather','status'].includes(id)))
const diagnostic=ref(new URLSearchParams(location.search).get('debug')==='1')
const date=value=>stamp(value,locale.value,t('widget.notCollected'))
const dataState=item=>!connected.value?'status.cached':item.windows?(isStale(item,data.value,clock.value)?'status.stale':item.status==='ok'?'status.fresh':'status.unavailable'):(observationExpired(item,clock.value)?'status.stale':item.status==='ok'?'status.fresh':'status.unavailable')
function refreshView(){load()}
let timer,tick,controller,wake,viewport,generation=0
watch(kiosk,()=>viewport?.settle(),{flush:'post'})
const saved=ref(null)
function save(){saved.value=persist(storage,'pixora-device',JSON.stringify(config.value))}
function resetDisplay(){config.value.layout='overview';config.value.quotaStyle='rings';config.value.theme='dark';save()}
function language(){saved.value=persist(storage,'pixora-locale',locale.value)}
watch(locale,()=>{document.documentElement.lang=locale.value;document.documentElement.dir='ltr'},{immediate:true})
function cancel(){stopWeather();systemHistory.value=[];historyNext.value=null;historyError.value=false;generation++;controller?.abort();busy.value=false}
async function load(){
 if(busy.value||authBusy.value||logoutPending.value||(!token.value&&!remembered.value)||config.value.shared)return
 const current=++generation, requestedMode=mode.value
 const requestController=new AbortController();controller=requestController;busy.value=true
 const timeout=setTimeout(()=>requestController.abort(),10000)
 try{
   const r=await fetch('/api/v1/device?mode='+requestedMode,{credentials:'same-origin',headers:token.value?{Authorization:'Bearer '+token.value}:{},signal:requestController.signal})
   if(!r.ok)throw {status:r.status}
   const result=await r.json()
   const cfg=await fetch('/api/v2/device-config',{credentials:'same-origin',headers:token.value?{Authorization:'Bearer '+token.value}:{},signal:requestController.signal})
   if(!cfg.ok&&cfg.status!==403)throw {status:cfg.status}
   const remote=cfg.ok?await cfg.json():null
   if(remote&&remote.device_id!==result.device_id)throw {status:409}
   result.observations=[]
   try{
    const v2=await fetch('/api/v2/observations?mode='+requestedMode,{credentials:'same-origin',headers:token.value?{Authorization:'Bearer '+token.value}:{},signal:requestController.signal})
    if(v2.ok)result.observations=(await v2.json()).observations
   }catch{}
   if(current!==generation||config.value.shared)return
   applyProfile(remote)
   if(profile.value.weather_location!==null){
    const cached=canChooseCity.value?data.value?.observations?.find(o=>o.provider==='weather'&&o.entity_id==='place-'+profile.value.weather_location):null
    result.observations=result.observations.filter(o=>o.provider!=='weather');if(cached)result.observations.push(cached)
   }
   data.value=result;connected.value=true;error.value=null;refreshWeather()
 }catch(e){if(current===generation){if(e.status===401){token.value='';remembered.value=false;sessionExpiry.value='';data.value=null;deviceProfile.value=null;profile.value={...defaultProfile};localProfile.value=false}error.value=e.status===401?{key:'auth.expired'}:e.status?{key:'status.failure',params:{status:e.status}}:{key:'status.network'};connected.value=false}}
 finally{clearTimeout(timeout);if(current===generation)busy.value=false}
}
function changeMode(){cancel();data.value=null;connected.value=false;load()}
async function loadHistory(more=false){
 if(config.value.shared||(!token.value&&!remembered.value)||logoutPending.value)return
 const current=generation,abort=new AbortController(),timeout=setTimeout(()=>abort.abort(),10000)
 const before=more&&historyNext.value?'&before='+historyNext.value:''
 try{
  const response=await fetch('/api/v2/history?provider=system&limit=20&mode='+mode.value+before,{credentials:'same-origin',headers:token.value?{Authorization:'Bearer '+token.value}:{},signal:abort.signal})
  if(!response.ok)throw Error('history unavailable')
  const result=await response.json()
  if(current!==generation||config.value.shared)return
  systemHistory.value=more?[...systemHistory.value,...result.items].slice(-200):result.items
  historyNext.value=result.next_before;historyError.value=false
 }catch{if(current===generation){systemHistory.value=[];historyNext.value=null;historyError.value=true}}
 finally{clearTimeout(timeout)}
}
async function sessionRequest(method, headers={}){
 const abort=new AbortController(),timeout=setTimeout(()=>abort.abort(),10000)
 try{return await fetch('/api/v1/session',{method,credentials:'same-origin',headers,signal:abort.signal})}
 finally{clearTimeout(timeout)}
}
function pendingLogout(value){logoutPending.value=value;persist(storage,'pixora-logout-pending',value?'1':'')}
async function clearRemoteSession(){
 if(!secureSession){pendingLogout(false);return}
 pendingLogout(true)
 const response=await sessionRequest('DELETE')
 if(!response.ok)throw Error('logout failed')
 pendingLogout(false)
}
async function connect(){
 if(authBusy.value||config.value.shared)return
 if(!token.value){load();return}
 cancel();const current=generation;error.value=null;data.value=null;deviceProfile.value=null;profile.value={...defaultProfile};localProfile.value=false;connected.value=false
 if(!rememberDevice.value){load();return}
 authBusy.value=true
 try{
  const response=await sessionRequest('POST',{Authorization:'Bearer '+token.value})
  if(!response.ok)throw {status:response.status}
  const session=await response.json()
  if(current!==generation){await clearRemoteSession();return}
  token.value='';remembered.value=true;sessionExpiry.value=session.expires_at;pendingLogout(false)
  if(!session.modes.includes(mode.value))mode.value=session.modes[0]
 }catch(e){if(current===generation)error.value={key:e.status===401?'auth.expired':'auth.loginFailed'}}
 finally{authBusy.value=false}
 if(current===generation&&remembered.value)load()
}
async function disconnect(){
 config.value.shared=false;save()
 cancel();token.value='';data.value=null;deviceProfile.value=null;profile.value={...defaultProfile};localProfile.value=false;connected.value=false;remembered.value=false;sessionExpiry.value='';error.value=null
 try{await clearRemoteSession()}catch{error.value={key:'auth.logoutFailed'}}
}
async function restoreSession(){
 if(!secureSession){pendingLogout(false);return}
 if(config.value.shared||logoutPending.value){await disconnect();return}
 const current=generation
 try{
  const response=await sessionRequest('GET')
  if(!response.ok){if(response.status!==401)error.value={key:'status.network'};return}
  const session=await response.json()
  if(current!==generation)return
  remembered.value=true;sessionExpiry.value=session.expires_at
  if(!session.modes.includes(mode.value))mode.value=session.modes[0]
  load()
 }catch{if(current===generation)error.value={key:'status.network'}}
}
async function wakeScreen(){
 if(!kiosk.value||document.visibilityState!=='visible'||wake||wakeState.value==='requesting')return
 if(!navigator.wakeLock?.request){wakeState.value='unsupported';return}
 wakeState.value='requesting'
 try{
  const lock=await navigator.wakeLock.request('screen')
  if(!kiosk.value||document.visibilityState!=='visible'){await lock.release();wakeState.value='idle';return}
  wake=lock;wakeState.value='active'
  lock.addEventListener('release',()=>{if(wake===lock){wake=null;wakeState.value=kiosk.value?'released':'idle'}})
 }catch{wakeState.value=kiosk.value?'failed':'idle'}
}
async function exit(){kiosk.value=false;try{if(document.fullscreenElement)await document.exitFullscreen()}catch{};wake?.release();wakeState.value='idle'}
async function display(){kiosk.value=true;try{await document.documentElement.requestFullscreen?.()}catch{};wakeScreen()}
onMounted(async()=>{
 colorMedia=window.matchMedia?.('(prefers-color-scheme: dark)');if(colorMedia){colorChanged();if(colorMedia.addEventListener)colorMedia.addEventListener('change',colorChanged);else colorMedia.addListener?.(colorChanged)}
 viewport=displayViewport(window,()=>kiosk.value)
 wakeScreen();timer=setInterval(()=>{pollStarted.value=Date.now();load()},30000);tick=setInterval(()=>clock.value=new Date(),1000)
 document.addEventListener('visibilitychange',visibilityChanged)
 if('serviceWorker' in navigator)navigator.serviceWorker.register('/sw.js').catch(()=>{})
 const pairing=new URLSearchParams(location.hash.slice(1)),incoming=pairing.get('token')
 if(pairing.has('token'))history.replaceState(null,'',location.pathname+location.search)
 if(incoming&&/^[A-Za-z0-9_-]{32,128}$/.test(incoming)){
  token.value=incoming;mode.value='real';config.value.shared=false;save();await connect()
 }else await restoreSession()
})
onUnmounted(()=>{if(colorMedia?.removeEventListener)colorMedia.removeEventListener('change',colorChanged);else colorMedia?.removeListener?.(colorChanged);viewport?.dispose();clearInterval(timer);clearInterval(tick);cancel();wake?.release();document.removeEventListener('visibilitychange',visibilityChanged)})
</script>
<template><div class="pixora-themed" :class="['preset-'+profile.theme,'appearance-'+resolvedAppearance,{'theme-motion':config.motion&&pageVisible}]" :style="themeVars"><OrbitDisplay v-if="!management" :data="config.shared?null:data" :profile="profile" :weather-busy="weatherBusy" :weather-error="weatherError" :clock="clock" :connected="connected" :busy="busy" :mode="mode" :error="error" :motion="config.motion" :visible="pageVisible" :poll-started="pollStarted" :kiosk="kiosk" :wake-state="wakeState" @manage="manage" @display="display" @exit="exit" @motion="config.motion=!config.motion;save()"/>
<main v-else class="dark settings-page" :class="{motion:config.motion&&pageVisible}" data-ui>
<header class="app-bar"><div class="brand-lockup"><span>Pixora</span><small>{{t('settings.title')}}</small></div><button class="secondary" @click="management=false">{{t('orbit.back')}}</button></header>
<p v-if="error" class="notice notice-error" role="alert">{{t(error.key,error.params||{})}}</p>
<section class="settings-section" aria-labelledby="display-heading"><h1 id="display-heading">{{t('settings.display')}}</h1><p class="muted">{{t('settings.local')}}</p><div class="settings-fields">
<label>{{t('config.language')}}<select v-model="locale" @change="language"><option value="en-US" lang="en">{{t('language.english')}}</option><option value="zh-CN" lang="zh-CN">{{t('language.chinese')}}</option></select></label>
<label class="check-field"><input type="checkbox" v-model="config.motion" @change="save">{{t('motion.enable')}}</label>
</div><fieldset class="layout-editor" :disabled="!deviceProfile||config.shared"><legend>{{t('layout.title')}}</legend><p class="muted">{{t('layout.hint')}}</p><div class="theme-picker" role="group" :aria-label="t('themes.title')"><button v-for="name in themeNames" :key="name" class="theme-option" :aria-pressed="profile.theme===name" :style="themeStyle({...profile,theme:name},systemDark)" @click="chooseTheme(name)"><span class="theme-mark" aria-hidden="true"/><strong>{{t('themes.'+name)}}</strong><small>{{t('themes.'+name+'Hint')}}</small></button></div><div class="settings-fields"><label>{{t('themes.accent')}}<select v-model="profile.accent" @change="saveLayout"><option v-for="name in accentNames" :key="name" :value="name">{{t('themes.'+name)}}</option></select></label><label>{{t('themes.appearance')}}<select v-model="profile.appearance" @change="saveLayout"><option value="theme">{{t('themes.themeDefault')}}</option><option value="light">{{t('config.light')}}</option><option value="dark">{{t('config.dark')}}</option><option value="auto">{{t('themes.auto')}}</option></select></label><label>{{t('themes.text')}}<select v-model="profile.text_size" @change="saveLayout"><option value="standard">{{t('themes.standard')}}</option><option value="large">{{t('themes.large')}}</option></select></label></div><p class="muted">{{t('themes.hint')}}</p><details class="weather-city"><summary>{{t('city.title')}} · {{selectedCity||(profile.weather_location?'#'+profile.weather_location:t('city.default'))}}</summary><fieldset :disabled="!canChooseCity" class="layout-editor"><p class="muted">{{t('city.hint')}}</p><div class="settings-actions"><button class="secondary" @click="searchCity('Shanghai')">上海</button><button class="secondary" @click="searchCity('Houston')">Houston</button><button class="secondary" @click="chooseCity(null)">{{t('city.default')}}</button></div><label>{{t('city.name')}}<input v-model="cityQuery" maxlength="80" @keyup.enter="searchCity()" :placeholder="t('city.placeholder')"></label><button class="secondary" :disabled="citySearching||cityQuery.trim().length<2" @click="searchCity()">{{t(citySearching?'city.searching':'city.search')}}</button><ul class="city-results"><li v-for="place in cityResults" :key="place.id"><button class="secondary" @click="chooseCity(place.id)">{{[place.name,place.admin1,place.country].filter(Boolean).join(' · ')}}<small>{{place.timezone}}</small></button></li></ul></fieldset><p v-if="!canChooseCity" class="muted">{{t('city.permission')}}</p><p v-if="cityError" role="status">{{t(cityError)}}</p><p v-if="weatherBusy" role="status">{{t('city.loading')}}</p><p v-if="weatherError" role="status">{{t('city.unavailable')}}</p><small><a href="https://open-meteo.com/en/docs/geocoding-api" target="_blank" rel="noopener noreferrer">Open-Meteo / GeoNames</a></small></details><div class="settings-fields"><label class="check-field"><input type="checkbox" v-model="profile.show_clock" @change="saveLayout">{{t('layout.clock')}}</label><label class="check-field"><input type="checkbox" v-model="profile.show_weather" @change="saveLayout">{{t('layout.weather')}}</label><label>{{t('layout.focus')}}<select v-model="profile.focus_window" @change="saveLayout"><option value="primary">{{t('layout.primary')}}</option><option value="weekly">{{t('layout.weekly')}}</option></select></label><label>{{t('layout.density')}}<select v-model="profile.density" @change="saveLayout"><option value="comfortable">{{t('layout.comfortable')}}</option><option value="compact">{{t('layout.compact')}}</option></select></label></div><div class="settings-actions"><button class="secondary" @click="management=false">{{t('layout.preview')}}</button><button class="secondary" @click="resetLayout">{{t('layout.reset')}}</button><button class="secondary" @click="exportLayout">{{t('layout.export')}}</button></div></fieldset><p class="muted" v-if="deviceProfile">{{t(localProfile?'layout.local':'layout.server',{revision:deviceProfile.revision})}} · {{deviceProfile.name}}</p><p class="muted" v-else>{{t('layout.pair')}}</p><div class="settings-actions"><button @click="management=false;display()">{{t('config.display')}}</button><span>{{t('display.wake_'+wakeState)}}</span></div><p class="muted">{{t('settings.wakeHint')}}</p><p v-if="saved!==null" role="status" class="saved-message">{{t(saved?'settings.saved':'settings.unsaved')}}</p></section>
<section class="settings-section" aria-labelledby="data-heading"><h2 id="data-heading">{{t('settings.data')}}</h2><div class="settings-actions"><span>{{t(connected?'status.connected':'status.offline')}}</span><button class="secondary" :disabled="busy||authBusy||config.shared||(!token&&!remembered)" @click="refreshView">{{t(busy?'ui.refreshing':'ui.refresh')}}</button></div><p class="muted">{{t('orbit.rhythm')}} · {{t('status.sync',{time:date(data?.server_time)})}}</p>
<p v-if="config.shared" class="muted">{{t('settings.privateHidden')}}</p>
<ul v-else class="source-list"><li v-for="p in data?.providers||[]" :key="p.provider"><strong>{{t('provider.'+p.provider)}}</strong><span>{{t(dataState(p))}}</span><small>{{p.source}} · {{date(p.collected_at||p.observed_at)}}</small></li><li v-for="o in data?.observations||[]" :key="o.connector_id+'/'+o.entity_id"><strong>{{o.provider}} · {{o.entity_id}}</strong><span>{{t(dataState(o))}}</span><small>{{o.source}} · {{date(o.collected_at)}}</small></li></ul>
<details v-if="!config.shared" class="content-details"><summary>{{t('settings.content')}}</summary><nav class="settings-actions" :aria-label="t('ui.views')"><button v-for="view in ['system','developer','personal']" :key="view" :aria-pressed="activeView===view" @click="activeView=view">{{t('ui.'+view)}}</button></nav><div class="cards"><Widget v-for="id in widgets" :key="id" :kind="id" quota-style="rings" :data="data" :connected="connected" :history="systemHistory" :history-next="historyNext" :history-error="historyError" @history="loadHistory" :clock="clock"/></div></details></section>
<section class="settings-section" aria-labelledby="auth-heading"><h2 id="auth-heading">{{t('settings.auth')}}</h2><p v-if="remembered" role="status">{{t('auth.remembered',{time:date(sessionExpiry)})}}</p><p v-else-if="token&&connected">{{t('settings.temporary')}}</p><p v-else>{{t('settings.signedOut')}}</p><p class="muted">{{t('settings.pairHint')}}</p>
<details v-if="!config.shared" class="manual-pair"><summary>{{t('settings.manual')}}</summary><p class="muted">{{t('settings.tokenPrivate')}}</p><div class="authorization-fields"><label>{{t('config.token')}}<input v-model="token" type="password" autocomplete="off" :placeholder="t('config.tokenHint')" @keyup.enter="connect"></label><label class="check-field"><input type="checkbox" v-model="rememberDevice" :disabled="authBusy||!secureSession">{{t('auth.remember')}}</label><button :disabled="busy||authBusy||!token" @click="connect">{{t('config.connect')}}</button></div></details></section>
<section v-if="diagnostic" class="settings-section"><h2>{{t('settings.diagnostics')}}</h2><p class="muted">{{t('settings.debugHint')}}</p><label>{{t('config.data')}}<select v-model="mode" @change="changeMode"><option value="real">{{t('config.real')}}</option><option value="demo">{{t('config.demo')}}</option></select></label><button class="secondary" @click="resetDisplay">{{t('settings.resetLegacy')}}</button></section>
<p v-if="mode==='demo'" class="notice">{{t('data.demo')}}</p>
<p class="admin-link"><a href="/?admin=1">{{t('admin.entry')}}</a></p>
<div class="sign-out-actions"><p class="muted">{{t('settings.logoutHint')}}</p><button class="secondary" :disabled="authBusy||(!token&&!remembered&&!logoutPending)" @click="disconnect">{{t(logoutPending?'settings.retryLogout':'config.disconnect')}}</button></div>
<footer><span>{{t('app.principle')}}</span><span>{{t('app.stage')}}</span></footer></main></div></template>
<style scoped>
.sign-out-actions{padding:24px 0}.sign-out-actions p{font-size:13px;margin-bottom:12px}
.settings-page{max-width:960px;margin:auto;padding:0 max(20px,env(safe-area-inset-left)) 28px}.settings-section{padding:24px 0;border-bottom:1px solid var(--line);line-height:1.7}.settings-section h1,.settings-section h2{font-size:18px;margin-bottom:12px}.settings-actions{display:flex;align-items:center;flex-wrap:wrap;gap:12px;margin:16px 0}.settings-actions button[aria-pressed=true]{border-color:var(--accent);color:var(--accent)}.source-list{list-style:none;padding:0;margin:16px 0}.source-list li{display:flex;flex-wrap:wrap;justify-content:space-between;gap:8px;padding:12px 0;border-bottom:1px solid var(--line);font-size:13px}.source-list small{flex-basis:100%;overflow-wrap:anywhere}.content-details,.manual-pair{margin-top:20px}.city-results{padding:0;list-style:none}.city-results button{display:flex;flex-direction:column;text-align:left;gap:6px;width:100%;margin:8px 0}.weather-city{margin-top:16px}.weather-city>small a{color:var(--muted)}.layout-editor{border:0;padding:16px 0 0;margin:12px 0 0;min-width:0}.layout-editor legend{font-size:14px}.settings-page summary{cursor:pointer;min-height:44px;padding:10px 0}.saved-message{color:var(--accent);font-size:13px}.settings-fields{grid-template-columns:repeat(2,minmax(0,1fr))}.manual-pair .authorization-fields{border-top:0;margin-top:0}.settings-section>button{margin-top:12px}@media(max-width:600px){.settings-fields{grid-template-columns:1fr}.settings-section{padding:20px 0}}
</style>
