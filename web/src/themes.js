import {layoutProfile} from './layout-profile.js'
export const themeNames=['orbit','paper','amoled','aurora']
export const accentNames=['mint','blue','amber','violet']
export function appearance(profile,systemDark=false){
 const p=layoutProfile(profile)
 return p.appearance==='auto'?(systemDark?'dark':'light'):p.appearance==='theme'?(p.theme==='paper'?'light':'dark'):p.appearance
}
const palettes={
 orbit:{dark:['#080f11','#eaf2ee','#99aaa5','#213330','#14211f'],light:['#f1f6f4','#182620','#53635c','#cddbd4','#e3ece7']},
 paper:{dark:['#191815','#f3ecdd','#b9b09e','#39372f','#27251f'],light:['#f4f0e7','#29271f','#656052','#d9d2c2','#e9e2d4']},
 amoled:{dark:['#000000','#f2f4f3','#aaaaaa','#292929','#171717'],light:['#f5f5f5','#202322','#5b615e','#d6dad8','#e7eae8']},
 aurora:{dark:['#0d1020','#edf0fa','#abb1cb','#2b334b','#1a2036'],light:['#f0f1fa','#252840','#5d627e','#d0d5e7','#e2e6f2']}
}
const accents={
 dark:{mint:['#8ee5bf','#8ebcdd'],blue:['#8ebcdd','#b0d9b0'],amber:['#edc776','#abc6e8'],violet:['#c2a6ef','#8bd8c1']},
 light:{mint:['#17694e','#326485'],blue:['#245f87','#306449'],amber:['#805b0a','#326485'],violet:['#714295','#1c6b55']}
}
export function themeStyle(profile,systemDark=false){
 const p=layoutProfile(profile),mode=appearance(p,systemDark)
 const [ground,ink,muted,track,raised]=palettes[p.theme][mode]
 const [accent,secondary]=accents[mode][p.accent]
 return {'--ground':ground,'--surface':ground,'--ink':ink,'--muted':muted,'--faint':muted,'--track':track,'--line':track,'--raised':raised,'--control':mode==='dark'?'#718077':'#7c8983','--accent':accent,'--secondary':secondary,'--warning':mode==='dark'?'#edc776':'#805b0a','--danger':mode==='dark'?'#f1a4a4':'#9b3535','--glow-one':accent+'24','--glow-two':secondary+'20','--type-scale':p.text_size==='large'?'1.18':'1','color-scheme':mode}
}
