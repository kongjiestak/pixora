import {createApp} from 'vue'
import App from './App.vue'
import {defineAsyncComponent} from 'vue'
import {i18n} from './i18n.js'
import './style.css'
import './themes.css'
createApp(new URLSearchParams(location.search).get('admin')==='1'?defineAsyncComponent(()=>import('./Admin.vue')):App).use(i18n).mount('#app')
