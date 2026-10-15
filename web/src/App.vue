<script setup>
import {ref, computed, onMounted,onUnmounted} from 'vue'
import Widget from './Widget.vue'
import {visibleWidgets} from './widgets.js'
const defaults={name:'我的信息终端',theme:'dark',layout:'overview',shared:false}
let saved={};try{saved=JSON.parse(localStorage.getItem('apm-device')||'{}')}catch{}
if(!saved||typeof saved!=='object')saved={}
const config=ref({...defaults,...saved}),token=ref(''),mode=ref('real'),data=ref(null),error=ref(''),connected=ref(false),busy=ref(false),clock=ref(new Date()),kiosk=ref(new URLSearchParams(location.search).has('kiosk'))
const widgets=computed(()=>visibleWidgets(config.value.layout,config.value.shared))
let timer,tick,controller,wake,generation=0
function save(){localStorage.setItem('apm-device',JSON.stringify(config.value))}
async function load(){
 if(busy.value||!token.value||config.value.shared)return
 const current=++generation;busy.value=true;controller=new AbortController();const timeout=setTimeout(()=>controller.abort(),10000)
 try{const r=await fetch('/api/v1/device?mode='+mode.value,{headers:{Authorization:'Bearer '+token.value},signal:controller.signal});if(!r.ok)throw Error('连接失败 '+r.status);const result=await r.json();if(current!==generation||config.value.shared)return;data.value=result;connected.value=true;error.value=''}catch(e){if(current===generation){error.value=e.message;connected.value=false}}finally{busy.value=false;clearTimeout(timeout)}
}
function disconnect(){generation++;controller?.abort();token.value='';data.value=null;connected.value=false}
function share(){if(config.value.shared)disconnect();save()}
async function exit(){kiosk.value=false;try{if(document.fullscreenElement)await document.exitFullscreen()}catch{};wake?.release()}
async function display(){kiosk.value=true;try{await document.documentElement.requestFullscreen?.()}catch{};try{wake=await navigator.wakeLock?.request('screen')}catch{}}
onMounted(()=>{timer=setInterval(load,30000);tick=setInterval(()=>clock.value=new Date(),1000);if('serviceWorker' in navigator)navigator.serviceWorker.register('/sw.js').catch(()=>{})})
onUnmounted(()=>{clearInterval(timer);clearInterval(tick);controller?.abort();wake?.release()})
</script>
<template><main :class="[config.theme,{kiosk}]">
<header><div><p class="eyebrow">AI POCKET MONITOR · V0.1</p><h1>{{config.name}}<span>让每一块屏幕，都有价值。</span></h1></div><button @click="kiosk?exit():display()">{{kiosk?'退出显示':'全屏显示'}}</button></header>
<section v-if="!kiosk" class="connection">
<label>设备名称<input v-model="config.name" maxlength="60" @change="save"></label>
<label>主题<select v-model="config.theme" @change="save"><option>dark</option><option>light</option></select></label>
<label>预设布局<select v-model="config.layout" @change="save"><option value="overview">总览</option><option value="focus">专注</option><option value="public">公共屏幕</option></select></label>
<label><input type="checkbox" v-model="config.shared" @change="share">共享屏幕（清除令牌、隐藏私人组件）</label>
<label v-if="!config.shared">只读 Token<input v-model="token" type="password" autocomplete="off" placeholder="仅保存于内存" @keyup.enter="load"></label>
<button :disabled="busy||!token||config.shared" @click="load">连接 / 刷新</button><button @click="disconnect">断开</button>
<label>数据<select v-model="mode" @change="data=null;load()"><option value="real">真实观测</option><option value="demo">演示数据</option></select></label>
</section>
<p v-if="mode==='demo'" class="warning">演示数据 · 固定模拟值，不代表任何账号真实额度</p>
<p v-if="error" class="warning">{{error}}；缓存可能已过期</p>
<div class="cards"><Widget v-for="id in widgets" :key="id" :kind="id" :data="data" :connected="connected" :clock="clock"/></div>
<footer v-if="!kiosk">AI · 系统 · 开发者 · 个人信息 · 自动化（后续扩展）<br>添加到主屏幕可独立显示；设备设置仅存本机，令牌及观测不会持久保存。</footer>
</main></template>