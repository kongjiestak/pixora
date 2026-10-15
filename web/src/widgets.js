export const modes = ['ai','system','developer','personal','automation']
export const registry = {
 clock: {titleKey:'widget.clock', mode:'personal', sensitivity:'public'},
 quota: {titleKey:'widget.quota', mode:'ai', sensitivity:'private'},
 status: {titleKey:'widget.status', mode:'system', sensitivity:'public'}
}
export const presets = {focus:['clock','quota'], overview:['clock','quota','status'], public:['clock','status']}
export function visibleWidgets(layout, shared){return (presets[layout] || presets.overview).filter(id=>!shared || registry[id].sensitivity==='public')}
