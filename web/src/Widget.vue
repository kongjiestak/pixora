<script setup>
import { remaining, stamp, windowLabel } from './format.js'
defineProps(['kind','data','clock','connected'])
</script>
<template>
<article v-if="kind==='clock'" class="clock-widget"><p class="eyebrow">PERSONAL · 本机时间</p><h2>{{clock.toLocaleTimeString()}}</h2><p>{{clock.toLocaleDateString(undefined,{weekday:'long',year:'numeric',month:'long',day:'numeric'})}}</p></article>
<article v-else-if="kind==='status'"><p class="eyebrow">SYSTEM · 同步状态</p><h2>{{connected?'服务已连接':'离线 / 尚未连接'}}</h2><p class="muted">最近服务同步 {{stamp(data?.server_time)}} · 30 秒轮询</p><p>此组件不包含账户额度或私人信息。</p></article>
<template v-else-if="kind==='quota'">
<article v-for="p in data?.providers || []" :key="p.provider"><div class="row"><h2>{{p.provider}}</h2><span class="badge">{{!connected?'离线缓存':p.stale?'数据过期':p.status==='ok'?'新鲜观测':'不可用'}}</span></div><p class="muted">{{p.source}} · {{stamp(p.observed_at)}}</p><div v-for="w in p.windows" :key="w.name" class="window"><div class="row"><span>{{w.name}} · {{windowLabel(w.duration_minutes)}}</span><strong>{{remaining(w.used_percent)}} <small>剩余</small></strong></div><progress :value="100-w.used_percent" max="100"/><p class="muted">重置 {{stamp(w.resets_at)}} · {{w.resets_at?Math.max(0,Math.ceil((new Date(w.resets_at)-clock)/60000))+' 分钟':'时间未知'}}</p></div><p class="muted">{{p.reason}}</p></article>
<p v-if="!data" class="empty">连接后显示真实观测；无数据时不推算额度。</p>
</template>
</template>