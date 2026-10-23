<script setup>
import {ref,watch,computed} from 'vue'
import {useI18n} from 'vue-i18n'
import {alertSettings,loadAlerts,evaluateQuota} from './quota-alerts.js'
import {windowLabel,stamp} from './format.js'
const props=defineProps({data:Object,connected:Boolean,allowed:Boolean,open:Boolean,active:Boolean})
const emit=defineEmits(['open'])
const {t,locale}=useI18n();let storage;try{storage=window.localStorage}catch{}
const settings=ref(alertSettings()),state=ref({}),events=ref([]),saved=ref(true),unread=ref(false)
const key=computed(()=>props.allowed&&props.data?.device_id?'pixora-alerts:'+props.data.device_id:null)
watch(key,k=>{const v=k?loadAlerts(storage,k):loadAlerts(null,null);settings.value=v.settings;state.value=v.state;events.value=v.events;unread.value=false},{immediate:true,flush:'sync'})
function save(){if(!key.value)return;try{storage.setItem(key.value,JSON.stringify({version:1,settings:settings.value,state:state.value,events:events.value}));saved.value=true}catch{saved.value=false}}
function changed(){settings.value=alertSettings(settings.value);unread.value=false;save();evaluate()}
function evaluate(){
 if(!key.value||!props.connected||!props.active)return
 const result=evaluateQuota(props.data,state.value,settings.value);state.value=result.state
 if(result.events.length){events.value=[...result.events,...events.value].slice(0,20);unread.value=!props.open}save()
}
watch(()=>[props.data,props.connected,props.active,key.value],evaluate)
watch(()=>props.open,v=>{if(v)unread.value=false})
function clear(){events.value=[];unread.value=false;save()}
const line=e=>t('alerts.'+e.kind,{window:windowLabel(e.duration,t,locale.value),remaining:e.remaining})
</script>
<template>
<Teleport v-if="open&&allowed&&key" defer to="#quota-reminder-settings"><section class="settings-section" aria-labelledby="alerts-heading">
<h2 id="alerts-heading">{{t('alerts.title')}}</h2><p class="muted">{{t('alerts.scope')}}</p>
<label class="check-field"><input type="checkbox" v-model="settings.enabled" @change="changed">{{t('alerts.enable')}}</label>
<fieldset :disabled="!settings.enabled" class="alert-fields"><label>{{t('alerts.threshold')}}<input type="number" min="1" max="50" v-model.number="settings.low" @change="changed"></label><label>{{t('alerts.restore')}}<input type="number" :min="settings.low+1" max="100" v-model.number="settings.recover" @change="changed"></label><label>{{t('alerts.cooldown')}}<input type="number" min="1" max="1440" v-model.number="settings.cooldown" @change="changed"></label><label class="check-field"><input type="checkbox" v-model="settings.quiet" @change="changed">{{t('alerts.quiet')}}</label><template v-if="settings.quiet"><label>{{t('alerts.start')}}<input type="number" min="0" max="23" v-model.number="settings.start" @change="changed"></label><label>{{t('alerts.end')}}<input type="number" min="0" max="23" v-model.number="settings.end" @change="changed"></label></template></fieldset>
<p v-if="!saved" role="status">{{t('settings.unsaved')}}</p><p v-if="!events.length" class="muted">{{t('alerts.empty')}}</p><ol class="alert-history"><li v-for="event in events" :key="event.id">{{line(event)}}<small>{{stamp(event.at,locale)}}</small></li></ol><button v-if="events.length" class="secondary" @click="clear">{{t('alerts.clear')}}</button>
</section></Teleport>
<button v-else-if="allowed&&connected&&settings.enabled&&unread&&events.length" class="quota-alert-toast" @click="emit('open')" aria-live="polite">{{line(events[0])}} · {{t('alerts.view')}}</button>
</template>
<style scoped>
.alert-fields{border:0;padding:16px 0;display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px}.alert-fields label{display:flex;flex-direction:column;gap:8px}.alert-fields .check-field{flex-direction:row}.alert-history{padding-left:20px}.alert-history li{margin:12px 0}.alert-history small{display:block;color:var(--muted)}.quota-alert-toast{position:fixed;bottom:max(18px,env(safe-area-inset-bottom));left:50%;transform:translateX(-50%);z-index:50;max-width:90vw;background:var(--surface,#14252d);color:var(--ink,#f2f7f8);border:1px solid var(--accent);border-radius:24px;padding:12px 20px;font-size:14px}@media(max-width:500px){.alert-fields{grid-template-columns:1fr}}
</style>
