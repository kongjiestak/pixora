export const supportedLocales = ['en-US', 'zh-CN']
export function resolveLocale(saved, languages = []) {
  if (supportedLocales.includes(saved)) return saved
  for (const language of languages) {
    if (/^zh(?:-|$)/i.test(language)) return 'zh-CN'
    if (/^en(?:-|$)/i.test(language)) return 'en-US'
  }
  return 'en-US'
}
export function preference(storage, key, fallback) {
  try { return storage?.getItem(key) ?? fallback } catch { return fallback }
}
export function persist(storage, key, value) {
  try { storage?.setItem(key, value) } catch { /* Storage disabled: session still works. */ }
}
export function deviceConfig(saved) {
  let v; try { v = JSON.parse(saved) } catch { v = {} }
  if (!v || typeof v !== 'object') v = {}
  return {
    name: typeof v.name === 'string' ? v.name.slice(0, 60) : '',
    theme: ['dark', 'light'].includes(v.theme) ? v.theme : 'dark',
    layout: ['focus', 'overview', 'public'].includes(v.layout) ? v.layout : 'overview',
    motion: v.motion !== false,
    quotaStyle: ['rings','bars'].includes(v.quotaStyle)?v.quotaStyle:'rings',
    shared: v.shared === true
  }
}
