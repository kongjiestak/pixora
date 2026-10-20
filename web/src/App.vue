<script setup>
import {ref, computed, watch, onMounted, onUnmounted} from 'vue'
import {useI18n} from 'vue-i18n'
import Widget from './Widget.vue'
import {visibleWidgets,displayWidgets} from './widgets.js'
import {deviceConfig, persist, preference} from './locale-core.js'
const {t,locale}=useI18n()
let storage;try{storage=window.localStorage}catch{}
const config=ref(deviceConfig(preference(storage,'pixora-device',preference(storage,'apm-device','{}'))))
const rememberDevice=ref(true),remembered=ref(false),sessionExpiry=ref(''),authBusy=ref(false),logoutPending=ref(preference(storage,'pixora-logout-pending','')==='1')
const token=ref(''),mode=ref('real'),data=ref(null),error=ref(null),connected=ref(false),busy=ref(false),clock=ref(new Date()),kiosk=ref(new URLSearchParams(location.search).has('kiosk'))
const displayLayout=ref(preference(storage,'pixora-display-layout','clock-quota')==='quota'?'quota':'clock-quota'),showDisplayTools=ref(false),wakeState=ref('idle')
const widgets=computed(()=>kiosk.value?displayWidgets(displayLayout.value,config.value.shared):visibleWidgets(config.value.layout,config.value.shared))
function saveDisplay(){persist(storage,'pixora-display-layout',displayLayout.value)}
let timer,tick,controller,wake,generation=0
function save(){persist(storage,'pixora-device',JSON.stringify(config.value))}
function language(){persist(storage,'pixora-locale',locale.value)}
watch(locale,()=>{document.documentElement.lang=locale.value;document.documentElement.dir='ltr'},{immediate:true})
function cancel(){generation++;controller?.abort();busy.value=false}
async function load(){
 if(busy.value||authBusy.value||logoutPending.value||(!token.value&&!remembered.value)||config.value.shared)return
 const current=++generation, requestedMode=mode.value
 const requestController=new AbortController();controller=requestController;busy.value=true
 const timeout=setTimeout(()=>requestController.abort(),10000)
 try{
   const r=await fetch('/api/v1/device?mode='+requestedMode,{credentials:'same-origin',headers:token.value?{Authorization:'Bearer '+token.value}:{},signal:requestController.signal})
   if(!r.ok)throw {status:r.status}
   const result=await r.json()
   if(current!==generation||config.value.shared)return
   data.value=result;connected.value=true;error.value=null
 }catch(e){if(current===generation){if(e.status===401){token.value='';remembered.value=false;sessionExpiry.value='';data.value=null}error.value=e.status===401?{key:'auth.expired'}:e.status?{key:'status.failure',params:{status:e.status}}:{key:'status.network'};connected.value=false}}
 finally{clearTimeout(timeout);if(current===generation)busy.value=false}
}
function changeMode(){cancel();data.value=null;connected.value=false;load()}
async function sessionRequest(method, headers={}){
 const abort=new AbortController(),timeout=setTimeout(()=>abort.abort(),10000)
 try{return await fetch('/api/v1/session',{method,credentials:'same-origin',headers,signal:abort.signal})}
 finally{clearTimeout(timeout)}
}
function pendingLogout(value){logoutPending.value=value;persist(storage,'pixora-logout-pending',value?'1':'')}
async function clearRemoteSession(){
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
 wakeScreen();timer=setInterval(load,30000);tick=setInterval(()=>clock.value=new Date(),1000)
 document.addEventListener('visibilitychange',wakeScreen)
 if('serviceWorker' in navigator)navigator.serviceWorker.register('/sw.js').catch(()=>{})
 const pairing=new URLSearchParams(location.hash.slice(1)),incoming=pairing.get('token')
 if(pairing.has('token'))history.replaceState(null,'',location.pathname+location.search)
 if(incoming&&/^[A-Za-z0-9_-]{32,128}$/.test(incoming)){
  token.value=incoming;mode.value='real';config.value.shared=false;save();await connect()
 }else await restoreSession()
})
onUnmounted(()=>{clearInterval(timer);clearInterval(tick);cancel();wake?.release();document.removeEventListener('visibilitychange',wakeScreen)})
</script>
<template><main :class="[config.theme,{kiosk},kiosk?'display-'+displayLayout:'']">
<div v-if="kiosk" class="display-bar"><span class="display-brand">Pixora <span>{{config.name}}</span></span><div class="display-actions"><span class="wake-status" role="status">{{t('display.wake_'+wakeState)}}</span><button class="secondary" :aria-expanded="showDisplayTools" @click="showDisplayTools=!showDisplayTools">{{t('display.settings')}}</button><button class="secondary" @click="exit">{{t('config.exit')}}</button></div></div>
<section v-if="kiosk&&showDisplayTools" class="display-tools"><label>{{t('display.layout')}}<select v-model="displayLayout" @change="saveDisplay"><option value="clock-quota">{{t('display.clockQuota')}}</option><option value="quota">{{t('display.quotaOnly')}}</option></select></label><button v-if="wakeState!=='active'" @click="wakeScreen">{{t('display.retryWake')}}</button><p>{{t('display.installHint')}}</p></section>
<header v-if="!kiosk"><div><p class="eyebrow">Pixora · {{t('app.stage')}}</p><h1>{{config.name||t('app.defaultName')}}<span>{{t('app.tagline')}}</span></h1></div><div class="options"><label>{{t('config.language')}}<select v-model="locale" @change="language"><option value="en-US" lang="en">{{t('language.english')}}</option><option value="zh-CN" lang="zh-CN">{{t('language.chinese')}}</option></select></label><button @click="kiosk?exit():display()">{{t(kiosk?'config.exit':'config.display')}}</button></div></header>
<section v-if="!kiosk" class="connection">
<label>{{t('config.name')}}<input v-model="config.name" maxlength="60" @change="save"></label>
<label>{{t('config.theme')}}<select v-model="config.theme" @change="save"><option value="dark">{{t('config.dark')}}</option><option value="light">{{t('config.light')}}</option></select></label>
<label>{{t('config.layout')}}<select v-model="config.layout" @change="save"><option value="overview">{{t('config.overview')}}</option><option value="focus">{{t('config.focus')}}</option><option value="public">{{t('config.public')}}</option></select></label>
<label><input type="checkbox" v-model="config.shared" @change="share">{{t('config.shared')}}</label>
<label v-if="!config.shared">{{t('config.token')}}<input v-model="token" type="password" autocomplete="off" :placeholder="t('config.tokenHint')" @keyup.enter="connect"></label>
<label v-if="!config.shared"><input type="checkbox" v-model="rememberDevice" :disabled="authBusy">{{t('auth.remember')}}</label>
<button :disabled="busy||authBusy||(!token&&!remembered)||config.shared" @click="connect">{{t('config.connect')}}</button><button @click="disconnect">{{t('config.disconnect')}}</button>
<label>{{t('config.data')}}<select v-model="mode" @change="changeMode"><option value="real">{{t('config.real')}}</option><option value="demo">{{t('config.demo')}}</option></select></label>
</section>
<p v-if="remembered&&!kiosk" class="muted" role="status">{{t('auth.remembered',{time:new Date(sessionExpiry).toLocaleString(locale)})}}</p>
<p v-if="!connected&&!token&&!remembered" class="warning" role="status">{{t('config.connectHint')}}</p>
<p v-if="mode==='demo'" class="warning">{{t('data.demo')}}</p>
<p v-if="error" class="warning" role="alert">{{t(error.key,error.params||{})}}</p>
<div class="cards"><Widget v-for="id in widgets" :key="id" :kind="id" :data="data" :connected="connected" :clock="clock"/></div>
<p v-if="kiosk" class="display-sync" :class="{'offline':!connected}">{{t(connected?'status.connected':'status.offline')}} · {{t('status.sync',{time:data?new Date(data.server_time).toLocaleTimeString(locale):t('widget.notCollected')})}}</p>
<footer v-if="!kiosk">{{t('app.support')}}<br>{{t('app.principle')}}<br>{{t('app.footer')}}<br>{{t('app.install')}} {{t('app.privacy')}}<br>{{t('app.brand')}}</footer>
</main></template>
