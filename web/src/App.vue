<script setup>
import {ref, computed, watch, onMounted, onUnmounted} from 'vue'
import {useI18n} from 'vue-i18n'
import Widget from './Widget.vue'
import DisplayStage from './DisplayStage.vue'
import {displayViewport} from './display-viewport.js'
import {dashboardWidgets,displayWidgets} from './widgets.js'
import {deviceConfig, persist, preference} from './locale-core.js'
const {t,locale}=useI18n()
let storage;try{storage=window.localStorage}catch{}
const config=ref(deviceConfig(preference(storage,'pixora-device',preference(storage,'apm-device','{}'))))
const secureSession=location.protocol==='https:'
const rememberDevice=ref(secureSession),remembered=ref(false),sessionExpiry=ref(''),authBusy=ref(false),logoutPending=ref(preference(storage,'pixora-logout-pending','')==='1')
const token=ref(''),mode=ref('real'),data=ref(null),error=ref(null),connected=ref(false),busy=ref(false),clock=ref(new Date()),kiosk=ref(new URLSearchParams(location.search).has('kiosk'))
const displayLayout=ref(['clock-quota','quota','system','developer','personal'].includes(preference(storage,'pixora-display-layout','clock-quota'))?preference(storage,'pixora-display-layout','clock-quota'):'clock-quota'),showDisplayTools=ref(false),wakeState=ref('idle')
const activeView=ref('overview'),showSettings=ref(false)
const systemHistory=ref([]),historyNext=ref(null),historyError=ref(false)
const widgets=computed(()=>kiosk.value?displayWidgets(displayLayout.value,config.value.shared):dashboardWidgets(config.value.layout,config.value.shared,activeView.value))
function refreshView(){load();if(!token.value&&!remembered.value)showSettings.value=true}
function saveDisplay(){persist(storage,'pixora-display-layout',displayLayout.value)}
let timer,tick,controller,wake,viewport,generation=0
watch(kiosk,()=>viewport?.settle(),{flush:'post'})
function save(){persist(storage,'pixora-device',JSON.stringify(config.value))}
function language(){persist(storage,'pixora-locale',locale.value)}
watch(locale,()=>{document.documentElement.lang=locale.value;document.documentElement.dir='ltr'},{immediate:true})
function cancel(){systemHistory.value=[];historyNext.value=null;historyError.value=false;generation++;controller?.abort();busy.value=false}
async function load(){
 if(busy.value||authBusy.value||logoutPending.value||(!token.value&&!remembered.value)||config.value.shared)return
 const current=++generation, requestedMode=mode.value
 const requestController=new AbortController();controller=requestController;busy.value=true
 const timeout=setTimeout(()=>requestController.abort(),10000)
 try{
   const r=await fetch('/api/v1/device?mode='+requestedMode,{credentials:'same-origin',headers:token.value?{Authorization:'Bearer '+token.value}:{},signal:requestController.signal})
   if(!r.ok)throw {status:r.status}
   const result=await r.json()
   result.observations=[]
   try{
    const v2=await fetch('/api/v2/observations?mode='+requestedMode,{credentials:'same-origin',headers:token.value?{Authorization:'Bearer '+token.value}:{},signal:requestController.signal})
    if(v2.ok)result.observations=(await v2.json()).observations
   }catch{}
   if(current!==generation||config.value.shared)return
   data.value=result;connected.value=true;error.value=null
 }catch(e){if(current===generation){if(e.status===401){token.value='';remembered.value=false;sessionExpiry.value='';data.value=null}error.value=e.status===401?{key:'auth.expired'}:e.status?{key:'status.failure',params:{status:e.status}}:{key:'status.network'};connected.value=false}}
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
 cancel();const current=generation;error.value=null;data.value=null;connected.value=false
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
 cancel();token.value='';data.value=null;connected.value=false;remembered.value=false;sessionExpiry.value='';error.value=null
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
function share(){if(config.value.shared)disconnect();save()}
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
async function exit(){kiosk.value=false;showDisplayTools.value=false;try{if(document.fullscreenElement)await document.exitFullscreen()}catch{};wake?.release();wakeState.value='idle'}
async function display(){kiosk.value=true;showDisplayTools.value=false;try{await document.documentElement.requestFullscreen?.()}catch{};wakeScreen()}
onMounted(async()=>{
 viewport=displayViewport(window,()=>kiosk.value)
 wakeScreen();timer=setInterval(load,30000);tick=setInterval(()=>clock.value=new Date(),1000)
 document.addEventListener('visibilitychange',wakeScreen)
 if('serviceWorker' in navigator)navigator.serviceWorker.register('/sw.js').catch(()=>{})
 const pairing=new URLSearchParams(location.hash.slice(1)),incoming=pairing.get('token')
 if(pairing.has('token'))history.replaceState(null,'',location.pathname+location.search)
 if(incoming&&/^[A-Za-z0-9_-]{32,128}$/.test(incoming)){
  token.value=incoming;mode.value='real';config.value.shared=false;save();await connect()
 }else await restoreSession()
})
onUnmounted(()=>{viewport?.dispose();clearInterval(timer);clearInterval(tick);cancel();wake?.release();document.removeEventListener('visibilitychange',wakeScreen)})
</script>
<template><main :class="[config.theme,{kiosk,'display-fit':kiosk&&!showDisplayTools},kiosk?'display-'+displayLayout:'',!kiosk?'view-'+activeView:'']" data-ui>
<div v-if="kiosk" class="display-bar"><h1 class="brand-lockup"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3 7V3h7M14 3h7v7M21 14v7h-7M10 21H3v-7"/><path d="M8 8h8v8H8z"/></svg><span>Pixora</span><small>{{config.name}}</small></h1><div class="display-actions"><span class="wake-status" role="status">{{t('display.wake_'+wakeState)}}</span><button class="secondary" :aria-expanded="showDisplayTools" @click="showDisplayTools=!showDisplayTools">{{t('display.settings')}}</button><button class="secondary" @click="exit">{{t('config.exit')}}</button></div></div>
<section v-if="kiosk&&showDisplayTools" class="display-tools"><label>{{t('display.layout')}}<select v-model="displayLayout" @change="saveDisplay"><option value="clock-quota">{{t('display.clockQuota')}}</option><option value="quota">{{t('display.quotaOnly')}}</option><option value="system">{{t('system.title')}}</option><option value="developer">{{t('ui.developer')}}</option><option value="personal">{{t('ui.personal')}}</option></select></label><button v-if="wakeState!=='active'" @click="wakeScreen">{{t('display.retryWake')}}</button><p>{{t('display.installHint')}}</p></section>
<template v-if="!kiosk">
<header class="app-bar"><div class="brand-lockup"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3 7V3h7M14 3h7v7M21 14v7h-7M10 21H3v-7"/><path d="M8 8h8v8H8z"/></svg><span>Pixora</span><span class="build-label">0.3 · {{t('app.stage')}}</span></div><div class="header-actions"><button class="secondary" :aria-expanded="showSettings" aria-controls="device-settings" @click="showSettings=!showSettings">{{t('ui.settings')}}</button><button class="primary" @click="display">{{t('config.display')}}</button></div></header>
<div class="page-heading"><div><h1>{{config.name||t('app.defaultName')}}</h1><p>{{t('ui.subtitle')}}</p></div><div class="sync-summary"><span class="connection-state" :class="{online:connected}">{{t(connected?'status.connected':'status.offline')}}</span><button class="secondary refresh-action" :disabled="busy||authBusy||config.shared" :title="t('ui.refreshHint')" @click="refreshView">{{t(busy?'ui.refreshing':'ui.refresh')}}</button></div></div>
<div class="view-toolbar"><nav :aria-label="t('ui.views')"><button v-for="view in ['overview','ai','system','developer','personal']" :key="view" :aria-pressed="activeView===view" @click="activeView=view">{{t('ui.'+view)}}</button></nav><span class="source-mode">{{t(mode==='real'?'config.real':'config.demo')}}</span></div>
<section v-if="showSettings" id="device-settings" class="settings-panel" :aria-label="t('ui.settings')"><div class="settings-heading"><h2>{{t('ui.settings')}}</h2><button class="secondary" @click="showSettings=false">{{t('ui.close')}}</button></div><p class="muted">{{t('app.privacy')}}</p><div class="settings-fields">
<label>{{t('config.name')}}<input v-model="config.name" maxlength="60" @change="save"></label>
<label>{{t('config.language')}}<select v-model="locale" @change="language"><option value="en-US" lang="en">{{t('language.english')}}</option><option value="zh-CN" lang="zh-CN">{{t('language.chinese')}}</option></select></label>
<label>{{t('config.theme')}}<select v-model="config.theme" @change="save"><option value="dark">{{t('config.dark')}}</option><option value="light">{{t('config.light')}}</option></select></label>
<label>{{t('config.layout')}}<select v-model="config.layout" @change="save"><option value="overview">{{t('config.overview')}}</option><option value="focus">{{t('config.focus')}}</option><option value="public">{{t('config.public')}}</option></select></label>
<label>{{t('config.data')}}<select v-model="mode" @change="changeMode"><option value="real">{{t('config.real')}}</option><option value="demo">{{t('config.demo')}}</option></select></label>
<label class="check-field"><input type="checkbox" v-model="config.shared" @change="share">{{t('config.shared')}}</label>
</div><div v-if="!config.shared" class="authorization-fields"><label>{{t('config.token')}}<input v-model="token" type="password" autocomplete="off" :placeholder="t('config.tokenHint')" @keyup.enter="connect"></label><label class="check-field"><input type="checkbox" v-model="rememberDevice" :disabled="authBusy||!secureSession">{{t('auth.remember')}}</label><button :disabled="busy||authBusy||(!token&&!remembered)" @click="connect">{{t('config.connect')}}</button><button class="secondary" @click="disconnect">{{t('config.disconnect')}}</button></div>
<p v-if="remembered" class="muted" role="status">{{t('auth.remembered',{time:new Date(sessionExpiry).toLocaleString(locale)})}}</p></section>
</template>
<div v-if="!connected&&!token&&!remembered" class="notice" role="status"><p>{{t('config.connectHint')}}</p><button v-if="!kiosk" class="secondary" @click="showSettings=true">{{t('ui.connectDevice')}}</button></div>
<p v-if="mode==='demo'" class="notice">{{t('data.demo')}}</p>
<p v-if="error" class="notice notice-error" role="alert">{{t(error.key,error.params||{})}}</p>
<DisplayStage :active="kiosk&&!showDisplayTools"><div class="cards"><Widget v-for="id in widgets" :key="id" :kind="id" :data="data" :connected="connected" :history="systemHistory" :history-next="historyNext" :history-error="historyError" @history="loadHistory" :clock="clock"/></div></DisplayStage>
<p v-if="kiosk" class="display-sync" :class="{'offline':!connected}">{{t(connected?'status.connected':'status.offline')}} · {{t('status.sync',{time:data?new Date(data.server_time).toLocaleTimeString(locale):t('widget.notCollected')})}}</p>
<footer v-if="!kiosk"><span>{{t('app.principle')}}</span><span>{{t('app.stage')}} · {{t('app.brand')}}</span></footer>
</main></template>
