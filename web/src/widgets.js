export const modes = ['ai','system','developer','personal','automation']
export const registry = {
 clock: {titleKey:'widget.clock', mode:'personal', sensitivity:'public'},
 quota: {titleKey:'widget.quota', mode:'ai', sensitivity:'private'},
 system: {titleKey:'system.title',mode:'system',sensitivity:'private'},
 github:{titleKey:'info.github',mode:'developer',sensitivity:'private'},
 rss:{titleKey:'info.rss',mode:'personal',sensitivity:'private'},
 tasks:{titleKey:'info.tasks',mode:'personal',sensitivity:'private'},
 status: {titleKey:'widget.status', mode:'system', sensitivity:'public'}
}
export const presets = {focus:['clock','quota'], overview:['clock','quota','system','github','tasks','rss','status'], public:['clock','status']}
export function visibleWidgets(layout, shared){return (presets[layout] || presets.overview).filter(id=>!shared || registry[id].sensitivity==='public')}

export function displayWidgets(layout, shared){return shared?visibleWidgets('public',true):layout==='developer'?['github']:layout==='personal'?['tasks','rss']:layout==='system'?['clock','system']:layout==='quota'?['quota']:['clock','quota']}

export function dashboardWidgets(layout,shared,view='overview'){
 const ids=visibleWidgets(['system','developer','personal'].includes(view)&&layout!=='public'?'overview':layout,shared)
 return view==='developer'?ids.filter(id=>['clock','github','status'].includes(id)):view==='personal'?ids.filter(id=>['clock','tasks','rss','status'].includes(id)):view==='ai'?ids.filter(id=>['clock','quota','status'].includes(id)):view==='system'?ids.filter(id=>['clock','system','status'].includes(id)):ids
}
