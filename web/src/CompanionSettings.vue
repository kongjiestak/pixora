<script setup>
import {useI18n} from 'vue-i18n'
const {t}=useI18n()
const props=defineProps(['value'])
const emit=defineEmits(['change'])
function update(key,value){emit('change',{...props.value,[key]:value})}
</script>
<template><section class="settings-section companion-settings"><h2>{{t('pet.settings')}}</h2><p class="muted">{{t('pet.settingsHint')}}</p><div class="settings-fields">
<label>{{t('pet.name')}}<input :value="value.name" maxlength="24" :placeholder="t('pet.title')" @input="update('name',$event.target.value)"></label>
<label>{{t('pet.startView')}}<select :value="value.view" @change="update('view',$event.target.value)"><option value="quota">{{t('pet.quota')}}</option><option value="pet">{{t('pet.title')}}</option></select></label>
<label>{{t('pet.behavior')}}<select :value="value.mode" @change="update('mode',$event.target.value)"><option value="auto">{{t('pet.auto')}}</option><option v-for="mode in ['idle','working','error']" :key="mode" :value="mode">{{t('pet.custom')}} · {{t('pet.'+mode)}}</option></select></label>
<label>{{t('pet.caption')}}<input :value="value.caption" maxlength="48" @input="update('caption',$event.target.value)"></label>
</div><p v-if="value.mode!=='auto'" class="muted">{{t('pet.customHint')}}</p></section></template>
