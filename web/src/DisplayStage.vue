<script setup>
import {ref,onMounted,onUnmounted,watch,nextTick} from 'vue'
import {fitScale} from './fit-scale.js'
const props=defineProps({active:Boolean})
const stage=ref(),content=ref(),scale=ref(null)
let observer,frame
function update(){
 cancelAnimationFrame(frame)
 frame=requestAnimationFrame(()=>{
  const a=stage.value,b=content.value
  scale.value=props.active&&a&&b?fitScale(a.clientWidth,a.clientHeight,Math.max(b.offsetWidth,b.scrollWidth),b.scrollHeight,window.visualViewport?.scale||1):null
 })
}
watch(()=>props.active,async()=>{scale.value=null;await nextTick();update()})
onMounted(()=>{
 if('ResizeObserver' in window){observer=new ResizeObserver(update);observer.observe(stage.value);observer.observe(content.value)}
 window.addEventListener('resize',update);window.visualViewport?.addEventListener('resize',update);update()
})
onUnmounted(()=>{observer?.disconnect();cancelAnimationFrame(frame);window.removeEventListener('resize',update);window.visualViewport?.removeEventListener('resize',update)})
</script>
<template><div ref="stage" :class="{'display-stage':active,'stage-scroll':active&&scale===null,'stage-pass':!active}"><div ref="content" :class="active?'stage-content':'stage-pass'" :style="active&&scale!==null?{position:'absolute',left:'50%',top:'50%',transform:`translate(-50%,-50%) scale(${scale})`}:null"><slot/></div></div></template>
