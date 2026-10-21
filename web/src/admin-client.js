import {defaultProfile,layoutProfile} from './layout-profile.js'
export function targetsFor(devices,selected){
 const ids=new Set(selected)
 return devices.filter(d=>ids.has(d.id)&&d.status==='active'&&!d.configuration_error).map(d=>({id:d.id,revision:d.revision}))
}
export function pairingUrl(origin,token){
 const url=new URL('/',origin)
 if(url.protocol!=='https:')throw new Error('HTTPS required')
 if(!/^[A-Za-z0-9_-]{32,128}$/.test(token))throw new Error('Invalid token')
 url.hash=new URLSearchParams({token}).toString()
 return url.href
}
export function errorKey(status){return status===401?'admin.expired':status===409?'admin.conflict':status===422?'admin.invalid':status===429?'admin.rate':'admin.failed'}

export function importLayout(text){
 if(text.length>16000)throw new Error('Invalid profile')
 const value=JSON.parse(text)
 if(!value||typeof value!=='object'||Array.isArray(value))throw new Error('Invalid profile')
 const normalized=layoutProfile(value)
 if(Object.keys(value).some(k=>!Object.hasOwn(defaultProfile,k)||value[k]!==normalized[k]))throw new Error('Invalid profile')
 return normalized
}
