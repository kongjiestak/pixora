export const remaining = (value, locale='en-US', unknown='Unknown') => Number.isFinite(value) ? new Intl.NumberFormat(locale,{style:'percent',maximumFractionDigits:0}).format(Math.max(0,Math.min(100,100-value))/100) : unknown
export const stamp = (value, locale='en-US', empty='Not collected') => value && Number.isFinite(new Date(value).getTime()) ? new Intl.DateTimeFormat(locale,{dateStyle:'medium',timeStyle:'medium'}).format(new Date(value)) : empty
export const windowLabel = (minutes, t, locale='en-US') => minutes ? t(minutes >= 1440 ? 'widget.days' : 'widget.hours',{count:new Intl.NumberFormat(locale,{maximumFractionDigits:1}).format(minutes/(minutes >= 1440 ? 1440 : 60))}) : t('widget.unknownWindow')
export const currency = (value, code, locale='en-US') => new Intl.NumberFormat(locale,{style:'currency',currency:code}).format(value)
export const isStale = (provider, data, clock) => provider.stale || !provider.observed_at || (clock-new Date(provider.observed_at))/1000 > data.stale_after_seconds || provider.windows.some(w=>w.resets_at && new Date(w.resets_at)<=clock)
export const compactReset=(value,locale='en-US',empty='Unknown')=>value&&Number.isFinite(new Date(value).getTime())?new Intl.DateTimeFormat(locale,{month:'short',day:'numeric',hour:'2-digit',minute:'2-digit'}).format(new Date(value)):empty
export const resetCountdown=(value,clock,t)=>{
 if(!value||!Number.isFinite(new Date(value).getTime()))return t('widget.unknownTime')
 const minutes=Math.max(0,Math.ceil((new Date(value)-clock)/60000))
 if(minutes>=1440)return t('widget.countdownDays',{days:Math.floor(minutes/1440),hours:Math.floor(minutes%1440/60)})
 if(minutes>=60)return t('widget.countdownHours',{hours:Math.floor(minutes/60),minutes:minutes%60})
 return t('widget.minutes',{count:minutes})
}
