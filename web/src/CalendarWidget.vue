<script setup>
import {ref,computed} from 'vue'
import {useI18n} from 'vue-i18n'
import {monthGrid} from './calendar.js'
const props=defineProps(['clock'])
const {t,locale}=useI18n(),offset=ref(0)
const month=computed(()=>new Date(props.clock.getFullYear(),props.clock.getMonth()+offset.value,1))
const days=computed(()=>monthGrid(month.value.getFullYear(),month.value.getMonth()))
const weekdays=computed(()=>Array.from({length:7},(_,i)=>new Date(2024,0,1+i).toLocaleDateString(locale.value,{weekday:'short'})))
const today=cell=>cell.year===props.clock.getFullYear()&&cell.month===props.clock.getMonth()&&cell.day===props.clock.getDate()
</script>
<template><article class="calendar-widget"><div class="panel-heading"><h2>{{month.toLocaleDateString(locale,{year:'numeric',month:'long'})}}</h2><div class="calendar-actions"><button class="secondary" :aria-label="t('calendar.previous')" @click="offset--">‹</button><button class="secondary" @click="offset=0">{{t('calendar.today')}}</button><button class="secondary" :aria-label="t('calendar.next')" @click="offset++">›</button></div></div><div class="month-grid" :key="month.getTime()"><span v-for="day in weekdays" :key="day" class="weekday">{{day}}</span><span v-for="(cell,i) in days" :key="i" :class="{outside:!cell.current,today:today(cell)}" :aria-current="today(cell)?'date':undefined">{{cell.day}}</span></div><p class="source-line">{{t('calendar.local')}}</p></article></template>
