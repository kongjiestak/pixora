<script setup>
import {ref, computed, watch, onMounted, onUnmounted} from 'vue'
import {useI18n} from 'vue-i18n'
import Widget from './Widget.vue'
import {visibleWidgets} from './widgets.js'
import {deviceConfig, persist, preference} from './locale-core.js'
const {t,locale}=useI18n()
let storage;try{storage=window.localStorage}catch{}
const config=ref(deviceConfig(preference(storage,'pixora-device',preference(storage,'apm-device','{}'))))
const token=ref(''),mode=ref('real'),data=ref(null),error=ref(null),connected=ref(false),busy=ref(false),clock=ref(new Date()),kiosk=ref(new URLSearchParams(location.search).has('kiosk'))
const widgets=computed(()=>visibleWidgets(config.value.layout,config.value.shared))
let timer,tick,controller,wake,generation=0
function save(){persist(storage,'pixora-device',JSON.stringify(config.value))}
function language(){persist(storage,'pixora-locale',locale.value)}
watch(locale,()=>{document.documentElement.lang=locale.value;document.documentElement.dir='ltr'},{immediate:true})
function cancel(){generation++;controller?.abort();busy.value=false}
async function load(){
 if(busy.value||!token.value||config.value.shared)return
 const current=++generation, requestedMode=mode.value
 const requestController=new AbortController();controller=requestController;busy.value=true
 const timeout=setTimeout(()=>requestController.abort(),10000)
 try{
   const r=await fetch('/api/v1/device?mode='+requestedMode,{headers:{Authorization:'Bearer '+token.value},signal:requestController.signal})
   if(!r.ok)throw {status:r.status}
   const result=await r.json()
   if(current!==generation||config.value.shared)return
   data.value=result;connected.value=true;error.value=null
 }catch(e){if(current===generation){error.value=e.status?{key:'status.failure',params:{status:e.status}}:{key:'status.network'};connected.value=false}}
 finally{clearTimeout(timeout);if(current===generation)busy.value=false}
}
function changeMode(){cancel();data.value=null;connected.value=false;load()}
function disconnect(){cancel();token.value='';data.value=null;connected.value=false;error.value=null}
function share(){if(config.value.shared)disconnect();save()}
async function wakeScreen(){try{if(kiosk.value&&document.visibilityState==='visible')wake=await navigator.wakeLock?.request('screen')}catch{}}
async function exit(){kiosk.value=false;try{if(document.fullscreenElement)await document.exitFullscreen()}catch{};wake?.release()}
async function display(){kiosk.value=true;try{await document.documentElement.requestFullscreen?.()}catch{};wakeScreen()}
onMounted(()=>{const pairing=new URLSearchParams(location.hash.slice(1));if(pairing.has('token')){const incoming=pairing.get('token');history.replaceState(null,'',location.pathname+location.search);if(incoming&&/^[A-Za-z0-9_-]{32,128}$/.test(incoming)){token.value=incoming;mode.value='real';config.value.shared=false;load()}}timer=setInterval(load,30000);tick=setInterval(()=>clock.value=new Date(),1000);document.addEventListener('visibilitychange',wakeScreen);if('serviceWorker' in navigator)navigator.serviceWorker.register('/sw.js').catch(()=>{})})
onUnmounted(()=>{clearInterval(timer);clearInterval(tick);cancel();wake?.release();document.removeEventListener('visibilitychange',wakeScreen)})
</script>
<template><main :class="[config.theme,{kiosk}]">
<header><div><p class="eyebrow">Pixora · {{t('app.stage')}}</p><h1>{{config.name||t('app.defaultName')}}<span>{{t('app.tagline')}}</span></h1></div><div class="options"><label>{{t('config.language')}}<select v-model="locale" @change="language"><option value="en-US" lang="en">{{t('language.english')}}</option><option value="zh-CN" lang="zh-CN">{{t('language.chinese')}}</option></select></label><button @click="kiosk?exit():display()">{{t(kiosk?'config.exit':'config.display')}}</button></div></header>
<section v-if="!kiosk" class="connection">
<label>{{t('config.name')}}<input v-model="config.name" maxlength="60" @change="save"></label>
<label>{{t('config.theme')}}<select v-model="config.theme" @change="save"><option value="dark">{{t('config.dark')}}</option><option value="light">{{t('config.light')}}</option></select></label>
<label>{{t('config.layout')}}<select v-model="config.layout" @change="save"><option value="overview">{{t('config.overview')}}</option><option value="focus">{{t('config.focus')}}</option><option value="public">{{t('config.public')}}</option></select></label>
<label><input type="checkbox" v-model="config.shared" @change="share">{{t('config.shared')}}</label>
<label v-if="!config.shared">{{t('config.token')}}<input v-model="token" type="password" autocomplete="off" :placeholder="t('config.tokenHint')" @keyup.enter="load"></label>
<button :disabled="busy||!token||config.shared" @click="load">{{t('config.connect')}}</button><button @click="disconnect">{{t('config.disconnect')}}</button>
<label>{{t('config.data')}}<select v-model="mode" @change="changeMode"><option value="real">{{t('config.real')}}</option><option value="demo">{{t('config.demo')}}</option></select></label>
</section>
<p v-if="!connected&&!token" class="warning" role="status">{{t('config.connectHint')}}</p>
<p v-if="mode==='demo'" class="warning">{{t('data.demo')}}</p>
<p v-if="error" class="warning" role="alert">{{t(error.key,error.params||{})}}</p>
<div class="cards"><Widget v-for="id in widgets" :key="id" :kind="id" :data="data" :connected="connected" :clock="clock"/></div>
<footer v-if="!kiosk">{{t('app.support')}}<br>{{t('app.principle')}}<br>{{t('app.footer')}}<br>{{t('app.install')}} {{t('app.privacy')}}<br>{{t('app.brand')}}</footer>
</main></template>
