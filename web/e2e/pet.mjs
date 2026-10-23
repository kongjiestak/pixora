// Isolated browser acceptance; every API response here is synthetic, never production.
import https from 'node:https'
import os from 'node:os'
import {execFileSync} from 'node:child_process'
import {readFile,mkdtemp,rm} from 'node:fs/promises'
import path from 'node:path'
import assert from 'node:assert/strict'
const {chromium}=await import(process.env.PIXORA_PLAYWRIGHT_MODULE||'playwright')
const root=path.resolve('web/dist');let left=8,stamp=Date.now(),denied=false
const fixture=()=>({schema_version:1,mode:'real',device_id:'synthetic-alert-device',server_time:new Date().toISOString(),stale_after_seconds:600,providers:[{provider:'codex',source:'codex-app-server',mode:'real',status:'ok',stale:false,observed_at:new Date(stamp).toISOString(),windows:[{name:'primary',duration_minutes:300,used_percent:100-left,remaining_percent:left,resets_at:new Date(Date.now()+3600000).toISOString()}]}]})
const scratch=await mkdtemp(path.join(os.tmpdir(),'pixora-alert-e2e-'));execFileSync('openssl',['req','-x509','-newkey','rsa:2048','-nodes','-days','1','-subj','/CN=localhost','-keyout',scratch+'/key','-out',scratch+'/cert'],{stdio:'ignore'});
const server=https.createServer({key:await readFile(scratch+'/key'),cert:await readFile(scratch+'/cert')},async(req,res)=>{
 res.setHeader('Cache-Control','no-store');const url=new URL(req.url,'http://localhost')
 const json=value=>{res.setHeader('Content-Type','application/json');res.end(JSON.stringify(value))}
 if(url.pathname==='/__fixture/recovered'){left=25;stamp+=1000;return json({ok:true})}
 if(url.pathname==='/__fixture/revoked'){denied=true;return json({ok:true})}
 if(url.pathname.startsWith('/api/')){
  if(url.pathname==='/api/v1/activity')return json({source:'codex-local-events',state:'working',observed_at:Math.floor(Date.now()/1000),expires_at:Math.floor(Date.now()/1000)+15})
  if(denied){res.statusCode=401;return json({detail:'test revoked'})}
  if(url.pathname==='/api/v1/session')return json({expires_at:new Date(Date.now()+3600000).toISOString(),modes:['real']})
  if(url.pathname==='/api/v1/device')return json(fixture())
  if(url.pathname==='/api/v2/device-config')return json({device_id:'synthetic-alert-device',name:'Synthetic browser test',providers:['codex'],profile:{show_weather:false},public_only:false,revision:1})
  return json({observations:[]})
 }
 try{const file=path.join(root,url.pathname==='/'?'index.html':url.pathname);if(!file.startsWith(root+path.sep))throw Error();res.setHeader('Content-Type',file.endsWith('.js')?'application/javascript':file.endsWith('.css')?'text/css':file.endsWith('.html')?'text/html':'application/octet-stream');res.end(await readFile(file))}catch{res.statusCode=404;res.end()}
})
await new Promise(r=>server.listen(0,'127.0.0.1',r));const origin='https://127.0.0.1:'+server.address().port
let browser
try{
 browser=await chromium.launch({headless:true,...(process.env.PIXORA_CHROME?{executablePath:process.env.PIXORA_CHROME}:{})})
 const context=await browser.newContext({viewport:{width:430,height:932},locale:'en-US',serviceWorkers:'block',ignoreHTTPSErrors:true}),page=await context.newPage(),errors=[]
 page.on('pageerror',e=>errors.push(e.message))
 await page.goto(origin)
 await page.getByRole('button',{name:'Companion',exact:true}).click()
 await page.getByText('Working',{exact:true}).waitFor()
 await page.getByRole('button',{name:'Say hello',exact:true}).click()
 assert.equal(await page.locator('.pet.waving').count(),1)
 for(const viewport of [{width:430,height:932},{width:932,height:430},{width:768,height:1024}]){
  await page.setViewportSize(viewport)
  assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1))
  const pet=await page.locator('.pet-body').boundingBox(),legends=await page.locator('.orbit-legends').boundingBox()
  assert.ok(pet.x+pet.width<=legends.x+1||pet.y+pet.height<=legends.y+1||legends.y+legends.height<=pet.y+1)
 }
 await page.evaluate(()=>localStorage.setItem('pixora-locale','zh-CN'))
 await page.reload();await page.getByRole('button',{name:'伙伴',exact:true}).click()
 await page.getByText('正在工作',{exact:true}).waitFor()
 await page.screenshot({path:'/tmp/pixora-v07-pet.png'})
 await page.route('**/api/v1/activity',route=>route.fulfill({status:401,contentType:'application/json',body:'{}'}))
 await page.getByText('状态未知',{exact:true}).waitFor({timeout:8000})
 assert.equal(errors.length,0,errors.join('; '))
 console.log('PASS: synthetic activity, wave, phone/tablet orientations, bilingual labels, authorization failure -> unknown; no page errors')
}finally{await browser?.close();await new Promise(r=>server.close(r));await rm(scratch,{recursive:true,force:true})}
