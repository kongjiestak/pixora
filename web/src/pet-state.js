// Expiry and connectivity always win over a last-known working animation.
export function activityState(event,now,active){
 if(!active||!event||event.source!=='codex-local-events'||!Number.isFinite(event.observed_at)||!Number.isFinite(event.expires_at)||event.observed_at*1000>now+60000||event.expires_at*1000<=now||event.expires_at<=event.observed_at||event.expires_at-event.observed_at>15)return 'unknown'
 return ['working','idle','error'].includes(event.state)?event.state:'unknown'
}
