<script setup>
import InformationWidget from './InformationWidget.vue'
import {systemMetric,observationExpired} from './system-format.js'
import {useI18n} from 'vue-i18n'
import {remaining,stamp,windowLabel,isStale,compactReset,resetCountdown} from './format.js'
const {t,locale}=useI18n()
defineProps(['kind','data','clock','connected','history','historyNext','historyError'])
defineEmits(['history'])
const date=value=>stamp(value,locale.value,t('widget.notCollected'))
const label=(p,data,clock,connected)=>{const state=t(!connected?'status.cached':isStale(p,data,clock)?'status.stale':p.status==='ok'?'status.fresh':'status.unavailable');return p.mode==='demo'?t('data.demoStatus',{status:state}):state}
const metricValue=(item,key)=>item.metrics.find(m=>m.key===key)?.value
const source=value=>t(value==='demo'?'data.sourceDemo':value==='codex-app-server'?'data.sourceCodex':'data.sourceUnavailable')
</script>
<template>
<article v-if="kind==='clock'" class="clock-widget"><span class="clock-context">{{t('widget.personal')}}</span><h2>{{clock.toLocaleTimeString(locale,{hour:'2-digit',minute:'2-digit',second:'2-digit',hour12:false})}}</h2><p>{{clock.toLocaleDateString(locale,{weekday:'long',year:'numeric',month:'long',day:'numeric'})}}</p></article>
<InformationWidget v-else-if="['github','rss','tasks'].includes(kind)" :provider="kind" :data="data" :clock="clock" :connected="connected"/>
<article v-else-if="kind==='status'" class="status-widget"><span class="sync-context">{{t('widget.status')}}</span><h2>{{t(connected?'status.connected':'status.offline')}}</h2><p class="muted">{{t('status.sync',{time:date(data?.server_time)})}}</p><p>{{t('status.safe')}}</p></article>
<article v-else-if="kind==='system'" class="system-widget">
<div class="panel-heading"><h2>{{t('system.title')}}</h2><span class="badge">{{t('system.private')}}</span></div>
<p v-if="!data?.observations?.some(o=>o.provider==='system')" class="muted">{{t('system.empty')}}</p>
<section v-for="item in (data?.observations||[]).filter(o=>o.provider==='system')" :key="item.connector_id+'/'+item.entity_id" class="system-observation">
<div class="system-target"><span>{{item.entity_id}}</span><span class="data-state">{{t(!connected?'status.cached':observationExpired(item,clock)?'system.expired':item.status==='ok'?'system.fresh':'system.unavailable')}}</span></div>
<p class="source-line">{{t('system.source')}}: {{item.source}}</p>
<div class="system-metrics"><div v-for="[key,label] in [['cpu.used','cpu'],['memory.used','memory'],['disk.used','disk']]" :key="key"><span>{{t('system.'+label)}}</span><strong>{{systemMetric(item,key,locale,t('widget.unknown'))}}</strong><progress v-if="Number.isFinite(metricValue(item,key))" :value="metricValue(item,key)" max="100" :aria-label="t('system.'+label)"/></div></div><p class="source-line collected-line">{{t('system.time')}}: {{date(item.collected_at)}}</p>
</section>
<template v-if="data?.observations?.some(o=>o.provider==='system')">
<button class="secondary" @click="$emit('history',false)">{{t('system.history')}}</button>
<p v-if="historyError" role="status">{{t('system.error')}}</p>
<div v-if="history?.length" class="history-scroll"><table><thead><tr><th>{{t('system.time')}}</th><th>{{t('system.entity')}}</th><th class="num">{{t('system.cpu')}}</th><th class="num">{{t('system.memory')}}</th><th class="num">{{t('system.disk')}}</th></tr></thead><tbody><tr v-for="row in history" :key="row.id"><td>{{date(row.observation.collected_at)}}</td><td>{{row.observation.entity_id}}</td><td class="num" v-for="key in ['cpu.used','memory.used','disk.used']" :key="key">{{systemMetric(row.observation,key,locale,t('widget.unknown'))}}</td></tr></tbody></table></div>
<button v-if="historyNext" class="secondary" @click="$emit('history',true)">{{t('system.more')}}</button>
</template>
</article>
<template v-else-if="kind==='quota'">
<article v-for="p in data?.providers || []" :key="p.provider" class="quota-widget"><div class="panel-heading"><h2>{{t('provider.'+p.provider)}}</h2><span class="badge">{{label(p,data,clock,connected)}}</span></div>
<p class="source-line">{{t('widget.source',{source:source(p.source)})}} · {{t('widget.collected',{time:date(p.collected_at||p.observed_at)})}}</p>

<div class="quota-windows"><div v-for="w in p.windows" :key="w.name" class="window"><div class="row"><span class="window-name">{{windowLabel(w.duration_minutes,t,locale)}}</span><strong>{{remaining(w.used_percent,locale,t('widget.unknown'))}} <small>{{t('widget.remaining')}}</small></strong></div><progress :value="100-w.used_percent" max="100" :aria-label="t('widget.remaining')"/><p class="reset-line" :title="date(w.resets_at)">{{t('widget.reset',{time:compactReset(w.resets_at,locale,t('widget.unknownTime'))})}}<span class="countdown">{{resetCountdown(w.resets_at,clock,t)}}</span></p></div>
</div><p v-if="(p.reason_code||p.reason) && p.mode!=='demo'" class="muted">{{t('data.'+(p.reason_code||'legacy'))}}</p></article>
<p v-if="!data" class="empty">{{t('widget.empty')}}</p>
</template>
</template>
