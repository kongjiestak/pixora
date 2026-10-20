// Rotation can publish several viewport sizes before WebKit settles.
export function displayViewport(win, active) {
 const root=win.document.documentElement
 let timers=[],frame
 function update(){
  if(!active())return
  const viewport=win.visualViewport
  // Preserve pinch zoom and keyboard accessibility rather than shrinking the UI.
  if(viewport && Math.abs(viewport.scale-1)>.01)return
  const height=viewport?.height||win.innerHeight
  root.style.setProperty('--display-height',`${height}px`)
 }
 function resize(){win.cancelAnimationFrame(frame);frame=win.requestAnimationFrame(update)}
 function settle(){
  timers.forEach(win.clearTimeout.bind(win));timers=[]
  if(!active())return
  for(const delay of [0,100,300,700])timers.push(win.setTimeout(()=>{
   if(!active())return
   update();win.scrollTo({top:0,left:0,behavior:'instant'})
  },delay))
 }
 win.addEventListener('resize',resize)
 win.addEventListener('orientationchange',settle)
 win.addEventListener('pageshow',settle)
 win.visualViewport?.addEventListener('resize',resize)
 settle()
 return {settle,dispose(){
  timers.forEach(win.clearTimeout.bind(win));win.cancelAnimationFrame(frame)
  win.removeEventListener('resize',resize);win.removeEventListener('orientationchange',settle)
  win.removeEventListener('pageshow',settle);win.visualViewport?.removeEventListener('resize',resize)
  root.style.removeProperty('--display-height')
 }}
}
