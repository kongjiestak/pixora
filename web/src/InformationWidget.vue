<script setup>
import {useI18n} from 'vue-i18n'
import {observationExpired} from './system-format.js'
import {stamp} from './format.js'
defineProps(['provider','data','clock','connected'])
const {t,locale}=useI18n()
const label=key=>t('info.'+({'github.stars':'stars','github.open_items':'openItems','feed.items':'items','tasks.pending':'pending','tasks.completed':'completed'}[key]||'items'))
</script>
<template><article class="information-widget"><div class="panel-heading"><h2>{{t('info.'+provider)}}</h2><span class="badge">{{t('info.private')}}</span></div><p v-if="!data?.observations?.some(o=>o.provider===provider)" class="muted">{{t('info.empty')}}</p>
<section v-for="item in (data?.observations||[]).filter(o=>o.provider===provider)" :key="item.connector_id+'/'+item.entity_id">
<div class="system-target"><span>{{item.entity_id}}</span><span class="data-state">{{t(!connected?'status.cached':observationExpired(item,clock)?'system.expired':item.status==='ok'?'system.fresh':'system.unavailable')}}</span></div>
<div class="information-metrics"><div v-for="metric in item.metrics" :key="metric.key"><span>{{label(metric.key)}}</span><strong>{{metric.value===null?t('widget.unknown'):metric.value.toLocaleString(locale)}}</strong></div></div>
<ul class="information-list"><li v-for="(entry,index) in item.entries||[]" :key="index"><a v-if="entry.url" :href="entry.url" target="_blank" rel="noopener noreferrer" referrerpolicy="no-referrer">{{entry.title}}</a><span v-else>{{entry.title}}</span><small v-if="entry.detail">{{entry.detail==='pending'?t('info.pending'):entry.detail}}</small></li></ul>
<p class="source-line">{{t('system.source')}}: {{item.source}} · {{t('system.time')}}: {{stamp(item.collected_at,locale,t('widget.notCollected'))}}</p>
</section></article></template>
