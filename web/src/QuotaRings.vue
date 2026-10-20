<script setup>
import {computed} from 'vue'
import {useI18n} from 'vue-i18n'
import {ringRemaining} from './calendar.js'
import {windowLabel,compactReset} from './format.js'
const props=defineProps(['windows'])
const {t,locale}=useI18n()
const rings=computed(()=>props.windows.slice(0,2).map((w,i)=>({window:w,value:ringRemaining(w.used_percent),radius:84-i*20})))
const tightest=computed(()=>{const known=rings.value.filter(r=>r.value!==null);return known.length?Math.min(...known.map(r=>r.value)):null})
const percent=value=>value===null?t('widget.unknown'):value.toLocaleString(locale.value,{maximumFractionDigits:0})+'%'
</script>
<template><div class="quota-ring-layout"><div class="ring-graphic"><svg viewBox="0 0 200 200" role="img" :aria-label="rings.map(r=>windowLabel(r.window.duration_minutes,t,locale)+': '+percent(r.value)+' '+t('widget.remaining')).join('; ')"><g v-for="(ring,i) in rings" :key="ring.window.name" :class="'ring-'+i"><circle class="ring-track" cx="100" cy="100" :r="ring.radius"/><circle v-if="ring.value!==null&&ring.value>0" class="ring-value" cx="100" cy="100" :r="ring.radius" :stroke-dasharray="`${2*Math.PI*ring.radius} ${2*Math.PI*ring.radius}`" :stroke-dashoffset="2*Math.PI*ring.radius*(1-ring.value/100)" transform="rotate(-90 100 100)"/></g><text x="100" y="100" text-anchor="middle" class="ring-number">{{percent(tightest)}}</text><text x="100" y="121" text-anchor="middle" class="ring-caption">{{t('quota.tightest')}}</text></svg></div><div class="ring-legends"><div v-for="(ring,i) in rings" :key="ring.window.name" :class="'ring-'+i"><div class="ring-legend-title"><span class="ring-dot"/>{{windowLabel(ring.window.duration_minutes,t,locale)}}</div><strong>{{percent(ring.value)}} <small>{{t('widget.remaining')}}</small></strong><p class="source-line">{{t('widget.reset',{time:compactReset(ring.window.resets_at,locale,t('widget.unknownTime'))})}}</p></div></div></div></template>
