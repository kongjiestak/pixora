export const modes = ['ai','system','developer','personal','automation']
export const registry = {
 clock: {title:'时间与日期', mode:'personal', sensitivity:'public'},
 quota: {title:'AI 额度', mode:'ai', sensitivity:'private'},
 status: {title:'同步状态', mode:'system', sensitivity:'public'}
}
export const presets = {focus:['clock','quota'], overview:['clock','quota','status'], public:['clock','status']}
export function visibleWidgets(layout, shared){return (presets[layout] || presets.overview).filter(id=>!shared || registry[id].sensitivity==='public')}
