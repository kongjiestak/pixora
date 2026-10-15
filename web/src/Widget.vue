<script setup>
import {useI18n} from 'vue-i18n'
import {remaining,stamp,windowLabel,isStale} from './format.js'
const {t,locale}=useI18n()
defineProps(['kind','data','clock','connected'])
const date=value=>stamp(value,locale.value,t('widget.notCollected'))
const label=(p,data,clock,connected)=>{const state=t(!connected?'status.cached':isStale(p,data,clock)?'status.stale':p.status==='ok'?'status.fresh':'status.unavailable');return p.mode==='demo'?t('data.demoStatus',{status:state}):state}
const source=value=>t(value==='demo'?'data.sourceDemo':value==='codex-app-server'?'data.sourceCodex':'data.sourceUnavailable')
</script>
<template>
<article v-if="kind==='clock'" class="clock-widget"><p class="eyebrow">{{t('widget.personal')}}</p><h2>{{clock.toLocaleTimeString(locale,{hour:'2-digit',minute:'2-digit',second:'2-digit',hour12:false})}}</h2><p>{{clock.toLocaleDateString(locale,{weekday:'long',year:'numeric',month:'long',day:'numeric'})}}</p></article>
<article v-else-if="kind==='status'"><p class="eyebrow">{{t('widget.system')}}</p><h2>{{t(connected?'status.connected':'status.offline')}}</h2><p class="muted">{{t('status.sync',{time:date(data?.server_time)})}}</p><p>{{t('status.safe')}}</p></article>
<template v-else-if="kind==='quota'">
<article v-for="p in data?.providers || []" :key="p.provider"><div class="row"><h2>{{t('provider.'+p.provider)}}</h2><span class="badge">{{label(p,data,clock,connected)}}</span></div>
<p class="muted">{{t('widget.source',{source:source(p.source)})}} · {{t('widget.collected',{time:date(p.collected_at||p.observed_at)})}}</p>

<div v-for="w in p.windows" :key="w.name" class="window"><div class="row"><span>{{w.name}} · {{windowLabel(w.duration_minutes,t,locale)}}</span><strong>{{remaining(w.used_percent,locale,t('widget.unknown'))}} <small>{{t('widget.remaining')}}</small></strong></div><progress :value="100-w.used_percent" max="100" :aria-label="t('widget.remaining')"/><p class="muted">{{t('widget.reset',{time:date(w.resets_at)})}} · {{w.resets_at?t('widget.minutes',{count:new Intl.NumberFormat(locale).format(Math.max(0,Math.ceil((new Date(w.resets_at)-clock)/60000)))}):t('widget.unknownTime')}}</p></div>
<p v-if="(p.reason_code||p.reason) && p.mode!=='demo'" class="muted">{{t('data.'+(p.reason_code||'legacy'))}}</p></article>
<p v-if="!data" class="empty">{{t('widget.empty')}}</p>
</template>
</template>
