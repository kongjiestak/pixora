import { createI18n } from 'vue-i18n'
import en from './locales/en-US.json'
import zh from './locales/zh-CN.json'
import { resolveLocale, preference } from './locale-core.js'
let storage; try { storage = window.localStorage } catch {}
export const i18n = createI18n({legacy:false, locale:resolveLocale(preference(storage,'pixora-locale'),navigator.languages), fallbackLocale:'en-US', messages:{'en-US':en,'zh-CN':zh}})
