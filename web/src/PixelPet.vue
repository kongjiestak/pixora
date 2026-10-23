<script setup>
import {ref,computed,watch,onUnmounted} from 'vue'
import {useI18n} from 'vue-i18n'
import {activityState} from './pet-state.js'
const props=defineProps(['token','active','motion'])
const {t}=useI18n()
const event=ref(null),now=ref(Date.now()),waving=ref(false)
const state=computed(()=>activityState(event.value,now.value,props.active))
let timer,controller,waveTimer,generation=0
function stop(){generation++;clearInterval(timer);controller?.abort();event.value=null}
async function poll(){
 if(controller)return
 const current=generation,request=new AbortController();controller=request
 const timeout=setTimeout(()=>request.abort(),4000)
 try{
  const response=await fetch('/api/v1/activity',{credentials:'same-origin',headers:props.token?{Authorization:'Bearer '+props.token}:{},signal:request.signal,cache:'no-store'})
  const value=response.ok?await response.json():null
  if(current===generation)event.value=value
 }catch{if(current===generation)event.value=null}
 finally{clearTimeout(timeout);if(controller===request)controller=null}
}
watch(()=>[props.active,props.token],()=>{stop();controller=null;if(props.active){poll();timer=setInterval(poll,5000)}},{immediate:true})
const tick=setInterval(()=>now.value=Date.now(),1000)
function wave(){waving.value=true;clearTimeout(waveTimer);waveTimer=setTimeout(()=>waving.value=false,1500)}
onUnmounted(()=>{stop();clearInterval(tick);clearTimeout(waveTimer)})
</script>
<template><div class="pet" :class="[state,{'pet-motion':motion&&active,waving:waving&&motion&&active}]">
<button class="pet-body" @click="wave" :aria-label="t('pet.wave')"><svg viewBox="0 0 160 160" role="img" :aria-label="t('pet.'+state)" shape-rendering="crispEdges">
<g fill="var(--accent)" stroke="var(--ground)" stroke-width="3"><path d="M46 25h12V15h44v10h12v10h12v54h-12v12H46V89H34V35h12z"/><path d="M58 103h44v32H91v14H73v-14H58z"/><path class="arm left" d="M55 104H43v27h13v-12h8v-15z"/><path class="arm right" d="M105 104h12v27h-13v-12h-8v-15z"/></g>
<path fill="var(--ground)" d="M48 43h64v40H48z"/><g fill="var(--ink)"><path v-if="state==='error'" d="M59 52h5v13h-5zm0 17h5v5h-5zm34-17h5v13h-5zm0 17h5v5h-5z"/><path v-else class="eyes" d="M58 52h5v5h5v5h-5v5h-5v-5h5v-5h-5zm28 12h17v5H86z"/></g><path fill="var(--ground)" d="M73 112h14v5H73z"/>
</svg></button><strong aria-live="polite">{{t('pet.'+state)}}</strong><small>{{t('pet.hint')}}</small></div></template>
<style scoped>
.pet{height:100%;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:8px}.pet-body{border:0;background:none;padding:0;width:min(80%,280px);cursor:pointer}.pet-body svg{display:block;width:100%;height:auto}.pet small{color:var(--muted);font-size:11px}.unknown svg{opacity:.45}.pet-motion.idle .eyes{animation:blink 6s step-end infinite}.pet-motion.working .left{animation:work .6s steps(2,end) infinite}.pet-motion.working .right{animation:work .6s steps(2,end) infinite reverse}.waving .right{animation:hello .3s steps(2,end) infinite!important;transform-origin:105px 106px}@keyframes blink{97%{opacity:0}}@keyframes work{50%{transform:translateY(-6px)}}@keyframes hello{50%{transform:rotate(-25deg)}}@media(prefers-reduced-motion:reduce){*{animation:none!important}}
</style>
