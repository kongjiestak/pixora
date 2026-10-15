// Cache only public shell files. Never cache API responses or tokens.
const CACHE='apm-shell-v1';
self.addEventListener('install',e=>{e.waitUntil((async()=>{
 const cache=await caches.open(CACHE);
 const shell=await fetch('/',{cache:'reload'});if(!shell.ok)throw Error('shell unavailable');
 const html=await shell.clone().text();await cache.put('/',shell);
 const assets=[...html.matchAll(/(?:src|href)="(\/assets\/[^"#]+)"/g)].map(m=>m[1]);
 await cache.addAll([...assets,'/manifest.webmanifest','/icon-192.png','/icon-512.png','/icon-180.png']);
 await self.skipWaiting();
})())});
self.addEventListener('activate',e=>e.waitUntil(caches.keys().then(keys=>Promise.all(keys.filter(k=>k!==CACHE).map(k=>caches.delete(k)))).then(()=>self.clients.claim())));
self.addEventListener('fetch',e=>{const u=new URL(e.request.url);if(u.origin!==location.origin||u.pathname.startsWith('/api/')||e.request.method!=='GET')return;if(u.pathname==='/'||u.pathname.startsWith('/assets/')||['/manifest.webmanifest','/icon.svg','/icon-192.png','/icon-512.png','/icon-180.png'].includes(u.pathname))e.respondWith(fetch(e.request).then(r=>{if(r.ok){const copy=r.clone();caches.open(CACHE).then(c=>c.put(e.request,copy))}return r}).catch(()=>caches.match(e.request).then(r=>r||Response.error())))});
