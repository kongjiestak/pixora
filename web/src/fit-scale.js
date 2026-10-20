// Fit the content to its available CSS viewport, never to a device model or DPR.
// If fitting would make text too small, retain readable content and allow scrolling.
export function fitScale(width,height,contentWidth,contentHeight,zoom=1){
 if(![width,height,contentWidth,contentHeight].every(n=>Number.isFinite(n)&&n>0)||Math.abs(zoom-1)>.01)return null
 const scale=Math.min(1,width/contentWidth,height/contentHeight)
 return scale>=.75?scale:null
}
